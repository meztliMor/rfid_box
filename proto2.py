import nfc
import nfc.ndef
import copy
import buttons

class Comms(object):
    def __init__(self):
        self.PIN1 = 16
        self.b = buttons.Button(self.PIN1)
        self.b.start()
        print "button started"

    def pressed(self):
        val = self.b.pressed()
        print "Pressed: " + str(val)
        return val


class Board(object):
    def __init__(self):
        # TODO: load saved queues
        self.basket_q = {}
        self.todo_q = {}
        self.done_q = {}

        self.comms = Comms()
        print "Board init done"

    def find_item(self, tag):
        key = get_tag_id(tag)
        print "find item " + str(key)
        # TODO: check if the task changes?
        if self.todo_q.get(id):
            self.mark_done(id)
        elif self.done_q.get(id):
            self.mark_todo(id)
        elif self.basket_q.get(id):
            print "In the basket"
            print self.basket_q[id]
        elif self.comms.pressed(): # if pressed, add to basket
            print "add to the basket"
            self.basket_q[id] = copy.deepcopy(tag.ndef.message)
        else: #ignore
            print "Button not pressed: ignoring"
        return True

    def move_item(self, id, queue_a, queue_b):
        val = queue_a[id]
        # use dict.pop instead?
        del queue_a[id]
        queue_b[id] = val
        return val

    def mark_done(self, id):
        val = move_item(id, self.todo_q, self.done_q)
        print "\t{d}: {v} - DONE".format(d=id, v=val)

    def mark_todo(self, id):
        move_item(id, self.done_q, self.todo_q)
        print "\t{d}: {v} - TODO".format(d=id, v=val)


def start_reader():
    clf = nfc.ContactlessFrontend('tty:serial0:pn532')
    return clf

def get_tag_id(tag):
    # convert tag's ID (bytearray) to int
    return int(tag.identifier.encode("hex"), 16)

def test_pn532(tag):
    print tag
    return True

if __name__ == "__main__":
    try:
        board = Board()
        clf = start_reader()
        try:
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
    finally:
        #FIXME: repalce this with sys.exceptionhook in buttons
        buttons.cleanup()


