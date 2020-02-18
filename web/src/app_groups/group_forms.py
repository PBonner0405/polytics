from flask_wtf import FlaskForm

from wtforms import (SelectMultipleField, StringField)
from bson import ObjectId
from wtforms.validators import DataRequired


class GroupForm(FlaskForm):
    group_id = StringField(validators=[DataRequired()])
    group_name = StringField(validators=[DataRequired()])
    group_members = SelectMultipleField(choices=[], coerce=ObjectId, validators=[DataRequired()])
