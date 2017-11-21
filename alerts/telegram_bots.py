from models import User, Candlestick_sub_detail, Currency_pair
import requests
import json
import arrow
from alerts.alerts_config import oandaApi, live_account, account_id

class Telegram_bot:
    def __init__(self, telegramApi):
        self._url = "https://api.telegram.org/bot"
        self._api = telegramApi

    def send(self, chat_id, message):
        method = "/sendMessage"
        payload = {
            "chat_id" : chat_id,
            "text" : message,
            "parse_mode" : "HTML"
        }

        sendMessage = requests.get(self._url + self._api + method, params=payload)
        response = sendMessage.json() 
        return response["ok"]


class Oanda_bot(Telegram_bot):
    _headers = {"Authorization":oandaApi,
               "Content-Type": "application/x-www-form-urlencoded",
               "X-Accept-Datetime-Format" : "UNIX"
              }
    fxpractice = "https://api-fxpractice.oanda.com"
    fxlive = "https://api-fxtrade.oanda.com/"
    _base_url = fxlive if live_account else fxpractice
    
    
    def create_stop_order(self, trigger_price, stop_loss, take_profit, side, instrument, units=1):
        """units: unit to open, side: [buy, sell],  instrument: EUR_USD"""
        
        endpoint = "/v1/accounts/{}/orders".format(account_id)
        expiry = arrow.utcnow().shift(hours=+23).timestamp

        if "JPY" in instrument:
            trigger_price = round(trigger_price, 2)
            stop_loss = round(stop_loss, 2)
            take_profit = round(take_profit, 2)

        payload = {
            "instrument" : instrument,
            "units" : units,
            "side" : side,
            "type" : "stop",
            "expiry" : expiry,
            "price" : trigger_price, 
            "stopLoss" : stop_loss,
            "takeProfit" : take_profit
        }

        response = requests.post(Oanda_bot._base_url + endpoint, headers=Oanda_bot._headers, data=payload)
        return response.json()
    
    def get_current_price(self, pair):
        endpoint = "/v1/prices"
        modified_pair = pair[:3] + "_" + pair[3:]
        cleaned_pair = modified_pair.upper()
        payload = {
            "instruments" : cleaned_pair
        }

        response = requests.get(Oanda_bot._base_url + endpoint, headers=Oanda_bot._headers, params=payload)
        price = response.json()
        if "message" in price:
            return price["message"]
        else:
            bid = price["prices"][0]["bid"]
            ask = price["prices"][0]["ask"]
            
            return str(bid) + "/" + str(ask)
        
    def notify_current_price(self,chat_id, pair):
        price = self.get_current_price(pair)
        message = "{} : {}".format(pair, price)
        return self.send(chat_id, message)

    @classmethod
    def getCandles(cls, pair, tf, count=30):
        """returns a json requests object. gets the last 30 candles, not including the current candle"""
        endpoint = "/v1/candles"
        now = arrow.utcnow()
        previous_hourUNIX = now.shift(hours=-1).timestamp
        candleformat = "midpoint"

        payload = {
        "instrument" : pair,
        "granularity" : tf,
        "count" : count,
        "end" : previous_hourUNIX,
        "alignmentTimezone" : "GMT",
        "dailyAlignment" : 22,
        "candleFormat" : candleformat
        }
        candles = requests.get(Oanda_bot._base_url + endpoint,  
                               headers=Oanda_bot._headers, 
                               params=payload)

        return candles

    def get_orderbook(self, pair):
        endpoint = "labs/v1/orderbook_data"

        payload = {
            "instrument" : pair,
            "period" : 3600
        }

        response = requests.get(Oanda_bot._base_url + endpoint, 
                                headers=Oanda_bot._headers, 
                                params=payload)
        return response.json()
    
    def get_latest_net_orders(self, pair):
        orderbook = self.get_orderbook(pair)

        latest_orderbook_timestamp = max(orderbook, key=int)
        latest_time = arrow.get(latest_orderbook_timestamp).format("D MMM HH:mm")
        orderbook_rate = float(orderbook[latest_orderbook_timestamp]["rate"])

        net_buystop_orders = []
        net_sellstop_orders = []
        orderbook_prices = orderbook[latest_orderbook_timestamp]["price_points"] 
        for key in orderbook_prices:
        
            if float(key) > orderbook_rate:
                tup = (key, round(orderbook_prices[key]["ol"] - orderbook_prices[key]["os"], 5))
                net_buystop_orders.append(tup)
            elif float(key) < orderbook_rate:
                tup = (key,round(orderbook_prices[key]["os"]- orderbook_prices[key]["ol"], 5))
                net_sellstop_orders.append(tup)

        #arrange by highest percentage first
        sorted_net_buystop_orders = sorted(net_buystop_orders, key = lambda x: x[1], reverse=True)   
        sorted_net_sellstop_orders = sorted(net_sellstop_orders, key = lambda x: x[1], reverse=True)    
        top_5_buy_order_vol = []
        top_5_sell_order_vol = []

        for no in range(5):
            top_5_buy_order_vol.append(sorted_net_buystop_orders[no])
            top_5_sell_order_vol.append(sorted_net_sellstop_orders[no])

        return latest_time, pair, top_5_buy_order_vol, top_5_sell_order_vol
    
    def get_ADR(self, pair, tf, count):
        data = Oanda_bot.getCandles(pair, tf, count).json()
        candles = data["candles"]
        daily_ranges = [candle["highMid"] - candle["lowMid"] for candle in candles]

        average_daily_range = sum(daily_ranges)/count

        return average_daily_range


class Bar_pattern_bot(Oanda_bot):
    pairs_master_list = ["EUR_USD", "GBP_USD", "AUD_USD", "EUR_GBP", "USD_CAD","USD_JPY", "EUR_JPY"]
    def __init__(self, api, tf):
        super(Oanda_bot, self).__init__(api)
        self.tf = tf
        self.pairs = {}
    
    def getCandles(self, pair):
        timeframe = self.tf
        return Oanda_bot.getCandles(pair, timeframe)

    @classmethod
    def _isBullishOutsideBar(cls, latestCandle, previousCandle, secondlastCandle):
        criteria_1 = latestCandle["highMid"] > previousCandle["highMid"]
        criteria_2 = latestCandle["lowMid"] < previousCandle["lowMid"]
        criteria_3 = latestCandle["closeMid"] > previousCandle["highMid"]
        criteria_4 = latestCandle["highMid"] > secondlastCandle["highMid"]
        criteria_5 = latestCandle["lowMid"] < secondlastCandle["lowMid"]

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isBearishOutsideBar(cls, latestCandle, previousCandle, secondlastCandle):
        criteria_1 = latestCandle["highMid"] > previousCandle["highMid"]
        criteria_2 = latestCandle["lowMid"] < previousCandle["lowMid"]
        criteria_3 = latestCandle["closeMid"] < previousCandle["lowMid"]
        criteria_4 = latestCandle["highMid"] > secondlastCandle["highMid"]
        criteria_5 = latestCandle["lowMid"] < secondlastCandle["lowMid"]

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isTopPin(cls, latestCandle, previousCandle):
        criteria_1 = latestCandle["closeMid"] < previousCandle["highMid"] 
        criteria_2 = latestCandle["lowMid"] > previousCandle["lowMid"]
        criteria_3 = latestCandle["highMid"] > previousCandle["highMid"]

        previousBarRange = previousCandle["highMid"] - previousCandle["lowMid"]

        distance_1 = previousCandle["highMid"] - latestCandle["lowMid"]
        distance_2 = latestCandle["highMid"] - previousCandle["highMid"]

        criteria_4 = distance_2 > distance_1
        criteria_5 = previousBarRange > 0.0010 # this has an issue for jpy and usd pairs. To improve with percentage instead

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isBottomPin(cls, latestCandle, previousCandle):

        criteria_1 = latestCandle["lowMid"] < previousCandle["lowMid"]
        criteria_2 = latestCandle["closeMid"] > previousCandle["lowMid"]
        criteria_3 = latestCandle["highMid"] < previousCandle["highMid"]

        previousBarRange = previousCandle["highMid"] - previousCandle["lowMid"]

        distance_1 = latestCandle["highMid"] - previousCandle["lowMid"]
        distance_2 = previousCandle["lowMid"] - latestCandle["lowMid"]

        criteria_4 = distance_2 > distance_1
        criteria_5 = previousBarRange > 0.0010

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isUpTrend(cls, sorted_candles):
        candleLows = [candle["lowMid"] for candle in sorted_candles]

        return candleLows[0] > min(candleLows)

    @classmethod
    def _isDownTrend(cls, sorted_candles):
        candleHighs = [candle["highMid"] for candle in sorted_candles]

        return candleHighs[0] < max(candleHighs)


    def _detectPattern(self, pair):
        data = self.getCandles(pair).json()
        candles = data["candles"]
        sorted_candles = sorted(candles, key=lambda k: k["time"], reverse=True)
        latestCandle = sorted_candles[0]
        previousCandle = sorted_candles[1]
        secondlastCandle = sorted_candles[2]
        uptrend = Bar_pattern_bot._isUpTrend(sorted_candles)
        downtrend = Bar_pattern_bot._isDownTrend(sorted_candles)

        if Bar_pattern_bot._isTopPin(latestCandle, previousCandle):
            return "{}: <b>Top</b> pin detected. Downtrend(30) <b>{}</b>.".format(pair, downtrend)
        elif Bar_pattern_bot._isBottomPin(latestCandle, previousCandle):
            return "{}: <b>Bottom</b> pin detected. Uptrend(30) <b>{}</b>.".format(pair, uptrend)
        elif Bar_pattern_bot._isBearishOutsideBar(latestCandle, previousCandle, secondlastCandle):
            return "{}: <b>BEOB</b> detected. Downtrend(30) <b>{}</b>.".format(pair, downtrend)
        elif Bar_pattern_bot._isBullishOutsideBar(latestCandle, previousCandle, secondlastCandle):
            return "{}: <b>BUOB</b> detected. Uptrend(30) <b>{}</b>.".format(pair,uptrend)


    def _get_current_patterns(self):
        #query oanda for pattern occuring in all pairs and saving result in master list called self.pairs
        for pair in Bar_pattern_bot.pairs_master_list:
            pattern = self._detectPattern(pair)
            if pattern:
                self.pairs[pair] = pattern
            else: 
                self.pairs[pair] = None

    def notify_patterns(self):
        self._get_current_patterns()
        # get list of users and their subscribed pairs, saving into user_subscription dict
        users = User.select(User.telegram_id, Currency_pair.full_name).join(Candlestick_sub_detail).join(Currency_pair).where(
            (User.active == True) & 
            (Candlestick_sub_detail.is_subscribed == True) & 
            (Candlestick_sub_detail.timeframe == self.tf) &
            (User.telegram_id.is_null(False))).tuples()

        user_subscription = {}
        for user in users:
            if user[0] not in user_subscription:
                user_subscription[user[0]] = [user[1]]
            else:
                user_subscription[user[0]].append(user[1]) 

        # for each user, compose message with subscribed pairs from master list and send notification
        for telegram_id, value in user_subscription.items():
            message = ""
            for pair in value:
                parsed_pair = pair[:3] + "_" + pair[3:]
                if self.pairs[parsed_pair]:
                    message += self.pairs[parsed_pair] + "\n"
            
            if message:
                timeframe = self.tf
                message += "\nTimeframe: <b>{}</b>. {} GMT".format(timeframe, str(arrow.utcnow().format("D MMM HH:mm")))
                self.send(telegram_id, message)




