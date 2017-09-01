from peewee import *
import arrow
from utils import make_hash


def unix_now():
    utc = arrow.utcnow()
    return utc.timestamp

#required to enable foreign key on cascade
class SqliteFKDatabase(SqliteDatabase):
    def initialize_connection(self, conn):
        self.execute_sql('PRAGMA foreign_keys=ON;')


db = SqliteFKDatabase("pandaspeculator.db")

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    user_id = IntegerField(primary_key=True)
    username = TextField(unique=True)
    password = TextField()
    email = TextField(unique=True)
    email_confirmed = BooleanField(default=False)
    telegram_id = IntegerField(unique=True, null=True)
    role = TextField(default="user")
    active = BooleanField(default=True)
    created_on = IntegerField(default=unix_now)
    subscribed_till = IntegerField(null=True)

    def add_user(username, password, email):   
        hashed_password = make_hash(password)
        User.insert(username=username, email=email, password=hashed_password).execute() 
    
    #methods for Flask-login
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.user_id)

    def is_active(self):
        if self.active == 1:
            return True
        else:
            return False

class Timeframe(BaseModel):
    tf_id = IntegerField(primary_key=True)
    oanda_tf = TextField(unique=True)
    full_name = TextField(unique=True)

class Currency_pair(BaseModel):
    pair_id = IntegerField(primary_key=True)
    short_name = TextField(unique=True)
    full_name = TextField(unique=True)

class Subscription_type(BaseModel):
    sub_id = IntegerField(primary_key=True)
    name = TextField(unique=True)
    description = TextField(unique=True) 

class Candlestick_sub_detail(BaseModel):
    sub_id = IntegerField(primary_key=True)
    subscription_type = ForeignKeyField(Subscription_type, on_delete="CASCADE", on_update="CASCADE")
    username = ForeignKeyField(User, db_column="username", to_field="username", on_delete="CASCADE", on_update="CASCADE")
    pair = ForeignKeyField(Currency_pair, db_column="pair", to_field="short_name", on_delete="CASCADE", on_update="CASCADE")
    timeframe = ForeignKeyField(Timeframe, db_column="timeframe", to_field="oanda_tf", on_delete="CASCADE", on_update="CASCADE")
    is_subscribed = BooleanField(default=True)

    class Meta:
        indexes = (
            (("username", "pair", "timeframe"), True),
        )
class OrderReport_sub_detail(BaseModel):
    sub_id = IntegerField(primary_key=True)
    subscription_type = ForeignKeyField(Subscription_type, on_delete="CASCADE", on_update="CASCADE")
    username = ForeignKeyField(User, db_column="username", to_field="username", on_delete="CASCADE", on_update="CASCADE")
    is_subscribed = BooleanField(default=True)

def create_tables():
    db.connect()
    db.create_tables([User, Timeframe, Currency_pair, Subscription_type, Candlestick_sub_detail, OrderReport_sub_detail])

#initial information for insertion
def insert_tf():
    timeframe = [
        {"oanda_tf": "H1", "full_name" : "1 hour"},
        {"oanda_tf": "H4", "full_name" : "4 hour"},
        {"oanda_tf": "D", "full_name" : "daily"}
    ]
    
    with db.atomic():
        Timeframe.insert_many(timeframe).execute()


def insert_pairs():
    pairs = [
        {"short_name" : "EU", "full_name" : "EURUSD"}, 
        {"short_name" : "GU", "full_name" : "GBPUSD"}, 
        {"short_name" : "UJ", "full_name" : "USDJPY"}, 
        {"short_name" : "AU", "full_name" : "AUDUSD"}, 
        {"short_name" : "UC", "full_name" : "USDCAD"}, 
        {"short_name" : "EG", "full_name" : "EURGBP"}, 
        {"short_name" : "EJ", "full_name" : "EURJPY"} 
    ]

    with db.atomic():
        Currency_pair.insert_many(pairs).execute()


def insert_subtype():
    subtype = [
        {"name": "candlestick alerts", "description" : "Bar pattern alerts on telegram as they occur. H1, 4H and daily timeframe available"},
        {"name": "stop orders cluster report", "description" : "daily email on prices with highest net stop orders"},
    ]
    
    with db.atomic():
        Subscription_type.insert_many(subtype).execute()


def update_telegram_id(telegram_id):
    pass

def grant_access_candle(username):
    #all new users should be subscribed to all alerts
    subs = [
        {"subscription_type" : 1, "username" : username, "pair" : "EU", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "EU", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "EU", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "GU", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "GU", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "GU", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "UJ", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "UJ", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "UJ", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "AU", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "AU", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "AU", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "UC", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "UC", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "UC", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "EG", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "EG", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "EG", "timeframe" : "D"},
        {"subscription_type" : 1, "username" : username, "pair" : "EJ", "timeframe" : "H1"},
        {"subscription_type" : 1, "username" : username, "pair" : "EJ", "timeframe" : "H4"},
        {"subscription_type" : 1, "username" : username, "pair" : "EJ", "timeframe" : "D"},
    ]

    with db.atomic():
        Candlestick_sub_detail.insert_many(subs).execute()

def grant_access_order(username):
    OrderReport_sub_detail.insert(subscription_type=2, username=username).execute()


def init_user(username, password, email):
    User.add_user(username, password, email)
    grant_access_candle(username)
    grant_access_order(username)


