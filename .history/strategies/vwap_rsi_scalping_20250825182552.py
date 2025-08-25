import traceback

np.NaN = np.nan
import pandas_ta as ta

def strategy():
    last_trade_time = None  # to prevent repeated trades per candle
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

    