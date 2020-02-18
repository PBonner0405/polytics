from bson import ObjectId
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import re
from text_cleaners import hyphen_date_str_to_dt, normalize_text, normalize_org_name, subjects_text_to_subjects_list, \
    normalize_person_name, make_ngrams, make_ngram_prefix, make_ngrams_from_beginning_of_phrase
from data_model import *



def comms_dict_from_row(row):
    proponent_org_id, com_id = row[0].split('-')

    row_dict = {"communication_number": row[0],
                "posted_date": hyphen_date_str_to_dt(row[1]),
                "comms_date": hyphen_date_str_to_dt(row[2]),
                "proponent_org_name": normalize_org_name(row[3]),
                "proponent_org_id": proponent_org_id,
                "registrant_name": row[4],
                "subjects": subjects_text_to_subjects_list(row[8]),
                }
    return row_dict


def get_org_from_org_name_or_id(reg_org_name, reg_org_id, org_name_dict):
    org_objs = child_org_collection.find({'org_id': reg_org_id})
    if org_objs.count() > 0:
        return "existing"

    else:
        norm_org_name = normalize_org_name(reg_org_name)
        result = process.extractOne(norm_org_name, org_name_dict)
        parent_org_id = None
        reviewed_by = None
        if result:
            # auto-link for very close fuzzy matches
            if 98 <= result[1]:
                parent_org_id = ObjectId(result[2])
                reviewed_by = 'auto'

        child_org_collection.insert({'org_id': reg_org_id,
                                     'org_name': reg_org_name,
                                     'parent_org_id': parent_org_id,
                                     'reviewed_by': reviewed_by,
                                     'verified_by': None,
                                     'name_ngrams': " ".join(make_ngrams(reg_org_name)),
                                     'name_prefixes': " ".join(make_ngrams_from_beginning_of_phrase(reg_org_name))})


    return "added"


def dpoh_dict_from_row(row, people_name_dict):
    norm_name = normalize_person_name(row[5])
    dpoh_name_query = dpoh_name_collection.find({'name': norm_name, 'title': row[6].title(), 'inst': row[7]}).limit(1)

    if dpoh_name_query.count() == 0:

        dpoh_name_obj = dpoh_name_collection.insert({'name': norm_name,
                                                     'title': row[6].title(),
                                                     'inst': row[7],
                                                     'reviewed_by': None,
                                                     'verified_by': None,
                                                     'person_id': None,
                                                     'assumed_last_name': row[5].split()[-1],
                                                     'name_ngrams': " ".join(make_ngrams(norm_name)),
                                                     'name_prefixes': " ".join(make_ngram_prefix(norm_name)),
                                                     }
                                                    )
    else:
        dpoh_name_obj = dpoh_name_query[0]['_id']

    return {"dpoh_name": row[5],
            "dpoh_title": row[6],
            "dpoh_inst": row[7],
            "dpoh_name_id": dpoh_name_obj,
            }


def coms_row_processor(row, people_name_dict, org_name_dict):
    existing_report = comm_report_collection.find_one({"communication_number": row[0]})
    if existing_report:
        if not comm_report_collection.find_one({"communication_number": row[0], "dpoh.dpoh_name": row[5]}):
            dpoh = dpoh_dict_from_row(row, people_name_dict)
            comm_report_collection.update({'_id': existing_report['_id']}, {"$addToSet": {"dpoh": dpoh}})

    else:
        coms_report_dict = comms_dict_from_row(row)
        # dpoh needs to be a dict, within a list.
        coms_report_dict['dpoh'] = [dpoh_dict_from_row(row, people_name_dict)]
        comm_report_collection.insert(coms_report_dict)
        org_status = get_org_from_org_name_or_id(coms_report_dict['proponent_org_name'],
                                                 coms_report_dict['proponent_org_id'],
                                                 org_name_dict)



    return people_name_dict, org_name_dict


