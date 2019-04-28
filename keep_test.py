import gkeepapi as gk
import ConfigParser, os
from read_email import Email as Email
import pdb

#TODO: move to Keep    
DONE_label = "DONE"
TODO_label = "TODO"

class Keep(object):
    def __init__(self, em): 
        self.k = gk.Keep()
        self.k.login(em.cfg.from_email, em.cfg.from_pwd)
        self.t_label = self.find_create_label(TODO_label)
        self.d_label = self.find_create_label(DONE_label)

    def create_note(self, title, text="", label=None):
        note = self.k.createNote(title, text)

        #note.pinned = True
        note.color = gk.node.ColorValue.Red
        if label:
            note.labels.add(label)

        print note.title
        print note.text
        # TODO: should the sync be done here?
        return note

    def find_by_label(self, label):
        notes = []
        if label:
            notes = self.k.find(labels=[label]) 
            #print [n.title + " // " + n.text + " // " + n.id for n in notes]
        return notes

    def find_notes(self, label, title):
        notes = self.find_by_label(label)
        res = []
        for n in notes:
            # TODO: it would be better to filter by id
            if n.title == title:
                print "found match - ", n.title, title
                res.append(n)
        return res

    def find_create_label(self, name):
        label = self.k.findLabel(name)
        if label is None:
            label = self.k.createLabel(name)
            # TODO: should the sync be done here?
            self.k.sync()
        return label

    def test_create(self):
        l = self.t_label
        self.create_note("Clean bedroom", label=l)
        self.create_note("Clean kitchen", label=l)
        self.create_note("But veg", label=l)
        self.k.sync()

    def relabel(self, note, old_label, new_label):
        if note.labels.get(old_label.id) != None:
            note.labels.remove(old_label)
        note.labels.add(new_label)

    def to_todo(self, notes):
        self.to_other(notes, self.d_label, self.t_label, gk.node.ColorValue.Red)
        self.k.sync()

    def to_done(self, notes):
        self.to_other(notes, self.t_label, self.d_label, gk.node.ColorValue.Green)
        self.k.sync()

    def to_other(self, notes, old_label, new_label, color):
        for n in notes:
            self.relabel(n, old_label, new_label)
            n.color = color

if __name__ == "__main__":
    em = Email()
    #keep = gk.Keep()
    #keep.login(em.cfg.from_email, em.cfg.from_pwd)
    #t_label = find_create_label(keep, TODO_label)
    #d_label =  find_create_label(keep, DONE_label)
    #print t_label, d_label
    #test_create(keep)
    #find_by_label(keep, t_label)
    kk = Keep(em)
    notes = kk.find_notes(kk.d_label, u"Clean bedroom")
    kk.to_todo(notes)
    #print notes


