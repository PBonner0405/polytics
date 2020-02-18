__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, Blueprint


from data_model import *

from app_user_mgmt.forms import LoginForm, UserForm, EditUserForm, ChangePassword

from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from app_user_mgmt.user_utils import make_user, requires_role, pw_complexity, get_duplicate_username_field_from_error
from passlib.hash import pbkdf2_sha256
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import sys

user_mgmt = Blueprint('user_mgmt', __name__,
                        template_folder='templates')


@user_mgmt.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data
        user_dict = user_collection.find_one({"username": username})
        if user_dict:
            if pbkdf2_sha256.verify(password, user_dict[u"password"]):
                print(user_dict)
                user = make_user(user_dict)
                if login_user(user):
                    flash("Logged in!", "success")
                    return redirect(url_for("home"))

        flash("Sorry, but you could not log in.", "danger")

    return render_template('login.html', form=form)


@user_mgmt.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("user_mgmt.login"))


@user_mgmt.route("/users")
@requires_role('admin')
def user_list():
    users = user_collection.find()
    return render_template("user_list.html",
                           users=users
                           )


@user_mgmt.route("/users/new", methods=['GET', 'POST'])
@requires_role('admin')
def user_add():
    new_user = True
    form = UserForm(request.form)
    if request.method == 'POST' and form.validate():
        password = pbkdf2_sha256.hash(form.password.data)

        try:
            user_collection.insert({u"username": form.username.data,
                                    u"password": password,
                                    u"roles": form.roles.data,
                                    u"active": form.active.data,
                                    u'email': form.email.data,
                                    u'email_system_updates': form.email_system_updates.data,
                                    u"most_recent_activity": None,
                                    })

            flash("user created", "success")
            return redirect(url_for('user_mgmt.user_list'), code=302)

        except DuplicateKeyError:
            error_field = get_duplicate_username_field_from_error(sys.exc_info())
            if error_field == 'username':
                flash("Error - username already exists. Please try another.", "danger")

    return render_template("user_form.html", form=form, title="Add User", new_user=new_user)


@user_mgmt.route("/users/<uid>/edit", methods=['GET', 'POST'])
@requires_role('admin')
def user_edit(uid):
    uid_obj_id = ObjectId(uid)
    user_dict = user_collection.find_one({u"_id": uid_obj_id})

    new_user = False
    title = "Edit user"

    form = EditUserForm(request.form, **user_dict)

    if request.method == 'POST' and form.validate():
        update_dict = {}
        update_dict["roles"] = form.roles.data
        update_dict["username"] = form.username.data
        update_dict['active'] = form.active.data
        update_dict['email'] = form.email.data
        update_dict['email_system_updates'] = form.email_system_updates.data

        if form.password.data:
            if pw_complexity(form.password.data):
                update_dict["password"] = pbkdf2_sha256.hash(form.password.data)
            else:
                flash("Password not changed. It needs to be 8 characters and at least one uppercase, lowercase, and number character.", "danger")

                #TODO Find a more elegant way to code this
                return render_template("user_form.html", form=form, title=title, user_dict=user_dict, uid=uid, new_user=new_user)


        try:
            user_collection.update({"_id": uid_obj_id}, {'$set': update_dict})
            flash("User updated", "success")
            return redirect(url_for('user_mgmt.user_edit', uid=uid), code=302)
        except DuplicateKeyError:
            error_field = get_duplicate_username_field_from_error(sys.exc_info())
            if error_field == 'username':
                flash("Error - username already exists. Please try another.", "danger")
                form.username.data = user_dict['username']

    return render_template("user_form.html", form=form, title=title, user_dict=user_dict, uid=uid, new_user=new_user)


@user_mgmt.route("/users/current/change-pw", methods=['GET', 'POST'])
@login_required
def user_change_password():
    user_obj_id = ObjectId(current_user.get_id())
    user_dict = user_collection.find_one({"_id": user_obj_id})
    form = ChangePassword(request.form, **user_dict)

    if request.method == "POST" and form.validate():
        if pbkdf2_sha256.verify(form.current_password.data, user_dict[u"password"]):
            if form.new_password.data == form.confirm_password.data:
                if pw_complexity(form.new_password.data):
                    pw_hash = pbkdf2_sha256.hash(form.new_password.data)
                    user_collection.update({"_id": user_obj_id}, {'$set': {"password": pw_hash}})
                    flash("Password changed", "success")
                else:
                    flash("Password not changed. It needs to be 8 characters and at least one uppercase, lowercase, and number character.", "danger")

            else:
                flash("New password and confirm new password do not match. Please try again.", "danger")

        else:
            flash("Incorrect current password. Please try again.", "danger")
    return render_template("user_pw.html", form=form)


@user_mgmt.route("/users/<uid>/delete", methods=['GET', 'POST'])
@login_required
@requires_role('admin')
def user_delete(uid):
    user_dict = user_collection.remove({u"_id": ObjectId(uid)})
    flash("User deleted", 'success')
    return redirect(url_for('user_mgmt.user_list'), code=302)

