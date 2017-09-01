from flask import Blueprint, jsonify, request, make_response
from models import User
import re
import sys
from alerts.telegram_bots import Oanda_bot
from alerts.alerts_config import telegramApi
#webhook for telegram bots

telegram_blueprint = Blueprint("telegram", __name__, template_folder = "../templates")

Bot = Oanda_bot(telegramApi)

@telegram_blueprint.route("/thisisnotforyou", methods=["POST"])
def webhook():
    updates = request.get_json(force=True)
    user_telegram_id = updates["message"]["from"]["id"]
    if "text" in updates["message"]:
        text = updates["message"]["text"]
        try:
            user = User.get(User.telegram_id == user_telegram_id)
        except:
            user = None
        if not user:
            if text.startswith("Verify"):
                new_text = text.replace("Verify", "")
                final_text = new_text.strip()

                try:
                    user1 = User.get(User.username == final_text)
                except: 
                    user1 = None

                if user1:
                    user1.telegram_id = int(user_telegram_id)
                    user1.save()

                    success_message = "Congrats. Verification is successful. You will start receiving notifications from me"
                    Bot.send(user_telegram_id, success_message)
                else:
                    failure_message = "Verification failed. Sorry...."
                    Bot.send(user_telegram_id, failure_message)

            else:
                message = "Hey! Someone new. To get started, please verify yourself. Enter 'Verify <b>username</b>'. Ex 'Verify <b>panda24512</b>" 

                Bot.send(user_telegram_id, message)
        
        elif user:
            if len(text) == 6:
                Bot.notify_current_price(user_telegram_id, text)
            
            else:
                generic_reply = "Sorry. I am not authorised to talk much :( I do have a secret service to get a currency's current price for you. To use, reply with the currency pair XXXYYY. Ex: EURUSD or gbpusd"

                Bot.send(user_telegram_id, generic_reply)
    else:
        Bot.send(user_telegram_id, "Sorry, I do not understand you. Please talk to me in text.")
    
    return "ok"            