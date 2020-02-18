from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint, jsonify
from flask_login import current_user, login_required

from data_model import *

from app_api.api_mgmt_forms import PersonSelector, GroupSelector

from app_api.helper_functions import rank_by_n_comms, date_range_maker, make_com_report_dict

from dateutil.rrule import rrule, MONTHLY
from collections import defaultdict
from operator import itemgetter

import operator


api = Blueprint('api', __name__, template_folder='templates')


@api.route('/api-tests/person')
@login_required
def api_person_test_page():
    pid = request.args.get('pid')
    form = PersonSelector()
    form.pid.choices = [(x['api_person_id'], x['full_name']) for x in person_collection.find().sort('last_name')]
    if pid:
        form.pid.data = pid
    return render_template("person_test.html", pid=pid, form=form)

@api.route('/api-tests/group')
@login_required
def api_group_test_page():
    gid = request.args.get('gid')
    form = GroupSelector()
    form.gid.choices = [(x['group_id'], x['group_name']) for x in group_collection.find().sort('group_name')]
    if gid:
        form.gid.data = gid

    return render_template("group_test.html", gid=gid, form=form)

@api.route('/api/person/summary')
def api_person_summary():
    api_person_id = request.args.get('pid')
    person = person_collection.find({'api_person_id': api_person_id}).limit(1)
    data_holder = {}
    if person.count() == 1:
        person_obj = person[0]

        last_3_mo = date_range_maker(3, 0)
        last_18_mo = date_range_maker(18, 0)

        dpoh_name_ids_list = dpoh_name_collection.find({'person_id': person_obj['_id']}).distinct('_id')
        dpoh_recent_query = {'dpoh.dpoh_name_id': {'$in': dpoh_name_ids_list},
                             'comms_date': last_3_mo,
                             'amended': {'$exists': False}}

        data_holder['total_comms'] = comm_report_collection.count(dpoh_recent_query)
        data_holder['person'] = person_obj['full_name']
        data_holder['recent_summary_title'] = 'Lobbying summary since {dt:%B} {dt.day}, {dt.year}'.format(
            dt=last_3_mo['$gte'])
        data_holder['recent_list_title'] = 'Lobbying reports since {dt:%B} {dt.day}, {dt.year}'.format(
            dt=last_3_mo['$gte'])

        corp_pipeline = [{'$match': dpoh_recent_query},
                         {'$lookup':
                              {'from': "child_org_collection",
                               'localField': "proponent_org_id",
                               'foreignField': "org_id",
                               'as': "child_org_deets"
                               }
                          },
                         {'$project': {
                             'child_org_deets': {'$arrayElemAt': ["$child_org_deets", 0]},
                         }},
                         {'$lookup':
                              {'from': "parent_org_collection",
                               'localField': "child_org_deets.parent_org_id",
                               'foreignField': "_id",
                               'as': "parent_org_deets"
                               }
                          },
                         {'$project': {
                             'parent_org_deets': {'$arrayElemAt': ["$parent_org_deets", 0]},
                         }},
                         {'$group': {'_id': "$parent_org_deets.org_name",
                                     'n_communications': {'$sum': 1}}},
                         {'$match': {'n_communications': {'$gt': 1}}},
                         {'$sort': {'n_communications': -1}},
                         {'$limit': 20}
                         ]

        data_holder['corp_count'] = rank_by_n_comms(list(comm_report_collection.aggregate(corp_pipeline)))
        subj_count_pipeline = [{'$match': dpoh_recent_query},
                               {'$unwind': '$subjects'},
                               {'$group': {'_id': "$subjects",
                                           'n_communications': {'$sum': 1}}},
                               {'$match': {'n_communications': {'$gt': 1}}},

                               {'$sort': {'n_communications': -1}},
                               ]
        data_holder['subj_count'] = rank_by_n_comms(list(comm_report_collection.aggregate(subj_count_pipeline)))

        subj_by_mo_query_dict = {'$match': {'dpoh.dpoh_name_id': {'$in': dpoh_name_ids_list},
                                            'comms_date': last_18_mo,
                                            'amended': {'$exists': False}}}

        subject_by_month_pipeline = [subj_by_mo_query_dict,
                                     {'$unwind': '$subjects'},
                                     {'$group': {'_id':
                                                     {'month': {'$concat':
                                                                    [{"$substr": [{'$year': "$comms_date"}, 0, -1]},
                                                                     "-",
                                                                     {"$cond": [
                                                                         {"$lte": [{"$month": "$comms_date"}, 9]},
                                                                         {"$concat": ["0", {
                                                                             "$substr": [{"$month": "$comms_date"}, 0,
                                                                                         2]}]},
                                                                         {"$substr": [{"$month": "$comms_date"}, 0, 2]}
                                                                     ]},
                                                                     ]},
                                                      'subj': '$subjects'},
                                                 'value': {'$sum': 1}}},
                                     ]

        subject_by_month_result = comm_report_collection.aggregate(subject_by_month_pipeline)

        heat_map_dates = [dt.strftime('%Y-%m') for dt in
                          rrule(MONTHLY, dtstart=last_18_mo['$gte'], until=last_18_mo['$lte'])]
        data_dict = defaultdict(lambda: [0 for x in range(len(heat_map_dates))])
        date_dict = {}
        for n, d in enumerate(heat_map_dates):
            date_dict[d] = n

        for agg in subject_by_month_result:
            data_dict[agg['_id']['subj']][date_dict[agg['_id']['month']]] = agg['value']

        final_data = []
        for d in data_dict:
            final_data.append({'label': d, 'data': data_dict[d]})
        final_data = sorted(final_data, key=itemgetter('label'))

        data_holder['heat_map_data'] = {'labels': heat_map_dates, 'datasets': final_data}

        comms_list = [make_com_report_dict(ob) for ob in
                      comm_report_collection.find(dpoh_recent_query).sort('comms_date', -1)]
        data_holder['comms_list'] = comms_list

    response = jsonify(data_holder)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@api.route('/api/group/<group_id>/by_month')
def api_group_by_month(group_id):
    subject = "Intellectual Property"
    group = group_collection.find_one({"group_id": group_id})
    group_members = person_collection.find({'_id': {'$in': group['group_members']}})

    final_data = []
    names_list = []
    heat_map_dates = []
    hover = []

    if group_members.count() > 0:
        group_members = list(group_members)
        group_member_ids = [x['_id'] for x in group_members]
        group_member_lookup = {str(x['api_person_id']): "%s, %s" % (x['last_name'], x['first_name']) for x in group_members}
        date_range = date_range_maker(12, 0)
        group_member_name_ids_list = dpoh_name_collection.find({'person_id': {'$in': group_member_ids}}).distinct('_id')

        person_by_mo_query_dict = {'$match': {'dpoh.dpoh_name_id': {'$in': group_member_name_ids_list},
                                              'comms_date': date_range,
                                              'amended': {'$exists': False},
                                              'subjects': subject}}

        person_by_month_pipeline = [person_by_mo_query_dict,
                                    {'$unwind': '$dpoh'},
                                    {'$lookup': {'from': 'dpoh_name_collection',
                                                 'localField': 'dpoh.dpoh_name_id',
                                                 'foreignField': '_id',
                                                 'as': 'dpoh_name_details'}},
                                    {'$unwind': '$dpoh_name_details'},

                                    {'$lookup': {'from': 'person_collection',
                                                 'localField': 'dpoh_name_details.person_id',
                                                 'foreignField': '_id',
                                                 'as': 'person_details'}},
                                    {'$unwind': '$person_details'},
                                    {'$unwind': '$subjects'},
                                    {'$match': {'person_details._id': {'$in': group['group_members']},
                                                'subjects': subject}},

                                    {'$group': {'_id':
                                                    {'month': {'$concat':
                                                                   [{"$substr": [{'$year': "$comms_date"}, 0, -1]},
                                                                    "-",
                                                                    {"$cond": [
                                                                        {"$lte": [{"$month": "$comms_date"}, 9]},
                                                                        {"$concat": ["0", {
                                                                            "$substr": [{"$month": "$comms_date"}, 0,
                                                                                        2]}]},
                                                                        {"$substr": [{"$month": "$comms_date"}, 0, 2]}
                                                                    ]},
                                                                    ]},
                                                     'person': '$person_details.api_person_id'},
                                                'value': {'$sum': 1}}},
                                    ]

        person_by_month_result = comm_report_collection.aggregate(person_by_month_pipeline)
        heat_map_dates = [dt.strftime('%Y-%m') for dt in
                          rrule(MONTHLY, dtstart=date_range['$gte'], until=date_range['$lte'])]

        data_dict = defaultdict(lambda: [0 for x in range(len(heat_map_dates))])

        date_dict = {}

        for n, d in enumerate(heat_map_dates):
            date_dict[d] = n

        for agg in person_by_month_result:
            data_dict[agg['_id']['person']][date_dict[agg['_id']['month']]] = agg['value']

        sorted_group_member_names = sorted(group_member_lookup.items(), key=operator.itemgetter(1),  reverse=True)

        for p in sorted_group_member_names:
            final_data.append([x if x != 0 else "" for x in data_dict[p[0]]])
            names_list.append(p[1])

            hover.append(["%s<br />%s: %s coms." % (p[1], heat_map_dates[n], y) for n, y in enumerate(data_dict[p[0]])])

    response = jsonify({'values': final_data,
                        'names': names_list,
                        'dates': heat_map_dates,
                        'hover': hover})

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response
