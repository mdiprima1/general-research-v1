# Phase 1 — Hypothesis Accounting

## Date: 2026-03-31
## Researcher: Autonomous System

---

## 1. Hypothesis Families

### Family A: Short-Term Mean Reversion (Long Only)
**Rationale**: Overreaction to negative information in liquid stocks creates temporary mispricings that revert within 1-5 days. Supported by academic literature (Jegadeesh 1990, Lehmann 1990) and our QC-validated Casino V2 result (Sharpe 0.674).
**Signals**: RSI, IBS, Bollinger z-score, SMA deviation, Williams %R, Stochastic, CCI, MFI
**Parameters**: Signal threshold, holding period
**Expected failure**: Extended bear markets, low-vol grinds with no signals

### Family B: Momentum (Cross-Sectional)
**Rationale**: Winners continue to outperform losers over 3-12 month horizons due to under-reaction, herding, and behavioral biases (Jegadeesh & Titman 1993).
**Signals**: 6M return rank, 12M-1M return rank
**Parameters**: Lookback, portfolio size, rebalance frequency
**Expected failure**: Momentum crashes (reversals after extended trends)

### Family C: Volatility-Based
**Rationale**: Low-volatility stocks outperform high-volatility stocks on risk-adjusted basis (low-vol anomaly, Baker et al. 2011).
**Signals**: Realized vol rank, vol-of-vol, ATR rank
**Parameters**: Vol lookback, portfolio construction
**Expected failure**: Vol regime transitions

### Family D: Regime Filter (Overlay Only)
**Rationale**: Mean reversion fails in extreme regimes. Filtering by market-level volatility should improve Sharpe.
**Signals**: SPY realized vol, VIX proxy (via vol expansion)
**Parameters**: Vol threshold
**Note**: NOT a standalone strategy. Applied as filter on Family A.

## 2. Total Hypothesis Count

### Enumeration

| Family | Signals | Thresholds | Hold Periods | Universes | Subtotal |
|--------|---------|------------|-------------|-----------|----------|
| A: Mean Reversion | 8 | 4 each | 3 (1,2,3 day) | 1 | 96 |
| A: Composites | 6 pairs | 3 combos | 3 | 1 | 54 |
| B: Momentum | 2 | 3 lookbacks | 3 rebal freq | 1 | 18 |
| C: Volatility | 2 | 3 lookbacks | 2 constructions | 1 | 12 |
| D: Regime filter | 2 | 3 thresholds | applied to top A | 1 | 6 |

**Total hypotheses: 186**

### Breakdown
- Family A (single indicators): 96
- Family A (composite): 54
- Family B: 18
- Family C: 12
- Family D (overlay): 6
- **Grand total: 186**

## 3. Multiple Testing Correction

### Primary: Bonferroni Correction (Conservative)
- Nominal significance: α = 0.05
- Corrected significance: α_corrected = 0.05 / 186 = **0.000269**
- Required t-statistic: **t > 3.65** (for ~2500 daily observations over 10 years)
- Required Sharpe ratio: t / √(years) ≈ 3.65 / √10 = **Sharpe > 1.15**

### Secondary: Benjamini-Hochberg (FDR = 5%)
- Rank all p-values
- Accept if p_k ≤ (k/186) × 0.05
- Less conservative, controls false discovery RATE rather than probability

### Tertiary: Deflated Sharpe Ratio (De Prado)
- Accounts for: number of trials, skewness, kurtosis, track record length
- DSR = Prob(SR > 0 | SR*, σ(SR), N_trials)
- Minimum acceptable DSR: > 95%

## 4. Minimum Thresholds AFTER Correction

| Metric | Bonferroni Threshold | BH Threshold | Notes |
|--------|---------------------|-------------|-------|
| Sharpe (annual) | > 1.15 | > 0.80 | After costs |
| t-statistic | > 3.65 | > 2.50 | On daily returns |
| p-value | < 0.000269 | BH-adjusted | — |
| Win rate | > 50% | > 50% | Long-only mean reversion |
| Max DD | < 25% | < 30% | Absolute limit |
| Min trades | > 200 | > 100 | Statistical adequacy |
| Sub-period consistency | 3/3 positive | 2/3 positive | — |

## 5. Pre-Registration

**I commit to the following BEFORE seeing any results:**

1. The 186 hypotheses enumerated above are the COMPLETE set. No additional hypotheses will be tested.
2. Thresholds are fixed. No post-hoc relaxation.
3. If ZERO strategies pass Bonferroni, I will report FAILURE and check BH as secondary.
4. If ZERO pass BH, I will report FAILURE. No further relaxation.
5. Parameter optimization after seeing results is PROHIBITED.
6. The strategy selected must have the highest Sharpe among those passing the corrected threshold. No cherry-picking.

---

**Hypothesis accounting complete. Proceeding to Phase 2.**
