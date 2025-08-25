import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

np.NaN = np.nan
import pandas_ta as ta
from oandapyV20 import API
from oandapyV20.endpoints import instruments, orders
import warnings
from dotenv import load_dotenv
import traceback

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


def place_order(units: int, side: str, sl: float, tp: float, symbol: str):
    data = {
        "order": {
            "instrument": symbol,
            "units": str(units if side == "buy" else -units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "price": str(round(sl, 5))
            },
            "takeProfitOnFill": {
                "price": str(round(tp, 5))
            }
        }
    }
    r = orders.OrderCreate(accountID=account_id, data=data)
    response = api.request(r)
    print(f"[{datetime.now(timezone.utc)}] Order placed: {response}")


# -----------------------------
# 2️⃣ Main trading loop
# -----------------------------
def main():
    symbol = "AUD_USD"
    backcandles = 15
    units = 1000

    # ATR-based SL/TP scaling (matches your backtest)
    ATR_multiplier = 1.2  # How far SL is from entry
    TPSL_ratio = 1.5  # TP distance = SL distance * TPSL_ratio

    while True:
        now = datetime.now(timezone.utc)
        next_minute = (now + timedelta(minutes=1)).replace(second=0,
                                                           microsecond=0)
        time.sleep(max(0, (next_minute - now).total_seconds()))

        candles = get_candles(symbol, count=5000)
        df = candles_to_df(candles)
        df = df[df['complete']]
        if len(df) < backcandles:
            continue

        df['Open'], df['High'], df['Low'], df['Close'], df['Volume'] = df[
            'mid_o'], df['mid_h'], df['mid_l'], df['mid_c'], df['volume']
        df = df.sort_values('time')
        df.set_index('time', inplace=True)

        # Indicators
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        df['RSI'] = ta.rsi(df['Close'], length=16)
        bb = ta.bbands(df['Close'], length=14, std=2.0)
        df = df.join(bb)
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['upper_band'] = df['Close'] + df['atr'] * 1.5
        df['lower_band'] = df['Close'] - df['atr'] * 1.5
        df.reset_index(inplace=True)

        # VWAP signals
        rolling_max = df['Close'].rolling(window=backcandles,
                                          min_periods=1).max()
        rolling_min = df['Close'].rolling(window=backcandles,
                                          min_periods=1).min()
        upt_condition = rolling_max >= df['VWAP']
        dnt_condition = rolling_min <= df['VWAP']

        VWAPsignal = np.zeros(len(df))
        VWAPsignal[upt_condition & dnt_condition] = 3
        VWAPsignal[upt_condition] = 2
        VWAPsignal[dnt_condition] = 1
        df['VWAPSignal'] = VWAPsignal

        # Buy/Sell signals
        condition_buy = (df['VWAPSignal'] == 2) & (
            df['Close'] <= df['BBM_14_2.0']) & (df['RSI'] < 45)
        condition_sell = (df['VWAPSignal'] == 1) & (
            df['Close'] >= df['BBU_14_2.0']) & (df['RSI'] > 55)
        df['TotalSignal'] = np.select([condition_buy, condition_sell], [2, 1],
                                      default=0)

        # Last candle
        last = df.iloc[-1]
        print(last)
        signal = last['TotalSignal']
        slatr = ATR_multiplier * last['atr']

        try:
            if signal == 2:  # Buy
                sl = last['Close'] - slatr
                tp = last['Close'] + slatr * TPSL_ratio
                print(f"[{last['time']}] BUY signal! Entry: {last['ask_c']}, SL: {sl}, TP: {tp}")
                place_order(units, 'buy', sl, tp, symbol)

            elif signal == 1:  # Sell
                sl = last['Close'] + slatr
                tp = last['Close'] - slatr * TPSL_ratio
                print(f"[{last['time']}] SELL signal! Entry: {last['bid_c']}, SL: {sl}, TP: {tp}")
                place_order(units, 'sell', sl, tp, symbol)
            else:
                print(f"[{last['time']}] No trade signal.")
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


# -----------------------------
# 3️⃣ Run script
# -----------------------------
if __name__ == "__main__":
    main()
