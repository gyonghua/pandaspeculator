from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from multiprocessing.dummy import Process
from functools import wraps
from flask_login import current_user
from flask import copy_current_request_context, url_for, render_template, abort
from app import mail
from flask_mail import Message
from config import SECRET_KEY, CONFIRMATION_TOKEN_SALT

#password hashing
def make_hash(password):
    return generate_password_hash(password, method="pbkdf2:sha256:40000", salt_length=16)   


def check_hash(hashed_password, password):
    return check_password_hash(hashed_password, password)

#token generation and checking
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=CONFIRMATION_TOKEN_SALT)

def confirm_token(token, expiration=43200):
    serializer = URLSafeTimedSerializer(SECRET_KEY)

    try:
        email = serializer.loads(token,salt=CONFIRMATION_TOKEN_SALT, max_age=expiration)
    except:
        return False
    
    return email


#emails
def send_async_email(subject, sender, recipients, html_msg):

    @copy_current_request_context
    def send_mail():
        try:
            msg = Message(subject=subject, sender=sender, recipients=recipients, html=html_msg, bcc=["alerts@pandaspeculator.com"])
            mail.send(msg)
            return False
        except:
            return True
    
    thread = Process(target=send_mail)
    thread.daemon = True
    thread.start()    
    
def send_confirmation_email(user_email):
    token = generate_confirmation_token(user_email)

    confirm_url = url_for("login.confirm_email", token=token, _external=True)
    html = render_template("email_confirmation.html", confirm_url=confirm_url)
    sender = ("PandaSpeculator", "alerts@pandaspeculator.com")
    recipients=[user_email]
    subject="Confirm your email"

    return send_async_email(subject, sender, recipients, html)

def send_reset_email(user_email, is_request_valid = False, username = None):
    token = generate_confirmation_token(user_email)    
    
    if is_request_valid:
        try:
            user = User.get(User.email==user_email)
        except:
            user = None
        template = "email_password_reset_correct.html"
        reset_url = url_for("login.password_change", token=token, _external=True)
        html = render_template(template, reset_url=reset_url, username=username)    
    else:
        template = "email_password_reset_wrong.html"
        reset_url = url_for("login.reset_password", _external=True)
        html = render_template(template, reset_url=reset_url)

    sender = ("PandaSpeculator", "alerts@pandaspeculator.com")
    recipients=[user_email]
    subject="Password reset request"

    return send_async_email(subject, sender, recipients, html)

#decorators
def authorized_user_required(func):
    @wraps(func)
    def func_wrapper(username):
        if not (current_user.is_authenticated):
            return abort(401)
        elif not ((current_user.username == username) or (current_user.role == "admin")):
            return abort(401)

        else:
            return func(username)

    return func_wrapper
