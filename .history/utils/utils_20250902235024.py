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
# -----------------------------
# 0️⃣ Setup
# -----------------------------
load_dotenv()
account_id = os.getenv('OANDA_ACCOUNT_ID')
access_key = os.getenv('OANDA_ACCESS_KEY_NEW')
api = API(access_token=access_key)
warnings.filterwarnings("ignore")

# -----------------------------
# Instrument Precision Handling
# -----------------------------
instrument_precisions = {}

def load_precisions(account_id):
    """Fetch instrument precision (number of decimals allowed for prices)."""
    r = AccountInstruments(accountID=account_id)
    response = api.request(r)
    for inst in response["instruments"]:
        instrument_precisions[inst["name"]] = inst["displayPrecision"]

def format_price(price, instrument):
    """Format price according to instrument precision."""
    precision = instrument_precisions.get(instrument, 5)  # default fallback
    return str(round(price, precision))

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

def place_order(units: int, side: str, sl_price: float, tp_price: float, symbol: str):
    """Send order with SL/TP rounded to correct precision."""
    data = {
        "order": {
            "instrument": symbol,
            "units": str(units if side == "buy" else -units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": format_price(sl_price, symbol)},
            "takeProfitOnFill": {"price": format_price(tp_price, symbol)}
        }
    }
    r = orders.OrderCreate(accountID=account_id, data=data)
    response = api.request(r)
    print(f"[{datetime.now(timezone.utc)}] Order placed: {response}")
