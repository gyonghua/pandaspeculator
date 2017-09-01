from models import User
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, HiddenField, SelectField
from wtforms.validators import InputRequired, EqualTo, Email, ValidationError, Optional

#custom validator to check unique value
def unique(Model, element, message=None):
    if not message:
        message = "This element is unique"
    def _unique(form, field):
        check = Model.select().where(element == field.data)
        if check.exists():
            raise ValidationError(message)

    return _unique

message = Markup("Email exist. <a href='/services'>Login?</a>")
    
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired("username required")])
    password = PasswordField("Password", validators=[InputRequired("password required")])

class UserProfileForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[InputRequired("password required")])
    email = StringField("Email", validators=[InputRequired("Email required"), Email("Please enter a valid email")])
    password = PasswordField("Change password (optional)", validators=[Optional()])

class AdminSettingForm(FlaskForm):
    email = StringField("email", validators=[InputRequired("Email required"), Email("Please enter a valid email")])
    role = SelectField("role", choices=[('admin', 'admin'), ('user', 'user')])
    active = BooleanField("is_active") 
    email_confirmed = BooleanField("email confirmed") 

class PasswordResetForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired("Email required"), Email("Please enter a valid email")])

class PasswordChangeForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired("Password required"), EqualTo("confirm", message="Passwords must match")])
    confirm = PasswordField("Repeat password", validators=[InputRequired("Please repeat password")])

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired("Username required"), unique(User, User.username, message="Username not available.")])
    email = StringField("Email", validators=[InputRequired("Email required"), Email("Please enter a valid email"), unique(User, User.email, message=message)])
    password = PasswordField("Password", validators=[InputRequired("Password required"), EqualTo("confirm", message="Passwords must match")])
    confirm = PasswordField("Repeat password", validators=[InputRequired("Please repeat password")])

class UserDeleteForm(FlaskForm):
    username = HiddenField("Username", validators=[InputRequired("Username required")])

class UserSettingForm(FlaskForm):
    EU_H1 = BooleanField("EURUSD")
    GU_H1 = BooleanField("GBPUSD")
    UJ_H1 = BooleanField("USDJPY")
    AU_H1 = BooleanField("AUDUSD")
    UC_H1 = BooleanField("USDCAD")
    EG_H1 = BooleanField("EURGBP")
    EJ_H1 = BooleanField("EURJPY")
    EU_H4 = BooleanField("EURUSD")
    GU_H4 = BooleanField("GBPUSD")
    UJ_H4 = BooleanField("USDJPY")
    AU_H4 = BooleanField("AUDUSD")
    UC_H4 = BooleanField("USDCAD")
    EG_H4 = BooleanField("EURGBP")
    EJ_H4 = BooleanField("EURJPY")
    EU_D = BooleanField("EURUSD")
    GU_D = BooleanField("GBPUSD")
    UJ_D = BooleanField("USDJPY")
    AU_D = BooleanField("AUDUSD")
    UC_D = BooleanField("USDCAD")
    EG_D = BooleanField("EURGBP")
    EJ_D = BooleanField("EURJPY")
    ordersub = BooleanField("Stop cluster report")

