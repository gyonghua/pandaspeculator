from models import User, Candlestick_sub_detail, Currency_pair
import requests
import json
import traceback
import arrow
from alerts.alerts_config import oandaApi, live_account, account_id_1, account_id_2, account_id_3, telegramApi

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
                "Content-Type": "application/json",
                "Accept-Datetime-Format" : "UNIX"
               }
    fxpractice = "https://api-fxpractice.oanda.com"
    fxlive = "https://api-fxtrade.oanda.com"
    _base_url = fxlive if live_account else fxpractice
    
    
    def create_order(self, trigger_price, stop_loss, take_profit, side, instrument, units=200, account="buy", expiry=23, order_type="stop"):
        """units: unit to open, side: [buy, sell],  instrument: EUR_USD"""
        if account == "buy":
            account_id = account_id_1
        elif account=="median_sell":
            account_id = account_id_2

        endpoint = "/v1/accounts/{}/orders".format(account_id)
        expiry = arrow.utcnow().shift(hours=+expiry).timestamp

        if "JPY" in instrument:
            trigger_price = round(trigger_price, 2)
            stop_loss = round(stop_loss, 2)
            take_profit = round(take_profit, 2)

        payload = {
            "instrument" : instrument,
            "units" : units,
            "side" : side,
            "type" : order_type,
            "expiry" : expiry,
            "price" : trigger_price, 
            "stopLoss" : stop_loss,
            "takeProfit" : take_profit
        }

        response = requests.post(Oanda_bot._base_url + endpoint, headers=Oanda_bot._headers, data=payload)
        return response.json()
    
    def get_current_price(self, pair):
        endpoint = "/v3/accounts/{}/pricing".format(account_id_3)
        modified_pair = pair[:3] + "_" + pair[3:]
        cleaned_pair = modified_pair.upper()
        payload = {
            "instruments" : cleaned_pair,
            "includeUnitsAvailable" : False
        }

        try:
            response = requests.get(Oanda_bot._base_url + endpoint,     headers=Oanda_bot._headers, params=payload)
            status_code =response.status_code
            price = response.json()
            if status_code == 200:
                bid = price["prices"][0]["bids"][0]["price"]
                ask = price["prices"][0]["asks"][0]["price"]
                return "{}/{}".format(bid, ask)
            elif status_code in [400, 401, 404, 405]:
                return price["errorMessage"]
        
        except:
            print(traceback.print_exc())
            return "unknown error in retrieving price"


    def notify_current_price(self,chat_id, pair):
        price = self.get_current_price(pair)
        message = "{} : {}".format(pair, price)
        return self.send(chat_id, message)

    @classmethod
    def getCandles(cls, pair, tf, count=31):
        """returns a json requests object. gets the last 30 candles, not including the current candle"""
        endpoint = "/v3/instruments/{}/candles".format(pair)
        now = arrow.utcnow()
        previous_hourUNIX = now.shift(hours=-1).timestamp
        candleformat = "midpoint"

        payload = {
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

    def get_orderbook_v20(self, pair):
        endpoint = "/v3/instruments/{}/orderBook".format(pair)

        response = requests.get(Oanda_bot._base_url + endpoint, 
                                headers=Oanda_bot._headers)
        
        return response.json()
    
    def get_orderbook(self, pair):
        #depreciated
        endpoint = "labs/v1/orderbook_data"

        payload = {
            "instrument" : pair,
            "period" : 3600
        }

        response = requests.get(Oanda_bot._base_url + endpoint, 
                                headers=Oanda_bot._headers, 
                                params=payload)
        return response.json()
    
    def get_latest_net_orders_v20(self, pair):
        orderbook = self.get_orderbook_v20(pair)

        latest_orderbook_timestamp = orderbook["orderBook"]["time"]
        latest_time = arrow.get(latest_orderbook_timestamp).format("D MMM HH:mm")
        orderbook_rate = float(orderbook["orderBook"]["price"])

        net_buystop_orders = []
        net_sellstop_orders = []
        orderbook_prices = orderbook["orderBook"]["buckets"] 
        for bucket in orderbook_prices:
            price = bucket["price"]
            long_order = float(bucket["longCountPercent"])
            short_order = float(bucket["shortCountPercent"])
            if float(price) > orderbook_rate:
                tup = (price, round(long_order - short_order, 5))
                net_buystop_orders.append(tup)
            elif float(price) < orderbook_rate:
                tup = (price,round(short_order - long_order, 5))
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
    
    def get_latest_net_orders(self, pair):
        # depreciated
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
        daily_ranges = [float(candle["mid"]["h"]) - float(candle["mid"]["l"]) for candle in candles if candle["complete"]]

        average_daily_range = sum(daily_ranges)/count

        return average_daily_range


class Bar_pattern_bot(Oanda_bot):
    pairs_master_list = ["EUR_USD", "GBP_USD", "AUD_USD", "EUR_GBP", "USD_CAD","USD_JPY", "EUR_JPY"]
    def __init__(self, api, tf):
        # parent of Oanda is Telegram 
        super(Oanda_bot, self).__init__(api)
        self.tf = tf
        self.pairs = {}
    
    def getCandles(self, pair):
        timeframe = self.tf
        return Oanda_bot.getCandles(pair, timeframe)

    @classmethod
    def _isBullishOutsideBar(cls, latestCandle, previousCandle, secondlastCandle):
        criteria_1 = float(latestCandle["h"]) > float(previousCandle["h"])
        criteria_2 = float(latestCandle["l"]) < float(previousCandle["l"])
        criteria_3 = float(latestCandle["c"]) > float(previousCandle["h"])
        criteria_4 = float(latestCandle["h"]) > float(secondlastCandle["h"])
        criteria_5 = float(latestCandle["l"]) < float(secondlastCandle["l"])

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isBearishOutsideBar(cls, latestCandle, previousCandle, secondlastCandle):
        criteria_1 = float(latestCandle["h"]) > float(previousCandle["h"])
        criteria_2 = float(latestCandle["l"]) < float(previousCandle["l"])
        criteria_3 = float(latestCandle["c"]) < float(previousCandle["l"])
        criteria_4 = float(latestCandle["h"]) > float(secondlastCandle["h"])
        criteria_5 = float(latestCandle["l"]) < float(secondlastCandle["l"])

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isTopPin(cls, latestCandle, previousCandle):
        criteria_1 = float(latestCandle["c"]) < float(previousCandle["h"])
        criteria_2 = float(latestCandle["l"]) > float(previousCandle["l"])
        criteria_3 = float(latestCandle["h"]) > float(previousCandle["h"])

        previousBarRange = float(previousCandle["h"]) - float(previousCandle["l"])

        distance_1 = float(previousCandle["h"]) - float(latestCandle["l"])
        distance_2 = float(latestCandle["h"]) - float(previousCandle["h"])

        criteria_4 = distance_2 > distance_1
        criteria_5 = previousBarRange > 0.0010 # this has an issue for jpy and usd pairs. To improve with percentage instead

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isBottomPin(cls, latestCandle, previousCandle):

        criteria_1 = float(latestCandle["l"]) < float(previousCandle["l"])
        criteria_2 = float(latestCandle["c"]) > float(previousCandle["l"])
        criteria_3 = float(latestCandle["h"]) < float(previousCandle["h"])

        previousBarRange = float(previousCandle["h"]) - float(previousCandle["l"])

        distance_1 = float(latestCandle["h"]) - float(previousCandle["l"])
        distance_2 = float(previousCandle["l"]) - float(latestCandle["l"])

        criteria_4 = distance_2 > distance_1
        criteria_5 = previousBarRange > 0.0010

        return (criteria_1 and criteria_2 and criteria_3 and criteria_4 and criteria_5)

    @classmethod
    def _isUpTrend(cls, sorted_candles):
        candleLows = [float(candle["mid"]["l"]) for candle in sorted_candles]

        return candleLows[0] > min(candleLows)

    @classmethod
    def _isDownTrend(cls, sorted_candles):
        candleHighs = [float(candle["mid"]["h"]) for candle in sorted_candles]

        return candleHighs[0] < max(candleHighs)


    def _detectPattern(self, pair):
        data = self.getCandles(pair).json()
        candles = data["candles"]
        sorted_candles = sorted(candles, key=lambda k: int(float(k["time"])), reverse=True)
        # v20 api returns current candle that is not complete hence the slicing
        true_sorted_candles = sorted_candles[1:]
        latestCandle = true_sorted_candles[0]["mid"]
        previousCandle = true_sorted_candles[1]["mid"]
        secondlastCandle = true_sorted_candles[2]["mid"]
        uptrend = Bar_pattern_bot._isUpTrend(true_sorted_candles)
        downtrend = Bar_pattern_bot._isDownTrend(true_sorted_candles)

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

if __name__ == "__main__":
    bot = Oanda_bot(telegramApi)
    candles = bot.getCandles("EUR_USD", "D").json()
    print(candles)