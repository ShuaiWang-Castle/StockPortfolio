#!/usr/bin/env python3
"""Macro regime check (inflation vs deflation, growth, policy, markets) as of 2026-11-23/24.
Run: python3 -I claude_analysis_20261124/macro_regime_20261124.py <repo_root>
Reads claude_analysis_20261124/data/ only; writes out/*.csv and out/summary.json.
Exits non-zero if any gate fails (data identity checks and web cross-checks)."""
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261124'
DATA, OUT = HERE / 'data', HERE / 'out'
OUT.mkdir(exist_ok=True)
INPUTS = ['fmp_economics_indicators_20261124.json', 'fmp_t10yie_inflationRate_20261124.json',
          'fmp_treasury_rates_20261124.json', 'fmp_quotes_20261124.json', 'sources_web_20261124.json']
J = {n: json.loads((DATA / n).read_text()) for n in INPUTS}
ECO = J['fmp_economics_indicators_20261124.json']['responses']
QUO = J['fmp_quotes_20261124.json']['responses']
WEB = {k: v['value'] for k, v in J['sources_web_20261124.json']['items'].items()}
GATES = {}


def gate(name, ok, detail=''):
    GATES[name] = {'pass': bool(ok), 'detail': detail}


def r(x, n=4):
    return None if x is None else round(x, n)


def pct(a, b):
    return None if a is None or b is None else 100.0 * (a / b - 1.0)


def mshift(m, k):
    t = int(m[:4]) * 12 + int(m[5:7]) - 1 + k
    return f'{t // 12:04d}-{t % 12 + 1:02d}'


def mrange(a, b):
    out = [a]
    while out[-1] != b:
        out.append(mshift(out[-1], 1))
    return out


def series(name):
    """Merge every stored response for one FMP indicator; identical overlaps only."""
    out = {}
    for key, rows in ECO.items():
        if key.split('|')[0] != name:
            continue
        for row in rows:
            assert row['name'] == name, key
            if row['date'] in out and out[row['date']] != row['value']:
                raise SystemExit(f'conflicting values for {name} {row["date"]}')
            out[row['date']] = row['value']
    return dict(sorted(out.items()))


def monthly(name):
    return {d[:7]: v for d, v in series(name).items()}


# ------------------------------------------------------------------ daily market series
def daily_rows(blob):
    rows = [row for resp in blob['responses'].values() for row in resp]
    for sub in blob.get('row_subsets', {}).values():
        rows += sub['rows']
    return rows


T10 = {}
for row in daily_rows(J['fmp_t10yie_inflationRate_20261124.json']):
    if row['date'] in T10 and T10[row['date']] != row['value']:
        raise SystemExit(f'conflicting T10YIE {row["date"]}')
    T10[row['date']] = row['value']
UST = {}
for row in daily_rows(J['fmp_treasury_rates_20261124.json']):
    if row['date'] in UST and UST[row['date']] != row:
        raise SystemExit(f'conflicting treasury row {row["date"]}')
    UST[row['date']] = row


def month_end(d, m):
    ds = [x for x in d if x[:7] == m]
    return max(ds) if ds else None


# ------------------------------------------------------------------ gate: FMP inflationRate == FRED T10YIE
fred = J['sources_web_20261124.json']['items']['fred_t10yie_crosscheck']['value']
bad = [(k, v, T10.get(k)) for k, v in fred['daily'].items() if T10.get(k) != v]
for key, v in fred['weekly'].items():
    end = datetime.strptime(key.split('|')[0], '%Y-%m-%d')
    stop = key.split('through=')[1] if 'through=' in key else key
    days = [(end - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    vals = [T10[x] for x in days if x in T10 and x <= stop]
    if abs(sum(vals) / len(vals) - v) > 0.005 + 1e-9:
        bad.append((key, v, sum(vals) / len(vals)))
for m, v in fred['monthly'].items():
    vals = [T10[x] for x in T10 if x[:7] == m]
    if abs(sum(vals) / len(vals) - v) > 0.005 + 1e-9:
        bad.append((m, v, sum(vals) / len(vals)))
gate('fred_t10yie_match', not bad,
     f"{len(fred['daily'])} daily exact, {len(fred['weekly'])} weekly and {len(fred['monthly'])} monthly averages"
     f" within 0.005; mismatches={bad}")

# ------------------------------------------------------------------ inflation
cpi = monthly('CPI')
gate('cpi_missing_only_2025_10', [m for m in mrange('2023-12', '2026-10') if m not in cpi] == ['2025-10'],
     'BLS did not collect October 2025 prices (shutdown)')
infl_rows = []
for m in mrange('2024-12', '2026-10'):
    c = cpi.get(m)
    yoy = pct(c, cpi.get(mshift(m, -12))) if c else None
    mom = pct(c, cpi.get(mshift(m, -1))) if c else None
    b3 = cpi.get(mshift(m, -3))
    ann3 = 100 * ((c / b3) ** 4 - 1) if c and b3 else None
    me = month_end(T10, m)
    infl_rows.append({'month': m, 'cpi': c, 'cpi_mom_pct': r(mom), 'cpi_yoy_pct': r(yoy), 'cpi_3m_ann_pct': r(ann3),
                      't10yie_month_end_date': me, 't10yie_month_end': T10.get(me) if me else None})
I = {x['month']: x for x in infl_rows}
cpi_6m_ann = 100 * ((cpi['2026-10'] / cpi['2026-04']) ** 2 - 1)
cpi_10m = pct(cpi['2026-10'], cpi['2025-12'])
gate('cpi_sep_yoy_matches_bls', round(I['2026-09']['cpi_yoy_pct'], 1) == WEB['cpi_oct2026']['headline_yoy_sep2026_pct']
     and round(I['2026-08']['cpi_yoy_pct'], 1) == WEB['cpi_oct2026']['headline_yoy_aug2026_pct'],
     f"computed Sep {I['2026-09']['cpi_yoy_pct']}, Aug {I['2026-08']['cpi_yoy_pct']}")
gate('cpi_oct_mom_matches_bls', round(I['2026-10']['cpi_mom_pct'], 2) == WEB['cpi_oct2026']['headline_mom_unrounded_pct'],
     f"computed {I['2026-10']['cpi_mom_pct']}")

t10_now_date = max(T10)
t10_now = T10[t10_now_date]
t10_recent = {d: v for d, v in T10.items() if d >= '2025-11-24'}
t10_hi_d = max(sorted(t10_recent), key=lambda d: (t10_recent[d], d))
t10_since_oct = {d: v for d, v in T10.items() if d >= '2026-10-01'}
t10_oct_hi_d = max(sorted(t10_since_oct), key=lambda d: (t10_since_oct[d], d))
bench = {}
for tag, lo, hi in [('2008', '2008-11-01', '2008-12-31'), ('2020', '2020-03-01', '2020-03-31')]:
    w = {d: v for d, v in T10.items() if lo <= d <= hi}
    dmin = min(sorted(w), key=lambda d: (w[d], d))
    bench[tag] = {'min': w[dmin], 'date': dmin}

# ------------------------------------------------------------------ growth
gdp = series('realGDP')
q = sorted(gdp)
gdp_rows = []
for i, d in enumerate(q):
    saar = 100 * ((gdp[d] / gdp[q[i - 1]]) ** 4 - 1) if i >= 1 else None
    yoy = pct(gdp[d], gdp[q[i - 4]]) if i >= 4 else None
    two = 100 * ((gdp[d] / gdp[q[i - 2]]) ** 2 - 1) if i >= 2 else None
    qq = f'{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}'
    months = [mshift(d[:7], k) for k in range(3)]
    cy = [I[m]['cpi_yoy_pct'] for m in months if m in I and I[m]['cpi_yoy_pct'] is not None]
    gdp_rows.append({'quarter': qq, 'real_gdp_bn_2017usd': gdp[d], 'saar_pct': r(saar), 'two_q_ann_pct': r(two),
                     'yoy_pct': r(yoy), 'cpi_yoy_quarter_avg_pct': r(sum(cy) / len(cy)) if cy else None,
                     'cpi_months_used': len(cy)})
G = {x['quarter']: x for x in gdp_rows}
gate('gdp_matches_bea', round(G['2026Q3']['saar_pct'], 1) == WEB['gdp_q3_2026_advance']['real_gdp_saar_pct']
     and round(G['2026Q2']['saar_pct'], 1) == WEB['gdp_q3_2026_advance']['real_gdp_q2_saar_pct'],
     f"computed Q3 {G['2026Q3']['saar_pct']}, Q2 {G['2026Q2']['saar_pct']}")

ip, rs = monthly('industrialProductionTotalIndex'), monthly('retailSales')
hs, mort = monthly('newPrivatelyOwnedHousingUnitsStartedTotalUnits'), series('30YearFixedRateMortgageAverage')
sent, recp = monthly('consumerSentiment'), monthly('smoothedUSRecessionProbabilities')
retail_sep_nom = pct(rs['2026-09'], rs['2025-09'])
retail_sep_real = 100 * ((1 + retail_sep_nom / 100) / (1 + I['2026-09']['cpi_yoy_pct'] / 100) - 1)
hs_2026 = {m: v for m, v in hs.items() if m >= '2026-01'}
hs_peak_m = max(sorted(hs_2026), key=lambda m: (hs_2026[m], m))
mort_recent = {d: v for d, v in mort.items() if d >= '2026-06-01'}
mort_low_d = min(sorted(mort_recent), key=lambda d: (mort_recent[d], d))
sent_12 = [sent[m] for m in mrange('2025-12', '2026-10') if m in sent]

# ------------------------------------------------------------------ labor
ur, nfp = monthly('unemploymentRate'), monthly('totalNonfarmPayroll')
gate('unrate_missing_only_2025_10', [m for m in mrange('2024-12', '2026-10') if m not in ur] == ['2025-10'],
     'October 2025 household survey not conducted (shutdown)')


def ur3(m):
    v = [ur[x] for x in (mshift(m, -2), mshift(m, -1), m) if x in ur]
    return sum(v) / len(v) if len(v) >= 2 else None


lab_rows = []
for m in mrange('2024-12', '2026-10'):
    a3 = ur3(m) if m >= '2025-02' else None
    prior = [ur3(mshift(m, -k)) for k in range(1, 13)]
    prior = [x for x in prior if x is not None and mshift(m, -12) >= '2025-02']
    sahm = a3 - min(prior) if a3 is not None and len(prior) >= 11 else None
    chg = nfp[m] - nfp[mshift(m, -1)] if mshift(m, -1) in nfp else None
    c3 = (nfp[m] - nfp[mshift(m, -3)]) / 3 if mshift(m, -3) in nfp else None
    lab_rows.append({'month': m, 'unrate': ur.get(m), 'unrate_3m_avg': r(a3), 'sahm_gap': r(sahm),
                     'payroll_k': nfp[m], 'payroll_chg_k': chg, 'payroll_chg_3m_avg_k': r(c3, 1)})
L = {x['month']: x for x in lab_rows}
pay_prior_year_avg = (nfp['2026-09'] - nfp['2025-09']) / 12
gate('payrolls_match_bls', L['2026-10']['payroll_chg_k'] == WEB['payrolls_oct2026']['payroll_change_k']
     and round(pay_prior_year_avg) == WEB['payrolls_oct2026']['avg_prior_year_k'],
     f"Oct change {L['2026-10']['payroll_chg_k']}k; Sep25->Sep26 average {pay_prior_year_avg:.1f}k")
claims = series('initialClaims')
cl = sorted(claims)[-4:]
claims_4wk = sum(claims[d] for d in cl) / 4

# ------------------------------------------------------------------ policy and rates
ff = monthly('federalFunds')
rate_rows = []
for m in mrange('2024-12', '2026-11'):
    d = month_end(UST, m)
    t = month_end(T10, m)
    if d != t:
        raise SystemExit(f'month-end dates differ {m}: UST {d} vs T10YIE {t}')
    u = UST[d]
    rate_rows.append({'month': m, 'date': d, 'effr_monthly_avg': ff.get(m), 'ust3m': u['month3'], 'ust2y': u['year2'],
                      'ust10y': u['year10'], 't10yie': T10[d], 'real10y': r(u['year10'] - T10[d], 2)})
gate('month_end_dates_aligned', True, 'treasury and T10YIE month-end dates identical for 2024-12..2026-11')
daily = []
for d in sorted(x for x in UST if x >= '2026-08-25'):
    u = UST[d]
    daily.append({'date': d, 'ust3m': u['month3'], 'ust2y': u['year2'], 'ust10y': u['year10'], 't10yie': T10.get(d),
                  'real10y': r(u['year10'] - T10[d], 2) if d in T10 else None})
gate('daily_t10yie_coverage', all(x['t10yie'] is not None for x in daily), 'every treasury date 2026-08-25..11-23 has T10YIE')
now = UST[max(UST)]
real_hi = max(daily, key=lambda x: (x['real10y'], x['date']))
ust10_hi = max(daily, key=lambda x: (x['ust10y'], x['date']))
core_pce = WEB['pce_sep2026']['core_pce_yoy_pct']

# ------------------------------------------------------------------ markets
EST = timezone(timedelta(hours=-5))
mk_rows = []
for sym, label in [('^IXIC', 'Nasdaq Composite'), ('^GSPC', 'S&P 500'), ('BZUSD', 'Brent'), ('GCUSD', 'Gold'),
                   ('BTCUSD', 'Bitcoin'), ('EURUSD', 'EUR/USD'), ('^VIX', 'VIX')]:
    x = QUO[sym][0]
    mk_rows.append({'symbol': sym, 'label': label, 'price': x['price'], 'change_pct_day': r(x['changePercentage'], 3),
                    'year_high': x['yearHigh'], 'drawdown_from_52w_high_pct': r(pct(x['price'], x['yearHigh']), 2),
                    'year_low': x['yearLow'], 'above_52w_low_pct': r(pct(x['price'], x['yearLow']), 2),
                    'vs_avg50_pct': r(pct(x['price'], x['priceAvg50']), 2),
                    'vs_avg200_pct': r(pct(x['price'], x['priceAvg200']), 2),
                    'quote_time_et': datetime.fromtimestamp(x['timestamp'], EST).strftime('%Y-%m-%d %H:%M')})
M = {x['symbol']: x for x in mk_rows}
fpe, cr = WEB['factset_forward_pe'], WEB['credit_spreads_nov2026']

# ------------------------------------------------------------------ regime rules (thresholds stated here, sources in README)
cbo, ism, pce = WEB['cbo_feb2026'], WEB['ism_manufacturing_oct2026'], WEB['pce_sep2026']
growth_tests = {
    'real_gdp_q3_saar_above_cbo_potential': (G['2026Q3']['saar_pct'], '>', cbo['potential_gdp_growth_2026_2030_pct']),
    'gdpnow_q4_above_cbo_potential': (WEB['gdpnow_q4_2026']['q4_saar_pct'], '>', cbo['potential_gdp_growth_2026_2030_pct']),
    'ism_manufacturing_above_50': (ism['pmi'], '>', 50.0),
    'unemployment_below_cbo_2026_projection': (ur['2026-10'], '<', cbo['unemployment_2026_avg_pct']),
}
inflation_tests = {
    'pce_yoy_above_2pct_target': (pce['pce_yoy_pct'], '>', 2.0),
    'core_pce_yoy_above_2pct_target': (pce['core_pce_yoy_pct'], '>', 2.0),
    'cpi_3m_annualized_above_12m': (I['2026-09']['cpi_3m_ann_pct'], '>', I['2026-09']['cpi_yoy_pct']),
    'ism_prices_above_50': (ism['prices_index'], '>', 50.0),
}
recession_tests = {
    'sahm_gap_at_least_0.5': (L['2026-10']['sahm_gap'], '>=', 0.5),
    'claims_4wk_above_250k': (claims_4wk / 1000, '>', 250.0),
    'ism_below_47.5': (ism['pmi'], '<', 47.5),
    'hy_spread_above_5pct': (cr['hy_spread_pct'], '>', 5.0),
    'gdpnow_below_0': (WEB['gdpnow_q4_2026']['q4_saar_pct'], '<', 0.0),
}
deflation_tests = {
    't10yie_below_1.5': (t10_now, '<', 1.5),
    'cpi_3m_annualized_below_0': (I['2026-10']['cpi_3m_ann_pct'], '<', 0.0),
}
OPS = {'>': lambda a, b: a > b, '<': lambda a, b: a < b, '>=': lambda a, b: a >= b}


def run(tests):
    return {k: {'value': r(v, 4), 'rule': f'{op} {r(th, 4)}', 'true': OPS[op](v, th)} for k, (v, op, th) in tests.items()}


GT, IT, RT, DT = run(growth_tests), run(inflation_tests), run(recession_tests), run(deflation_tests)
g_hot, i_hot = sum(x['true'] for x in GT.values()), sum(x['true'] for x in IT.values())
growth_state = 'above_trend' if g_hot >= 3 else ('below_trend' if g_hot <= 1 else 'mixed')
infl_state = 'above_target' if i_hot >= 3 else ('below_target' if i_hot <= 1 else 'mixed')
REGIME = {('above_trend', 'above_target'): 'overheating', ('below_trend', 'above_target'): 'stagflation',
          ('below_trend', 'below_target'): 'deflation_or_recession', ('above_trend', 'below_target'): 'goldilocks'}
regime = REGIME.get((growth_state, infl_state), 'transition')
nq = M['^IXIC']['drawdown_from_52w_high_pct']
equity_state = 'bear' if nq <= -20 else ('correction' if nq <= -10 else ('pullback' if nq <= -5 else 'near_high'))
deep = [x['label'] for x in mk_rows if x['symbol'] not in ('^VIX', 'EURUSD') and x['drawdown_from_52w_high_pct'] <= -20]

# ------------------------------------------------------------------ dashboard
D = []


def dash(dim, ind, val, unit, as_of, ref, reading, src):
    D.append({'dimension': dim, 'indicator': ind, 'value': val, 'unit': unit, 'as_of': as_of, 'reference': ref,
              'reading': reading, 'source': src})


dash('inflation', 'CPI y/y', r(I['2026-09']['cpi_yoy_pct'], 2), '%', '2026-09', 'Fed target 2% (PCE basis)', 'hot', 'FMP CPI')
dash('inflation', 'CPI m/m', r(I['2026-10']['cpi_mom_pct'], 2), '%', '2026-10', 'Oct y/y not published (no Oct-2025 base)', 'hot', 'FMP CPI; BLS via web')
dash('inflation', 'CPI 3m annualized', r(I['2026-10']['cpi_3m_ann_pct'], 2), '%', '2026-10', f"6m annualized {cpi_6m_ann:.2f}", 'hot', 'FMP CPI')
dash('inflation', 'PCE / core PCE y/y', f"{pce['pce_yoy_pct']} / {pce['core_pce_yoy_pct']}", '%', '2026-09', '2%', 'hot', 'BEA via web')
dash('inflation', 'ISM prices paid', ism['prices_index'], 'index', '2026-10', '50', 'hot', 'ISM via web')
dash('inflation', '10y breakeven (T10YIE)', t10_now, '%', t10_now_date,
     f"{T10[t10_oct_hi_d]} on {t10_oct_hi_d}; 2008 low {bench['2008']['min']}, 2020 low {bench['2020']['min']}",
     'anchored, falling', 'FMP = FRED T10YIE')
dash('growth', 'Real GDP q/q SAAR', r(G['2026Q3']['saar_pct'], 2), '%', '2026Q3', f"CBO potential {cbo['potential_gdp_growth_2026_2030_pct']}", 'hot', 'FMP realGDP; BEA')
dash('growth', 'GDPNow Q4', WEB['gdpnow_q4_2026']['q4_saar_pct'], '%', '2026-11-18', 'CBO potential 2.1', 'hot', 'Atlanta Fed via web')
dash('growth', 'ISM manufacturing PMI', ism['pmi'], 'index', '2026-10', '50 (47.5 = economy-wide)', 'hot', 'ISM via web')
dash('growth', 'Real retail sales y/y (CPI-deflated)', r(retail_sep_real, 2), '%', '2026-09', f"nominal {retail_sep_nom:.2f}", 'warm', 'FMP retailSales, CPI')
dash('growth', 'Industrial production y/y', r(pct(ip['2026-10'], ip['2025-10']), 2), '%', '2026-10', '0', 'warm', 'FMP')
dash('labor', 'Unemployment rate', ur['2026-10'], '%', '2026-10', f"CBO 2026 projection {cbo['unemployment_2026_avg_pct']}; Nov-2025 {ur['2025-11']}", 'hot', 'FMP')
dash('labor', 'Sahm gap', L['2026-10']['sahm_gap'], 'pp', '2026-10', 'recession signal >= 0.5', 'no signal', 'computed')
dash('labor', 'Payrolls 3m avg', L['2026-10']['payroll_chg_3m_avg_k'], 'k/month', '2026-10', f"CBO 2026 {cbo['payroll_2026_avg_monthly_k']}k", 'hot', 'FMP')
dash('labor', 'Initial claims 4wk avg', r(claims_4wk / 1000, 2), 'k', cl[-1], '250k rule of thumb', 'hot', 'FMP')
dash('policy', 'Effective fed funds (monthly avg)', ff['2026-10'], '%', '2026-10', f"Aug {ff['2026-08']}; hike 2026-09-16, hold 2026-10-28 (10-2)", 'tightening', 'FMP; Fed via web')
dash('policy', 'Real policy rate (EFFR - core PCE)', r(ff['2026-10'] - core_pce, 2), '%', '2026-10/09', 'positive = restrictive side', 'mildly restrictive', 'computed')
dash('policy', '10y Treasury', now['year10'], '%', max(UST), f"high {ust10_hi['ust10y']} on {ust10_hi['date']}", 'tight', 'FMP treasury')
dash('policy', '10y real yield (10y - T10YIE)', r(now['year10'] - t10_now, 2), '%', max(UST), f"high {real_hi['real10y']} on {real_hi['date']}", 'tight', 'computed')
dash('policy', '30y mortgage rate', mort[max(mort)], '%', max(mort), f"low {mort_recent[mort_low_d]} on {mort_low_d}", 'tight', 'FMP')
dash('policy', 'Yield curve 10y-3m', r(100 * (now['year10'] - now['month3']), 0), 'bp', max(UST), 'inversion < 0', 'positive slope', 'FMP treasury')
dash('market', 'Nasdaq vs 52w high', nq, '%', M['^IXIC']['quote_time_et'][:10], '-10 correction / -20 bear', equity_state, 'FMP quote')
dash('market', 'S&P 500 vs 52w high', M['^GSPC']['drawdown_from_52w_high_pct'], '%', M['^GSPC']['quote_time_et'][:10], '-10 / -20', 'pullback', 'FMP quote')
dash('market', 'VIX', M['^VIX']['price'], 'index', M['^VIX']['quote_time_et'][:10], f"prior close {QUO['^VIX'][0]['previousClose']}", 'elevated', 'FMP quote')
dash('market', 'S&P 500 forward P/E', fpe['sp500_forward_pe'], 'x', '2026-11-05', f"5y avg {fpe['avg_5y']}, 10y avg {fpe['avg_10y']}", 'below averages', 'FactSet via web')
dash('market', 'HY spread / CCC spread', f"{cr['hy_spread_pct']} / ~{cr['ccc_spread_bp_approx'] / 100:.0f}", '%', '2026-11', 'HY > 5 = stress', 'calm / CCC stressed', 'Trefis, Vanguard via web')
dash('market', 'Gold / Brent / BTC vs 52w high',
     f"{M['GCUSD']['drawdown_from_52w_high_pct']} / {M['BZUSD']['drawdown_from_52w_high_pct']} / {M['BTCUSD']['drawdown_from_52w_high_pct']}",
     '%', M['GCUSD']['quote_time_et'][:10], '-20', 'deleveraging', 'FMP quote')
dash('sentiment', 'UMich consumer sentiment', sent['2026-10'], 'index', '2026-10', f"12m range {min(sent_12)}-{max(sent_12)}", 'cold', 'FMP')
dash('sentiment', 'Smoothed recession probability', recp['2026-09'], '%', '2026-09', 'coincident model, not a forecast', 'low', 'FMP (Chauvet-Piger)')


# ------------------------------------------------------------------ write
def write_csv(name, rows):
    with open(OUT / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        for row in rows:
            w.writerow({k: '' if v is None else v for k, v in row.items()})


write_csv('inflation_monthly.csv', infl_rows)
write_csv('gdp_quarterly.csv', gdp_rows)
write_csv('labor_monthly.csv', lab_rows)
write_csv('rates_monthly.csv', rate_rows)
write_csv('rates_daily_recent.csv', daily)
write_csv('markets.csv', mk_rows)
write_csv('dashboard.csv', D)

if not all(g['pass'] for g in GATES.values()):
    print(json.dumps(GATES, indent=1))
    raise SystemExit('gate failure')

S = {
    'as_of': {'macro': 'latest prints through 2026-10 (CPI, jobs), 2026Q3 (GDP), 2026-11-14 (claims)',
              'rates': max(UST), 'indices_close': M['^IXIC']['quote_time_et'], 'other_quotes': M['GCUSD']['quote_time_et']},
    'gates': GATES,
    'inflation': {'cpi_yoy_sep2026': I['2026-09']['cpi_yoy_pct'], 'cpi_mom_oct2026': I['2026-10']['cpi_mom_pct'],
                  'cpi_3m_ann_oct2026': I['2026-10']['cpi_3m_ann_pct'], 'cpi_6m_ann_oct2026': r(cpi_6m_ann),
                  'cpi_dec2025_to_oct2026': r(cpi_10m), 'cpi_yoy_peak_2026': max((x['cpi_yoy_pct'], x['month']) for x in infl_rows if x['cpi_yoy_pct'] is not None and x['month'] >= '2026-01'),
                  'pce_yoy_sep2026': pce['pce_yoy_pct'], 'core_pce_yoy_sep2026': pce['core_pce_yoy_pct'],
                  't10yie_now': {'value': t10_now, 'date': t10_now_date},
                  't10yie_high_since_oct': {'value': T10[t10_oct_hi_d], 'date': t10_oct_hi_d},
                  't10yie_change_bp_from_oct_high': r(100 * (t10_now - T10[t10_oct_hi_d]), 1),
                  't10yie_12m_high': {'value': t10_recent[t10_hi_d], 'date': t10_hi_d},
                  'deflation_benchmarks_t10yie_min': bench},
    'growth': {'gdp_saar': {k: G[k]['saar_pct'] for k in G if G[k]['saar_pct'] is not None},
               'gdp_yoy_2026Q3': G['2026Q3']['yoy_pct'], 'gdp_two_q_ann_2026Q3': G['2026Q3']['two_q_ann_pct'],
               'gdpnow_q4': WEB['gdpnow_q4_2026']['q4_saar_pct'], 'ism_pmi_oct': ism['pmi'],
               'real_retail_sales_yoy_sep2026': r(retail_sep_real), 'ip_yoy_oct2026': r(pct(ip['2026-10'], ip['2025-10'])),
               'housing_starts_oct2026_k': hs['2026-10'], 'housing_starts_2026_peak': {'value': hs_2026[hs_peak_m], 'month': hs_peak_m},
               'housing_starts_vs_2026_peak_pct': r(pct(hs['2026-10'], hs_2026[hs_peak_m]), 2)},
    'labor': {'unrate_oct2026': ur['2026-10'], 'unrate_nov2025': ur['2025-11'], 'sahm_gap_oct2026': L['2026-10']['sahm_gap'],
              'payroll_chg_oct2026_k': L['2026-10']['payroll_chg_k'], 'payroll_3m_avg_k': L['2026-10']['payroll_chg_3m_avg_k'],
              'payroll_12m_avg_to_sep2026_k': r(pay_prior_year_avg, 1),
              'payroll_2025_avg_k': r((nfp['2025-12'] - nfp['2024-12']) / 12, 1),
              'payroll_2026_ytd_avg_k': r((nfp['2026-10'] - nfp['2025-12']) / 10, 1),
              'claims_latest': {'value': claims[cl[-1]], 'week': cl[-1]}, 'claims_4wk_avg': claims_4wk},
    'policy_rates': {'effr_oct2026': ff['2026-10'], 'effr_aug2026': ff['2026-08'], 'effr_dec2024': ff['2024-12'],
                     'real_policy_rate_effr_minus_core_pce': r(ff['2026-10'] - core_pce),
                     'curve_now': {k: now[k] for k in ('month3', 'year2', 'year10', 'year30')},
                     'ust10y_high': {'value': ust10_hi['ust10y'], 'date': ust10_hi['date']},
                     'real10y_now': r(now['year10'] - t10_now), 'real10y_high': {'value': real_hi['real10y'], 'date': real_hi['date']},
                     'real10y_month_end': {x['month']: x['real10y'] for x in rate_rows},
                     'spread_10y_3m_bp': r(100 * (now['year10'] - now['month3']), 1), 'spread_10y_2y_bp': r(100 * (now['year10'] - now['year2']), 1),
                     'mortgage_30y': {'value': mort[max(mort)], 'date': max(mort)}, 'mortgage_30y_low_since_jun': {'value': mort_recent[mort_low_d], 'date': mort_low_d}},
    'markets': {x['symbol']: {k: x[k] for k in ('price', 'drawdown_from_52w_high_pct', 'vs_avg200_pct', 'quote_time_et')} for x in mk_rows},
    'valuation_credit': {'sp500_forward_pe': fpe, 'credit': cr},
    'sentiment': {'umich_oct2026': sent['2026-10'], 'umich_12m_min': min(sent_12), 'umich_12m_max': max(sent_12),
                  'recession_prob_sep2026': recp['2026-09']},
    'regime': {'growth_tests': GT, 'inflation_tests': IT, 'recession_tests': RT, 'deflation_tests': DT,
               'growth_hot_count': g_hot, 'inflation_hot_count': i_hot, 'growth_state': growth_state,
               'inflation_state': infl_state, 'macro_regime': regime, 'equity_state': equity_state,
               'assets_20pct_below_52w_high': deep,
               'recession_signals_true': [k for k, v in RT.items() if v['true']],
               'deflation_signals_true': [k for k, v in DT.items() if v['true']]},
    'inputs_sha256': {f'claude_analysis_20261124/data/{n}': hashlib.sha256((DATA / n).read_bytes()).hexdigest() for n in INPUTS},
}
(OUT / 'summary.json').write_text(json.dumps(S, indent=1, ensure_ascii=False, sort_keys=True) + '\n')
print(json.dumps({'regime': S['regime']['macro_regime'], 'growth_hot': g_hot, 'inflation_hot': i_hot,
                  'equity_state': equity_state, 'recession_signals': S['regime']['recession_signals_true'],
                  'deflation_signals': S['regime']['deflation_signals_true'],
                  'gates': {k: v['pass'] for k, v in GATES.items()}}, ensure_ascii=False))
