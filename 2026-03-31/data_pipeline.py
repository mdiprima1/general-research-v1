"""
Phase 2 — Data Pipeline

EODHD daily OHLCV for S&P 500 + ETFs.
Explicit handling of missing data, survivorship, and corporate actions.
"""
import os, time, requests, json
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / "trend-futures" / ".env")
EODHD_KEY = os.getenv("EODHD_API_KEY")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Universe: S&P 500 sample + ETFs (no survivorship bias on ETFs)
UNIVERSE = [
    # Tech (20)
    "AAPL","MSFT","AMZN","GOOGL","META","NVDA","TSLA","AVGO","ORCL","ADBE",
    "AMD","INTC","CRM","PYPL","CSCO","NFLX","QCOM","TXN","AMAT","MU",
    # Financials (20)
    "JPM","BAC","WFC","GS","MS","C","BLK","SCHW","AXP","USB",
    "PNC","TFC","COF","BK","STT","FITB","RF","CFG","KEY","HBAN",
    # Healthcare (15)
    "UNH","JNJ","LLY","PFE","ABBV","MRK","TMO","ABT","DHR","BMY",
    "AMGN","GILD","ISRG","MDT","CVS",
    # Consumer (15)
    "WMT","PG","KO","PEP","COST","HD","MCD","NKE","SBUX","TGT",
    "LOW","TJX","ROST","YUM","CMG",
    # Industrials (10)
    "CAT","GE","HON","UNP","BA","DE","LMT","RTX","MMM","FDX",
    # Energy (10)
    "XOM","CVX","COP","SLB","EOG","MPC","VLO","PSX","OXY","HAL",
    # Materials (7)
    "LIN","APD","SHW","NEM","FCX","NUE","DOW",
    # Utilities (5)
    "NEE","DUK","SO","D","SRE",
    # REITs (5)
    "PLD","AMT","CCI","PSA","O",
    # Communications (5)
    "DIS","CMCSA","T","VZ","TMUS",
    # ETFs — NO survivorship bias (18)
    "SPY","QQQ","IWM","XLF","XLE","XLK","XLV","XLP","XLI","XLU",
    "XLB","XLRE","GLD","TLT","HYG","LQD","EEM","EFA",
]

START = "2014-01-01"
END = "2025-01-01"


def fetch(ticker):
    cache = DATA_DIR / f"{ticker}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    url = f"https://eodhd.com/api/eod/{ticker}.US"
    params = {"api_token": EODHD_KEY, "period": "d", "from": START, "to": END, "fmt": "json"}
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if not data or isinstance(data, dict): return None
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df = df.rename(columns={"adjusted_close": "adj_close"})
        df = df[["open","high","low","close","adj_close","volume"]].astype(float)
        if len(df) < 500: return None
        df.to_parquet(cache)
        return df
    except:
        return None


def load_all(force=False):
    data = {}
    for i, t in enumerate(UNIVERSE):
        if i % 30 == 0: print(f"  [{i}/{len(UNIVERSE)}]", flush=True)
        if force and (DATA_DIR / f"{t}.parquet").exists():
            (DATA_DIR / f"{t}.parquet").unlink()
        # Try local cache from trend-futures first
        alt = Path(__file__).parent.parent.parent / "trend-futures" / "casino-stocks" / "data" / "sp500" / f"{t}.parquet"
        alt2 = Path(__file__).parent.parent.parent / "trend-futures" / "institutional" / "data" / f"{t}.parquet"
        cache = DATA_DIR / f"{t}.parquet"
        if not cache.exists():
            for src in [alt, alt2]:
                if src.exists():
                    import shutil
                    shutil.copy(src, cache)
                    break
        df = fetch(t)
        if df is not None and len(df) > 500:
            data[t] = df
        time.sleep(0.1)
    print(f"  Loaded {len(data)}/{len(UNIVERSE)}")
    return data


def integrity_report(data):
    """Generate data integrity report."""
    lines = ["# Data Integrity Report\n"]
    lines.append(f"**Date**: 2026-03-31\n")
    lines.append(f"**Stocks loaded**: {len(data)}/{len(UNIVERSE)}\n")

    # Date coverage
    starts = {t: df.index[0] for t, df in data.items()}
    ends = {t: df.index[-1] for t, df in data.items()}
    common_start = max(starts.values())
    common_end = min(ends.values())
    lines.append(f"**Common period**: {common_start.date()} to {common_end.date()}\n")

    # Missing data
    n_missing = 0
    for t, df in data.items():
        m = df["close"].isna().sum()
        if m > 0: n_missing += 1
    lines.append(f"**Stocks with missing close data**: {n_missing}\n")

    # Survivorship bias discussion
    lines.append("\n## Survivorship Bias\n")
    lines.append("- Universe is CURRENT S&P 500 constituents. This introduces survivorship bias:\n")
    lines.append("  stocks that were delisted/removed before 2024 are not included.\n")
    lines.append("- **Mitigation**: 18 ETFs (SPY, QQQ, sector ETFs) have NO survivorship bias.\n")
    lines.append("  Any strategy must also be profitable on ETF subset.\n")
    lines.append("- **Risk**: Backtest may overstate returns by ~1-2% annually due to survivor bias.\n")
    lines.append("  We acknowledge this and apply conservative thresholds.\n")

    # Corporate actions
    lines.append("\n## Corporate Actions\n")
    lines.append("- EODHD provides `adjusted_close` which accounts for splits and dividends.\n")
    lines.append("- All signals computed on `adj_close` (no split artifacts).\n")
    lines.append("- Raw `close` used only for position sizing (approximate fill price).\n")

    # Data quality
    lines.append("\n## Data Quality Checks\n")
    zero_vol = sum(1 for t, df in data.items() if (df["volume"] == 0).sum() > 20)
    lines.append(f"- Stocks with >20 zero-volume days: {zero_vol}\n")

    large_gaps = 0
    for t, df in data.items():
        ret = df["adj_close"].pct_change().dropna()
        if (ret.abs() > 0.5).sum() > 3:
            large_gaps += 1
    lines.append(f"- Stocks with >3 days of >50% move: {large_gaps}\n")

    report = "".join(lines)
    Path(__file__).parent / "data_integrity_report.md"
    (Path(__file__).parent / "data_integrity_report.md").write_text(report)
    return report


if __name__ == "__main__":
    print("Phase 2: Data Pipeline")
    data = load_all()
    report = integrity_report(data)
    print(report)
