import gkeepapi as gk
import ConfigParser, os
from read_email import Email as Email
import pdb

#TODO: move to Keep    
DONE_label = "DONE"
TODO_label = "TODO"

#class Keep(object):
#    def __init__(self, em): 
#    self.k = gk.Keep()
#    self.k.login(em.cfg.from_email, em.cfg.from_pwd)
#    self.t_label = find_create_label(keep, TODO_label)
#    self.d_label =find_create_label(keep, DONE_label)

def create_note(keep, title, text="", label=None):
    note = keep.createNote(title, text)

    #note.pinned = True
    note.color = gk.node.ColorValue.Red
    if label:
        note.labels.add(label)

    print note.title
    print note.text


# TODO: use find_create_label
def find_by_label(k, label):
    notes = []
    if label:
        notes = k.find(labels=[label]) 
        print [n.title + " // " + n.text + " // " + n.id for n in notes]
    return notes

def find_notes(k, label, title):
    notes = find_by_label(k, label)
    res = []
    for n in notes:
        # TODO: it would be better to filter by id
        if n.title == title:
            res.append(n)
    return res

def find_create_label(k, name):
    label = k.findLabel(name)
    if label is None:
        label = k.createLabel(name)
        # TODO: should the sync be done here?
        k.sync()
    return label

def test_create(k):
    l = k.findLabel("TODO")
    create_note(k, "Clean bedroom", label=l)
    create_note(k, "Clean kitchen", label=l)
    create_note(k, "But veg", label=l)
    k.sync()

def relabel(note, old_label, new_label):
    if note,labels.get(old_label.id) != None:
        note.labels.remove(old_label)
    note.labels.add(new_label)

def to_todo(k, notes):
    t_label = find_create_label(k, TODO_label)
    d_label = find_create_label(k, DONE_label)
    to_other(notes, d_label, t_label, )
    k.sync()

def to_other(notes, old_label, new_label, color):
    for n in notes:
        relabel(note, old_label, new_label, color)

if __name__ == "__main__":
    em = Email()
    keep = gk.Keep()
    keep.login(em.cfg.from_email, em.cfg.from_pwd)
    t_label = find_create_label(keep, TODO_label)
    d_label =  find_create_label(keep, DONE_label)
    print t_label, d_label
    #test_create(keep)
    #find_by_label(keep, t_label)
    notes = find_notes(keep, t_label, "Clean bedroom")


