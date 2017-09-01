from models import User, OrderReport_sub_detail
from alerts.telegram_bots import Oanda_bot
from alerts.alerts_config import telegramApi, emailPassword
from jinja2 import Environment, PackageLoader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

env = Environment(loader=PackageLoader("alerts", "templates"))
template = env.get_template("orders_email.html")

forex_pairs = ["EUR_USD","GBP_USD", "AUD_USD", "EUR_GBP", "USD_CAD","USD_JPY", "EUR_JPY"]

Alert = Oanda_bot(telegramApi)

#settings
fromaddr = "alerts@pandaspeculator.com"
msg = MIMEMultipart("alternative")
name = "PandaSpeculator <{}>".format(fromaddr)
msg["From"] = name
msg["Date"] = formatdate(localtime=True)

orderbook = list()
for pair in forex_pairs:
    average_daily_range = round(Alert.get_ADR(pair, "D", 20), 4)
    net_orders = Alert.get_latest_net_orders(pair)
    formatted_pair = pair.replace("_", "")
    current_price = Alert.get_current_price(formatted_pair)
    tup = (net_orders, current_price, average_daily_range)
    orderbook.append(tup)

users = User.select(User.email).join(OrderReport_sub_detail).where(
            (User.active == True) &
            (User.email_confirmed == True) &
            (OrderReport_sub_detail.is_subscribed == True)).tuples()


msg["Subject"] = "Forex stop-cluster report. " + str(orderbook[0][0][0]) + " GMT"
html = template.render(orderbook = orderbook)
content = MIMEText(html, "html")
msg.attach(content)

server = smtplib.SMTP_SSL("aus.mxroute.com", 465)
server.login(fromaddr, emailPassword)
for user in users:
    del msg["To"] #this line is needed, else there will be multiple To fields in email sent
    msg["To"] = user[0]
    server.sendmail(fromaddr, [user[0], fromaddr], msg.as_string())
server.quit()