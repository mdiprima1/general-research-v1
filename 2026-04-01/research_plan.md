# ORB V10 Improvement Research Plan

## Baseline: ORB V10 Winner (QC-Validated)

### Architecture
```
1. Opening Range: 9:30-9:45 high/low on ES and NQ
2. Range Filter: skip if range < 0.15% or > 1.5% of price
3. Trend Filter: 20-day SMA — only long above, short below
4. Confirmation: price must stay beyond range for 7 minutes
5. Entry: market order after confirmation
6. Stop Loss: opposite range boundary
7. Profit Target: 2x range width (2:1 R:R)
8. Time Stop: flatten at 15:45
9. Vol Filter: skip when realized vol < 12% OR VIX < 15
10. VIX Compression: skip when VIX dropped >20% in 10 days AND VIX < 18
11. Monday Skip: no trading Mondays
12. Position Sizing: risk per trade = ES 1.0%, NQ 0.5% of portfolio
```

### QC-Validated Performance (2018-2025)
- Sharpe: 0.618 (QC reported) / 1.465 (OOS from 8-Gate)
- CAGR: 22.1%
- Max DD: 31.9%
- Win Rate: 54%
- Trades: 2,166 (order fills) ≈ 1,083 round trips
- Net Profit: 393%
- 8-Gate Score: 85/100

### QC Project
- Project ID: 29466018
- Backtest ID: 12aaf948e3065a105f9aeba7dc20da9f

## Improvement Hypotheses

### H1: Instrument Expansion
**Current**: ES + NQ only
**Test**: Add GC (Gold), CL (Crude), ZN (10-Year), 6E (Euro FX)
**Rationale**: More instruments = more diversification = smoother equity curve
**Risk**: Some instruments may not have ORB edge

### H2: Confirmation Timer Optimization
**Current**: 7 minutes fixed
**Test**: 3, 5, 7, 10, 15 minutes
**Rationale**: The V10 sprint found 7 was optimal vs 5. But the search was limited.
**Note**: Already tested in original research. Re-validate with updated data.

### H3: Range Period Optimization
**Current**: 9:30-9:45 (15 min)
**Test**: 5, 10, 15, 30, 60 min ranges
**Rationale**: Different range periods capture different market dynamics

### H4: R:R Ratio Optimization
**Current**: 2:1 (target = 2x range width)
**Test**: 1:1, 1.5:1, 2:1, 2.5:1, 3:1
**Rationale**: Higher R:R = lower win rate but bigger winners

### H5: Asymmetric Long/Short
**Current**: Both long and short with same R:R
**Test**: Long only, Short only, Asymmetric R:R (different for long vs short)
**Rationale**: Markets have upward bias — long breakouts may be stronger

### H6: Day-of-Week Effects
**Current**: Skip Mondays
**Test**: Skip Mon+Fri, Trade specific days only, No filter
**Rationale**: Different days have different volatility profiles

### H7: Time-of-Day Exit Optimization
**Current**: Flatten at 15:45
**Test**: 14:00, 14:30, 15:00, 15:30, 15:45
**Rationale**: Late-day reversals can eat profits

### H8: Volatility-Adjusted Position Sizing
**Current**: Fixed % risk per trade
**Test**: Scale position inversely with VIX/ATR, Kelly-based sizing
**Rationale**: Take bigger bets in low-vol (calmer) environments

### H9: Multi-Timeframe Confirmation
**Current**: 1-min bars for confirmation
**Test**: Add daily trend + 5-min momentum as filters
**Rationale**: Higher-timeframe alignment improves win rate

### H10: Adjacent Range Breakout
**Current**: Only first breakout of the day
**Test**: Allow re-entry if price returns to range and breaks out again
**Rationale**: "Second chance" breakouts may be higher conviction

## Execution Plan

1. Copy ORB V10 algo to this project
2. Run baseline on QC (re-verify 2018-2025 performance)
3. Test each hypothesis ONE AT A TIME on QC
4. Keep changes that improve Sharpe OR reduce Max DD without hurting Sharpe
5. Combine winning improvements
6. Final validation with 8-Gate framework

## Success Criteria
- Sharpe > 0.7 (improvement over V10's 0.618)
- Max DD < 25% (improvement over V10's 31.9%)
- Win Rate ≥ 54% (maintain or improve)
- 8-Gate Score ≥ 85/100 (maintain or improve)
- All on QC, not local backtest
