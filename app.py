import config
from flask import Flask, render_template
from flask_mail import Mail

app = Flask(__name__)
#setup for Flask-Mail
mail = Mail(app)
app.config.from_object(config)

@app.route("/")
def homepage():
    return render_template("eventually.html")


mail.init_app(app)
