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
    def realTimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        bot.on_bar_update(reqId, time, open_, high, low, close, volume, wap, count)
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
    #Listen to socket in seperate thread
    def run_loop(self):
        self.ib.run()
    #Pass realtime bar data back to our bot object
    def on_bar_update(reqId, time, open_, high, low, close, volume, wap, count):
        print(reqId)
#Start Bot
bot = Bot()