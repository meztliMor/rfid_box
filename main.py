import copy
import json
import nfc
import ndef
import nfc.ndef
from multiprocessing import Process, Lock, Queue, Event, Manager
from Queue import Empty as QueueEmpty
import time
import re
import argparse

import buttons
from email_client import Email
import RPi_I2C_driver as i2c_lcd
from keep_client import Keep as Keep

import logging
LOG_FORMAT = "%(process)d %(levelname)s:%(name)s:%(funcName)s %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
log = logging.getLogger(__name__)

#import pdb
#import traceback

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
        self.todo_q = {}
        self.done_q = {}
        # TODO: this needs to be dumped to file or fetched from keep
        self.keep_q = {}

        self.keep = Keep(Email())

        #TODO add basket to the file dump
        self.basket = sm_manager.list()
        self.queue_list = ["todo_q", "done_q", "keep_q"]
        self.q_mutex = Lock()
        self.comms = Comms()
        self.dump_path = "queue_dump.json"

        log.debug("Board ctor finished")

    def __str__(self):
        #TODO: mutex for basket - check if it doesnt deadlock with mutex
        #with self.q_mutex:
        return "Board(todo_q:{q1}, done_q{q2}, basket{s1})".format(q1=json.dumps(self.todo_q), q2=json.dumps(self.done_q), l1=json.dumps(self.basket))

    def add_to_basket(self, tasks):
        clean_tasks = [x.strip() for x in tasks]
        with self.q_mutex:
            self.basket.extend(clean_tasks)
            log.debug("%s", tasks)
            self.save_state()
        self.comms.lcd_evt.set()

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
                # TODO fix __str__ and use it instead -- or no, could deadlock
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
        log.debug("tag ID:%s", str(key))

        if self.comms.pressed():
            # create task from basket
            self.create_task(key, tag)
        elif self.todo_q.get(key):
            #TODO: check if someone messed with tags
            log.debug("In TODO")
            self.mark_done(key)
        elif self.done_q.get(key):
            log.debug("In DONE")
            self.mark_todo(key)
        else: #ignore
            log.debug("ignoring new tag")
            self.comms.show_text(["Empty tag", "Press btn to add"])
        
        return True # wait for the removal of tag

    # FIXME: holding mutex for too long?
    def _add_to_todo(self, key, tag):
        log.debug("tag: %s", tag)
        val = copy.deepcopy(tag.ndef.records[0].text)
        # TODO: check if in other queue and delete
        self.todo_q[key] = val 
        log.debug("\t{d}: {v} - create TODO".format(d=key, v=val))

        self._add_to_keep(key, val)
        self.save_state()

        #TODO: should not this be called when mutex is unlocked?
        self.comms.show_text([val, "TODO"])

    def _add_to_keep(self, key, val, label=None, color=None):
        if label is None:
            label = self.keep.t_label

        log.debug("create note")
        note = self.keep.create_note(val, label=label, color=color)
        self.keep_q[key] = note.id

    #TODO: move bulk create to Keep
    def save_all_to_keep(self):
        # would be better to sync only once rather than after each
        for k, v in self.todo_q.iteritems():
            self._add_to_keep(k, v)

        for k, v in self.done_q.iteritems():
            self._add_to_keep(k, v, self.keep.d_label, self.keep.green)

    def clear_orphans_keep(self):
        # clear orphans
        ids = self.keep_q.viewitems()
        print ids
        #for n in self.keep.k.all():
        #    if n.id not in ids:
        #        n.delete()
        #self.keep.k.sync()

    def _move_item(self, key, queue_a, queue_b):
        # TODO: should it check for duplicates? and missing values?
        queue_b[key] = queue_a.pop(key)
        self.save_state()
        return queue_b[key]

    def mark_done(self, key):
        val = None
        with self.q_mutex:
            val = self._move_item(key, self.todo_q, self.done_q)
        self.comms.show_text([val, "DONE"])

        # TODO: update keep
        #notes = self.keep.find_notes(self.keep.d_label, val)
        #self.keep.to_done(notes)

        # FIXME: assert here or something
        id = self.keep_q[key]
        note = self.keep.k.get(id)
        self.keep.to_done([note])

        log.debug("\t{d}: {v} - DONE".format(d=key, v=val))

    def mark_todo(self, key):
        val = None
        with self.q_mutex:
            val = self._move_item(key, self.done_q, self.todo_q)
        self.comms.show_text([val, "TODO"])
        # TODO: update keep
        #notes = self.keep.find_notes(self.keep.t_label, val)
        #self.keep.to_todo(notes)

        id = self.keep_q[key]
        note = self.keep.k.get(id)
        self.keep.to_todo([note])

        log.debug("\t{d}: {v} - TODO".format(d=key, v=val))

    def _delete_task(self, key):
        def delitem(d, key):
            if key in d:
                del d[key]
        delitem(self.todo_q, key)
        delitem(self.done_q, key)
        
        to_delete = self.keep_q.pop(key, None)
        if to_delete is not None: 
            self.keep.delete_note(to_delete)

        #self.save_state()

    def create_task(self, key, tag):
        #log.debug("wait for q_mutex")
        with self.q_mutex:
            if len(self.basket):
                log.debug("basket: %s", self.basket)
                self._delete_task(key)
                #print "Has changed", tag.ndef.has_changed
                if self._write_tag(tag):
                    # does it ever change?
                    #print "Has changed", tag.ndef.has_changed
                    self._add_to_todo(key, tag)

            else:
                log.debug("cannot create task from empty basket")

    def _write_tag(self, tag):
        # FIXME: sort out return values
        log.debug("%s", tag)

        if tag.ndef is None:
            log.info("This is not an NDEF Tag.")
            return False

        if not tag.ndef.is_writeable:
            log.info("This Tag is not writeable.")
            return False

        new_msg = None

        task = self.basket[0]
        new_msg = self.create_msg([task])

        if new_msg is None:
            log.warning("Msg is empty")
            return False

        if new_msg == tag.ndef.message:
            log.warning("The Tag already contains the message to write.")

        if len(str(new_msg)) > tag.ndef.capacity:
            log.warn("The new message exceeds the Tag's capacity.")
            return False

        try:
            log.debug("Old message: %s", tag.ndef.message.pretty())
            tag.ndef.message = new_msg
        except Exception as e:
            log.error(e)
            return False

        self.basket.pop(0)
        log.debug("New message: %s", tag.ndef.message.pretty())
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

    def next_new_task(self):
        with self.q_mutex:
            if len(self.basket):
                return self.basket[0]
            return None

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
    email = Email()
    while True:
        #log.debug("check email")
        result = email.get_from_gmail()
        if len(result):
            tasks = re.split(",|;|\r\n", result[0])
            log.debug("tasks: %s", tasks)
            board.add_to_basket(tasks)
        time.sleep(poll_interval)

def screen_loop(board):
    lcd = board.comms.lcd
    def show_mode(mode):
        lcd.lcd_clear()
        if mode:
            task = board.next_new_task()
            if task is not None:
                lcd.lcd_display_string("Create tag:", 1)
                lcd.lcd_display_string(task, 2)
            else:
                lcd.lcd_display_string("Queue is empty", 1)
                lcd.lcd_display_string("Add tasks via @", 2)
        else:
            lcd.lcd_display_string("Ready to read", 1)

        
    log.debug("start lcd loop")
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
            m, lines, dur = board.comms.lcd_mq.get_nowait()
        except QueueEmpty as e:
            #traceback.print_exc()
            dur = None
        else:
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
    # FIXME: handle SIGINT ??

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    mg = parser.add_mutually_exclusive_group()
    mg.add_argument("--main", default=True, action="store_true", help="Default mode that launches the main program.")
    mg.add_argument("--dbg-email", action="store_true")
    mg.add_argument("--clear-keep", action="store_true")
    mg.add_argument("--save-to-keep", action="store_true")
    args = parser.parse_args()
    if args.main:
        run()
    elif args.save_to_keep:
        board = Board()
        board.load_state()
        board.save_all_to_keep()
        board.clear_orphans_keep()
        board.save_state()
    elif args.clear_keep:
        board = Board()
        board.keep.delete_all()
    elif args.dbg_email: # test email loop
        board = Board()
        board.load_state()
        email_loop(board)

