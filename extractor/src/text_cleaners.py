import unicodedata
import datetime
import re
from nameparser import HumanName


def normalize_text(raw_txt):
    raw_txt = " ".join(raw_txt.split())
    text = unicodedata.normalize('NFC', raw_txt)
    return text.strip()


def clean_cell(cell):
    cell = normalize_text(cell)
    if cell == "" or cell == 'null':
        return None
    else:
        return cell


def hyphen_date_str_to_dt(date_str):
    date_list = date_str.split('-')
    return datetime.datetime(*[int(x) for x in date_list])


inc_reg_ex = re.compile(" inc\.$| inc$| incorporated$", re.IGNORECASE)
corp_reg_ex = re.compile(" corp\.$| corp$| corporation$", re.IGNORECASE)
ltd_reg_ex = re.compile(" ltd\.$| ltd$| limited$", re.IGNORECASE)
co_reg_ex = re.compile(" co\.$| co$| company$", re.IGNORECASE)


def normalize_org_name(org_name):
    org_name = inc_reg_ex.sub(" Inc.", org_name)
    org_name = corp_reg_ex.sub(" Corp.", org_name)
    org_name = ltd_reg_ex.sub(" Ltd.", org_name)
    org_name = co_reg_ex.sub(" Co.", org_name)
    return org_name.strip()


def subjects_text_to_subjects_list(subject_str):
    return subject_str.split(',')


name_reg_ex = re.compile("Honourable |The Honourable |hon\.|the hon\.|Rt\. Hon\.|The Right Honourable|Rt\. Honourable", re.IGNORECASE)


def normalize_person_name(person_name):
    new_string = name_reg_ex.sub("", person_name)
    name = HumanName(new_string)
    name.capitalize(force=True)
    return str(name)


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


def make_ngram_prefix(full_name, min_size=3):
    names = full_name.split()
    prefixes = []
    for name in names:
        length = len(name)
        size_range = range(min_size, max(length, min_size) + 1)
        prefixes.extend([name[0:size] for size in size_range])
    return prefixes


def make_ngrams_from_beginning_of_phrase(phrase, min_size=3):
    phrase = " ".join(phrase.split())
    length = len(phrase)
    size_range = range(min_size, max(length, min_size) + 1)
    return [phrase[0:size] for size in size_range]
