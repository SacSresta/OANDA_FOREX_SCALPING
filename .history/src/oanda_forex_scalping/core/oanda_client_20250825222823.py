"""
OANDA API client implementation
"""
import os
from datetime import datetime, timezone
import pandas as pd
from oandapyV20 import API
from oandapyV20.endpoints import instruments, orders
from dotenv import load_dotenv

class OandaClient:
    def __init__(self, environment="practice"):
        load_dotenv()
        self.account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.access_key = os.getenv('OANDA_ACCESS_KEY')
        self.api = API(access_token=self.access_key, environment=environment)

    def get_candles(self, symbol: str, count: int = 20, granularity: str = 'M1'):
        """Get candlestick data from OANDA."""
        params = {"count": count, "granularity": granularity, "price": "MBA"}
        r = instruments.InstrumentsCandles(instrument=symbol, params=params)
        response = self.api.request(r)
        return response['candles']

    def candles_to_df(self, candles):
        """Convert OANDA candles to pandas DataFrame."""
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

    @staticmethod
    def format_price(price, instrument):
        """Format price according to instrument type."""
        if "JPY" in instrument:
            return str(round(price, 3))
        else:
            return str(round(price, 5))

    def place_order(self, units: int, side: str, sl_price: float, tp_price: float, symbol: str):
        """Place a market order with stop loss and take profit."""
        data = {
            "order": {
                "instrument": symbol,
                "units": str(units if side == "buy" else -units),
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "stopLossOnFill": {"price": self.format_price(sl_price, symbol)},
                "takeProfitOnFill": {"price": self.format_price(tp_price, symbol)}
            }
        }
        r = orders.OrderCreate(accountID=self.account_id, data=data)
        response = self.api.request(r)
        print(f"[{datetime.now(timezone.utc)}] Order placed: {response}")
        return response
