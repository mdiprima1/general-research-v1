#!/usr/bin/env python3
"""
ORB V10 Systematic Improvement Tests

Runs each hypothesis on QC one at a time.
Compares against the V10 baseline.
"""
import hashlib, time, requests, json, re, copy
from pathlib import Path

USER_ID = '184399'
API_TOKEN = 'cd2c781599607914f77cc08798e35cfcd9b4da52155b73efdbd21b3417367ca7'
BASE_URL = 'https://www.quantconnect.com/api/v2'

# Create a dedicated QC project
PROJECT_NAME = "ORB-V11-Research"


def api(method, endpoint, **kwargs):
    ts = str(int(time.time()))
    h = hashlib.sha256(f'{API_TOKEN}:{ts}'.encode()).hexdigest()
    kwargs.setdefault('headers', {}).update({'Timestamp': ts})
    r = getattr(requests, method)(f'{BASE_URL}/{endpoint}', auth=(USER_ID, h), **kwargs)
    return r.json()


def get_or_create_project():
    r = api('post', 'projects/create', json={'name': PROJECT_NAME, 'language': 'Py'})
    if r.get('success'):
        return r['projects'][0]['projectId']
    # Already exists
    r = api('get', 'projects/read')
    for p in r.get('projects', []):
        if p['name'] == PROJECT_NAME:
            return p['projectId']
    raise Exception("Cannot create project")


def run_backtest(project_id, code, name):
    """Upload, compile, run, return stats."""
    api('post', 'files/update', json={'projectId': project_id, 'name': 'main.py', 'content': code})

    r = api('post', 'compile/create', json={'projectId': project_id})
    cid = r.get('compileId'); state = r.get('state', '')
    for _ in range(60):
        if state == 'BuildSuccess': break
        if state == 'BuildError': return {'error': str(r.get('logs', [])[:200])}
        time.sleep(2)
        r = api('get', 'compile/read', params={'projectId': project_id, 'compileId': cid})
        state = r.get('state', '')
    if state != 'BuildSuccess': return {'error': 'compile timeout'}

    r = api('post', 'backtests/create', json={
        'projectId': project_id, 'compileId': cid, 'backtestName': name,
    })
    bt_id = r.get('backtestId') or r.get('backtest', {}).get('backtestId')
    if not bt_id: return {'error': f'no bt_id: {str(r)[:100]}'}

    for _ in range(240):
        time.sleep(15)
        r = api('get', 'backtests/read', params={'projectId': project_id, 'backtestId': bt_id})
        bt = r.get('backtest', r)
        if bt.get('completed'):
            time.sleep(3)
            r = api('get', 'backtests/read', params={'projectId': project_id, 'backtestId': bt_id})
            bt = r.get('backtest', r)
            stats = bt.get('statistics', {})
            runtime = bt.get('runtimeStatistics', {})
            return {
                'backtest_id': bt_id,
                'sharpe': stats.get('Sharpe Ratio', 'N/A'),
                'cagr': stats.get('Compounding Annual Return', 'N/A'),
                'max_dd': stats.get('Drawdown', 'N/A'),
                'orders': stats.get('Total Orders', 'N/A'),
                'win_rate': stats.get('Win Rate', 'N/A'),
                'net_profit': stats.get('Net Profit', 'N/A'),
                'fees': stats.get('Total Fees', 'N/A'),
                'runtime': runtime,
            }
    return {'error': 'timeout'}


def modify_param(code, param_name, new_value):
    """Replace a parameter value in the algorithm code."""
    # Match: self.param_name = value
    pattern = rf'(self\.{param_name}\s*=\s*).+?(\s*\n)'
    replacement = rf'\g<1>{new_value}\2'
    modified = re.sub(pattern, replacement, code)
    if modified == code:
        print(f"  WARNING: Could not modify {param_name}")
    return modified


def main():
    print("=" * 70)
    print("ORB V10 → V11 SYSTEMATIC IMPROVEMENT")
    print("=" * 70)

    project_id = get_or_create_project()
    print(f"QC Project: {PROJECT_NAME} (ID: {project_id})")

    baseline_code = Path("2026-04-01/orb_v10_baseline.py").read_text()

    # ── Test 0: Baseline (re-verify) ──
    tests = [
        ("BASELINE", baseline_code, "V10 Baseline Re-verify"),
    ]

    # ── H2: Confirmation timer ──
    for minutes in [3, 5, 10, 15]:
        code = modify_param(baseline_code, "confirmation_minutes", str(minutes))
        tests.append((f"H2_confirm_{minutes}min", code, f"Confirmation {minutes}min"))

    # ── H4: R:R ratio ──
    for rr in [1.0, 1.5, 2.5, 3.0]:
        code = modify_param(baseline_code, "reward_risk_ratio", str(rr))
        tests.append((f"H4_RR_{rr}", code, f"R:R {rr}:1"))

    # ── H5: Long only ──
    # Add a flag to skip short trades
    long_only_code = baseline_code.replace(
        'elif price < rl and trend <= 0:',
        'elif False and price < rl and trend <= 0:  # LONG ONLY'
    )
    tests.append(("H5_long_only", long_only_code, "Long Only"))

    # ── H6: Day of week ──
    # Skip Monday + Friday
    no_mon_fri = baseline_code.replace(
        'if now.weekday() == 0:',
        'if now.weekday() in (0, 4):  # Skip Mon + Fri'
    )
    tests.append(("H6_skip_mon_fri", no_mon_fri, "Skip Mon+Fri"))

    # No day filter at all
    no_day_filter = baseline_code.replace(
        'if now.weekday() == 0:\n            return',
        'if False:  # No day filter\n            pass'
    )
    tests.append(("H6_no_day_filter", no_day_filter, "No Day Filter"))

    # ── H7: Earlier flatten ──
    for flatten_h, flatten_m in [(14, 30), (15, 0), (15, 15)]:
        code = baseline_code
        code = code.replace(
            '"flatten_hour": 15, "flatten_min": 45,',
            f'"flatten_hour": {flatten_h}, "flatten_min": {flatten_m},'
        )
        tests.append((f"H7_flatten_{flatten_h}{flatten_m:02d}", code, f"Flatten {flatten_h}:{flatten_m:02d}"))

    # ── H3: Range period (change to 30 min: 9:30-10:00) ──
    range_30 = baseline_code.replace(
        '"range_end_hour": 9, "range_end_min": 45,',
        '"range_end_hour": 10, "range_end_min": 0,'
    )
    tests.append(("H3_range_30min", range_30, "30min Range (9:30-10:00)"))

    # Range 10 min: 9:30-9:40
    range_10 = baseline_code.replace(
        '"range_end_hour": 9, "range_end_min": 45,',
        '"range_end_hour": 9, "range_end_min": 40,'
    )
    tests.append(("H3_range_10min", range_10, "10min Range (9:30-9:40)"))

    print(f"\nTotal tests: {len(tests)}")

    # Run all tests
    results = []
    for i, (test_id, code, description) in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] {test_id}: {description}...", end=" ", flush=True)
        result = run_backtest(project_id, code, test_id)
        result['test_id'] = test_id
        result['description'] = description
        results.append(result)

        if 'error' in result:
            print(f"ERROR: {result['error'][:60]}")
        else:
            print(f"Sharpe={result['sharpe']}  CAGR={result['cagr']}  DD={result['max_dd']}  Orders={result['orders']}")

        time.sleep(3)  # Rate limit

    # ── Report ──
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")

    print(f"\n  {'Test':>25s}  {'Sharpe':>8s}  {'CAGR':>8s}  {'MaxDD':>8s}  {'WR':>6s}  {'Orders':>7s}  {'Net':>8s}")
    print(f"  {'-'*25}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*6}  {'-'*7}  {'-'*8}")

    for r in results:
        if 'error' in r:
            print(f"  {r['test_id']:>25s}  {'ERROR':>8s}")
        else:
            print(f"  {r['test_id']:>25s}  {r['sharpe']:>8s}  {r['cagr']:>8s}  {r['max_dd']:>8s}  {r['win_rate']:>6s}  {r['orders']:>7s}  {r['net_profit']:>8s}")

    # Save
    Path("2026-04-01/orb_test_results.json").write_text(
        json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to 2026-04-01/orb_test_results.json")


if __name__ == "__main__":
    main()
