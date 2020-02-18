__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint, jsonify

from data_model import *

from app_persons.person_forms import PersonForm
from app_user_mgmt.user_utils import requires_role

from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from bson import ObjectId

person_views = Blueprint('person_views', __name__, template_folder='templates')


@person_views.route('/person', methods=["GET"])
@requires_role('admin')
def person_list():
    persons = person_collection.find().sort('last_name')
    return render_template('person_list.html', persons=persons)


@person_views.route('/person/<person_id>/edit', methods=["GET", "POST"])
@requires_role('admin')
def person_edit(person_id):
    person_id = ObjectId(person_id)
    person = person_collection.find_one({'_id': person_id})
    form = PersonForm(request.form, **person)

    if form.validate_on_submit():
        try:
            person_collection.update({'_id': person_id}, {'$set': dict(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                full_name="%s %s" % (form.first_name.data, form.last_name.data),
                person_type=form.person_type.data,
                api_person_id=form.api_person_id.data)
            })
            flash('Person saved!', 'success')
            return redirect(url_for('person_views.person_list'))

        except DuplicateKeyError:
            flash("Error - that person api ID already exists. Please verify you are using the correct one.", "danger")
            form.api_person_id.data = person['api_person_id']
    return render_template('person_form.html', form=form, title="Edit Person")


@person_views.route('/person/new', methods=["GET", "POST"])
@requires_role('admin')
def person_new():
    form = PersonForm(request.form)

    if form.validate_on_submit():
        try:
            full_name = "%s %s" % (form.first_name.data, form.last_name.data)

            person_collection.insert({'first_name': form.first_name.data,
                                      'last_name': form.last_name.data,
                                      'full_name': full_name,
                                      'person_type': form.person_type.data,
                                      'api_person_id': form.api_person_id.data,})


            flash('Person created.', 'success')
            return redirect(url_for('person_views.person_list'))

        except DuplicateKeyError:
            flash("Error - that person API ID already exists. Please verify you are using the correct one.", "danger")
            form.api_person_id.data = ""
    return render_template('person_form.html', form=form, title="Create Person")