"""
Phase 3 — Feature Generation

Deterministic, lag-safe feature library.
Every feature uses ONLY past data. No leakage.
"""
import numpy as np
import pandas as pd


def rsi(close, period):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ibs(high, low, close):
    rng = high - low
    return (close - low) / rng.replace(0, np.nan)


def bb_zscore(close, period=20):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return (close - sma) / std.replace(0, np.nan)


def sma_dev_atr(close, high, low, sma_p=20, atr_p=14):
    sma = close.rolling(sma_p).mean()
    pc = close.shift(1)
    tr = pd.concat([high-low, (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
    a = tr.rolling(atr_p).mean()
    return (close - sma) / a.replace(0, np.nan)


def williams_r(high, low, close, period=14):
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return -100 * (hh - close) / (hh - ll).replace(0, np.nan)


def stochastic_k(high, low, close, period=14):
    ll = low.rolling(period).min()
    hh = high.rolling(period).max()
    return 100 * (close - ll) / (hh - ll).replace(0, np.nan)


def cci(high, low, close, period=20):
    tp = (high + low + close) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma) / (0.015 * mad).replace(0, np.nan)


def mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    mf = tp * volume
    pos = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(period).sum()
    return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))


def consecutive_down(close):
    neg = (close.diff() < 0).astype(int)
    result = pd.Series(0, index=close.index, dtype=int)
    for i in range(1, len(close)):
        result.iloc[i] = result.iloc[i-1] + 1 if neg.iloc[i] else 0
    return result


def rolling_vol(close, period=20):
    return close.pct_change().rolling(period).std() * np.sqrt(252)


def compute_features(df):
    """Compute all features for one stock. Returns DataFrame."""
    c = df["adj_close"]; h = df["high"]; l = df["low"]; v = df["volume"]
    f = pd.DataFrame(index=df.index)

    for p in [2, 3, 5, 14]: f[f"rsi_{p}"] = rsi(c, p)
    f["ibs"] = ibs(h, l, df["close"])
    for p in [10, 20]: f[f"bb_z_{p}"] = bb_zscore(c, p)
    f["sma_dev_atr"] = sma_dev_atr(c, h, l)
    f["williams_r"] = williams_r(h, l, c)
    f["stoch_k"] = stochastic_k(h, l, c)
    f["cci"] = cci(h, l, c)
    f["mfi"] = mfi(h, l, c, v)
    f["down_days"] = consecutive_down(c)
    f["vol_20"] = rolling_vol(c)
    for p in [1,2,3,5,21]: f[f"ret_{p}d"] = c.pct_change(p) * 100
    # Cross-sectional rank features computed at portfolio level, not here
    return f


SIGNAL_FEATURES = [
    "rsi_2","rsi_3","rsi_5","rsi_14","ibs","bb_z_10","bb_z_20",
    "sma_dev_atr","williams_r","stoch_k","cci","mfi","down_days",
    "vol_20","ret_1d","ret_2d","ret_3d","ret_5d","ret_21d",
]
