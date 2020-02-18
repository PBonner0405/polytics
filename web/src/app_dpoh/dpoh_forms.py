from flask_wtf import FlaskForm
from wtforms import Form as NoCsrfForm


from wtforms import (PasswordField, RadioField, SelectField, FieldList, FormField, StringField, TextAreaField,
                     IntegerField, BooleanField, SelectMultipleField, HiddenField, SubmitField)

from wtforms.validators import DataRequired, Email


class DpohToPerson(FlaskForm):
    person_id = SelectField('Select MP/Senator', validators=[DataRequired()])

class DPHOSearchForm(NoCsrfForm):
    search = StringField("Find name")