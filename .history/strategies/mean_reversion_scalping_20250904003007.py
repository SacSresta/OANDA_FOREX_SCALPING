import traceback
import numpy as np
np.NaN = np.nan
import pandas_ta as ta
import pandas as pd


def mean_reversion_scalping(df, lookback=20, z_score_threshold=2, stop_loss_pips=10, take_profit_pips=5):
    """
    Mean reversion scalping strategy for forex data

    Parameters:
    - lookback: Period for calculating moving average and standard deviation
    - z_score_threshold: Number of standard deviations for entry signal
    - stop_loss_pips: Stop loss in pips (0.0001 for EUR/USD)
    - take_profit_pips: Take profit in pips
    """

    # Calculate indicators
    df['SMA'] = df['Close'].rolling(window=lookback).mean()
    df['STD'] = df['Close'].rolling(window=lookback).std()
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['Z_Score'] = (df['Close'] - df['SMA']) / df['STD']

    # Generate signals
    df['TotalSignal'] = 0
    df.loc[df['Z_Score'] < -z_score_threshold, 'TotalSignal'] = 1  # Buy signal (oversold)
    df.loc[df['Z_Score'] > z_score_threshold, 'TotalSignal'] = 2  # Sell signal (overbought)
    return df
