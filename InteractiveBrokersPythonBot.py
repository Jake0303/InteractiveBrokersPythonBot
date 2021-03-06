#Imports
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
#
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time
#Vars

#Class for Interactive Brokers Connection
class IBApi(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self, self)
    # Listen for realtime bars
    def realtimeBar(self, reqId, time, open_, high, low, close,volume, wap, count):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        try:
            bot.on_bar_update(reqId, time, open_, high, low, close, volume, wap, count)
        except Exception as e:
            print(e)
    def error(self, id, errorCode, errorMsg):
        print(errorCode)
        print(errorMsg)
#Bot Logic
class Bot:
    ib = None
    def __init__(self):
        #Connect to IB on init
        self.ib = IBApi()
        self.ib.connect("127.0.0.1", 7496,1)
        ib_thread = threading.Thread(target=self.run_loop, daemon=True)
        ib_thread.start()
        time.sleep(1)
        #Get symbol info
        symbol = input("Enter the symbol you want to trade : ")
        #Create our IB Contract Object
        contract = Contract()
        contract.symbol = symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        # Request Market Data
        self.ib.reqRealTimeBars(0, contract, 5, "TRADES", 1, [])
        # TODO Submit ORDER
        # Create Order Object
        order = Order()
        order.orderType = "MKT" # or LMT ETC....
        order.action = "BUY" # or SELL ETC...
        quantity = 1
        order.totalQuantity = quantity
        # Create Contract Object
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK" # or FUT ETC....
        contract.exchange = "SMART"
        contract.primaryExchange = "ISLAND"
        contract.currency = "USD"
        # Place the order
        self.ib.placeOrder(2, contract, order)
    #Listen to socket in seperate thread
    def run_loop(self):
        self.ib.run()
    #Pass realtime bar data back to our bot object
    def on_bar_update(self, reqId, time, open_, high, low, close, volume, wap, count):
        print(close)
#Start Bot
bot = Bot()