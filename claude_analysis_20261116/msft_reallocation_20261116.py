#!/usr/bin/env python3
"""MSFT reallocation check at the 2026-11-16 close: move the MSFT slice of the one-shot purchase to NVDA and/or GOOGL?

Inputs (read-only):
  gpt_review_20261113/data_audit/adjusted_close.csv         closes through 2026-11-13 (SHA-256 checked vs GPT manifest)
  claude_analysis_20261116/data/fmp_raw/*.json              FMP responses pasted verbatim: 2026-11-16 closes, quarterly and annual
                                                            statements, latest balance sheets (fetched 2026-11-17 UTC)
  claude_analysis_20261116/data/sources_web_20261116.json   web facts; only GOOGL's Q3 2025 operating income ex EC fine enters the math
  claude_analysis_20261115/data/fmp_raw/*.json              consensus EPS and TTM metrics fetched 2026-11-16 UTC (inputs of the 11/15 plan)
  claude_analysis_20261115/out/timing_table_ai8.csv         11/13 valuation table (TSM, AVGO, MU, META, AMZN rows)
  claude_analysis_20261115/out/summary.json                 Monday one-shot weights and long-term weights
  claude_analysis_20261114/out/summary.json                 VTI look-through weights
Outputs: claude_analysis_20261116/out/
Run: python3 -I claude_analysis_20261116/msft_reallocation_20261116.py <repo_root>
Descriptive only. Earnings and FCF yields are valuation levels, not return forecasts.
"""
import sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
GPT, H14, H15 = ROOT / 'gpt_review_20261113', ROOT / 'claude_analysis_20261114', ROOT / 'claude_analysis_20261115'
HERE = ROOT / 'claude_analysis_20261116'
RAW, OUT = HERE / 'data' / 'fmp_raw', HERE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
B = 1e9
TAX = 0.21                    # statutory rate applied to non-operating items when cleaning EPS
D13, D16 = pd.Timestamp('2026-11-13'), pd.Timestamp('2026-11-16')
THREE = ['NVDA', 'MSFT', 'GOOGL']
S = {}

# ------------------------------------------------------------------ 0. prices
man = json.loads((GPT / 'MANIFEST_SHA256.json').read_text())
assert man['data_audit/adjusted_close.csv'] == sha(GPT / 'data_audit' / 'adjusted_close.csv')
P = pd.read_csv(GPT / 'data_audit' / 'adjusted_close.csv', index_col=0, parse_dates=True)
assert P.index[-1] == D13
Q = json.loads((RAW / 'quotes_close_20261116.json').read_text())
QUOTED = ['NVDA', 'MSFT', 'GOOGL', 'TSM', 'META', 'AMZN']          # AVGO and MU quotes were denied by the FMP plan
close16 = {t: float(Q[t][0]['price']) for t in QUOTED}
mcap16 = {t: float(Q[t][0]['marketCap']) for t in QUOTED}
for t in QUOTED:              # FMP previousClose must equal the 11/13 close used by every earlier run
    assert abs(Q[t][0]['previousClose'] - P.loc[D13, t]) < 0.011, t
P16 = pd.concat([P, pd.DataFrame([close16], index=[D16])])


def position(t):
    s = P16[t].dropna()
    last, w = s.iloc[-1], s.iloc[-252:]
    return dict(asof=str(s.index[-1].date()), close=float(last), hi52=float(w.max()), hi52_date=str(w.idxmax().date()),
                lo52=float(w.min()), dd_from_hi52=float(last / w.max() - 1), up_from_lo52=float(last / w.min() - 1),
                vs_sma200=float(last / s.iloc[-200:].mean() - 1), ret_1d=float(last / s.iloc[-2] - 1),
                ret_since_2026_06_30=float(last / s.loc[:'2026-06-30'].iloc[-1] - 1))


POS = pd.DataFrame({t: position(t) for t in ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']}).T

# ------------------------------------------------------------------ 1. accounting, last four reported quarters
F = {t: json.loads((RAW / f'{t}_20261116.json').read_text()) for t in THREE}
E15 = json.loads((H15 / 'data' / 'fmp_raw' / 'estimates_MSFT_AMZN_META_TSM.json').read_text())
EST = {'MSFT': E15['MSFT'], 'AMZN': E15['AMZN'], 'META': E15['META'],
       'GOOGL': json.loads((H15 / 'data' / 'fmp_raw' / 'estimates_GOOGL.json').read_text())['GOOGL'],
       'NVDA': json.loads((H15 / 'data' / 'fmp_raw' / 'NVDA.json').read_text())['estimates_annual']}
FY1 = {'NVDA': ('2026-01-26', '2027-01-25'), 'MSFT': ('2026-07-01', '2027-06-30'), 'GOOGL': ('2026-01-01', '2026-12-31'),
       'META': ('2026-01-01', '2026-12-31'), 'AMZN': ('2026-01-01', '2026-12-31')}
WEB = json.loads((HERE / 'data' / 'sources_web_20261116.json').read_text())['used_in_script']
GOOGL_Q3_25_OI_EX_FINE = WEB['GOOGL_Q3_2025_operating_income_ex_EC_fine_USD_B'] * B


def eps(t, end, k='epsAvg'):
    r = [x for x in EST[t] if x['date'] == end]
    assert len(r) == 1, (t, end)
    return r[0][k]


def next_end(t, end):
    ends = sorted(x['date'] for x in EST[t])
    return ends[ends.index(end) + 1]


def ntm(t, eps1):
    start, e1 = FY1[t]
    e2 = next_end(t, e1)
    w = (pd.Timestamp(e1) - D16).days / 365.0
    return w * eps1 + (1 - w) * eps(t, e2), w, e2


def accounting(t):
    iq, cq, bs = F[t]['income_quarter'], F[t]['cashflow_quarter'], F[t]['balance_sheet_quarter'][0]
    assert [x['date'] for x in iq] == [x['date'] for x in cq] and len(iq) == 5
    q4, c4, now, yago = iq[:4], cq[:4], iq[0], iq[4]          # newest first; iq[4] is the same quarter a year earlier
    s = lambda rows, k: float(sum(r[k] for r in rows))
    rev, oi, da = s(q4, 'revenue'), s(q4, 'operatingIncome'), s(q4, 'depreciationAndAmortization')
    pretax, ni = s(q4, 'incomeBeforeTax'), s(q4, 'netIncome')
    ocf, capex, fcf = s(c4, 'operatingCashFlow'), -s(c4, 'capitalExpenditure'), s(c4, 'freeCashFlow')
    mc = mcap16[t]
    ev_fmp = mc + bs['totalDebt'] - bs['cashAndCashEquivalents']          # FMP convention (cash only); same basis as FMP's FY history
    ev_op = mc + bs['totalDebt'] + bs['preferredStock'] - bs['cashAndShortTermInvestments'] - bs['longTermInvestments']
    yago_oi = GOOGL_Q3_25_OI_EX_FINE if t == 'GOOGL' else yago['operatingIncome']
    # consensus NTM P/E and a clean version: strip after-tax non-operating items of the FY1 quarters already reported
    start, e1 = FY1[t]
    fy1_q = [r for r in iq if pd.Timestamp(start) <= pd.Timestamp(r['date']) <= D16]
    adj = sum((r['incomeBeforeTax'] - r['operatingIncome']) * (1 - TAX) / r['weightedAverageShsOutDil'] for r in fy1_q)
    eps1 = eps(t, e1)
    n_cons, w, e2 = ntm(t, eps1)
    n_clean, _, _ = ntm(t, eps1 - adj)
    e3 = next_end(t, e2)
    return dict(
        latest_quarter=now['date'], balance_sheet_date=bs['date'], close_2026_11_16=close16[t], mcap_B=mc / B,
        rev_ttm_B=rev / B, oi_ttm_B=oi / B, op_margin_ttm=oi / rev, nonop_ttm_B=(pretax - oi) / B, nonop_share_of_pretax_ttm=(pretax - oi) / pretax,
        ni_ttm_B=ni / B, ocf_ttm_B=ocf / B, capex_ttm_B=capex / B, fcf_ttm_B=fcf / B, ocf_to_ni_ttm=ocf / ni, capex_to_rev_ttm=capex / rev,
        fcf_last_q_B=cq[0]['freeCashFlow'] / B, fcf_prev_q_B=cq[1]['freeCashFlow'] / B,
        financing_cf_ttm_B=s(c4, 'netCashProvidedByFinancingActivities') / B, buybacks_ttm_B=-s(c4, 'commonStockRepurchased') / B,
        dividends_ttm_B=-s(c4, 'netDividendsPaid') / B, net_debt_issuance_ttm_B=s(c4, 'netDebtIssuance') / B,
        diluted_shares_yoy=now['weightedAverageShsOutDil'] / yago['weightedAverageShsOutDil'] - 1,
        rev_yoy_latest_q=now['revenue'] / yago['revenue'] - 1, oi_yoy_latest_q=now['operatingIncome'] / yago_oi - 1,
        op_margin_latest_q=now['operatingIncome'] / now['revenue'], op_margin_year_ago_q=yago_oi / yago['revenue'],
        cash_and_sti_B=bs['cashAndShortTermInvestments'] / B, total_debt_B=bs['totalDebt'] / B, preferred_B=bs['preferredStock'] / B,
        lt_investments_B=bs['longTermInvestments'] / B, ev_fmp_B=ev_fmp / B, ev_oper_B=ev_op / B,
        ev_ebit_fmp=ev_fmp / oi, ev_ebit_oper=ev_op / oi, ev_opebitda_fmp=ev_fmp / (oi + da), ebit_yield_oper=oi / ev_op,
        fcf_yield=fcf / mc, eps_fy1=eps1, fy1_end=e1, fy1_quarters_reported=len(fy1_q), fy1_nonop_after_tax_per_share=adj,
        eps_fy1_clean=eps1 - adj, eps_fy2=eps(t, e2), fy2_end=e2, eps_fy3=eps(t, e3), ntm_weight_fy1=w,
        eps_ntm_consensus=n_cons, eps_ntm_clean=n_clean, pe_ntm_consensus=close16[t] / n_cons, pe_ntm_clean=close16[t] / n_clean,
        eps_fy2_dispersion=(eps(t, e2, 'epsHigh') - eps(t, e2, 'epsLow')) / eps(t, e2), g_fy3_vs_fy2=eps(t, e3) / eps(t, e2) - 1)


A3 = pd.DataFrame({t: accounting(t) for t in THREE}).T
A3 = A3.join(POS[['dd_from_hi52', 'up_from_lo52', 'vs_sma200', 'ret_since_2026_06_30', 'ret_1d']])
A3.to_csv(OUT / 'accounting_ttm_3names.csv', index_label='t')
# the 11/15 TTM file for GOOGL used FMP's EBITDA, which includes non-operating gains; keep the contrast on record
km15 = json.loads((H15 / 'data' / 'fmp_raw' / 'GOOGL_MSFT.json').read_text())
S['fmp_ev_ebitda_ttm_11_13_includes_nonop'] = {t: km15[t]['key_metrics_ttm'][0]['evToEBITDATTM'] for t in ['GOOGL', 'MSFT']}

# ------------------------------------------------------------------ 2. own history, FMP EV convention (FY-end EV / FY operating income)
hist = []
for t in ['MSFT', 'GOOGL']:
    km = {r['fiscalYear']: r for r in F[t]['key_metrics_annual']}
    inc = {r['fiscalYear']: r for r in F[t]['income_annual']}
    for fy in sorted(km):
        k, i = km[fy], inc[fy]
        hist.append(dict(t=t, period=f'FY{fy[2:]}', date=k['date'], ev_B=k['enterpriseValue'] / B,
                         ev_ebit=k['enterpriseValue'] / i['operatingIncome'],
                         ev_opebitda=k['enterpriseValue'] / (i['operatingIncome'] + i['depreciationAndAmortization']),
                         fcf_yield=k['freeCashFlowYield'], capex_to_rev=k['capexToRevenue'], ocf_to_ni=k['incomeQuality'],
                         op_margin=i['operatingIncome'] / i['revenue']))
    a = A3.loc[t]
    hist.append(dict(t=t, period='TTM 11/16', date='2026-11-16', ev_B=a.ev_fmp_B, ev_ebit=a.ev_ebit_fmp, ev_opebitda=a.ev_opebitda_fmp,
                     fcf_yield=a.fcf_yield, capex_to_rev=a.capex_to_rev_ttm, ocf_to_ni=a.ocf_to_ni_ttm, op_margin=a.op_margin_ttm))
H = pd.DataFrame(hist)
H.to_csv(OUT / 'own_history_ev_ebit.csv', index=False)
OWN = {}
for t in ['MSFT', 'GOOGL']:
    h = H[(H.t == t) & (H.period != 'TTM 11/16')]
    now = H[(H.t == t) & (H.period == 'TTM 11/16')].iloc[0]
    OWN[t] = dict(ev_ebit_ttm=now.ev_ebit, ev_ebit_fy_min=h.ev_ebit.min(), ev_ebit_fy_median=h.ev_ebit.median(), ev_ebit_fy_max=h.ev_ebit.max(),
                  fy_years_above_ttm=int((h.ev_ebit > now.ev_ebit).sum()), fy_years=len(h),
                  fcf_yield_ttm=now.fcf_yield, fcf_yield_fy_min=h.fcf_yield.min(), fcf_yield_fy_max=h.fcf_yield.max(),
                  capex_to_rev_ttm=now.capex_to_rev, capex_to_rev_fy_max=h.capex_to_rev.max(),
                  ocf_to_ni_ttm=now.ocf_to_ni, ocf_to_ni_fy_min=h.ocf_to_ni.min())
S['own_history'] = OWN

# ------------------------------------------------------------------ 3. the 11/15 classification rerun at 11/16 prices
T15 = pd.read_csv(H15 / 'out' / 'timing_table_ai8.csv').set_index('t')
X = T15[['price', 'pe_ntm', 'ebit_op_yield', 'g_fy3_vs_fy2', 'cyclical_peak_flag']].copy()
X['price_2026_11_16'] = [close16.get(t, np.nan) for t in X.index]
X['price_basis'] = ['2026-11-16 close' if t in close16 else '2026-11-13 close (FMP quote denied)' for t in X.index]
for t in X.index:
    if t in THREE:                               # recomputed exactly from consensus EPS and 11/16 EV (FMP convention, as on 11/15)
        X.loc[t, 'pe_ntm'] = A3.loc[t, 'pe_ntm_consensus']
        X.loc[t, 'ebit_op_yield'] = A3.loc[t, 'oi_ttm_B'] / A3.loc[t, 'ev_fmp_B']
    elif t in ('META', 'AMZN'):                  # consensus EPS re-blended at 11/16; EV moved with the price (EV/mcap ~1)
        X.loc[t, 'pe_ntm'] = close16[t] / ntm(t, eps(t, FY1[t][1]))[0]
        X.loc[t, 'ebit_op_yield'] = T15.loc[t, 'ebit_op_yield'] * T15.loc[t, 'price'] / close16[t]
    elif t == 'TSM':                             # TWD estimates and ADR premium as on 11/15; scaled by the ADR price move
        X.loc[t, 'pe_ntm'] = T15.loc[t, 'pe_ntm'] * close16[t] / T15.loc[t, 'price']
        X.loc[t, 'ebit_op_yield'] = T15.loc[t, 'ebit_op_yield'] * T15.loc[t, 'price'] / close16[t]
X['peg_fy3_vs_fy2'] = np.where(X.g_fy3_vs_fy2 > 0, X.pe_ntm / (100 * X.g_fy3_vs_fy2), np.nan)
X = X.join(POS[['dd_from_hi52', 'vs_sma200', 'asof']])
ranked = X[~X.cyclical_peak_flag]
RK = pd.DataFrame({'rank_pe_ntm': ranked.pe_ntm.rank(), 'rank_ebit_op_yield': (-ranked.ebit_op_yield).rank(),
                   'rank_peg': ranked.peg_fy3_vs_fy2.rank()})
X = X.join(RK)
X['value_score_rank'] = RK.mean(axis=1)
X['value_bucket'] = pd.cut(X.value_score_rank, [0, 3.0, 5.0, 8], labels=['cheap', 'mid', 'expensive']).astype(object)
X.loc['MU', 'value_bucket'] = 'cyclical-peak'
X['price_bucket'] = np.where((X.dd_from_hi52 <= -0.20) & (X.vs_sma200 < 0), 'relative-low',
                             np.where((X.dd_from_hi52 >= -0.10) & (X.vs_sma200 > 0), 'relative-high', 'middle'))


def action(r):                                   # identical to claude_analysis_20261115/timing_20261115.py
    if r.value_bucket == 'cyclical-peak':
        return 'underweight (cycle-adjusted)'
    if r.value_bucket == 'cheap' and r.price_bucket == 'relative-low':
        return 'overweight'
    if r.value_bucket == 'expensive' and r.price_bucket == 'relative-high':
        return 'underweight'
    if r.value_bucket == 'expensive':
        return 'at target (expensive, no add)'
    return 'at target'


X['action_2026_11_16'] = X.apply(action, axis=1)
X['action_2026_11_15'] = T15['action']
X.to_csv(OUT / 'cross_section_20261116.csv', index_label='t')

# ------------------------------------------------------------------ 4. reallocation options: risk (issuer level, VTI look-through) and valuation
plan = json.loads((H15 / 'out' / 'summary.json').read_text())['plan']
monday, long_term = plan['monday'], plan['long_term']
L = json.loads((H14 / 'out' / 'summary.json').read_text())['vti_lookthrough']
om_now = pd.Series(L['drifted_2026_11_13'])
k7 = list(om_now.index)
w0930 = pd.Series(L['weights_2026_09_30'])
R = P.pct_change().iloc[1:]
rel = (P[k7] / P.loc['2026-09-30', k7]).div(P['VTI'] / P.loc['2026-09-30', 'VTI'], axis=0)
OM = rel.mul(w0930, axis=1).shift(1).loc[R.index]
RI = R.copy()
RI['VTI_rest'] = (R['VTI'] - (OM * R[k7]).sum(axis=1)) / (1 - OM.sum(axis=1))
SIG = RI.loc['2023-11-14':'2026-11-13'].drop(columns=['VTI']).cov() * 252       # same window and construction as 11/15
AI8 = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']


def exposure(w):
    e = {}
    for k, v in w.items():
        if k == 'VTI':
            for kk, o in om_now.items():
                e[kk] = e.get(kk, 0) + v * o
            e['VTI_rest'] = e.get('VTI_rest', 0) + v * (1 - om_now.sum())
        else:
            e[k] = e.get(k, 0) + v
    return pd.Series(e).reindex(SIG.index, fill_value=0.0)


E_LT = exposure(long_term)
EP = {t: 1 / A3.loc[t, 'pe_ntm_clean'] for t in THREE}         # clean NTM earnings yield
FY = {t: A3.loc[t, 'fcf_yield'] for t in THREE}


def evaluate(w):
    e = exposure(w)
    cv = SIG @ e
    var = float(e @ cv)
    rc = e * cv / var
    d = e - E_LT
    single = e.drop('VTI_rest')
    dw = {t: w.get(t, 0) - monday.get(t, 0) for t in THREE}
    return dict(NVDA_w=w['NVDA'], MSFT_w=w['MSFT'], GOOGL_w=w['GOOGL'], vol=np.sqrt(var),
                nvda_lt=float(e['NVDA']), rc_nvda=float(rc['NVDA']), googl_lt=float(e['GOOGL']), rc_googl=float(rc['GOOGL']),
                msft_lt=float(e['MSFT']), rc_msft=float(rc['MSFT']), ai8_lt=float(e[AI8].sum()), rc_ai8=float(rc[AI8].sum()),
                largest_issuer=single.idxmax(), largest_issuer_lt=float(single.max()),
                te_vs_long_term=float(np.sqrt(d @ SIG @ d)),
                loss_if_nvda_minus30_usd=-0.30 * float(e['NVDA']) * 7000, loss_if_googl_minus30_usd=-0.30 * float(e['GOOGL']) * 7000,
                nvda_report_day_move_usd=0.106 * float(e['NVDA']) * 7000,
                d_fwd_ep_bp=1e4 * sum(dw[t] * EP[t] for t in THREE), d_fcf_yield_bp=1e4 * sum(dw[t] * FY[t] for t in THREE))


def shift(**kw):
    w = dict(monday)
    for k, v in kw.items():
        w[k] = round(w[k] + v, 6)
    assert abs(sum(w.values()) - 1) < 1e-9 and min(w.values()) >= 0
    return w


OPTS = {
    'A  current Monday plan (MSFT 7)': dict(monday),
    'B  MSFT 7->0, +3.5 NVDA, +3.5 GOOGL': shift(MSFT=-0.07, NVDA=+0.035, GOOGL=+0.035),
    'C  MSFT 7->0, +7 GOOGL': shift(MSFT=-0.07, GOOGL=+0.07),
    'D  MSFT 7->0, +7 NVDA': shift(MSFT=-0.07, NVDA=+0.07),
    'E  MSFT 7->3.5, +3.5 GOOGL': shift(MSFT=-0.035, GOOGL=+0.035),
    'F  MSFT 7->5, +2 GOOGL': shift(MSFT=-0.02, GOOGL=+0.02),
}
OPT = pd.DataFrame({k: evaluate(w) for k, w in OPTS.items()}).T
OPT.loc['long-term proportions (reference)'] = pd.Series(evaluate(long_term))
OPT.to_csv(OUT / 'reallocation_options.csv', index_label='option')
a = OPT.iloc[0]
assert abs(a.vol - 0.1762) < 6e-5 and abs(a.rc_nvda - 0.3031) < 6e-5     # reproduces the 11/15 Monday-plan risk numbers
S['options'] = {k: {kk: (vv if isinstance(vv, str) else float(vv)) for kk, vv in r.items()} for k, r in OPT.iterrows()}
S['option_weights'] = {k: {t: w[t] for t in ['NVDA', 'MSFT', 'GOOGL']} for k, w in OPTS.items()}

# ------------------------------------------------------------------ 5. summary
S['asof'] = dict(prices='2026-11-16 close (AVGO, MU: 2026-11-13; FMP quote denied)', statements='latest 10-Q per company (NVDA: quarter ended 2026-07-26)',
                 consensus='FMP estimates fetched 2026-11-16 UTC', nvda_next_report='2026-11-17 after the close')
S['accounting'] = {t: {k: (v if isinstance(v, str) else float(v)) for k, v in r.items()} for t, r in A3.iterrows()}
S['cross_section'] = {t: dict(pe_ntm=float(r.pe_ntm), ebit_op_yield=float(r.ebit_op_yield), peg=float(r.peg_fy3_vs_fy2) if pd.notna(r.peg_fy3_vs_fy2) else None,
                              value_score_rank=float(r.value_score_rank) if pd.notna(r.value_score_rank) else None, value_bucket=r.value_bucket,
                              price_bucket=r.price_bucket, action_2026_11_16=r.action_2026_11_16, action_2026_11_15=r.action_2026_11_15,
                              price_basis=r.price_basis) for t, r in X.iterrows()}
S['inputs_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in sorted(RAW.glob('*.json')) + [
    HERE / 'data' / 'sources_web_20261116.json', GPT / 'data_audit' / 'adjusted_close.csv', H15 / 'data' / 'fmp_raw' / 'estimates_GOOGL.json',
    H15 / 'data' / 'fmp_raw' / 'estimates_MSFT_AMZN_META_TSM.json', H15 / 'data' / 'fmp_raw' / 'NVDA.json', H15 / 'data' / 'fmp_raw' / 'GOOGL_MSFT.json',
    H15 / 'out' / 'timing_table_ai8.csv', H15 / 'out' / 'summary.json', H14 / 'out' / 'summary.json']}
(OUT / 'summary.json').write_text(json.dumps(S, indent=2, ensure_ascii=False, default=float) + '\n')

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 60)
print(A3.T.to_string())
print(H.round(3).to_string())
print(X[['price', 'price_2026_11_16', 'pe_ntm', 'ebit_op_yield', 'peg_fy3_vs_fy2', 'dd_from_hi52', 'vs_sma200', 'value_score_rank', 'value_bucket',
         'price_bucket', 'action_2026_11_16', 'action_2026_11_15']].round(3).to_string())
print(OPT.drop(columns=['largest_issuer']).round(4).to_string())
print(OPT[['largest_issuer', 'largest_issuer_lt']].to_string())
