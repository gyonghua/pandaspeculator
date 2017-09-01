from models import User
from movieapi import api_blueprint
from telegram import telegram_blueprint
from user_login import login_blueprint
from flask_login import LoginManager
from app import app

# init flask-login module
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.get(User.user_id==user_id)
    except User.DoesNotExist:
        user = None
    
    return user

app.register_blueprint(api_blueprint, url_prefix="/api")
app.register_blueprint(telegram_blueprint, url_prefix="/telegram")
app.register_blueprint(login_blueprint, url_prefix="/services")


if __name__ == "__main__":
    app.run()