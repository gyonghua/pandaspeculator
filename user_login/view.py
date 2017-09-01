from models import User, init_user, Candlestick_sub_detail, OrderReport_sub_detail, Timeframe, Currency_pair
from flask_login import login_user, logout_user, login_required, current_user
from app import mail
from utils import make_hash, check_hash, generate_confirmation_token, confirm_token, send_confirmation_email, send_reset_email, authorized_user_required
from .forms import LoginForm, RegistrationForm, UserSettingForm, UserDeleteForm, UserProfileForm, AdminSettingForm, PasswordResetForm, PasswordChangeForm
from flask import Blueprint, jsonify, flash, request, make_response, render_template, redirect, url_for, abort
from flask_mail import Message

login_blueprint = Blueprint("login", __name__, template_folder = "../templates")


def get_user(username):
    try:
        user = User.get(User.username==username)
    except User.DoesNotExist:
        user = None

    return user

@login_blueprint.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("login.settings", username= current_user.username))

    form = LoginForm()
    if form.validate_on_submit():
        user = get_user(form.username.data)
        
        if user and check_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("login.settings", username = user.username))
        
        flash("Invalid username or password. Please register or try again.", "negative")
            
    return render_template("login.html", form = form)

@login_blueprint.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Log out successful.", "positive")
    return redirect(url_for("login.login"))

@login_blueprint.route("/register", methods=["GET", "POST"])
def register_user():
    form = RegistrationForm()

    if form.validate_on_submit():
        #unique email, username check is done in wtforms validation
        #create user, subscribes user to service and send confirmation email
        init_user(form.username.data, form.password.data, form.email.data)
        user = User.get(User.username==form.username.data)
        login_user(user)
        
        send_confirmation_email(form.email.data)

        return render_template("confirmation_email_sent.html", email = form.email.data)

    return render_template("register.html", form = form)

@login_blueprint.route("/confirm/<token>")
def confirm_email(token):
    
    email = confirm_token(token)
    if not email:
        flash("The confirmation link is invalid or expired.", "error")

    
    if email:
        try:    
            user = User.get(User.email==email)
        except:
            user = None
        if not user:
            flash("Error has occurred", "error")
        elif user.email_confirmed:
            flash("Email already confirmed.", "negative")
            if current_user.is_authenticated:
                return redirect(url_for("login.settings", username=current_user.username))
            else:
                return redirect(url_for("login.login"))
        else:
            user.email_confirmed = True
            user.save()
            flash("Email confirmed!", "positive")
            if current_user.is_authenticated:
                return redirect(url_for("login.settings", username=current_user.username))
            else:
                login_user(user)
                return redirect(url_for("login.settings", username=current_user.username))

    
    return redirect(url_for("login.login"))

@login_blueprint.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    form = PasswordResetForm()

    if form.validate_on_submit():
        try:
            user = User.get(User.email==form.email.data)
        except User.DoesNotExist:
            user = None
        
        if user and user.email_confirmed:
            send_reset_email(user.email, is_request_valid=True, username=user.username)
        else:
            send_reset_email(form.email.data)
        
        flash("Password reset email sent! Check your inbox", "positive")
        return redirect(url_for("login.login"))
            
    return render_template("password_reset.html", form=form)

@login_blueprint.route("/reset/<token>", methods=["GET", "POST"])
def password_change(token):
    email = confirm_token(token)
    if request.method == "GET":
        
        if not email:
            flash("The password reset link is invalid or expired.", "error")
            return redirect(url_for("login.login"))
        
    try:
        user = User.get(User.email==email)
    except User.DoesNotExist:
        user = None
    
    if not user:
        flash("User does not exist. Password change denied", "error")
        return redirect(url_for("login.login"))
    
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        user.password = make_hash(form.password.data)
        user.save()
        flash("password change successful", "positive")
        
        return redirect(url_for("login.login"))
        
        
    return render_template("password_change.html", form=form, token=token)


@login_blueprint.route("/user/<username>", methods=["GET", "POST"])
@authorized_user_required
@login_required
def settings(username):
    user = get_user(username)
    if not user:
        return abort(404)
    
    alert_subscriptions = Candlestick_sub_detail.select().join(Currency_pair).switch(Candlestick_sub_detail).join(Timeframe).where(Candlestick_sub_detail.username == username)
    order_subscription = OrderReport_sub_detail.select().where(OrderReport_sub_detail.username == username)
    
    alert_sub = {}
    
    for sub in alert_subscriptions:
        alert_sub[sub.pair.short_name + "_" + sub.timeframe.oanda_tf] = sub.is_subscribed
    
    alert_sub["ordersub"] = order_subscription[0].is_subscribed
    
    sub_form = UserSettingForm(data = alert_sub)
    admin_form = AdminSettingForm(obj = user)
    
    if sub_form.validate_on_submit():
    
        for field, value in sub_form.data.items():
            if len(field) == 5 or len(field) == 4:
                pair, tf = field.split("_")
                current_sub = alert_subscriptions.where((Candlestick_sub_detail.pair == pair) & 
                                                        (Candlestick_sub_detail.timeframe == tf))[0]
                
                if current_sub.is_subscribed != value:
                    
                    current_sub.is_subscribed = value 
                    current_sub.save()

            elif field == "ordersub":
                if order_subscription[0].is_subscribed != value:
                    order_subscription[0].is_subscribed = value
                    order_subscription[0].save()

        flash("Subscriptions updated.", "positive")
        return redirect(url_for("login.settings", username=username))
    
    return render_template("user.html", username=username, form = sub_form,admin_form=admin_form, user = user)

@login_blueprint.route("/admin/<username>/edit_profile", methods=["POST"])
@login_required
def admin_edit_profile(username):
    if current_user.role != "admin":
        return abort(401)
    
    user = get_user(username)
    if not user:
        return abort(404)

    admin_form = AdminSettingForm(obj = user)

    if admin_form.validate_on_submit():
        changes = 0
        if user.email != admin_form.email.data:
            try:
                check = User.get(User.email == admin_form.email.data)
            except User.DoesNotExist:
                check = None
            if check:
                changes += 1
                flash("email update unsuccessful. Email taken", "negative")
            else:
                user.email = admin_form.email.data
                changes += 1
                flash("email updated", "positive")

        if user.role != admin_form.role.data:
            if user.username == "pandasr":
                changes+=1
                flash("Cannot change role for pandasr", "negative")
            else:
                user.role = admin_form.role.data
                changes+=1
                flash("role updated", "positive")
        
        if user.email_confirmed != admin_form.email_confirmed.data:
            user.email_confirmed = admin_form.email_confirmed.data
            changes+=1
            flash("email_confirmed updated", "positive")
        
        if user.active != admin_form.active.data:
            user.active = admin_form.active.data
            changes+1
            flash("active state updated", "positive")
        
        user.save()
        if changes==0:
            flash("no profile changes detected", "warning")
        return redirect(url_for("login.settings", username=username))



@login_blueprint.route("/user/<username>/resend_email")
@authorized_user_required
@login_required
def resend_confirmation_email(username):
    user = get_user(username)
    
    send_confirmation_email(user.email)
    return render_template("confirmation_email_resend.html", email = user.email, username=username)


@login_blueprint.route("/user/<username>/delete_account", methods=["GET", "POST"])
@authorized_user_required
@login_required
def delete_account(username):
    form = UserDeleteForm(data = {"username" : username})

    if form.validate_on_submit():
        if form.username.data == "pandasr":
            flash("User cannot be deleted", "positive")
            return redirect(url_for("login.login"))
        else:
            user = User.delete().where(User.username == form.username.data)
            user.execute()
            flash("Account for {} deleted.".format(username), "negative")
            if current_user.role == "admin":
                return redirect(url_for("login.admin_panel"))
            else:
                return redirect(url_for("login.login"))
    
    return render_template("delete_account.html", username = username, form=form)

@login_blueprint.route("/user/<username>/change_details", methods=["GET", "POST"])
@login_required
def change_info(username):
    if current_user.username != username:
        return abort(401)

    user=get_user(username)
    form = UserProfileForm(data = {"email" : user.email})

    if form.validate_on_submit():
        if not check_hash(user.password, form.current_password.data):
            flash("Update fail. Current password does not match", "negative")
            return redirect(url_for('login.change_info', username = username))
        
        elif check_hash(user.password, form.current_password.data):
            #to process when email is different from user original. Also checking if new email is unique
            if user.email != form.email.data:
                email_check = User.select().where(User.email == form.email.data)
                if email_check.exist():
                    flash("email update unsuccessful. Email taken.", "negative")
                else:
                    user.email = form.email.data
                    user.email_confirmed = False
                    send_confirmation_email(form.email.data)
                    flash("Email update successful. Confirmation email sent. Please check your email to verify.", "positive")
            if form.password.data:
                user.password = make_hash(form.password.data)
                flash("Password update successful", "positive")
            
            user.save()
            return redirect(url_for('login.settings', username = username))

    return render_template("change_info.html", form = form, username=username)    

@login_blueprint.route("/admin_panel")
@login_required
def admin_panel():
    if current_user.role != "admin":
        return abort(401)
    
    users = User.select()
    return render_template("admin_panel.html", users = users)