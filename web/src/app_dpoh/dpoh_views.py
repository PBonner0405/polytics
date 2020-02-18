__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint

from data_model import *
from pymongo.errors import DuplicateKeyError

from app_dpoh.dpoh_forms import DpohToPerson, DPHOSearchForm

from flask_login import current_user, login_required
from app_user_mgmt.user_utils import requires_role
from common_utils import make_ngrams, confirm_has_lock

from bson import ObjectId

dpoh = Blueprint('dpoh', __name__, template_folder='templates')


def get_person_for_names_list(dpoh_names_list):
        processed_names = []
        for dn in dpoh_names_list:
            print(dn)
            dn_dict = dict(dn)
            if dn['person_id']:
                dn_dict['person_name'] = person_collection.find_one({'_id': dn['person_id']})['full_name']
            else:
                dn_dict['person_name'] = None
            processed_names.append(dn_dict)
        return processed_names

@dpoh.route('/dpoh-names', methods=["GET"])
@requires_role('admin')
def dpoh_name_list():
    form = DPHOSearchForm(request.form)
    processed_names = []
    search_term = request.args.get('search', None)
    if search_term not in ("", None):
        dpoh_names = dpoh_name_collection.find({"$text": {"$search": " ".join(make_ngrams(search_term))}},
                                               {
                                                   "name": True,
                                                   "title": True,
                                                   "inst": True,
                                                   "person_id": True,
                                                   "score": {
                                                       "$meta": "textScore"
                                                   }
                                               }
                                               ).sort([("score", {"$meta": "textScore"}),
                                                       ("assumed_last_name", 1),
                                                       ("name", 1)]).limit(100)
        processed_names = get_person_for_names_list(dpoh_names)

    return render_template('dpoh_names_list.html', form=form, dpoh_names=processed_names)


@dpoh.route('/dpoh-names/flagged', methods=["GET"])
@requires_role('admin')
def dpoh_name_flagged_list():

    flagged_dpoh_names = dpoh_name_collection.find({'flagged': True})
    processed_names = get_person_for_names_list(flagged_dpoh_names)
    return render_template('dpoh_names_flagged_list.html', flagged_dpoh_names=processed_names)


@dpoh.route('/dpoh-names/<dpoh_id>/edit', methods=["GET", "POST"], endpoint='dpoh_name_edit')
@dpoh.route('/dpoh-names/<dpoh_id>/edit-flagged', methods=["GET", "POST"], endpoint='dpoh_name_flagged_edit')
@requires_role('admin')
def dpoh_name_edit(dpoh_id):
    dpoh_name = dpoh_name_collection.find_one({'_id': ObjectId(dpoh_id)})
    can_edit = True
    if confirm_has_lock(dpoh_name['_id']) is None:
        flash('DPOH name "%s" is being reviewed finalized or edited by someone else. You cannot edit it at this time.' %
              dpoh_name['name'], 'danger')
        can_edit = False

    form = DpohToPerson(request.form, **dpoh_name)
    dpoh_choices = [(str(p['_id']), "%s (%s)" % (p['full_name'], p['person_type'])) for p in
                    person_collection.find({'person_type': {'$in': ('MP', 'Senator')}}).sort('last_name')]

    dpoh_choices.insert(0, ("dont-link", "Not MP/Senator"))
    form.person_id.choices = dpoh_choices
    if request.method == "POST" and form.validate():
        print(form.data)
        if 'save' in request.form:
            if form.person_id.data == 'dont-link':
                person_id = None
            else:
                person_id = ObjectId(form.person_id.data)

            result = dpoh_name_collection.update({'_id': dpoh_name['_id']},
                                                 {'$set': {'flagged': False,
                                                           'flagged_by': None,
                                                           'person_id': person_id,
                                                           'reviewed_by': current_user.name,
                                                           'verified_by': current_user.name,
                                                           'manually_updated': True,
                                                           }})
            flash("DPOH %s saved." % dpoh_name['name'], "success")
        r.delete(str(dpoh_name['_id']))

        if request.url_rule.rule.endswith("edit-flagged"):
            return redirect(url_for('dpoh.dpoh_name_flagged_list'))
        elif request.url_rule.rule.endswith("edit"):
            return redirect(url_for('dpoh.dpoh_name_list', search=dpoh_name['assumed_last_name'][:4]))

    return render_template('dpoh_name_edit.html', form=form, dpoh_name=dpoh_name, can_edit=can_edit)

@dpoh.route('/dpoh-names/queue', methods=["GET", "POST"])
@login_required
def dpoh_name_queue():
    existing_lock_keys = [ObjectId(k) for k in r.keys()]
    dpoh_to_finalize = dpoh_name_collection.find({'reviewed_by': {'$nin': (None, current_user.name)},
                                                  'verified_by': None,
                                                  'flagged': {'$ne': True},
                                                  '_id': {'$nin': existing_lock_keys}}).limit(1)
    if dpoh_to_finalize.count() > 0:
        return redirect(url_for('dpoh.dpoh_name_finalize', dpoh_id=dpoh_to_finalize[0]['_id']))

    dpoh_to_review = dpoh_name_collection.find({'reviewed_by': None,
                                                'verified_by': None,
                                                'flagged': {'$ne': True},
                                                '_id': {'$nin': existing_lock_keys}}).limit(1)
    if dpoh_to_review.count() > 0:
        return redirect(url_for('dpoh.dpoh_name_review', dpoh_id=dpoh_to_review[0]['_id']))

    return render_template("dpoh_name_queue.html")


@dpoh.route('/dpoh-names/<dpoh_id>/review', methods=["GET", "POST"])
@login_required
def dpoh_name_review(dpoh_id):
    dpoh_name = dpoh_name_collection.find_one({'_id': ObjectId(dpoh_id)})
    if confirm_has_lock(dpoh_name['_id']) is None:
        flash('DPOH name "%s" is being edited by someone else. You have been redirected to the next available name.' %
              dpoh_name['name'], 'danger')
        return redirect(url_for('dpoh.dpoh_name_queue'))

    reviewed = dpoh_name['reviewed_by'] != None
    if reviewed:
        flash("This DPOH name has already been reviewed.", 'danger')
    form = DpohToPerson(request.form, **dpoh_name)
    dpoh_choices = [(str(p['_id']), "%s (%s)" % (p['full_name'], p['person_type'])) for p in
                    person_collection.find({'person_type': {'$in': ('MP', 'Senator')}}).sort('last_name')]

    dpoh_choices.insert(0, ("dont-link", "Not MP/Senator"))
    dpoh_choices.insert(0, ("", "Select one"))
    form.person_id.choices = dpoh_choices

    if request.method == "POST" and form.validate():
        if form.person_id.data == 'dont-link':
            person_id = None
        else:
            person_id = ObjectId(form.person_id.data)

        result = dpoh_name_collection.update({'_id': dpoh_name['_id']},
                                             {'$set': {'person_id': person_id,
                                                       'reviewed_by': current_user.name
                                                       }})
        flash("DPOH %s saved." % dpoh_name['name'], "success")

        r.delete(str(dpoh_name['_id']))
        return redirect(url_for('dpoh.dpoh_name_queue'))

    return render_template('dpoh_name_review.html', form=form, dpoh_name=dpoh_name, reviewed=reviewed)


@dpoh.route('/dpoh-names/<dpoh_id>/finalize', methods=["GET", "POST"])
@login_required
def dpoh_name_finalize(dpoh_id):
    dpoh_id = ObjectId(dpoh_id)
    dpoh_name = dpoh_name_collection.find_one({'_id': dpoh_id})
    if confirm_has_lock(dpoh_name['_id']) is None:
        flash('DPOH name %s is being edited by someone else. You have been redirected to the next available dpoh.' %
              dpoh_name['name'], 'danger')
        return redirect(url_for('dpoh.dpoh_name_queue'))

    form = DpohToPerson(request.form, **dpoh_name)
    dpoh_choices = [(str(p['_id']), "%s (%s)" % (p['full_name'], p['person_type'])) for p in
                    person_collection.find({'person_type': {'$in': ('MP', 'Senator')}}).sort('last_name')]

    dpoh_choices.insert(0, ("dont-link", "Not MP/Senator"))
    form.person_id.choices = dpoh_choices

    if request.method == "POST" and form.validate():
        if form.person_id.data == 'dont-link':
            person_id = None
        else:
            person_id = ObjectId(form.person_id.data)

        if person_id == dpoh_name['person_id']:
            dpoh_name_collection.update({'_id': dpoh_name['_id']}, {'$set': {'verified_by': current_user.name}})
            flash("%s finalized!" % dpoh_name['name'], "success")
        else:
            dpoh_name_collection.update({'_id': dpoh_name['_id']},
                                        {'$set': {'person_id': person_id,
                                                  'reviewed_by': current_user.name
                                                  }})
            flash("%s updated and returned to finalize queue!" % dpoh_name['name'], "warning")

        r.delete(str(dpoh_name['_id']))
        return redirect(url_for('dpoh.dpoh_name_queue'))

    can_verify = current_user.name != dpoh_name['reviewed_by']
    if not can_verify:
        flash("You reviewed this dpoh.", 'warning')

    return render_template('dpoh_name_finalize.html', form=form, dpoh_name=dpoh_name, can_verify=can_verify)


@dpoh.route('/dpoh-names/<dpoh_id>/unlock', methods=["GET", "POST"])
@login_required
def dpoh_name_unlock(dpoh_id):
    dpoh = dpoh_name_collection.find_one({'_id': ObjectId(dpoh_id)})
    r.delete(str(dpoh['_id']))
    flash('DPOH name %s unlocked' % dpoh['name'], 'success')
    return redirect(url_for('home'))


@dpoh.route('/dpoh-names/<dpoh_id>/flag', methods=["GET", "POST"])
@login_required
def dpoh_name_flag(dpoh_id):
    dpoh = dpoh_name_collection.find_one({'_id': ObjectId(dpoh_id)})
    result = dpoh_name_collection.update({'_id': ObjectId(dpoh_id)},
                                         {'$set': {'flagged': True,
                                                   'flagged_by': current_user.name}})
    r.delete(str(dpoh['_id']))
    flash('DPOH name %s flagged for follow up.' % dpoh['name'], 'warning')
    return redirect(url_for('dpoh.dpoh_name_queue'))
