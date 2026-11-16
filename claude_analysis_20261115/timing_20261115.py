#!/usr/bin/env python3
"""Entry timing for the Hybrid-Core plan: relative price position x accounting valuation x events.

Inputs (read-only):
  gpt_review_20261113/data_audit/adjusted_close.csv  prices through the 2026-11-13 close (SHA-256 checked vs GPT manifest)
  claude_analysis_20261115/data/fmp_raw/*.json       FMP fundamentals and consensus estimates pasted verbatim (fetched 2026-11-16 UTC)
  claude_analysis_20261113/out_valuation.csv         11/13 snapshot (stockanalysis pages) -- only for AVGO and MU, where FMP access was denied
  claude_analysis_20261114/out/summary.json          Hybrid-Core weights and VTI look-through weights
Outputs: claude_analysis_20261115/out/
Run: python3 -I claude_analysis_20261115/timing_20261115.py <repo_root>
No forward-return estimate is produced; the historical check in section 5 is descriptive and low-power.
"""
import sys, json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import spearmanr

ROOT = Path(sys.argv[1]).resolve()
GPT, OLD, H14 = ROOT / 'gpt_review_20261113', ROOT / 'claude_analysis_20261113', ROOT / 'claude_analysis_20261114'
HERE = ROOT / 'claude_analysis_20261115'
RAW, OUT = HERE / 'data' / 'fmp_raw', HERE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
S = {}

# ------------------------------------------------------------------ prices
man = json.loads((GPT / 'MANIFEST_SHA256.json').read_text())
assert man['data_audit/adjusted_close.csv'] == sha(GPT / 'data_audit' / 'adjusted_close.csv')
P = pd.read_csv(GPT / 'data_audit' / 'adjusted_close.csv', index_col=0, parse_dates=True)
AS_OF = pd.Timestamp('2026-11-13')
assert P.index[-1] == AS_OF
AI8 = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
HOLD = AI8 + ['VTI', 'BRK-B', 'XLV', 'SGOV']


def position(t, end=AS_OF):
    s = P[t].loc[:end]
    last, w = s.iloc[-1], s.iloc[-252:]
    return dict(t=t, close=last, hi52=w.max(), hi52_date=str(w.idxmax().date()), lo52=w.min(), lo52_date=str(w.idxmin().date()),
                dd_from_hi52=last / w.max() - 1, range_pos52=(last - w.min()) / (w.max() - w.min()),
                vs_sma200=last / s.iloc[-200:].mean() - 1, ret_1m=last / s.iloc[-22] - 1, ret_3m=last / s.iloc[-64] - 1,
                mom_12_1=s.iloc[-22] / s.iloc[-253] - 1, ytd=last / s.loc[:'2025-12-31'].iloc[-1] - 1,
                vol_63d=s.pct_change().iloc[-63:].std() * np.sqrt(252))


POS = pd.DataFrame([position(t) for t in HOLD]).set_index('t')
POS.to_csv(OUT / 'price_position.csv')

# ------------------------------------------------------------------ fundamentals
def load(name):
    return json.loads((RAW / name).read_text())


nv, ts, gm, am = load('NVDA.json'), load('TSM.json'), load('GOOGL_MSFT.json'), load('AMZN_META.json')
est = {**load('estimates_MSFT_AMZN_META_TSM.json'), 'GOOGL': load('estimates_GOOGL.json')['GOOGL'], 'NVDA': nv['estimates_annual']}
KM = {'NVDA': nv['key_metrics_ttm'][0], 'TSM': ts['key_metrics_ttm'][0], 'GOOGL': gm['GOOGL']['key_metrics_ttm'][0],
      'MSFT': gm['MSFT']['key_metrics_ttm'][0], 'AMZN': am['AMZN']['key_metrics_ttm'][0], 'META': am['META']['key_metrics_ttm'][0]}
RT = {'NVDA': nv['ratios_ttm'][0], 'TSM': ts['ratios_ttm'][0], 'GOOGL': gm['GOOGL']['ratios_ttm'][0],
      'MSFT': gm['MSFT']['ratios_ttm'][0], 'AMZN': am['AMZN']['ratios_ttm'][0], 'META': am['META']['ratios_ttm'][0]}
FY1_END = {'NVDA': '2027-01-25', 'MSFT': '2027-06-30', 'GOOGL': '2026-12-31', 'AMZN': '2026-12-31', 'META': '2026-12-31',
           'TSM': '2026-12-31'}
val = pd.read_csv(OLD / 'out_valuation.csv').set_index('t')


def eps_row(t, end):
    r = [x for x in est[t] if x['date'] == end]
    assert len(r) == 1, (t, end)
    return r[0]


def next_end(t, end):
    ends = sorted(x['date'] for x in est[t])
    return ends[ends.index(end) + 1]


def solve_g(m, r, gT=0.03):
    """Two-stage reverse DCF with corrected first-year timing: cash_t = (1+g)^(t-1) for a forward multiple."""
    f = lambda g: sum((1 + g) ** (t - 1) / (1 + r) ** t for t in range(1, 11)) + (1 + g) ** 9 * (1 + gT) / ((r - gT) * (1 + r) ** 10) - m
    try:
        return brentq(f, -0.5, 1.5)
    except ValueError:
        return float('nan')


rows = []
for t in AI8:
    px = float(P.loc[AS_OF, t])
    rec = dict(t=t, price=px, r_capm=float(val.loc[t, 'r_capm']))
    if t in KM:
        km, rt = KM[t], RT[t]
        e1 = FY1_END[t]
        e2 = next_end(t, e1)
        e3 = next_end(t, e2)
        w = (pd.Timestamp(e1) - AS_OF).days / 365.0
        if t == 'TSM':   # TWD estimates: forward P/E from net income vs TWD market cap, then ADR premium from the 11/13 snapshot
            ni1, ni2, ni3 = (eps_row(t, e)['netIncomeAvg'] for e in (e1, e2, e3))
            pe_local = km['marketCap'] / (w * ni1 + (1 - w) * ni2)
            adr_prem = float(val.loc['TSM', 'ttmPE']) / rt['priceToEarningsRatioTTM']
            rec.update(pe_ntm=pe_local * adr_prem, adr_premium_vs_local=adr_prem - 1, g_fy3_vs_fy2=ni3 / ni2 - 1,
                       eps_dispersion_fy2=(eps_row(t, e2)['epsHigh'] - eps_row(t, e2)['epsLow']) / eps_row(t, e2)['epsAvg'])
            rec['ebit_op_yield'] = float(val.loc['TSM', 'op_margin']) * 155.16 / (float(val.loc['TSM', 'mcapB']) - float(val.loc['TSM', 'net_cash_B']))
            rec['fcf_yield'] = float(val.loc['TSM', 'fcf_yield'])
        else:
            eps1, eps2, eps3 = (eps_row(t, e)['epsAvg'] for e in (e1, e2, e3))
            ntm = w * eps1 + (1 - w) * eps2
            rec.update(eps_fy1=eps1, eps_fy2=eps2, eps_fy3=eps3, eps_ntm=ntm, pe_ntm=px / ntm, g_fy3_vs_fy2=eps3 / eps2 - 1,
                       eps_dispersion_fy2=(eps_row(t, e2)['epsHigh'] - eps_row(t, e2)['epsLow']) / eps2)
            rec['ebit_op_yield'] = rt['operatingProfitMarginTTM'] / km['evToSalesTTM']
            rec['fcf_yield'] = km['freeCashFlowYieldTTM']
        rec.update(fy1_end=e1, fy2_end=e2, fy3_end=e3, ntm_weight_fy1=w, pe_ttm_gaap=rt['priceToEarningsRatioTTM'],
                   ev_ebitda_ttm=km['evToEBITDATTM'], ocf_to_ni=km['incomeQualityTTM'],
                   nonop_share_of_pretax=1 - 1 / rt['ebtPerEbitTTM'], effective_tax=rt['effectiveTaxRateTTM'],
                   capex_to_rev=km['capexToRevenueTTM'], sbc_to_rev=km['stockBasedCompensationToRevenueTTM'],
                   dso=km['daysOfSalesOutstandingTTM'], dio=km['daysOfInventoryOutstandingTTM'],
                   gross_margin=rt['grossProfitMarginTTM'], op_margin=rt['operatingProfitMarginTTM'], source='FMP (fetched 2026-11-16 UTC)')
    else:   # AVGO, MU: FMP plan denied; 11/13 snapshot (stockanalysis pages, rescaled to the 11/13 close)
        v = val.loc[t]
        ev = float(v.mcapB) - float(v.net_cash_B)
        rev = {'AVGO': 89.10, 'MU': 133.19}[t]   # TTM revenue from claude_analysis_20261113/analysis.py VAL
        rec.update(pe_ntm=float(v.fwdPE), pe_ttm_gaap=float(v.ttmPE), ebit_op_yield=float(v.op_margin) * rev / ev,
                   fcf_yield=float(v.fcf_yield), ocf_to_ni=float('nan'), fcf_to_ni=float(v.fcf_to_ni), ni_to_opinc=float(v.ni_to_opinc),
                   capex_to_rev=float(v.capex_to_rev), op_margin=float(v.op_margin),
                   source='11/13 snapshot (stockanalysis pages, forward basis FY1/NTM not frozen)')
    rec['peg_fy3_vs_fy2'] = rec['pe_ntm'] / (100 * rec['g_fy3_vs_fy2']) if rec.get('g_fy3_vs_fy2', 0) > 0 else float('nan')
    rec['g_implied_10y'] = solve_g(rec['pe_ntm'], rec['r_capm'])
    rows.append(rec)
V = pd.DataFrame(rows).set_index('t')
V['cyclical_peak_flag'] = False
V.loc['MU', 'cyclical_peak_flag'] = True   # GM 86.8% vs 44.7% a year earlier (FQ4 FY26); FQ1 FY27 guided as the FY27 GM low (see data/sources_web_20261115.json)

# NVDA own history (fiscal-year-end values) vs TTM
nh = pd.DataFrame(load('NVDA_key_metrics_annual.json')['NVDA']).set_index('fiscalYear').sort_index()
ttm = KM['NVDA']
nh.loc['TTM (11/13)'] = dict(date='2026-11-13', marketCap=ttm['marketCap'], enterpriseValue=ttm['enterpriseValueTTM'],
                             evToSales=ttm['evToSalesTTM'], evToOperatingCashFlow=ttm['evToOperatingCashFlowTTM'],
                             evToFreeCashFlow=ttm['evToFreeCashFlowTTM'], evToEBITDA=ttm['evToEBITDATTM'], incomeQuality=ttm['incomeQualityTTM'],
                             earningsYield=ttm['earningsYieldTTM'], freeCashFlowYield=ttm['freeCashFlowYieldTTM'], capexToRevenue=ttm['capexToRevenueTTM'],
                             stockBasedCompensationToRevenue=ttm['stockBasedCompensationToRevenueTTM'], returnOnInvestedCapital=ttm['returnOnInvestedCapitalTTM'],
                             averageReceivables=ttm['averageReceivablesTTM'], averageInventory=ttm['averageInventoryTTM'],
                             daysOfSalesOutstanding=ttm['daysOfSalesOutstandingTTM'], daysOfInventoryOutstanding=ttm['daysOfInventoryOutstandingTTM'],
                             cashConversionCycle=ttm['cashConversionCycleTTM'])
nh.to_csv(OUT / 'nvda_own_history.csv')
S['nvda_own_history'] = {
    'ev_ebitda_ttm': ttm['evToEBITDATTM'], 'ev_ebitda_fy_min': float(nh.evToEBITDA.iloc[:-1].min()), 'ev_ebitda_fy_max': float(nh.evToEBITDA.iloc[:-1].max()),
    'fcf_yield_ttm': ttm['freeCashFlowYieldTTM'], 'fcf_yield_fy_max': float(nh.freeCashFlowYield.iloc[:-1].max()),
    'ev_sales_ttm': ttm['evToSalesTTM'], 'ev_sales_fy_min': float(nh.evToSales.iloc[:-1].min()),
    'ocf_to_ni_ttm': ttm['incomeQualityTTM'], 'ocf_to_ni_fy_min': float(nh.incomeQuality.iloc[:-1].min()),
    'dso_ttm': ttm['daysOfSalesOutstandingTTM'], 'dso_fy26': float(nh.loc['2026', 'daysOfSalesOutstanding']), 'dso_fy_max': float(nh.daysOfSalesOutstanding.iloc[:-1].max()),
    'dio_ttm': ttm['daysOfInventoryOutstandingTTM'], 'dio_fy26': float(nh.loc['2026', 'daysOfInventoryOutstanding']),
    'ccc_ttm': ttm['cashConversionCycleTTM'], 'ccc_fy26': float(nh.loc['2026', 'cashConversionCycle'])}

# ------------------------------------------------------------------ 3. classification
X = V.join(POS[['dd_from_hi52', 'range_pos52', 'vs_sma200', 'mom_12_1', 'ret_1m', 'ytd', 'hi52_date']])
ranked = X[~X.cyclical_peak_flag]
RK = pd.DataFrame({'rank_pe_ntm': ranked.pe_ntm.rank(), 'rank_ebit_op_yield': (-ranked.ebit_op_yield).rank(),
                   'rank_peg': ranked.peg_fy3_vs_fy2.rank()})     # PEG missing for AVGO (no consensus access): mean of available ranks
X = X.join(RK)
X['value_score_rank'] = RK.mean(axis=1)       # 1 = cheapest among the 7 non-cyclical names
X['value_bucket'] = pd.cut(X.value_score_rank, [0, 3.0, 5.0, 8], labels=['cheap', 'mid', 'expensive']).astype(object)
X.loc['MU', 'value_bucket'] = 'cyclical-peak'
X['price_bucket'] = np.where((X.dd_from_hi52 <= -0.20) & (X.vs_sma200 < 0), 'relative-low',
                             np.where((X.dd_from_hi52 >= -0.10) & (X.vs_sma200 > 0), 'relative-high', 'middle'))
EVENT = {'NVDA': '2026-11-17 Q3 FY27 report (options imply about +/-10.6%)', 'AVGO': 'next report in December (date per company)',
         'MU': 'next report in December (date per company)'}
X['next_event'] = [EVENT.get(t, '') for t in X.index]


def action(r):
    # valuation decides targets; price position only acts together with valuation (section 5: price alone is not reliable here)
    if r.value_bucket == 'cyclical-peak':
        return 'underweight (cycle-adjusted)'
    if r.value_bucket == 'cheap' and r.price_bucket == 'relative-low':
        return 'overweight'
    if r.value_bucket == 'expensive' and r.price_bucket == 'relative-high':
        return 'underweight + stage'
    if r.value_bucket == 'expensive':
        return 'stage'
    return 'buy at target'


X['action'] = X.apply(action, axis=1)
X.to_csv(OUT / 'timing_table_ai8.csv')

# ------------------------------------------------------------------ 4. tactical plan
base = json.loads((H14 / 'out' / 'summary.json').read_text())['weights']['Hybrid_Core']
TILT_PP = {'NVDA': +0.025, 'MU': -0.015, 'MSFT': -0.010}          # one NVDA dial notch, funded by the two flagged names
assert X.loc['NVDA', 'action'] == 'overweight' and X.loc['MU', 'action'].startswith('underweight') and X.loc['MSFT', 'action'].startswith('underweight')
tilt = {k: round(v + TILT_PP.get(k, 0.0), 6) for k, v in base.items()}
assert abs(sum(tilt.values()) - 1) < 1e-9 and abs(sum(tilt[k] for k in AI8) - sum(base[k] for k in AI8)) < 1e-12
NOW = {'NVDA': 0.075, 'AVGO': 0.025, 'MSFT': 0.035}                # bought on 2026-11-16; the rest is deferred by rule
day0 = {t: NOW.get(t, tilt[t]) for t in tilt}
day0['SGOV'] = round(tilt['SGOV'] + sum(tilt[t] - day0[t] for t in NOW), 6)
deferred = {t: round(tilt[t] - day0[t], 6) for t in NOW}
DEFER_RULE = {'NVDA': 'after the 11/17 report: add 5% if revenue >= $108B, GM >= 73.5% and the FY28 framework holds; otherwise stay at 7.5%',
              'AVGO': 'after its December report, unless that report cuts AI guidance',
              'MSFT': 'at the 12/31 quarterly rebalance, or earlier if it closes below its 200-day average'}

# ------------------------------------------------------------------ risk of each weight vector (issuer level, VTI look-through)
L = json.loads((H14 / 'out' / 'summary.json').read_text())['vti_lookthrough']
om_now = pd.Series(L['drifted_2026_11_13'])
k7 = list(om_now.index)
w0930 = pd.Series(L['weights_2026_09_30'])
R = P.pct_change().iloc[1:]
rel = (P[k7] / P.loc['2026-09-30', k7]).div(P['VTI'] / P.loc['2026-09-30', 'VTI'], axis=0)
OM = rel.mul(w0930, axis=1).shift(1).loc[R.index]
RI = R.copy()
RI['VTI_rest'] = (R['VTI'] - (OM * R[k7]).sum(axis=1)) / (1 - OM.sum(axis=1))
SIG = RI.loc['2023-11-14':'2026-11-13'].drop(columns=['VTI']).cov() * 252


def risk(w):
    e = {}
    for k, v in w.items():
        if k == 'VTI':
            for kk, o in om_now.items():
                e[kk] = e.get(kk, 0) + v * o
            e['VTI_rest'] = e.get('VTI_rest', 0) + v * (1 - om_now.sum())
        else:
            e[k] = e.get(k, 0) + v
    e = pd.Series(e).reindex(SIG.index, fill_value=0.0)
    cv = SIG @ e
    var = float(e @ cv)
    rc = e * cv / var
    return dict(vol=np.sqrt(var), nvda_lt=float(e['NVDA']), ai8_lt=float(e[AI8].sum()), rc_nvda=float(rc['NVDA']),
                rc_ai8=float(rc[AI8].sum()), scen_nvda_only_minus30=-0.3 * float(e['NVDA']),
                cash=float(w.get('SGOV', 0)))


RISK = pd.DataFrame({'Hybrid_Core (strategic)': risk(base), 'Timing target (after rules)': risk(tilt), 'Day-0 (11/16) holdings': risk(day0)}).T
RISK.to_csv(OUT / 'timing_plan_risk.csv')
S['plan'] = dict(base=base, tilt_pp=TILT_PP, tilt_target=tilt, day0=day0, deferred=deferred, defer_rule=DEFER_RULE,
                 dollars_7000={k: {t: round(7000 * v) for t, v in w.items()} for k, w in {'tilt_target': tilt, 'day0': day0}.items()})

# ------------------------------------------------------------------ 5. historical check: did "buy the dip" or momentum rank these 8 names?
me = P.index.to_series().groupby(P.index.to_period('M')).max()
me = me[(me >= pd.Timestamp('2022-11-01')) & (me <= pd.Timestamp('2026-09-30'))]
recs = []
for d in me:
    i = P.index.get_loc(d)
    if i + 63 >= len(P):
        continue
    sig = pd.DataFrame([position(t, d) for t in AI8]).set_index('t')
    f1 = P[AI8].iloc[i + 21] / P[AI8].iloc[i] - 1
    f3 = P[AI8].iloc[i + 63] / P[AI8].iloc[i] - 1
    rec = dict(date=str(d.date()))
    for name, s in [('dip', -sig.dd_from_hi52), ('below_sma200', -sig.vs_sma200), ('mom_12_1', sig.mom_12_1)]:
        rec[f'ic1m_{name}'] = spearmanr(s, f1).statistic
        rec[f'ic3m_{name}'] = spearmanr(s, f3).statistic
        top, bot = s.nlargest(2).index, s.nsmallest(2).index
        rec[f'ls1m_{name}'] = f1[top].mean() - f1[bot].mean()
    recs.append(rec)
IC = pd.DataFrame(recs)
IC.to_csv(OUT / 'timing_signal_ic_monthly.csv', index=False)
summ = {}
for name in ['dip', 'below_sma200', 'mom_12_1']:
    a, b, c = IC[f'ic1m_{name}'], IC[f'ic3m_{name}'], IC[f'ls1m_{name}']
    q = IC[f'ic3m_{name}'].iloc[::3]        # non-overlapping 3-month observations
    summ[name] = dict(months=len(a), ic1m_mean=a.mean(), ic1m_t=a.mean() / (a.std(ddof=1) / np.sqrt(len(a))),
                      ic3m_mean_nonoverlap=q.mean(), ic3m_t_nonoverlap=q.mean() / (q.std(ddof=1) / np.sqrt(len(q))), n3m=len(q),
                      ls1m_mean=c.mean(), ls1m_t=c.mean() / (c.std(ddof=1) / np.sqrt(len(c))),
                      share_months_ic1m_positive=(a > 0).mean())
S['historical_signal_check'] = dict(universe=AI8, window='month-ends 2022-11..2026-08 (forward returns to 2026-11)', signals=summ,
                                    note='rank IC = Spearman correlation across 8 names; long-short = top-2 minus bottom-2 by signal; low power')
S['inputs_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in sorted(RAW.glob('*.json')) + [GPT / 'data_audit' / 'adjusted_close.csv',
                      OLD / 'out_valuation.csv', H14 / 'out' / 'summary.json', HERE / 'data' / 'sources_web_20261115.json']}
(OUT / 'summary.json').write_text(json.dumps(S, indent=2, ensure_ascii=False, default=float) + '\n')

pd.set_option('display.width', 250)
cols = ['price', 'pe_ntm', 'pe_ttm_gaap', 'ebit_op_yield', 'fcf_yield', 'g_fy3_vs_fy2', 'peg_fy3_vs_fy2', 'g_implied_10y', 'ocf_to_ni',
        'nonop_share_of_pretax', 'capex_to_rev', 'dso', 'dio', 'eps_dispersion_fy2']
print(V[cols].round(3).to_string())
print(X[['dd_from_hi52', 'hi52_date', 'range_pos52', 'vs_sma200', 'mom_12_1', 'ret_1m', 'ytd', 'value_score_rank', 'value_bucket', 'price_bucket', 'action']].round(3).to_string())
print(POS.loc[['VTI', 'BRK-B', 'XLV', 'SGOV']].round(3).to_string())
print(nh[['evToEBITDA', 'evToSales', 'freeCashFlowYield', 'incomeQuality', 'daysOfSalesOutstanding', 'daysOfInventoryOutstanding', 'cashConversionCycle']].round(3).to_string())
print(RISK.round(4).to_string())
print(json.dumps({k: S['plan'][k] for k in ['tilt_target', 'day0', 'deferred']}, indent=0))
print(json.dumps(summ, indent=1, default=float))
