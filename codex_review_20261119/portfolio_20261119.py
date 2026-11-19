"""Offline reconstruction of issuer risk and ANT funding from frozen plan/prices."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(sys.argv[1]).resolve()
FOLDER = ROOT / 'codex_review_20261119'
OUT = FOLDER / 'out'
OUT.mkdir(exist_ok=True)
PRICE = ROOT / 'gpt_review_20261113/data_audit/adjusted_close.csv'
PLAN = ROOT / 'current_plan.json'
SOURCES = FOLDER / 'data/sources_web_20261119.json'
QUOTE = FOLDER / 'data/ant_nasdaq_quote_1535.json'
IPO = FOLDER / 'data/ant_filing_inputs.json'
TIMING = ROOT / 'claude_analysis_20261115/out/timing_table_ai8.csv'
AI = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
plan = json.loads(PLAN.read_text())
sources = {row['id']: row for row in json.loads(SOURCES.read_text()) if row['section'] == 'portfolio'}
anchor = pd.Series(sources['vti']['numeric_inputs']['weights_pct']) / 100
caps = pd.Series(sources['market_caps']['numeric_inputs']['market_cap_usd'])
stakes = pd.Series(sources['ant_holders']['numeric_inputs']['shares'])
# Hold price constant at PR #4's timestamp for the stake comparison.
comparison_px = json.loads(IPO.read_text())['claude_comparison_price']
intraday_px = float(json.loads(QUOTE.read_text())['data']['primaryData']['lastSalePrice'].strip('$'))
prices = pd.read_csv(PRICE, index_col='Date', parse_dates=True)
r = prices.pct_change(fill_method=None)
relative = prices.div(prices.loc['2026-09-30'])
drift = relative[anchor.index].div(relative['VTI'], axis=0) * anchor
previous = drift.shift(1)
r['VTI_rest'] = (r['VTI'] - (r[anchor.index] * previous).sum(axis=1)) / (1 - previous.sum(axis=1))
r = r.loc['2023-11-14':'2026-11-13']
assert len(r) == 753 and r.notna().all().all()
weights_at_cutoff = drift.loc['2026-11-13']
names = AI + ['BRK-B', 'XLV', 'SGOV', 'VTI_rest']
cov = r[names].cov() * 252
basket = r[AI].mean(axis=1)
factor_variance = basket.var() * 252
cross = r[names].apply(lambda s: s.cov(basket)) * 252
initial = pd.Series(plan['initial_purchase_2026_11_16']['weights'], dtype=float)
budget = plan['budget_usd']

def exposure(direct):
    e = direct.drop('VTI').reindex(names, fill_value=0.).copy()
    e.loc[anchor.index] += direct['VTI'] * weights_at_cutoff
    e['VTI_rest'] = direct['VTI'] * (1 - weights_at_cutoff.sum())
    return e

def baseline(direct):
    e = exposure(direct)
    s2 = e @ cov @ e
    rc = e * (cov @ e) / s2
    return dict(vol=s2**.5, nvda_rc=rc.NVDA, nvda_weight=e.NVDA, ai8_weight=e[AI].sum(),
                googl_rc=rc.GOOGL)

base = baseline(initial)
assert round(base['vol'] * 100, 2) == 17.62
assert round(base['nvda_rc'] * 100, 1) == 30.3

def evaluate(direct, weight, mode, beta, sigma):
    post = direct.copy()
    total = budget
    if mode == 'new_cash':
        post *= 1 - weight
        total = budget / (1 - weight)
    else:
        post[mode] -= weight
    assert post.min() >= -1e-10 and abs(post.sum() + weight - 1) < 1e-10
    e = exposure(post)
    # r_ANT = beta * r_AI8 + noise. Verify existence of the independent residual.
    assert sigma**2 >= beta**2 * factor_variance
    cov_ant = beta * cross
    portfolio_var = (e @ cov @ e) + 2 * weight * (e @ cov_ant) + (weight * sigma)**2
    rc = e * (cov @ e + weight * cov_ant) / portfolio_var
    rc_ant = weight * (e @ cov_ant + weight * sigma**2) / portfolio_var
    assert abs(rc.sum() + rc_ant - 1) < 1e-10
    indirect = float((e[stakes.index] * stakes * comparison_px / caps).sum())
    stress = weight * -.60 + e[AI].sum() * -.30 - .15 * e.VTI_rest - .10 * e['BRK-B'] - .05 * e.XLV
    return dict(vol=portfolio_var**.5, rc_ant=rc_ant, rc_nvda=rc.NVDA,
                rc_googl=rc.GOOGL, ai9_weight=e[AI].sum()+weight, indirect_two_holders_at_100_18=indirect,
                indirect_two_holders_at_1535=indirect * intraday_px / comparison_px,
                portfolio_usd=total, ant_usd=weight*total, sgov_usd=post.SGOV*total,
                msft_usd=post.MSFT*total, ant_only_minus60_direct=-.60*weight,
                ant_only_minus60_two_holders_at_1535=-.60*(weight+indirect*intraday_px/comparison_px),
                joint_stress=stress)

# Reconstruct ERC with cyclic coordinate minimization (risk budgets 1/n).
def erc(matrix):
    a = matrix.to_numpy()
    x = 1 / np.sqrt(a.diagonal())
    for _ in range(1000):
        for i in range(len(x)):
            b = a[i] @ x - a[i, i] * x[i]
            x[i] = 2 / (b + np.sqrt(b*b + 4*a[i, i]))
        if np.max(np.abs(x*(a@x) - 1)) < 1e-12:
            break
    assert np.max(np.abs(x*(a@x) - 1)) < 1e-12
    return pd.Series(x/x.sum(), index=matrix.index)

peers = AI[1:]
erc7 = erc(cov.loc[peers, peers])
cut = initial.copy()
cut['NVDA'] -= .05
cut.loc[peers] += .05 * erc7
rows = []
for label, direct in [('entry_12.5', initial), ('export_gate_7.5', cut)]:
    for mode in ['MSFT', 'SGOV', 'new_cash']:
        for weight in [0, .015, .02, .025, .03, .037, .04, .05, .06, .07]:
            for beta, sigma in [(b, s) for b in [1., 1.25, 1.5] for s in [.50, .70, .90]] + [
                    (.85*.90/np.sqrt(factor_variance), .90)]:
                rows.append(dict(plan=label, funding=mode, weight=weight, beta=beta, sigma=sigma,
                                 **evaluate(direct, weight, mode, beta, sigma)))
frame = pd.DataFrame(rows)
frame.to_csv(OUT/'portfolio_scenarios.csv', index=False, float_format='%.10f')

# Realized volatility under quarterly resetting from daily buy-and-hold paths within each quarter.
def quarterly_vol(weights, start, end):
    daily = prices.loc[start:end, weights.index].pct_change(fill_method=None).iloc[1:]
    relative_nav = (1 + daily).groupby(daily.index.to_period('Q')).cumprod() @ weights
    prev_nav = relative_nav.groupby(relative_nav.index.to_period('Q')).shift(1).fillna(1.)
    return (relative_nav / prev_nav - 1).std() * np.sqrt(252)
neutral = pd.Series(plan['weights'])
old = pd.Series(plan['previous_plan']['conviction8'])
def exact_hybrid(a):
    return pd.Series({'NVDA': .10, 'VTI': .25, **((a - .10)*erc7).to_dict(),
                      'BRK-B': .40*(.75-a), 'XLV': .20*(.75-a), 'SGOV': .40*(.75-a)})
window = ('2023-11-13','2026-11-13')
old_vol = quarterly_vol(old, *window)
a_core = brentq(lambda a: quarterly_vol(exact_hybrid(a), *window) - old_vol, .2, .6)
def risk_parity_comparison(w):
    return evaluate(initial,w,'new_cash',1.25,.70)
old_googl_parity = brentq(lambda w: risk_parity_comparison(w)['rc_ant'] - base['googl_rc'], 0, .1)
concurrent_parity = brentq(lambda w: risk_parity_comparison(w)['rc_ant'] - risk_parity_comparison(w)['rc_googl'], 0, .1)
# Sanity-check the assumed factor loading against listed peers excluding each peer from its own benchmark.
peer_risk = {}
for ticker in AI:
    others = r[[t for t in AI if t != ticker]].mean(axis=1)
    peer_risk[ticker] = dict(vol=r[ticker].std()*np.sqrt(252), beta_leave_one_out=r[ticker].cov(others)/others.var())

# Check the 11/15 classification arithmetic using the frozen valuation ratios and independent price history.
table = pd.read_csv(TIMING, index_col='t')
rank_inputs = table.loc[[t for t in AI if t != 'MU'], ['pe_ntm','ebit_op_yield','peg_fy3_vs_fy2']].copy()
rank_inputs['ebit_op_yield'] *= -1
mean_rank = rank_inputs.rank().mean(axis=1)
timing_check = {}
for ticker in AI:
    series = prices[ticker]
    drawdown = series.iloc[-1]/series.tail(252).max()-1
    vs_ma = series.iloc[-1]/series.tail(200).mean()-1
    low = drawdown <= -.20 and vs_ma < 0
    high = drawdown >= -.10 and vs_ma > 0
    price_band = 'relative-low' if low else ('relative-high' if high else 'middle')
    value_band = 'cyclical-peak' if ticker == 'MU' else (
        'cheap' if mean_rank[ticker] <= 3 else ('mid' if mean_rank[ticker] <= 5 else 'expensive'))
    assert table.loc[ticker, 'price_bucket'] == price_band
    assert table.loc[ticker, 'value_bucket'] == value_band
    timing_check[ticker] = dict(drawdown=drawdown, vs_ma200=vs_ma, price_band=price_band, value_band=value_band)
# Independent 63-session forward Spearman IC for each month-end. Test all three start months.
monthly_closes = prices.index.to_series().groupby(prices.index.to_period('M')).last()
ic = {}
for date in monthly_closes.loc['2022-11':'2026-09']:
    pos = prices.index.get_loc(date)
    if pos + 63 >= len(prices):
        continue
    trailing = prices[AI].iloc[pos-251:pos+1]
    dip = 1 - trailing.iloc[-1]/trailing.max()
    future = prices[AI].iloc[pos+63]/trailing.iloc[-1] - 1
    ic[date] = dip.rank().corr(future.rank())
phases = []
for i in range(3):
    part = pd.Series(ic).iloc[i::3]
    gaps = np.diff(prices.index.get_indexer(part.index))
    phases.append(dict(first_date=part.index[0].date().isoformat(), n=len(part), mean=part.mean(),
                       descriptive_t=part.mean()/part.std()*np.sqrt(len(part)),
                       overlapping_adjacent_windows=int((gaps<63).sum()),
                       max_overlap_days=int(max(0, 63-gaps.min()))))

result = dict(
    ic_window=[min(ic).date().isoformat(), max(ic).date().isoformat()], ic_3m_phases=phases,
    peer_risk=peer_risk, timing_check_1113=timing_check,
    entry=base, neutral=baseline(neutral), export_gate_baseline=baseline(cut),
    per_issuer_after_export_gate=cut.to_dict(), erc7=erc7.to_dict(), ai8_factor_vol=factor_variance**.5,
    vol_quarterly_old=old_vol, vol_quarterly_neutral=quarterly_vol(neutral,*window),
    exact_hybrid_ai_budget=a_core, exact_hybrid_weights=exact_hybrid(a_core).to_dict(),
    weight_for_pre_ipo_googl_rc=old_googl_parity, weight_for_same_portfolio_googl_rc=concurrent_parity,
    vti_seven_asof=weights_at_cutoff.to_dict(),
    indirect_extra_if_amzn_converts_no_cap=(exposure(initial)['AMZN'] * comparison_px *
            sources['ant_holders']['numeric_inputs']['amzn_uncapped_additional_shares'] / caps['AMZN']),
    inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PRICE,PLAN,SOURCES,IPO,QUOTE,TIMING]})
(OUT/'portfolio.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
