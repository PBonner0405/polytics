from flask_wtf import FlaskForm
from wtforms import (PasswordField, RadioField, SelectField, FieldList, FormField, StringField, TextAreaField,
                     IntegerField, BooleanField, SelectMultipleField)
from wtforms.validators import DataRequired, Email

roles = [("admin", "admin"), ("staff", "staff")]

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    roles = SelectMultipleField('Select Role', choices=roles, default="staff", validators=[DataRequired()])
    active = BooleanField("Active", default=True)
    email = StringField("Email address", validators=[DataRequired(), Email()])
    email_system_updates = BooleanField("Send system updates", default=False)


class EditUserForm(UserForm):
    password = PasswordField('Password', validators=[])



class ChangePassword(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])

