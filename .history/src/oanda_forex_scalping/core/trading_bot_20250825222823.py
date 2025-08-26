"""
Trading bot implementation
"""
import time
from datetime import datetime, timedelta, timezone
import traceback
import pandas as pd

from ..core.oanda_client import OandaClient

class TradingBot:
    def __init__(self, symbol: str, units: int = 1000, backcandles: int = 15,
                 sl_pips: float = 10, tp_pips: float = 15):
        self.symbol = symbol
        self.units = units
        self.backcandles = backcandles
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.client = OandaClient()
        self.last_trade_time = None

    def _calculate_pip_value(self):
        """Calculate pip value based on currency pair."""
        return 0.01 if "JPY" in self.symbol else 0.0001

    def _calculate_sl_tp(self, current_price: float, side: str):
        """Calculate stop loss and take profit prices."""
        pip_value = self._calculate_pip_value()
        if side == "buy":
            sl_price = current_price - (self.sl_pips * pip_value)
            tp_price = current_price + (self.tp_pips * pip_value)
        else:
            sl_price = current_price + (self.sl_pips * pip_value)
            tp_price = current_price - (self.tp_pips * pip_value)
        return sl_price, tp_price

    def run(self, strategy_func):
        """Run the trading bot with the given strategy."""
        while True:
            now = datetime.now(timezone.utc)
            next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            time.sleep(max(0, (next_minute - now).total_seconds()))

            try:
                # Get and process candles
                candles = self.client.get_candles(self.symbol, count=500)
                df = self.client.candles_to_df(candles)
                df = df[df['complete']]

                if len(df) < self.backcandles:
                    continue

                # Prepare DataFrame for strategy
                df['Open'], df['High'], df['Low'], df['Close'], df['Volume'] = \
                    df['mid_o'], df['mid_h'], df['mid_l'], df['mid_c'], df['volume']
                df = df.sort_values('time')
                df.set_index('time', inplace=True)
                
                # Run strategy
                df = strategy_func(df, self.backcandles)
                last = df.iloc[-1]
                
                print(f"[{datetime.now(timezone.utc)}] {self.symbol} - Processing candle: {last.name}")
                signal = last.get('TotalSignal', 0)

                if signal in [1, 2] and self.last_trade_time != last.name:
                    current_price = last['Close']
                    side = 'buy' if signal == 2 else 'sell'
                    sl_price, tp_price = self._calculate_sl_tp(current_price, side)
                    
                    # Place order
                    self.client.place_order(self.units, side, sl_price, tp_price, self.symbol)
                    print(f"[{last.name}] {self.symbol} {side.upper()} | SL:{sl_price} TP:{tp_price}")
                    self.last_trade_time = last.name

            except Exception as e:
                print(f"[{datetime.now()}] Error for {self.symbol}: {e}")
                traceback.print_exc()
