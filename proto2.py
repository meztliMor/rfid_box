import copy
import json
import nfc
import ndef
import nfc.ndef

from multiprocessing import Process, Lock, Queue, Event, Manager
from Queue import Empty as QueueEmpty
import time
import re

import buttons
import read_email as email
import i2c_lcd
#from ../denis_lcd/RPi_I2C_driver as i2c_lcd

import logging
#LOG_FORMAT = "(%threadName)-9s %(message)s"
#logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("proto")
import pdb
import traceback

# should move to main?
sm_manager = Manager()

class Comms(object):
    def __init__(self):
        self.PIN1 = 16
        self.b = buttons.Button(self.PIN1, cb=self.set_btn_evt)
        self.lcd = i2c_lcd.lcd(0x3f)
        self.lcd.lcd_clear()
        self.lcd_mq = Queue()
        self.lcd_evt = Event()

    def set_btn_evt(self, val):
        self.lcd_evt.set()

    def show_text(self, text=None, dur=2):
        cmd = None
        mode = 1
        lines = []
        for i, t in enumerate(text):
            lines.append((t, i+1))
            
        cmd = (mode, lines, dur)
        self.lcd_mq.put(cmd)
        self.lcd_evt.set()

    def pressed(self):
        return self.b.pressed()

    def start(self):
        self.b.start()
        log.debug("button started")


class Board(object):
    def __init__(self):
        # TODO probably need two mutexes
        self.staging_q = {}
        self.todo_q = {}
        self.done_q = {}

        #TODO add basket to the file dump
        self.basket = sm_manager.list()
        #self.queue_list = ["todo_q", "done_q", "staging_q", "basket"]
        self.queue_list = ["todo_q", "done_q", "staging_q"]
        self.q_mutex = Lock()
        self.comms = Comms()

        # TODO: let the path to be modified
        self.dump_path = "queue_dump.json"

        log.debug("Board ctor finished")

    def __str__(self):
        #TODO: mutex for basket
        return "Board(todo_q:{q1}, done_q{q2}, staging_q{q3}, basket{s1})".format(q1=json.dumps(self.todo_q), q2=json.dumps(self.done_q), q3=json.dumps(self.staging_q), l1=json.dumps(self.basket))

    def add_to_basket(self, tasks):
        clean_tasks = [x.strip() for x in tasks]
        with self.q_mutex:
            #self.basket.update(clean_tasks)
            self.basket.extend(clean_tasks)
            #log.debug("Add to basket", tasks)
            print "Basket: " + str(self.basket)
            self.save_state()

    def start(self):
        self.comms.start()

    def save_state(self):
        with open(self.dump_path, "w") as f:
            state = {k: getattr(self, k) for k in self.queue_list}
            print state
            json.dump(state, f)

    def load_state(self):
        # modified version of a function found in https://stackoverflow.com/questions/45068797/how-to-convert-string-int-json-into-real-int-with-json-loads/45069099
        def _conv_to_int(o):
            # Note the "unicode" part is only for python2
            if isinstance(o, str) or isinstance(o, unicode):
                try:
                    return int(o)
                except ValueError:
                    return o
            elif isinstance(o, dict):
                return {_conv_to_int(k): _conv_to_int(v) for k, v in o.items()}
            #elif isinstance(o, list):
            #    return [_conv_to_int(v) for v in o]
            else:
                return o

        try:
            with open(self.dump_path, "r") as f:
                state = json.load(f, object_hook=_conv_to_int)
                # TODO fix __str__ and use it instead
                log.debug("Board's state:\n" + json.dumps(state, indent=4))
                with self.q_mutex:
                    for k in self.queue_list:
                        setattr(self, k, state[k])
        except (IOError, ValueError) as e:
            self.clear_queues()

    def clear_queues(self):
        for k in self.queue_list:
            setattr(self, k, {})

    def find_item(self, tag):
        key = get_tag_id(tag)
        print "find_item " + str(key)

        if self.comms.pressed():
            # create task from basket
            self.create_task(key, tag)
        elif self.todo_q.get(key):
            #TODO: check if someone messed with tags
            log.debug("In TODO")
            self.mark_done(key)
            self.comms.show_text([self.done_q[key], "DONE"])
        elif self.done_q.get(key):
            log.debug("In DONE")
            self.mark_todo(key)
            self.comms.show_text([self.todo_q[key], "TODO"])
        elif self.staging_q.get(key):
            print "In the staging"
            print self.staging_q[key]
        else: #ignore
            print "Button not pressed: ignoring"
        
        return True # wait for the removal of tag

    def _move_item(self, key, queue_a, queue_b):
        # TODO: should it check for duplicates? and missing values?
        #TODO: might need a mutex
        queue_b[key] = queue_a.pop(key)
        self.save_state()
        return queue_b[key]

    def move_staging_to_todo(self):
        with self.q_mutex:
            self.todo_q.update(self.staging_q)
            self.staging_q = {}
            self.save_state()

    def _make_todo(self, key): # rename
        val = None
        val = self._move_item(key, self.staging_q, self.todo_q)
        print "\t{d}: {v} - make TODO".format(d=key, v=val)

    def mark_done(self, key):
        val = None
        with self.q_mutex:
            val = self._move_item(key, self.todo_q, self.done_q)
        print "\t{d}: {v} - DONE".format(d=key, v=val)

    def mark_todo(self, key):
        val = None
        with self.q_mutex:
            val = self._move_item(key, self.done_q, self.todo_q)
        print "\t{d}: {v} - TODO".format(d=key, v=val)

    def _delete_task(self, key):
        def delitem(d, key):
            if key in d:
                del d[key]
        delitem(self.todo_q, key)
        delitem(self.done_q, key)
        delitem(self.staging_q, key)
        #self.save_state()

    def create_task(self, key, tag):
        print "Wait for qmutex"
        with self.q_mutex:
            print "basket:", self.basket
            if len(self.basket):
                self._delete_task(key)
                print "Has changed", tag.ndef.has_changed
                if self.write_tag(tag):
                    # does it ever change?
                    print "Has changed", tag.ndef.has_changed
                    # TODO: delete staging_q
                    self.add_to_staging(key, tag)
                    self._make_todo(key)
                    self.save_state()

    def add_to_staging(self, key, tag):
        print "add to staging"
        self.staging_q[key] = copy.deepcopy(tag.ndef.records[0].text)

    def write_tag(self, tag):
        # FIXME: sort out return values
        print "IN write_tag"

        if tag.ndef is None:
            print "This is not an NDEF Tag."
            return False

        if not tag.ndef.is_writeable:
            print "This Tag is not writeable."
            return False

        task = None
        new_msg = None

        task = self.basket[0]
        new_msg = self.create_msg([task])

        if new_msg is None:
            print "Msg is empty"
            return False

        if new_msg == tag.ndef.message:
            print "The Tag already contains the message to write."

        if len(str(new_msg)) > tag.ndef.capacity:
            print "The new message exceeds the Tag's capacity."
            return False

        try:
            print "Old message:", tag.ndef.message.pretty()
            tag.ndef.message = new_msg
        except Exception as e:
            print e
            return False

        self.basket.pop(0)
        print "New message:"
        print tag.ndef.message.pretty()
        print "Written"
        return True

    def create_msg(self, tasks):
        print "create msg"
        new_msg = nfc.ndef.Message()
        for t in tasks:
            new_msg.append(self.create_record(t))
        print "msg made"
        return new_msg

    def create_record(self, t): 
        rec = nfc.ndef.TextRecord(text=t)
        #msg = nfc.ndef.Message()
        #msg.append(rec)
        print rec
        return rec

def start_reader():
    clf = nfc.ContactlessFrontend('tty:serial0:pn532')
    return clf

def get_tag_id(tag):
    # convert tag's ID (bytearray) to int
    return int(tag.identifier.encode("hex"), 16)


def email_loop(board):
    poll_interval = 20
    log.debug("start email loop")
    # TODO: add graceful termination
    while True:
        log.debug("check email")
        result = email.get_from_gmail()
        if len(result):
            tasks = re.split(",|;|\r\n", result[0])
            print "tasks: ", tasks
            board.add_to_basket(tasks)
        time.sleep(poll_interval)

def screen_loop(board):
    lcd = board.comms.lcd
    def show_mode(mode):
        lcd.lcd_clear()
        if mode:
            lcd.lcd_display_string("Create tag:", 1)
            lcd.lcd_display_string("<task>", 2)
        
    log.debug("Start lcd loop")
    lcd.lcd_clear()
    lcd.lcd_display_string("Starting-up", 1)
    lcd.lcd_display_string("board", 2)
    time.sleep(2)
    show_mode(board.comms.pressed())

    dur = None
    while True:
        # if dur is None and timed out then waited == False
        waited = board.comms.lcd_evt.wait(dur) # waited
        board.comms.lcd_evt.clear() # waited
        if dur is not None and waited:
            log.debug("evt waited for {t}".format(t=dur))
        elif not waited:
            log.debug("evt timed out")
        else:
            log.debug("evt obtained")

        show_mode(board.comms.pressed())

        try:
            #mode, cmds, dur = board.comms.lcd_mq.get()
            m, lines, dur = board.comms.lcd_mq.get_nowait()
        except QueueEmpty as e:
            #traceback.print_exc()
            dur = None
        else:
            # can I clear only one line easily?
            lcd.lcd_clear()
            for text, idx in lines:
                lcd.lcd_display_string(text, idx)

def run():
    try:
        board = Board()
        board.load_state()
        email_p = Process(target=email_loop, args=(board,))
        screen_p = Process(target=screen_loop, args=(board,))

        clf = start_reader()
        try:
            board.start()
            screen_p.start()
            email_p.start()
            # TODO: maybe move board to another process
            log.debug("start main loop")
            run = True
            while run:
                # TODO: need to handle bad tag reads
                run = clf.connect(rdwr={'on-connect': board.find_item})
        except Exception as e:
            print e
        finally:
            #FIXME: make sure it's run on SIGKILL
            clf.close()
            board.save_state()
            email_p.join()
    finally:
        #FIXME: replace this with sys.exceptionhook in buttons
        buttons.cleanup()

if __name__ == "__main__":
    # FIXME: use this to handl SIGINT
    if 1:
        run()
    else: # test email loop
        board = Board()
        board.load_state()
        email_loop(board)

