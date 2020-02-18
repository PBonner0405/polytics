import re
from nameparser import HumanName
from data_model import *
from flask_login import current_user

def make_ngrams(full_name, min_size=3):
    """
    basestring          word: word to split into ngrams
           int      min_size: minimum size of ngrams
    """
    length = len(full_name)
    size_range = range(min_size, max(length, min_size) + 1)

    return list(set(
        full_name[i:i + size]
        for size in size_range
        for i in range(0, max(0, length - size) + 1)
    ))


def make_ngrams_from_beginning_of_phrase(phrase, min_size=3):
    phrase = " ".join(phrase.split())
    length = len(phrase)
    size_range = range(min_size, max(length, min_size) + 1)
    return [phrase[0:size] for size in size_range]

name_reg_ex = re.compile("Honourable |The Honourable |hon\.|the hon\.|Rt\. Hon\.|The Right Honourable|Rt\. Honourable", re.IGNORECASE)


def confirm_has_lock(obj_id):
    obj_id = str(obj_id)
    set_lock = r.set(obj_id, current_user.name, ex=900, nx=True, xx=False)
    if set_lock is True:
        return True
    if r.get(obj_id) == current_user.name:
        return r.set(obj_id, current_user.name, ex=900, nx=False, xx=True)
    return None