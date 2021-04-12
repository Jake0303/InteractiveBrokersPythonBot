#Imports
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import ta
import numpy as np
import pandas as pd
import pytz
import math
from datetime import datetime, timedelta
import threading
import time
#Vars
orderId = 1
#Class for Interactive Brokers Connection
class IBApi(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self, self)
    # Historical Backtest Data
    def historicalData(self, reqId, bar):
        try:
            bot.on_bar_update(reqId,bar,False)
        except Exception as e:
            print(e)
    # On Realtime Bar after historical data finishes
    def historicalDataUpdate(self, reqId, bar):
        try:
            bot.on_bar_update(reqId,bar,True)
        except Exception as e:
            print(e)
    # On Historical Data End
    def historicalDataEnd(self, reqId, start, end):
        print(reqId)
    # Get next order id we can use
    def nextValidId(self, nextorderId):
        global orderId
        orderId = nextorderId
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
#Bar Object
class Bar:
    open = 0
    low = 0
    high = 0
    close = 0
    volume = 0
    date = datetime.now()
    def __init__(self):
        self.open = 0
        self.low = 0
        self.high = 0
        self.close = 0
        self.volume = 0
        self.date = datetime.now()
#Bot Logic
class Bot:
    ib = None
    barsize = 1
    currentBar = Bar()
    bars = []
    reqId = 1
    global orderId
    smaPeriod = 50
    symbol = ""
    initialbartime = datetime.now().astimezone(pytz.timezone("America/New_York"))
    def __init__(self):
        #Connect to IB on init
        self.ib = IBApi()
        self.ib.connect("127.0.0.1", 7496,1)
        ib_thread = threading.Thread(target=self.run_loop, daemon=True)
        ib_thread.start()
        time.sleep(1)
        currentBar = Bar()
        #Get symbol info
        self.symbol = input("Enter the symbol you want to trade : ")
        #Get bar size
        self.barsize = int(input("Enter the barsize you want to trade in minutes : "))
        mintext = " min"
        if (int(self.barsize) > 1):
            mintext = " mins"
        queryTime = (datetime.now().astimezone(pytz.timezone("America/New_York"))-timedelta(days=1)).replace(hour=16,minute=0,second=0,microsecond=0).strftime("%Y%m%d %H:%M:%S")
        #Create our IB Contract Object
        contract = Contract()
        contract.symbol = self.symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        self.ib.reqIds(-1)
        # Request Market Data
        #self.ib.reqRealTimeBars(0, contract, 5, "TRADES", 1, [])
        self.ib.reqHistoricalData(self.reqId,contract,"","2 D",str(self.barsize)+mintext,"TRADES",1,1,True,[])
    #Listen to socket in seperate thread
    def run_loop(self):
        self.ib.run()
    #Bracet Order Setup
    def bracketOrder(self, parentOrderId, action, quantity, profitTarget, stopLoss):
        #Initial Entry
        #Create our IB Contract Object
        contract = Contract()
        contract.symbol = self.symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        # Create Parent Order / Initial Entry
        parent = Order()
        parent.orderId = parentOrderId
        parent.orderType = "MKT"
        parent.action = action
        parent.totalQuantity = quantity
        parent.transmit = False
        # Profit Target
        profitTargetOrder = Order()
        profitTargetOrder.orderId = parent.orderId+1
        profitTargetOrder.orderType = "LMT"
        profitTargetOrder.action = "SELL"
        profitTargetOrder.totalQuantity = quantity
        profitTargetOrder.lmtPrice = round(profitTarget,2)
        profitTargetOrder.transmit = False
        # Stop Loss
        stopLossOrder = Order()
        stopLossOrder.orderId = parent.orderId+2
        stopLossOrder.orderType = "STP"
        stopLossOrder.action = "SELL"
        stopLossOrder.totalQuantity = quantity
        stopLossOrder.auxPrice = round(stopLoss,2)
        stopLossOrder.transmit = True

        bracketOrders = [parent, profitTargetOrder, stopLossOrder]
        return bracketOrders
    #Pass realtime bar data back to our bot object
    def on_bar_update(self, reqId, bar,realtime):
        global orderId
        #Historical Data to catch up
        if (realtime == False):
            self.bars.append(bar)
        else:
            bartime = datetime.strptime(bar.date,"%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))
            minutes_diff = (bartime-self.initialbartime).total_seconds() / 60.0
            self.currentBar.date = bartime
            lastBar = self.bars[len(self.bars)-1]
            #On Bar Close
            if (minutes_diff > 0 and math.floor(minutes_diff) % self.barsize == 0):
                self.initialbartime = bartime
                #Entry - If we have a higher high, a higher low and we cross the 50 SMA Buy
                #1.) SMA
                closes = []
                for bar in self.bars:
                    closes.append(bar.close)
                self.close_array = pd.Series(np.asarray(closes))
                self.sma = ta.trend.sma(self.close_array,self.smaPeriod,True)
                print("SMA : " + str(self.sma[len(self.sma)-1]))
                #2.) Calculate Higher Highs and Lows
                lastLow = self.bars[len(self.bars)-1].low
                lastHigh = self.bars[len(self.bars)-1].high
                lastClose = self.bars[len(self.bars)-1].close

                # Check Criteria
                if (bar.close > lastHigh
                    and self.currentBar.low > lastLow
                    and bar.close > str(self.sma[len(self.sma)-1])
                    and lastClose < str(self.sma[len(self.sma)-2])):
                    #Bracket Order 2% Profit Target 1% Stop Loss
                    profitTarget = bar.close*1.02
                    stopLoss = bar.close*0.99
                    quantity = 1
                    bracket = self.bracketOrder(orderId,"BUY",quantity, profitTarget, stopLoss)
                    contract = Contract()
                    contract.symbol = self.symbol.upper()
                    contract.secType = "STK"
                    contract.exchange = "SMART"
                    contract.currency = "USD"
                    #Place Bracket Order
                    for o in bracket:
                        o.ocaGroup = "OCA_"+str(orderId)
                        o.ocaType = 2
                        self.ib.placeOrder(o.orderId,o.contract,o)
                    orderId += 3
                #Bar closed append
                self.currentBar.close = bar.close
                print("New bar!")
                self.bars.append(self.currentBar)
                self.currentBar = Bar()
                self.currentBar.open = bar.open
        #Build  realtime bar
        if (self.currentBar.open == 0):
            self.currentBar.open = bar.open
        if (self.currentBar.high == 0 or bar.high > self.currentBar.high):
            self.currentBar.high = bar.high
        if (self.currentBar.low == 0 or bar.low < self.currentBar.low):
            self.currentBar.low = bar.low

#Start Bot
bot = Bot()