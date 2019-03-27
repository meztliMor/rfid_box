import copy
import json
import nfc
import ndef
#import nfc.ndef
#import cPickle as pickle
from multiprocessing import Process, Lock, Condition
import time

import buttons
import read_email as email

#from ../denis_lcd/RPi_I2C_driver as i2c_lcd
import i2c_lcd

#import logging as log
#log.basicConfig(level=logging.DEBUG, format="(%threadName)-9s %(message)s",)

class Comms(object):
    def __init__(self):
        self.PIN1 = 16
        self.b = buttons.Button(self.PIN1)
        self.lcd = i2c_lcd.lcd(0x3f)
        self.lcd.lcd_clear()
        self.lcd.lcd_display_string("TEST",1)

    def pressed(self):
        val = self.b.pressed()
        print "Pressed: " + str(val)
        return val

    def start(self):
        self.b.start()
        print "button started"


class Board(object):
    def __init__(self):
        # TODO: load saved queues
        self.staging_q = {} # while need a mutex
        self.todo_q = {}
        self.done_q = {}
        #TODO add basket to the file dump
        #TODO: use ordered set
        self.basket = set()
        self.queue_list = ["todo_q", "done_q", "staging_q"]
        self.q_mutex = Lock()
        self.comms = Comms()

        # FIXME: let the path to be modified
        self.dump_path = "queue_dump.json"

        print "Board init done"

    def __str__(self):
        #TODO: mutex for basket
        return "Board(todo_q:{q1}, done_q{q2}, staging_q{q3}, basket{s1})".format(q1=json.dumps(self.todo_q), q2=json.dumps(self.done_q), q3=json.dumps(self.staging_q), l1=json.dumps(list(self.basket)))

    def add_to_basket(self, tasks):
        clean_tasks = [x.strip() for x in tasks]
        with self.q_mutex:
            self.basket.update(clean_tasks)
            print "Basket: " + str(self.basket)

    def start(self):
        self.comms.start()

    def save_state(self):
        with open(self.dump_path, "w") as f:
            state = {k: getattr(self, k) for k in self.queue_list}
            print state
            json.dump(state, f)
            #json.dump({k: getattr(self, k) for k in self.queue_list}, f)

    def load_state(self):
        def _conv_to_int(o):
            # modified version of a function found in https://stackoverflow.com/questions/45068797/how-to-convert-string-int-json-into-real-int-with-json-loads/45069099
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
                print state
                for k in self.queue_list:
                    setattr(self, k, state[k])
        except (IOError, ValueError) as e:
            self.clear_queues()

    def clear_queues(self):
        for k in self.queue_list:
            setattr(self, k, {})

    def find_item(self, tag):
        key = get_tag_id(tag)
        print "find item " + str(key)
        # TODO: check if the task changes?
        if self.todo_q.get(key):
            print "In TODO"
            self.mark_done(key)
            #FIXME: just testing move to another process
            self.comms.lcd.lcd_clear()
            self.comms.lcd.lcd_display_string(self.done_q[key], 1)
            self.comms.lcd.lcd_display_string("DONE", 2)
        elif self.done_q.get(key):
            print "IN DONE"
            self.mark_todo(key)
            #FIXME: just testing move to another process
            self.comms.lcd.lcd_clear()
            self.comms.lcd.lcd_display_string(self.todo_q[key], 1)
            self.comms.lcd.lcd_display_string("TODO", 2)
        elif self.staging_q.get(key):
            print "In the staging"
            print self.staging_q[key]
        elif self.comms.pressed(): # if pressed, add to staging
            ##TODO: pickle and store entire Message or Record object
            ##self.staging_q[key] = copy.deepcopy(tag.ndef.records[0].text)
            #self.add_to_staging(key, tag.ndef.records)
            
            print "Write to tag: ", self.basket
            if len(self.basket):
                self.write_tag(tag)
                self.save_state()
        else: #ignore
            print "Button not pressed: ignoring"
        
        return True

    def move_item(self, key, queue_a, queue_b):
        # TODO: should it check for duplicates? and missing values?
        #TODO: might need a mutex
        queue_b[key] = queue_a.pop(key)
        self.save_state()
        return queue_b[key]

    def move_staging_to_todo(self):
        #TODO: might need a mutex
        self.todo_q.update(self.staging_q)
        self.staging_q = {}
        self.save_state()

    def mark_done(self, key):
        val = self.move_item(key, self.todo_q, self.done_q)
        print "\t{d}: {v} - DONE".format(d=key, v=val)

    def mark_todo(self, key):
        val = self.move_item(key, self.done_q, self.todo_q)
        print "\t{d}: {v} - TODO".format(d=key, v=val)

    def add_to_staging(self, key, records):
        print "add to the staging"
        self.staging_q[key] = copy.deepcopy(tag.ndef.records[0].text)

    ######
    # FIXME: sort out return values
    def write_tag(self, tag):
        record = None
        task = None
        try:
            # TODO: if writing fails add the task back
            task = self.basket.pop()
            # TODO: do this when adding to the basket
            record = self.create_record(task)
        except Exception as e:
            print e
            return True
        # TODO: should can it format tags too?
        if tag.ndef is not None:
            key = get_tag_id(tag)
            tag.ndef.records = [record,]
            if tag.ndef.has_changed:
                # figure out how this works
                print "Write succeful?"
                # TODO: pass the string only
            self.add_to_staging(key, tag.ndef.records)
        return True

    def create_record(self, t): 
        #rec = nfc.ndef.Record("urn:nfc:wkt:T", "task", data=b"en{task}".format(task=t))
        rec = ndef.Record("urn:nfc:wkt:T", data=b"en{task}".format(task=t))
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

def test_pn532(tag):
    print tag
    return True

def run():
    try:
        board = Board()
        board.load_state()
        email_p = Process(target=email_loop, args=(board,))

        clf = start_reader()
        try:
            email_p.start()
            # TODO: move board to another process
            board.start()
            board.add_to_basket(["Wash dishes"])
            print "start loop"
            run = True
            while run:
                #tag = clf.connect(rdwr={'on-connect': lambda tag: False})
                #clf.connect(rdwr={'on-connect': test_pn532})
                # TODO: need to handle bad tag reads
                run = clf.connect(rdwr={'on-connect': board.find_item})

            #print tag.ndef.records
            #nfc.ndef.Record
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

def email_loop(board):
    poll_interval = 60
    # TODO: add graceful termination
    while True:
        print "check email"
        tasks = email.get_from_gmail()
        if len(tasks):
            print "tasks: ", tasks
            #TODO: handle lists of tasks
            board.add_to_basket(tasks)
        time.sleep(poll_interval)

# FIMXE: clashes with nfcpy
#RUN = True
#import signal
#def exit_gracefully():
#    RUN = False
#    signal.signal(signal.SIGINT, orignal_sigint)
#
#orignal_sigint = signal.getsignal(signal.SIGINT)
#signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == "__main__":
    # FIXME: use this to handl SIGINT
    run()

