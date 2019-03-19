import copy
import json
import nfc
import nfc.ndef
import cPickle as pickle

import buttons

class Comms(object):
    def __init__(self):
        self.PIN1 = 16
        self.b = buttons.Button(self.PIN1)

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
        self.basket_q = {}
        self.todo_q = {}
        self.done_q = {}
        self.queue_list = ["todo_q", "done_q", "basket_q"]
        self.comms = Comms()

        # FIXME: let the path to be modified
        self.dump_path = "queue_dump.json"

        print "Board init done"

    def __str__(self):
        return "Board(todo_q:{q1}, done_q{q2}, basket_q{q3})".format(q1=json.dumps(self.todo_q), q2=json.dumps(self.done_q), q3=json.dumps(self.basket_q))


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
        elif self.done_q.get(key):
            print "IN DONE"
            self.mark_todo(key)
        elif self.basket_q.get(key):
            print "In the basket"
            print self.basket_q[key]
        elif self.comms.pressed(): # if pressed, add to basket
            #TODO: pickle and store entire Message or Record object
            #self.basket_q[id] = copy.deepcopy(tag.ndef.message)
            print "add to the basket"
            self.basket_q[key] = copy.deepcopy(tag.ndef.records[0].text)
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

    def move_basket_to_todo(self):
        #TODO: might need a mutex
        self.todo_q.update(self.basket_q)
        self.basket_q = {}
        self.save_state()

    def mark_done(self, key):
        val = self.move_item(key, self.todo_q, self.done_q)
        print "\t{d}: {v} - DONE".format(d=key, v=val)

    def mark_todo(self, key):
        val = self.move_item(key, self.done_q, self.todo_q)
        print "\t{d}: {v} - TODO".format(d=key, v=val)


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
        clf = start_reader()
        try:
            board.start()
            print "start loop"
            while True:
                #tag = clf.connect(rdwr={'on-connect': lambda tag: False})
                clf.connect(rdwr={'on-connect': board.find_item})
                #clf.connect(rdwr={'on-connect': test_pn532})

            #print tag.ndef.records
            #nfc.ndef.Record
        except Exception as e:
            print e
        finally:
            #FIXME: make sure it's run on SIGKILL
            clf.close()
            board.save_state()
    finally:
        #FIXME: repalce this with sys.exceptionhook in buttons
        buttons.cleanup()


if __name__ == "__main__":
    run()
