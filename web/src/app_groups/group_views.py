__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint, jsonify

from data_model import *

from app_groups.group_forms import GroupForm
from app_user_mgmt.user_utils import requires_role

from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from bson import ObjectId

group_views = Blueprint('group_views', __name__, template_folder='templates')


@group_views.route('/group', methods=["GET"])
@requires_role('admin')
def group_list():
    groups = group_collection.find().sort('name')
    return render_template('group_list.html', groups=groups)


@group_views.route('/group/add', methods=["GET", "POST"])
@requires_role('admin')
def group_add():
    form = GroupForm(request.form)

    form.group_members.choices = [(p['_id'], "%s (%s)" % (p['full_name'], p['person_type'])) for p in
                                  person_collection.find({'person_type': {'$in': ('MP', 'Senator')}}).sort('last_name')]

    if form.validate_on_submit():
        try:

            group_collection.insert({'group_id': form.group_id.data,
                                     'group_name': form.group_name.data,
                                     'group_members': form.group_members.data
                                     })

            flash('Group created.', 'success')
            return redirect(url_for('group_views.group_list'))

        except DuplicateKeyError:
            flash("Error - that group ID already exists. Please try another.", "danger")
    return render_template('group_form.html', form=form, title="Create Group")


@group_views.route('/group/<group_id>/edit', methods=["GET", "POST"])
@requires_role('admin')
def group_edit(group_id):
    group = group_collection.find_one({'group_id': group_id})
    if not group:
        flash('That group does not exist!', 'danger')
        return redirect(url_for('group_views.group_list'))

    form = GroupForm(request.form, **group)
    form.group_members.choices = [(p['_id'], "%s (%s)" % (p['full_name'], p['person_type'])) for p in
                                  person_collection.find({'person_type': {'$in': ('MP', 'Senator')}}).sort('last_name')]


    if form.validate_on_submit():
        try:
            group_collection.update({'group_id': group_id}, {'$set':
                                                                 {'group_id': form.group_id.data,
                                                                  'group_name': form.group_name.data,
                                                                  'group_members': form.group_members.data
                                                                  }})

            flash('Group saved!', 'success')
            return redirect(url_for('group_views.group_list'))

        except DuplicateKeyError:
            flash("Error - that group ID already exists. Please try another.", "danger")
    return render_template('group_form.html', form=form, title="Edit Person")
