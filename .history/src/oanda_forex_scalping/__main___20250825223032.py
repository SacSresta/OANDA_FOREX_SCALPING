"""
Main entry point for the OANDA Forex Scalping Trading System
"""
import threading
from oanda_forex_scalping.core.trading_bot import TradingBot
from src.oanda_forex_scalping.strategies.vwap_rsi_scalping import strategy

# Trading pairs
SYMBOLS = [
    'EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF', 'AUD_USD', 'NZD_USD',
    'USD_CAD', 'EUR_GBP', 'EUR_JPY', 'GBP_JPY', 'EUR_CHF', 'GBP_CHF',
    'AUD_JPY', 'CAD_JPY', 'NZD_JPY', 'EUR_AUD', 'GBP_AUD', 'EUR_CAD'
]

# Trading parameters
UNITS = 1000
BACKCANDLES = 15
SL_PIPS = 10
TP_PIPS = 15

def run_bot(symbol: str):
    """Initialize and run a trading bot for a single symbol."""
    bot = TradingBot(
        symbol=symbol,
        units=UNITS,
        backcandles=BACKCANDLES,
        sl_pips=SL_PIPS,
        tp_pips=TP_PIPS
    )
    bot.run(strategy)

def main():
    """Start trading bots for all symbols."""
    print(f"Starting trading bots for {len(SYMBOLS)} currency pairs...")
    
    threads = []
    for symbol in SYMBOLS:
        t = threading.Thread(target=run_bot, args=(symbol,))
        t.start()
        threads.append(t)
        print(f"Started bot for {symbol}")
    
    # Wait for all threads
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
