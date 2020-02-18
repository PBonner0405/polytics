__author__ = 'Mike'

from flask import Flask, request, render_template, redirect, url_for, flash, abort
from flask_wtf.csrf import CSRFProtect
from app_user_mgmt.user_views import user_mgmt
from app_user_mgmt.user_utils import load_user, AnonymousUser
from app_dpoh.dpoh_views import dpoh
from app_persons.person_views import person_views
from app_groups.group_views import group_views
from data_model import *

from flask_login import (LoginManager, current_user, login_required)
from app_user_mgmt.user_utils import requires_role
from app_orgs.org_views import orgs
from app_api.api_mgmt_views import api
from bson import ObjectId
import pytz
import re

app = Flask(__name__)
app.register_blueprint(user_mgmt)
app.register_blueprint(orgs)
app.register_blueprint(api)
app.register_blueprint(dpoh)
app.register_blueprint(person_views)
app.register_blueprint(group_views)


app.secret_key = '7XMM16OY34Q91NTEI86VMJAMW3TA2KPM5I6O'

app.config.from_object(__name__)

csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.login_view = "user_mgmt.login"
login_manager.login_message = u"Please log in to access this page."
login_manager.refresh_view = "reauth"
login_manager.init_app(app)
login_manager.user_loader(load_user)
login_manager.anonymous_user = AnonymousUser


@app.route("/")
def home():
    if current_user.is_authenticated:
        return render_template('_base.html')
    else:
        return "Home"

@app.route('/status')
@requires_role('admin')
def status():
    n = dict(
        dpoh_names_to_review=dpoh_name_collection.count({'reviewed_by': None}),
        dpoh_names_to_finalize=dpoh_name_collection.count({'reviewed_by': {'$ne': None},
                                                           'verified_by': None}),
        dpoh_names_finalized=dpoh_name_collection.count({'reviewed_by': {'$ne': None},
                                                         'verified_by': {'$ne': None}}),
        child_org_to_review=child_org_collection.count({'reviewed_by': None}),
        child_org_to_verify=child_org_collection.count({'reviewed_by': {'$ne': None},
                                                        'verified_by': None}),
        child_org_finalized=child_org_collection.count({'reviewed_by': {'$ne': None},
                                                        'verified_by': {'$ne': None}}),
        parent_org_to_verify=parent_org_collection.count({'verified_by': None}),
        parent_org_finalized=parent_org_collection.count({'reviewed_by': {'$ne': None},
                                                          'verified_by': {'$ne': None}}),
)

    return render_template("status.html", n=n)


@app.template_filter('date_str')
def date_str(value):
    if value:
        dt = value.replace(tzinfo=pytz.UTC)
        return dt.astimezone(pytz.timezone("Canada/Eastern")).strftime("%B %d, %Y %H:%M %Z")
    else:
        return None


@app.template_filter('naive_date_only_str')
def date_str(value):
    if value:
        return value.strftime("%B %d, %Y")
    else:
        return None

@app.template_filter('name_from_id')
def person_id_to_name(value):
    if value:
        person = person_collection.find_one({"_id": value})
        return person['full_name']
    else:
        return None


@app.context_processor
def to_verify():
    return dict(dpoh_names_to_review=dpoh_name_collection.count({'reviewed_by': None, 'flagged': {'$ne': True}},),
                dpoh_names_to_verify=dpoh_name_collection.count({'reviewed_by': {'$nin': (None, current_user.name)},
                                                                 'verified_by': None,
                                                                 'flagged': {'$ne': True}}),
                child_org_to_review=child_org_collection.count({'reviewed_by': None, 'flagged': {'$ne': True}}),
                child_org_to_verify=child_org_collection.count({'reviewed_by': {'$nin': (None, current_user.name)},
                                                                'verified_by': None,
                                                                'flagged': {'$ne': True}}),
                parent_org_to_verify=parent_org_collection.count({'verified_by': None, 'flagged': {'$ne': True}}),
                flagged_dpoh_name_count=dpoh_name_collection.count({'flagged': True}),
                flagged_parent_orgs=parent_org_collection.count({'flagged': True}),
                flagged_child_orgs=child_org_collection.count({'flagged': True})
                )


if __name__ == "__main__":
    app.run(debug=True)
    # app.run(host='0.0.0.0', debug=True)
