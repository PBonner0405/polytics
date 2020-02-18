__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint

from data_model import *
from pymongo.errors import DuplicateKeyError

from app_orgs.org_forms import VerifyOrg, VerifyParentOrg, OrgSearchForm, ParentOrgEdit, ParentOrgDelete, \
    ChangeParentOrg, ParentOrgNew

from flask_login import current_user, login_required
from app_user_mgmt.user_utils import requires_role


from bson import ObjectId
from fuzzywuzzy import process

from common_utils import make_ngrams, make_ngrams_from_beginning_of_phrase
from operator import itemgetter

orgs = Blueprint('orgs', __name__, template_folder='templates')


def confirm_has_lock(obj_id):
    obj_id = str(obj_id)
    set_lock = r.set(obj_id, current_user.name, ex=900, nx=True, xx=False)
    if set_lock is True:
        return True
    if r.get(obj_id) == current_user.name:
        return r.set(obj_id, current_user.name, ex=900, nx=False, xx=True)
    return None


@orgs.route('/orgs/queue', methods=["GET", "POST"])
@login_required
def orgs_queue():
    existing_lock_keys = [ObjectId(k) for k in r.keys()]
    parent_org_to_verify = parent_org_collection.find({'reviewed_by': {'$nin': (None, current_user.name)},
                                                       'verified_by': None,
                                                       'flagged': {'$ne': True},
                                                       '_id': {'$nin': existing_lock_keys}}).limit(1)
    if parent_org_to_verify.count() > 0:
        return redirect(url_for('orgs.parent_orgs_verify', org_id=parent_org_to_verify[0]['_id']))

    org_to_verify = child_org_collection.find({'reviewed_by': {'$nin': (None, current_user.name)},
                                               'verified_by': None,
                                               'flagged': {'$ne': True},
                                               '_id': {'$nin': existing_lock_keys}}).limit(1)
    if org_to_verify.count() > 0:
        return redirect(url_for('orgs.orgs_finalize', org_id=org_to_verify[0]['org_id']))

    org_to_review = child_org_collection.find({'reviewed_by': None,
                                               'flagged': {'$ne': True},
                                               '_id': {'$nin': existing_lock_keys}}).limit(1)
    if org_to_review.count() > 0:
        return redirect(url_for('orgs.org_review', org_id=org_to_review[0]['org_id']))

    return render_template("org_queue.html")


def get_org_sims(org_name, org_obj_id):
    if org_obj_id:
        parent_org_list = parent_org_collection.find({'_id': {'$ne': org_obj_id}})
    else:
        parent_org_list = parent_org_collection.find()

    org_names_dict = {str(x['_id']): x['org_name'] for x in parent_org_list}
    sim_result = process.extract(org_name, org_names_dict, limit=10)
    return [x[0] for x in sim_result if x[1] > 55]


def org_aggregation(parent_ids, child_ids):
    return child_org_collection.aggregate([
            {'$match': {'$or': [{'parent_org_id': {'$in': parent_ids}}, {"_id": {'$in': child_ids}}]}},
            {'$lookup':
                {
                    'from': 'parent_org_collection',
                    'localField': 'parent_org_id',
                    'foreignField': '_id',
                    'as': 'parent_org'
                }},
            {'$unwind': {'path': "$parent_org", 'preserveNullAndEmptyArrays': True}},
            {"$group": {"_id": {'parent_id': "$parent_org._id", 'parent_name': '$parent_org.org_name', 'flagged':'$parent_org.flagged', 'flagged_by':'$parent_org.flagged_by'},
                        "child_orgs": {'$push': {'org_name': "$org_name", 'org_id': "$org_id", 'flagged':'$flagged', 'flagged_by':'$flagged_by'}}}}])

@orgs.route('/orgs/flagged', methods=["GET"], endpoint='flagged_orgs')
@orgs.route('/orgs', methods=["GET"], endpoint='org_list')
@requires_role('admin')
def org_list():
    search_term = request.args.get('search', None)
    form = OrgSearchForm(request.form)
    edit_parent_form = ParentOrgEdit(request.form)
    new_parent_form = ParentOrgNew(request.form)
    delete_parent_form = ParentOrgDelete(request.form)
    change_parent_form = ChangeParentOrg(request.form)
    change_parent_form.parent_org_id.choices = [(str(o['_id']), o['org_name']) for o in
                                                parent_org_collection.find().sort('org_name')]

    redirect_path = "%s?search=%s" % (request.path, search_term)
    delete_parent_form.parent_delete_form_path.data = redirect_path
    edit_parent_form.parent_edit_form_path.data = redirect_path
    change_parent_form.change_parent_form_path.data = redirect_path
    new_parent_form.new_parent_form_path.data = redirect_path

    if request.url_rule.rule.endswith("flagged"):
        parent_ids = parent_org_collection.find({'flagged': True}).distinct('_id')
        child_ids = child_org_collection.find({'flagged': True}).distinct('_id')
        orgs = org_aggregation(parent_ids, child_ids)


    elif search_term:
        possible_parents = parent_org_collection.find({"$text": {"$search": " ".join(make_ngrams(search_term))}},
                                                      {
                                                          "org_name": True,
                                                          "_id": True,
                                                          "score": {
                                                              "$meta": "textScore"
                                                          }
                                                      })
        parent_ids = [o['_id'] for o in possible_parents]
        parent_score = {str(o['_id']): o['score'] for o in possible_parents.rewind()}
        possible_children = child_org_collection.find({"$text": {"$search": " ".join(make_ngrams(search_term))}},
                                                      {
                                                          "org_id": True,
                                                          "_id": True,
                                                          "score": {
                                                              "$meta": "textScore"
                                                          }
                                                      })
        child_ids = [o['_id'] for o in possible_children]
        child_score = {str(o['org_id']): o['score'] for o in possible_children.rewind()}
        result = org_aggregation(parent_ids, child_ids)

        result = list(result)
        parent_ids = []
        for r in result:
            n = 1
            score = 0
            score += parent_score.get(str(r['_id'].get('parent_id')), 0)
            for c in r['child_orgs']:
                score += child_score.get(c['org_id'], 0)
                n += 1
            r['score'] = score / n
            parent_ids.append(r['_id'].get('parent_id'))

        for pp in possible_parents.rewind():
            if pp['_id'] not in parent_ids:
                childless = {'_id': {'parent_id': pp['_id'], 'parent_name': pp['org_name']}, 'child_orgs': [], 'score': pp['score']}
                result.append(childless)

        if len(result) > 10:
            filtered_results = [o for o in result if o['score'] > 500]
        else:
            filtered_results = result

        orgs = sorted(filtered_results, key=itemgetter('score'), reverse=True)
    else:
        orgs = None

    return render_template('orgs_list.html', form=form, edit_parent_form=edit_parent_form,
                           delete_parent_form=delete_parent_form, change_parent_form=change_parent_form,
                           new_parent_form=new_parent_form, orgs=orgs)


@orgs.route('/orgs/parent/edit', methods=["POST"])
@requires_role('admin')
def org_parent_edit():
    form = ParentOrgEdit(request.form)
    if form.validate_on_submit():
        try:
            parent_org_collection.update_one({'_id': ObjectId(form.parent_edit_org_id.data)},
                                             {'$set': {'org_name': form.parent_edit_org_new_name.data,
                                                       'name_ngrams': " ".join(
                                                           make_ngrams(form.parent_edit_org_new_name.data)),
                                                       'name_prefixes': " ".join(make_ngrams_from_beginning_of_phrase(
                                                           form.parent_edit_org_new_name.data)),
                                                       'flagged': False,
                                                       'flagged_by': None}})
            flash('Parent org name successfully updated!', 'success')

        except DuplicateKeyError:
            flash("Error - parent org with that name already exists. Please link to the existing parent org.", "danger")

    else:
        flash('Error updating name. Please try again', 'danger')

    return redirect(form.parent_edit_form_path.raw_data[0].strip())

@orgs.route('/orgs/parent/add', methods=["POST"])
@requires_role('admin')
def org_parent_add():
    form = ParentOrgNew(request.form)
    if form.validate_on_submit():
        name = form.new_parent_org_name.data.strip()
        try:
            parent_org_collection.insert({'org_name': name,
                                          'reviewed_by': current_user.name,
                                          'verified_by': current_user.name,
                                          'manually_updated': True,
                                          'name_ngrams': " ".join(make_ngrams(name)),
                                          'name_prefixes': " ".join(make_ngrams_from_beginning_of_phrase(name))})

            flash('Parent org name successfully created!', 'success')

        except DuplicateKeyError:
            flash("Error - parent org with that name already exists. Please link to the existing parent org.", "danger")

    print(form.errors)
    return redirect(form.new_parent_form_path.raw_data[0].strip())


@orgs.route('/orgs/parent/delete', methods=["POST"])
@requires_role('admin')
def org_parent_delete():
    form = ParentOrgDelete(request.form)
    if form.validate_on_submit():
        parent_id = ObjectId(form.parent_delete_org_id.data)
        parent_org_collection.remove({'_id': parent_id})
        child_org_collection.update_many({'parent_org_id': parent_id},
                                         {"$set": {'parent_org_id': None,
                                                   'verified_by': None,
                                                   'reviewed_by': None,
                                                   'flagged': False,
                                                   'flagged_by': None,}})

    return redirect(form.parent_delete_form_path.raw_data[0].strip())


@orgs.route('/orgs/child/change-parent', methods=["POST"])
@requires_role('admin')
def child_org_change_parent():
    form = ChangeParentOrg(request.form)
    form.parent_org_id.choices = [(str(o['_id']), o['org_name']) for o in
                                  parent_org_collection.find().sort('org_name')]
    if form.validate_on_submit():
        child_org_collection.update_one({'org_id': form.org_id.data},
                                        {"$set": {'parent_org_id': ObjectId(form.parent_org_id.data),
                                                  'reviewed_by': current_user.name,
                                                  'verified_by': current_user.name,
                                                  'manually_updated': True,
                                                  'flagged': False,
                                                  'flagged_by': None,}})
        flash("Child organization's parent has been successfully changed", 'success')
    else:
        flash("Error updating child org.", "danger")
        print(form.errors)

    return redirect(form.change_parent_form_path.raw_data[0].strip())


@orgs.route('/orgs/child/<org_id>/review', methods=["GET", "POST"])
@login_required
def org_review(org_id):
    org = child_org_collection.find_one({'org_id': org_id})
    if confirm_has_lock(org['_id']) is None:
        flash('Org %s is being edited by someone else. You have been redirected to the next available org.' % org[
            'org_name'], 'danger')
        return redirect(url_for('orgs.orgs_queue'))

    reviewed = org['reviewed_by'] != None
    if reviewed:
        flash("This org has already been reviewed.", 'danger')
    form = VerifyOrg(request.form, **org)
    org_choices = [(str(o['_id']), o['org_name']) for o in
                   parent_org_collection.find().sort('org_name')]

    org_choices.insert(0, ("create", "Create new parent org"))
    org_choices.insert(0, ("", "Select one"))
    form.parent_org_id.choices = org_choices

    if request.method == "POST" and form.validate():
        if form.parent_org_id.data == 'create':

            try:
                parent_org_id = parent_org_collection.insert({'org_name': org['org_name'],
                                                              'reviewed_by': current_user.name,
                                                              'verified_by': None,
                                                              'name_ngrams': " ".join(make_ngrams(org['org_name'])),
                                                              'name_prefixes': " ".join(
                                                                  make_ngrams_from_beginning_of_phrase(
                                                                      org['org_name']))})

                flash("Added new parent organization", "success")

            except DuplicateKeyError:
                flash("Error - parent org already exists. Please link to the existing parent org.", "danger")
                return render_template('org_review.html', form=form, org=org, reviewed=reviewed)

        else:
            parent_org_id = ObjectId(form.parent_org_id.data)

        result = child_org_collection.update_many({'org_name': org['org_name']},
                                                  {'$set': {'parent_org_id': parent_org_id,
                                                            'reviewed_by': current_user.name
                                                            }})
        flash("Organization %s and %d others with the same name linked to parent org." % (
            org_id, result.modified_count - 1), "success")

        r.delete(str(org['_id']))
        return redirect(url_for('orgs.orgs_queue'))

    sims = get_org_sims(org['org_name'], org['_id'])

    return render_template('org_review.html', form=form, org=org, reviewed=reviewed, sims=sims)


@orgs.route('/orgs/child/<org_id>/finalize', methods=["GET", "POST"])
@login_required
def orgs_finalize(org_id):
    child_org = child_org_collection.find_one({'org_id': org_id})
    if confirm_has_lock(child_org['_id']) is None:
        flash('Org %s is being edited by someone else. You have been redirected to the next available org.' % child_org[
            'org_name'], 'danger')
        return redirect(url_for('orgs.orgs_queue'))

    can_verify = current_user.name != child_org['reviewed_by']
    if not can_verify:
        flash("You reviewed this org.", 'warning')

    form = VerifyOrg(request.form, **child_org)
    org_choices = [(str(o['_id']), o['org_name']) for o in
                   parent_org_collection.find().sort('org_name')]

    form.parent_org_id.choices = org_choices
    form.parent_org_id.default = str(child_org['parent_org_id'])

    if request.method == "POST" and form.validate():
        child_org_collection.update({'org_id': org_id},
                                    {"$set": {'parent_org_id': ObjectId(form.parent_org_id.data),
                                              'verified_by': current_user.name}})
        flash("%s finalized!" % child_org['org_name'], "success")
        r.delete(str(child_org['_id']))
        return redirect(url_for('orgs.orgs_queue'))

    sims = get_org_sims(child_org['org_name'], child_org['parent_org_id'])

    return render_template('org_finalize_child.html', form=form, org=child_org, can_verify=can_verify, sims=sims)


@orgs.route('/orgs/parent/<org_id>/finalize', methods=["GET", "POST"])
@login_required
def parent_orgs_verify(org_id):
    org_obj_id = ObjectId(org_id)
    org = parent_org_collection.find_one({'_id': org_obj_id})

    if confirm_has_lock(org_obj_id) is None:
        flash('Org %s is being edited by someone else. You have been redirected to the next available org.' % org[
            'org_name'], 'danger')
        return redirect(url_for('orgs.orgs_queue'))

    can_verify = current_user.name != org['reviewed_by']

    if not can_verify:
        flash("You reviewed this org.", 'warning')
    form = VerifyParentOrg(request.form, **org)
    if form.validate_on_submit():
        if form.verify.data:
            parent_org_id = parent_org_collection.update({'_id': org_obj_id},
                                                         {'$set': {'verified_by': current_user.name}})

            flash('Parent org %s finalize' % org['org_name'], 'success')
            return redirect(url_for('orgs.orgs_queue'))

        elif form.cancel.data:
            parent_org_collection.remove({'_id': org_obj_id})
            child_result = child_org_collection.update_many({'parent_org_id': org_obj_id},
                                                            {"$set": {'parent_org_id': None,
                                                                      'verified_by': None,
                                                                      'reviewed_by': None}})

            flash(
                'Parent org %s removed and %d child orgs unlinked' % (org['org_name'], child_result.modified_count),
                'success')

            r.delete(str(org_obj_id))
            return redirect(url_for('orgs.orgs_queue'))

    sims = get_org_sims(org['org_name'], org['_id'])

    return render_template("org_finalize_parent.html", org=org, form=form, can_verify=can_verify, sims=sims)


@orgs.route('/orgs/child/<child_org_id>/unlock', methods=["GET", "POST"])
@login_required
def child_org_unlock(child_org_id):
    org = child_org_collection.find_one({'org_id': child_org_id})
    r.delete(str(org['_id']))
    flash('Child org %s unlocked' % org['org_name'], 'success')
    return redirect(url_for('home'))


@orgs.route('/orgs/parent/<parent_org_id>/unlock', methods=["GET", "POST"])
@login_required
def parent_org_unlock(parent_org_id):
    org = parent_org_collection.find_one({'_id': ObjectId(parent_org_id)})
    r.delete(parent_org_id)
    flash('Parent org %s unlocked' % org['org_name'], 'success')
    return redirect(url_for('home'))


@orgs.route('/orgs/child/<child_org_id>/flag', methods=["GET", "POST"])
@login_required
def child_org_flag(child_org_id):
    org = child_org_collection.find_one({'org_id': child_org_id})
    result = child_org_collection.update({'_id': org['_id']},
                                         {'$set': {'flagged': True,
                                                   'flagged_by': current_user.name}})
    r.delete(str(org['_id']))
    flash('Child org %s flagged for follow up.' % org['org_name'], 'warning')
    return redirect(url_for('orgs.orgs_queue'))


@orgs.route('/orgs/parent/<parent_org_id>/flag', methods=["GET", "POST"])
@login_required
def parent_org_flag(parent_org_id):
    org = parent_org_collection.find_one({'_id': ObjectId(parent_org_id)})
    result = parent_org_collection.update({'_id': ObjectId(parent_org_id)},
                                          {'$set': {'flagged': True,
                                                    'flagged_by': current_user.name}})
    r.delete(parent_org_id)
    flash('Parent org %s flagged for follow up.' % org['org_name'], 'warning')
    return redirect(url_for('orgs.orgs_queue'))
