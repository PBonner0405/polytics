from data_model import *
import datetime
from dateutil.relativedelta import relativedelta


def rank_by_n_comms(n_coms_list, max_rank=5):
    if not n_coms_list:
        return []
    rank = 1
    most_recent = n_coms_list[0]['n_communications']
    new_list = []
    for corp in n_coms_list:
        if corp['n_communications'] < most_recent:
            rank = len(new_list)
            most_recent = corp['n_communications']
        if rank > max_rank:
            return new_list
        corp['rank'] = rank
        new_list.append(corp)
    return new_list


def date_range_maker(num_months, num_months_offset):
    now = datetime.datetime.now()  # timezone-aware datetime.utcnow()
    date_until = now + relativedelta(months=-num_months_offset)  # midnight
    m = now + relativedelta(months=-(num_months + num_months_offset))
    date_from = datetime.datetime(m.year, m.month, 1)

    return {'$gte': date_from, '$lte': date_until}


def get_api_key_from_dpoh(name_id):
    dpoh_name = dpoh_name_collection.find_one({'_id': name_id})
    if dpoh_name:
        person_obj = person_collection.find_one({"_id": dpoh_name['person_id']})
        if person_obj:
            return person_obj['api_person_id']
    return None


def make_com_report_dict(com_report):
    report_dict = {}
    org = child_org_collection.find_one({'org_id': com_report['proponent_org_id']})
    parent_org_id = org.get('parent_org_id', None)

    if parent_org_id:
        parent_org = parent_org_collection.find_one({'_id': parent_org_id})
        try:
            report_dict['org'] = parent_org['org_name']
        except:
            print(org)
            print(com_report)
    else:
        report_dict['org'] = org['org_name']

    report_dict['com_date'] = com_report['comms_date'].strftime("%Y-%m-%d")
    report_dict['registrant'] = com_report['registrant_name']
    report_dict['subj'] = ", ".join(com_report['subjects'])
    report_dict['report_number'] = com_report['communication_number']

    dpoh_list = [{'text': "%s - %s | %s" % (x['dpoh_name'], x['dpoh_title'], x['dpoh_inst']),
                  'pid': get_api_key_from_dpoh(x['dpoh_name_id'])} for x in com_report['dpoh']]
    report_dict['dpoh'] = [dict(t) for t in set([tuple(d.items()) for d in dpoh_list])]

    return report_dict