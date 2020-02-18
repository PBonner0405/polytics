from flask_wtf import FlaskForm

from wtforms import (PasswordField, RadioField, SelectField, FieldList, FormField, StringField, TextAreaField,
                     IntegerField, BooleanField, SelectMultipleField, HiddenField, SubmitField)

class PersonSelector(FlaskForm):
    pid = SelectField('Person', choices=[])

class GroupSelector(FlaskForm):
    gid = SelectField('Group', choices=[])
