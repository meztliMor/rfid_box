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
        self.red = gk.node.ColorValue.Red
        self.green = gk.node.ColorValue.Green

    def create_note(self, title, text="", label=None, color=None):
        if label is None:
            label = self.t_label
        note = self.k.createNote(title, text)
        #note.pinned = True

        if color is None:
            color = gk.node.ColorValue.Red
        note.color = color

        if label:
            note.labels.add(label)

        print note.title
        print note.text
        # TODO: should the sync be done here?
        self.k.sync()
        return note

    def delete_note(self, id):
        note = self.k.get(id)
        if note:
            note.delete()
            # TODO: should the sync be done here?

    def delete_all(self):
        for n in self.k.all():
            n.delete()
        # TODO: should the sync be done here?
        self.k.sync()

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

    def find_create(self, label, title):
        #notefind_notes(label, title)
        pass

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


