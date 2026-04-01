# General Research V1

## What This Is
Fresh quantitative research project building on Casino V1 findings.
All code starts clean — no legacy baggage from trend-futures repo.

## Prior Knowledge (from Casino V1)
- Stocks > Futures for mean reversion (lower costs, no rolls)
- Long only beats long/short on stocks
- RSI(2), IBS, Bollinger, SMA deviation are proven signals
- 1-3 day hold period is optimal
- Always validate on QC — local backtests overstate by 2-35x on futures
- Down5_IBS0.3 (Sharpe 0.569) is the institutional-validated winner
- Casino V2 (Sharpe 0.674, CAGR 18%) is the aggressive QC-validated winner

## Data
- EODHD API key in .env
- S&P 500 stocks + ETFs
- 10 years daily data (2014-2024)

## QC Integration
- lean-cli installed, Docker available
- QC project "CalibrationSuite" (ID: 29551368)
- Always validate final strategies on QC before considering them real

## Rules
- No forward-looking bias
- All results must include transaction costs ($0.005/share + 5bps slippage)
- Sub-period validation required (3 periods minimum)
- Parameter sensitivity check required
- QC validation for any strategy going to production
