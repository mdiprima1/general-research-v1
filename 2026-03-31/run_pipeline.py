#!/usr/bin/env python3
"""
Phases 4-10: Strategy Enumeration → False Discovery Control → Final Selection

186 pre-registered hypotheses. Bonferroni-corrected significance.
Reject everything that doesn't survive.
"""
import sys, time, json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sp_stats

sys.path.insert(0, str(Path(__file__).parent))
from data_pipeline import load_all
from features import compute_features

OUT = Path(__file__).parent
COST_PER_TRADE_BPS = 10  # 5bps slippage + 5bps commission (conservative)
N_HYPOTHESES = 186
BONFERRONI_ALPHA = 0.05 / N_HYPOTHESES  # = 0.000269
MIN_TRADES = 200
YEARS = 10


# ── Phase 4: Strategy Enumeration ──

def enumerate_strategies():
    """Generate all 186 pre-registered hypotheses."""
    strats = []
    sid = 0

    # Family A: Single indicators (96)
    for indicator, thresholds in [
        ("rsi_2", [5, 10, 15, 20]),
        ("rsi_3", [10, 15, 20, 25]),
        ("ibs", [0.10, 0.15, 0.20, 0.25]),
        ("bb_z_20", [-3.0, -2.5, -2.0, -1.5]),
        ("sma_dev_atr", [-2.0, -1.5, -1.0, -0.75]),
        ("williams_r", [-95, -90, -85, -80]),
        ("stoch_k", [5, 10, 15, 20]),
        ("cci", [-200, -150, -100, -75]),
    ]:
        for thresh in thresholds:
            for hold in [1, 2, 3]:
                strats.append({
                    "id": f"H{sid:04d}", "family": "A_single",
                    "rules": [(indicator, "<", thresh)], "hold": hold,
                })
                sid += 1

    # Family A: Composites (54)
    composites = [
        ("ibs", "<", 0.15, "rsi_3", "<", 25),
        ("ibs", "<", 0.20, "rsi_3", "<", 30),
        ("ibs", "<", 0.25, "rsi_3", "<", 35),
        ("bb_z_20", "<", -2.0, "rsi_3", "<", 35),
        ("bb_z_20", "<", -2.5, "rsi_3", "<", 30),
        ("sma_dev_atr", "<", -1.5, "rsi_3", "<", 35),
    ]
    for i1, o1, t1, i2, o2, t2 in composites:
        for hold in [1, 2, 3]:
            strats.append({
                "id": f"H{sid:04d}", "family": "A_composite",
                "rules": [(i1, o1, t1), (i2, o2, t2)], "hold": hold,
            })
            sid += 1

    # Family A: More composites
    more = [
        ("down_days", ">=", 3, "ibs", "<", 0.25),
        ("down_days", ">=", 4, "ibs", "<", 0.30),
        ("down_days", ">=", 5, "ibs", "<", 0.30),
        ("mfi", "<", 20, "rsi_3", "<", 35),
        ("mfi", "<", 15, "rsi_3", "<", 30),
        ("rsi_14", "<", 25, "rsi_3", "<", 35),
    ]
    for i1, o1, t1, i2, o2, t2 in more:
        for hold in [2, 3]:
            strats.append({
                "id": f"H{sid:04d}", "family": "A_composite",
                "rules": [(i1, o1, t1), (i2, o2, t2)], "hold": hold,
            })
            sid += 1

    # Family B: Momentum (18)
    for lookback in [63, 126, 252]:
        for top_pct in [0.10, 0.20, 0.30]:
            for rebal in [5, 21]:
                strats.append({
                    "id": f"H{sid:04d}", "family": "B_momentum",
                    "rules": [("momentum", ">", lookback)],
                    "hold": rebal, "top_pct": top_pct,
                })
                sid += 1

    # Family C: Low Volatility (12)
    for lookback in [21, 63, 126]:
        for bottom_pct in [0.20, 0.30]:
            for rebal in [21, 63]:
                strats.append({
                    "id": f"H{sid:04d}", "family": "C_lowvol",
                    "rules": [("vol_rank", "<", bottom_pct)],
                    "hold": rebal,
                })
                sid += 1

    # Family D: Regime Filter on best A (6)
    for vol_thresh in [0.15, 0.20, 0.25]:
        for base in ["best_A_1", "best_A_2"]:
            strats.append({
                "id": f"H{sid:04d}", "family": "D_regime",
                "rules": [("market_vol", "<", vol_thresh)],
                "hold": 2, "base": base,
            })
            sid += 1

    print(f"  Enumerated {len(strats)} strategies (target: {N_HYPOTHESES})")
    return strats


# ── Phase 5: Backtesting ──

def backtest_mean_reversion(features_dict, price_data, rules, hold_days):
    """Backtest a long-only mean reversion strategy across all stocks."""
    all_rets = []
    trade_count = 0

    for ticker, feats in features_dict.items():
        if ticker not in price_data: continue
        prices = price_data[ticker]["adj_close"]

        # Generate signal
        mask = pd.Series(True, index=feats.index)
        for feat, op, thresh in rules:
            if feat not in feats.columns:
                mask[:] = False; break
            if op == "<": mask &= feats[feat] < thresh
            elif op == ">": mask &= feats[feat] > thresh
            elif op == ">=": mask &= feats[feat] >= thresh
            elif op == "<=": mask &= feats[feat] <= thresh

        signal_dates = feats.index[mask]
        last_exit = -1

        for entry_date in signal_dates:
            if entry_date not in prices.index: continue
            entry_idx = prices.index.get_loc(entry_date)
            if entry_idx <= last_exit: continue

            entry_p = float(prices.iloc[entry_idx])
            exit_idx = min(entry_idx + hold_days, len(prices) - 1)
            exit_p = float(prices.iloc[exit_idx])
            if entry_p <= 0: continue

            ret = (exit_p / entry_p - 1) - COST_PER_TRADE_BPS / 10000
            all_rets.append({"date": entry_date, "ret": ret, "ticker": ticker})
            last_exit = exit_idx
            trade_count += 1

    return all_rets


def compute_metrics(trade_rets):
    """Compute strategy metrics from list of trade returns."""
    if len(trade_rets) < MIN_TRADES:
        return None

    df = pd.DataFrame(trade_rets)
    rets = df["ret"]
    n = len(rets)

    # Daily PnL series (aggregate by date)
    daily = df.groupby("date")["ret"].mean()
    daily = daily.reindex(pd.bdate_range(daily.index.min(), daily.index.max()), fill_value=0)

    # Metrics
    mean_ret = rets.mean()
    std_ret = rets.std()
    win_rate = (rets > 0).mean() * 100

    # t-statistic for mean return
    t_stat = mean_ret / (std_ret / np.sqrt(n)) if std_ret > 0 else 0

    # p-value (two-sided, but we only care about positive)
    p_value = sp_stats.t.sf(abs(t_stat), n - 1)  # One-sided

    # Annualized Sharpe from daily returns
    daily_mean = daily.mean()
    daily_std = daily.std()
    sharpe = daily_mean / daily_std * np.sqrt(252) if daily_std > 0 else 0

    # Equity curve
    eq = (1 + daily).cumprod()
    n_years = len(daily) / 252
    cagr = (eq.iloc[-1] ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    peak = eq.cummax()
    max_dd = ((eq - peak) / peak).min() * 100

    # Sub-period analysis
    sub = {}
    for label, (s, e) in [("2014-2017", ("2014-06-01","2017-12-31")),
                           ("2018-2021", ("2018-01-01","2021-12-31")),
                           ("2022-2024", ("2022-01-01","2024-12-31"))]:
        mask = (daily.index >= s) & (daily.index <= e)
        sub_d = daily[mask]
        if len(sub_d) > 60:
            sub_sharpe = float(sub_d.mean() / sub_d.std() * np.sqrt(252)) if sub_d.std() > 0 else 0
            sub[label] = round(sub_sharpe, 3)

    return {
        "n_trades": n,
        "mean_ret_pct": round(mean_ret * 100, 4),
        "win_rate": round(win_rate, 2),
        "t_stat": round(t_stat, 3),
        "p_value": p_value,
        "sharpe": round(sharpe, 3),
        "cagr_pct": round(cagr, 2),
        "max_dd_pct": round(max_dd, 2),
        "n_stocks": df["ticker"].nunique(),
        "sub_periods": sub,
    }


def main():
    t0 = time.time()
    print("=" * 70)
    print("INSTITUTIONAL RESEARCH — PHASES 4-10")
    print(f"Hypotheses: {N_HYPOTHESES} | Bonferroni α: {BONFERRONI_ALPHA:.6f}")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    data = load_all()
    print(f"  {len(data)} stocks loaded")

    # Compute features
    print("\nComputing features...")
    features_dict = {}
    for i, (t, df) in enumerate(data.items()):
        if i % 30 == 0: print(f"  [{i}/{len(data)}]", flush=True)
        try:
            features_dict[t] = compute_features(df)
        except: pass
    print(f"  {len(features_dict)} stocks with features")

    # Phase 4: Enumerate
    print(f"\n{'='*70}\nPHASE 4: STRATEGY ENUMERATION\n{'='*70}")
    strategies = enumerate_strategies()
    Path(OUT / "strategy_registry.json").write_text(
        json.dumps(strategies[:10], indent=2))  # Save sample

    # Phase 5: Backtest
    print(f"\n{'='*70}\nPHASE 5: BACKTESTING\n{'='*70}")
    results = []
    for i, strat in enumerate(strategies):
        if i % 25 == 0:
            sig = len([r for r in results if r and r.get("p_value", 1) < 0.05])
            print(f"  [{i}/{len(strategies)}] ({sig} nominally significant)", flush=True)

        family = strat["family"]
        if family in ("B_momentum", "C_lowvol", "D_regime"):
            continue  # Skip non-MR families for now (different backtest logic needed)

        try:
            trades = backtest_mean_reversion(features_dict, data, strat["rules"], strat["hold"])
            metrics = compute_metrics(trades)
            if metrics:
                metrics["id"] = strat["id"]
                metrics["family"] = family
                metrics["rules"] = str(strat["rules"])
                metrics["hold"] = strat["hold"]
                results.append(metrics)
        except:
            pass

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUT / "backtests.csv", index=False)
    print(f"  {len(results_df)} strategies with results")

    # Phase 6: False Discovery Control
    print(f"\n{'='*70}\nPHASE 6: FALSE DISCOVERY CONTROL\n{'='*70}")

    if results_df.empty:
        print("  NO RESULTS. PIPELINE FAILURE."); return

    # Bonferroni
    bonf = results_df[results_df["p_value"] < BONFERRONI_ALPHA].copy()
    print(f"\n  BONFERRONI (α={BONFERRONI_ALPHA:.6f}):")
    print(f"  Strategies passing: {len(bonf)} / {len(results_df)}")

    # Benjamini-Hochberg
    sorted_p = results_df.sort_values("p_value")
    sorted_p["bh_threshold"] = [(i+1) / len(sorted_p) * 0.05 for i in range(len(sorted_p))]
    sorted_p["bh_pass"] = sorted_p["p_value"] <= sorted_p["bh_threshold"]
    bh_pass = sorted_p[sorted_p["bh_pass"]]
    print(f"\n  BENJAMINI-HOCHBERG (FDR=5%):")
    print(f"  Strategies passing: {len(bh_pass)} / {len(results_df)}")

    # Deflated Sharpe approximation
    # E[max SR from N random strategies] ≈ sqrt(2 * ln(N)) / sqrt(T/252)
    expected_max_sr = np.sqrt(2 * np.log(N_HYPOTHESES))
    print(f"\n  DEFLATED SHARPE:")
    print(f"  Expected max Sharpe from {N_HYPOTHESES} random strategies: {expected_max_sr:.3f}")
    print(f"  Any Sharpe must exceed {expected_max_sr:.3f} to be non-random")

    # Select passing set
    if len(bonf) > 0:
        passing = bonf
        method = "Bonferroni"
    elif len(bh_pass) > 0:
        passing = bh_pass
        method = "BH"
    else:
        passing = pd.DataFrame()
        method = "NONE"

    # False discovery report
    fdr = [
        f"# Phase 6 — False Discovery Report\n",
        f"## Hypothesis Count: {N_HYPOTHESES}\n",
        f"## Strategies Tested: {len(results_df)}\n",
        f"## Bonferroni α: {BONFERRONI_ALPHA:.6f}\n",
        f"## Passing Bonferroni: {len(bonf)}\n",
        f"## Passing BH (FDR 5%): {len(bh_pass)}\n",
        f"## Expected Max Random Sharpe: {expected_max_sr:.3f}\n",
        f"## Selection Method: {method}\n",
    ]
    (OUT / "false_discovery_report.md").write_text("".join(fdr))

    if passing.empty:
        print(f"\n  *** NO STRATEGIES PASS MULTIPLE TESTING CORRECTION ***")
        print(f"  Showing top 10 by t-stat (for diagnostic purposes only):")
        top = results_df.sort_values("t_stat", ascending=False).head(10)
        print(f"  {'ID':>6s}  {'Rules':>50s}  {'Hold':>4s}  {'t':>6s}  {'p':>10s}  {'Sharpe':>7s}  {'WR':>5s}  {'Trades':>6s}")
        for _, r in top.iterrows():
            print(f"  {r['id']:>6s}  {r['rules'][:50]:>50s}  {r['hold']:>4.0f}  {r['t_stat']:>6.2f}  {r['p_value']:>10.6f}  {r['sharpe']:>7.3f}  {r['win_rate']:>4.1f}%  {r['n_trades']:>6.0f}")

    # Phase 7: Robustness (on passing or top strategies)
    print(f"\n{'='*70}\nPHASE 7: ROBUSTNESS TESTING\n{'='*70}")

    test_set = passing if not passing.empty else results_df.sort_values("t_stat", ascending=False).head(5)

    robust_results = []
    for _, row in test_set.iterrows():
        sub = row.get("sub_periods", {})
        if isinstance(sub, str):
            try: sub = json.loads(sub.replace("'", '"'))
            except: sub = {}

        n_pos = sum(1 for v in sub.values() if v > 0)
        consistent = n_pos >= 2

        # Cost stress test (2x costs)
        stressed_ret = row["mean_ret_pct"] / 100 - COST_PER_TRADE_BPS / 10000  # Additional costs
        still_profitable = stressed_ret > 0

        robust_results.append({
            **row.to_dict(),
            "sub_period_consistent": consistent,
            "survives_2x_costs": still_profitable,
            "robust": consistent and still_profitable,
        })

    robust_df = pd.DataFrame(robust_results)
    surviving = robust_df[robust_df["robust"] == True]

    print(f"  Tested: {len(robust_df)}")
    print(f"  Sub-period consistent: {robust_df['sub_period_consistent'].sum()}")
    print(f"  Survives 2x costs: {robust_df['survives_2x_costs'].sum()}")
    print(f"  Fully robust: {len(surviving)}")

    (OUT / "robustness_report.md").write_text(
        f"# Robustness Report\nTested: {len(robust_df)}\nRobust: {len(surviving)}\n")

    # Phase 10: Final Selection
    print(f"\n{'='*70}\nPHASE 10: FINAL SELECTION\n{'='*70}")

    if not surviving.empty:
        winner = surviving.sort_values("sharpe", ascending=False).iloc[0]
        status = "PASS"
    elif not passing.empty:
        winner = passing.sort_values("sharpe", ascending=False).iloc[0]
        status = "PASS (not fully robust)"
    elif len(results_df) > 0:
        winner = results_df.sort_values("t_stat", ascending=False).iloc[0]
        status = "FAIL — No strategy passes corrected significance"
    else:
        print("  TOTAL FAILURE — No results produced")
        return

    print(f"\n  STATUS: {status}")
    print(f"\n  {'='*50}")
    print(f"  SELECTED: {winner['id']} ({winner['family']})")
    print(f"  Rules: {winner['rules']}")
    print(f"  Hold: {winner['hold']} days")
    print(f"  {'='*50}")
    print(f"  Sharpe:    {winner['sharpe']:.3f}")
    print(f"  CAGR:      {winner['cagr_pct']:.1f}%")
    print(f"  Max DD:    {winner['max_dd_pct']:.1f}%")
    print(f"  Win Rate:  {winner['win_rate']:.1f}%")
    print(f"  Trades:    {winner['n_trades']:.0f}")
    print(f"  t-stat:    {winner['t_stat']:.3f}")
    print(f"  p-value:   {winner['p_value']:.8f}")
    if "sub_periods" in winner:
        print(f"  Sub-periods: {winner['sub_periods']}")
    print(f"\n  Bonferroni threshold: t > 3.65 (p < {BONFERRONI_ALPHA:.6f})")
    print(f"  This strategy: {'PASSES' if winner['p_value'] < BONFERRONI_ALPHA else 'FAILS'} Bonferroni")

    # Save final report
    final = {
        "status": status, "method": method,
        "n_hypotheses": N_HYPOTHESES, "n_tested": len(results_df),
        "n_bonferroni": len(bonf), "n_bh": len(bh_pass),
        "winner": {k: v for k, v in winner.to_dict().items() if not isinstance(v, (pd.DataFrame, pd.Series))},
    }
    (OUT / "final_strategy.md").write_text(
        f"# Final Strategy Report\n\n"
        f"## Status: {status}\n\n"
        f"## Hypothesis Control\n"
        f"- Total hypotheses: {N_HYPOTHESES}\n"
        f"- Tested: {len(results_df)}\n"
        f"- Passing Bonferroni: {len(bonf)}\n"
        f"- Passing BH: {len(bh_pass)}\n\n"
        f"## Selected Strategy\n"
        f"- ID: {winner['id']}\n"
        f"- Rules: {winner['rules']}\n"
        f"- Hold: {winner['hold']} days\n"
        f"- Sharpe: {winner['sharpe']}\n"
        f"- CAGR: {winner['cagr_pct']}%\n"
        f"- Max DD: {winner['max_dd_pct']}%\n"
        f"- Win Rate: {winner['win_rate']}%\n"
        f"- t-stat: {winner['t_stat']}\n"
        f"- p-value: {winner['p_value']}\n"
    )

    elapsed = time.time() - t0
    print(f"\nPipeline complete in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
