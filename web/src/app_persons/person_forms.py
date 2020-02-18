from flask_wtf import FlaskForm

from wtforms import (SelectField, StringField)

from wtforms.validators import DataRequired


class PersonForm(FlaskForm):
    first_name = StringField(validators=[DataRequired()])
    last_name = StringField(validators=[DataRequired()])
    person_type = SelectField(choices=[('MP', 'MP'), ('Senator', 'Senator')], validators=[DataRequired()])
    api_person_id = StringField(validators=[DataRequired()])