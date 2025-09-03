import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from oandapyV20 import API
from oandapyV20.endpoints import instruments, orders
from oandapyV20.endpoints.accounts import AccountInstruments
import warnings
from dotenv import load_dotenv
import traceback
import threading
from strategies.mean_reversion_scalping import mean_reversion_scalping
from utils.mean_utils import get_candles, candles_to_df, place_order, load_precisions, format_price, instrument_precisions, account_id
# -----------------------------
# 2️⃣ Main trading loop
# -----------------------------
def run_symbol(symbol):
    backcandles = 15
    units = 1000
    ATR_multiplier_SL = 1.0
    ATR_multiplier_TP = 1.5
    last_trade_time = None  

    while True:
        now = datetime.now(timezone.utc)
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        time.sleep(max(0, (next_minute - now).total_seconds()))

        try:
            candles = get_candles(symbol, count=500)
            df = candles_to_df(candles)
            df = df[df['complete']]

            if len(df) < backcandles:
                continue

            df['Open'], df['High'], df['Low'], df['Close'], df['Volume'] = \
                df['mid_o'], df['mid_h'], df['mid_l'], df['mid_c'], df['volume']
            df = df.sort_values('time')
            df.set_index('time', inplace=True)
            
            # Run strategy
            df = mean_reversion_scalping(df, backcandles, ATR_multiplier_SL)  # returns df with 'TotalSignal' & 'atr'

            # Last candle
            last = df.iloc[-1]
            print(last)
            signal = last['TotalSignal']
            atr = last['atr']

            # Convert ATR to price distance
            sl_distance = ATR_multiplier_SL * atr
            tp_distance = ATR_multiplier_TP * atr

            if signal in [1, 2] and last_trade_time != last.name:
                if signal == 2:  # Buy
                    sl_price = last['Close'] - sl_distance
                    tp_price = last['Close'] + tp_distance
                    place_order(units, 'buy', sl_price, tp_price, symbol)
                    print(f"[{last.name}] {symbol} BUY | SL:{sl_distance} TP:{tp_distance}")

                elif signal == 1:  # Sell
                    sl_price = last['Close'] + sl_distance
                    tp_price = last['Close'] - tp_distance
                    place_order(units, 'sell', sl_price, tp_price, symbol)
                    print(f"[{last.name}] {symbol} SELL | SL:{sl_distance} TP:{tp_distance}")

                last_trade_time = last.name

        except Exception as e:
            print(f"[{datetime.now()}] Error for {symbol}: {e}")
            traceback.print_exc()

# -----------------------------
# 3️⃣ Run bot for multiple instruments
# -----------------------------
if __name__ == "__main__":
    # Load instrument precisions once
    load_precisions(account_id)

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
        t = threading.Thread(target=run_symbol, args=(sym,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
