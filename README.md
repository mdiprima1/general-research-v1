# General Research V1

Institutional-grade quantitative strategy research.

## Starting Point

This project builds on validated findings from the Casino V1 research:

### What we proved works (QC-validated)
- **Short-term mean reversion on stocks**: long only, daily bars, 1-3 day hold
- **Best signals**: RSI(2) extreme, IBS+RSI(3) confirmation, SMA deviation, Bollinger+RSI
- **Casino Stocks V2**: +129%, Sharpe 0.674, CAGR 18% on QuantConnect
- **Institutional winner**: Down5_IBS0.3 (Sharpe 0.569, consistent across 3 sub-periods)

### What we proved doesn't work
- Futures trend following (edge too small vs execution costs)
- Intraday futures casino (commission > edge)
- Short selling on stocks (drags down returns)

### Calibration infrastructure
- QC/LEAN integration via lean-cli + Docker
- 20-test calibration suite (4 PERFECT, 3 OK)
- Single-stream stock calibration: 99.1% match with QC

## Structure

```
├── data/           # Market data (EODHD)
├── features/       # Feature engineering modules
├── strategies/     # Strategy definitions
├── backtests/      # Backtest results
├── validation/     # Statistical validation
├── reports/        # Research reports
├── production/     # Production-ready implementations
└── notebooks/      # Jupyter analysis
```

## Data Source
- EODHD API (key in .env)
- S&P 500 + major ETFs
- Daily OHLCV, adjusted for splits/dividends
