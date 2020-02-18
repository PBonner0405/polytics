from flask_wtf import FlaskForm
from wtforms import Form as NoCsrfForm


from wtforms import (PasswordField, RadioField, SelectField, FieldList, FormField, StringField, TextAreaField,
                     IntegerField, BooleanField, SelectMultipleField, HiddenField, SubmitField)

from wtforms.validators import DataRequired, Email


class VerifyOrg(FlaskForm):
    org_id = HiddenField()
    parent_org_id = SelectField('Parent Organization', choices=[], validators=[DataRequired()])


class VerifyParentOrg(FlaskForm):
    parent_org_oid = HiddenField()
    verify = SubmitField("Finalize parent org creation")
    cancel = SubmitField("Reject parent org")


class OrgSearchForm(NoCsrfForm):
    search = StringField("Find org name")


class ParentOrgNew(FlaskForm):
    new_parent_form_path = HiddenField(validators=[DataRequired()])
    new_parent_org_name = StringField("New parent organization name:", validators=[DataRequired()])

class ParentOrgEdit(FlaskForm):
    parent_edit_form_path = HiddenField(validators=[DataRequired()])
    parent_edit_org_id = HiddenField(validators=[DataRequired()])
    parent_edit_org_new_name = StringField("New name for parent organization:", validators=[DataRequired()])

class ParentOrgDelete(FlaskForm):
    parent_delete_form_path = HiddenField(validators=[DataRequired()])
    parent_delete_org_id = HiddenField(validators=[DataRequired()])

class ChangeParentOrg(FlaskForm):
    org_id = HiddenField()
    parent_org_id = SelectField('Parent Organization', choices=[], validators=[DataRequired()])
    change_parent_form_path = HiddenField()
