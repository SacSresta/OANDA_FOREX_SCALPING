import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from oandapyV20 import API
from oandapyV20.endpoints import instruments, orders
import warnings
from dotenv import load_dotenv
import traceback
from strategies.vwap_rsi_scalping import strategy

# -----------------------------
# 0️⃣ Setup
# -----------------------------
load_dotenv()
account_id = os.getenv('OANDA_ACCOUNT_ID')
access_key = os.getenv('OANDA_ACCESS_KEY')
api = API(access_token=access_key)
warnings.filterwarnings("ignore")


# -----------------------------
# 1️⃣ Helper functions
# -----------------------------
def get_candles(symbol: str, count: int = 20, granularity: str = 'M1'):
    params = {"count": count, "granularity": granularity, "price": "MBA"}
    r = instruments.InstrumentsCandles(instrument=symbol, params=params)
    response = api.request(r)
    return response['candles']


def candles_to_df(candles):
    records = []
    for c in candles:
        records.append({
            "time": pd.to_datetime(c["time"]),
            "complete": c["complete"],
            "volume": c["volume"],
            "mid_o": float(c["mid"]["o"]),
            "mid_h": float(c["mid"]["h"]),
            "mid_l": float(c["mid"]["l"]),
            "mid_c": float(c["mid"]["c"]),
            "bid_o": float(c["bid"]["o"]),
            "bid_h": float(c["bid"]["h"]),
            "bid_l": float(c["bid"]["l"]),
            "bid_c": float(c["bid"]["c"]),
            "ask_o": float(c["ask"]["o"]),
            "ask_h": float(c["ask"]["h"]),
            "ask_l": float(c["ask"]["l"]),
            "ask_c": float(c["ask"]["c"]),
        })
    return pd.DataFrame(records)


def format_price(price, instrument):
    # JPY pairs → 3 decimals, others → 5 decimals
    if "JPY" in instrument:
        return str(round(price, 3))
    else:
        return str(round(price, 5))


def pips_to_price(pips, symbol):
    # For JPY pairs, 1 pip = 0.01, for others 1 pip = 0.0001
    if "JPY" in symbol:
        return pips * 0.01
    else:
        return pips * 0.0001


def place_order(units: int, side: str, sl_pips: float, tp_pips: float, symbol: str):
    # Get current price from the last candle
    current_price = float(get_candles(symbol, count=1)[0]["mid"]["c"])
    
    # Calculate SL and TP prices based on pips
    if side == "buy":
        sl_price = current_price - pips_to_price(sl_pips, symbol)
        tp_price = current_price + pips_to_price(tp_pips, symbol)
    else:  # sell
        sl_price = current_price + pips_to_price(sl_pips, symbol)
        tp_price = current_price - pips_to_price(tp_pips, symbol)
    
    data = {
        "order": {
            "instrument": symbol,
            "units": str(units if side == "buy" else -units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "price": format_price(sl_price, symbol)
            },
            "takeProfitOnFill": {
                "price": format_price(tp_price, symbol)
            }
        }
    }
    r = orders.OrderCreate(accountID=account_id, data=data)
    response = api.request(r)
    print(f"[{datetime.now(timezone.utc)}] Order placed: {response}")


# -----------------------------
# 2️⃣ Main trading loop
# -----------------------------
def run_symbol(symbol):
    backcandles = 15
    units = 1000
    sl_pips = 10  # Stop loss in pips
    tp_pips = 15  # Take profit in pips

    last_trade_time = None  # to prevent repeated trades per candle

    while True:
        now = datetime.now(timezone.utc)
        next_minute = (now + timedelta(minutes=1)).replace(second=0,
                                                           microsecond=0)
        time.sleep(max(0, (next_minute - now).total_seconds()))

        try:
            candles = get_candles(symbol, count=500)
            df = candles_to_df(candles)
            df = df[df['complete']]
            if len(df) < backcandles:
                continue
            df = strategy(df, backcandles, 1.2)  # Keep ATR for strategy signals
            # Last candle
            last = df.iloc[-1]
            print(last)
            signal = last['TotalSignal']


            if signal in [1, 2] and last_trade_time != last['time']:
                if signal == 2:  # Buy
                    place_order(units, 'buy', sl_pips, tp_pips, symbol)
                    print(f"[{last['time']}] {symbol} BUY | SL:{sl_pips} pips TP:{tp_pips} pips")

                elif signal == 1:  # Sell
                    place_order(units, 'sell', sl_pips, tp_pips, symbol)
                    print(f"[{last['time']}] {symbol} SELL | SL:{sl_pips} pips TP:{tp_pips} pips")

                last_trade_time = last['time']

        except Exception as e:
            print(f"[{datetime.now()}] Error for {symbol}: {e}")
            traceback.print_exc()


# -----------------------------
# 3️⃣ Run script
# -----------------------------
import threading

if __name__ == "__main__":
    symbols = [
        'TRY_JPY', 'HKD_JPY', 'USD_PLN', 'GBP_AUD', 'NZD_USD', 'EUR_ZAR',
        'AUD_JPY', 'USD_NOK', 'CAD_CHF', 'GBP_SGD', 'USD_SEK', 'NZD_SGD',
        'ZAR_JPY', 'SGD_JPY', 'GBP_ZAR', 'USD_JPY', 'EUR_TRY', 'EUR_JPY',
        'AUD_SGD', 'EUR_NZD', 'GBP_HKD', 'CHF_JPY', 'EUR_HKD', 'USD_THB',
        'GBP_CHF', 'AUD_CHF', 'NZD_CHF', 'AUD_HKD', 'USD_CHF', 'CAD_HKD',
        'USD_HKD', 'AUD_NZD', 'CHF_ZAR', 'EUR_CHF', 'USD_DKK', 'CAD_SGD',
        'EUR_DKK', 'USD_ZAR', 'CAD_JPY', 'USD_HUF', 'EUR_CAD', 'EUR_USD',
        'EUR_HUF', 'CHF_HKD', 'GBP_NZD', 'USD_SGD', 'EUR_SEK', 'USD_TRY',
        'GBP_JPY', 'GBP_PLN', 'EUR_PLN', 'AUD_CAD', 'EUR_CZK', 'GBP_USD',
        'USD_MXN', 'GBP_CAD', 'SGD_CHF', 'NZD_CAD', 'AUD_USD', 'NZD_JPY',
        'USD_CNH', 'EUR_GBP', 'USD_CZK', 'NZD_HKD', 'EUR_NOK', 'USD_CAD',
        'EUR_AUD', 'EUR_SGD'
    ]

    threads = []

    for sym in symbols:
        t = threading.Thread(target=run_symbol, args=(sym, ))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
