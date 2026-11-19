#!/usr/bin/env python3
"""NVDA Q3 FY27 (reported 2026-11-17 16:20 ET) against the pre-committed 11/17 decision rules, plus a five-quarter earnings-quality update.

Inputs (read-only):
  current_plan.json                                                 rule text; the thresholds below are asserted against it
  claude_analysis_20261117/data/fmp_raw/NVDA_q3fy27_20261117.json   FMP Q3 FY27 statements, five balance sheets, 11/17 close, after-hours prints
  claude_analysis_20261117/data/sources_web_20261117.json           release, CFO commentary, call and board facts (numbers under used_in_script)
  claude_analysis_20261116/data/fmp_raw/NVDA_20261116.json          FMP income and cash-flow statements for the four earlier quarters
  claude_analysis_20261115/data/fmp_raw/NVDA.json                   pre-earnings consensus (fetched 2026-11-16 UTC)
  claude_analysis_20261115/out/summary.json                         Monday one-shot weights and their risk
Outputs: claude_analysis_20261117/out/
Run: python3 -I claude_analysis_20261117/nvda_q3fy27_check.py <repo_root>
Descriptive only: implied figures below are arithmetic on company guidance, not forecasts.
"""
import sys, json, hashlib
from pathlib import Path
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
H15, H16, HERE = ROOT / 'claude_analysis_20261115', ROOT / 'claude_analysis_20261116', ROOT / 'claude_analysis_20261117'
OUT = HERE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
B = 1e9
DAYS_Q = 91                                   # every quarter used here is 13 weeks; Q4 FY27 (14 weeks) is only used through guidance
REPORT, NTM_FY1_END = pd.Timestamp('2026-11-17'), pd.Timestamp('2027-01-25')
TAX_NONOP = 0.21

N17 = json.loads((HERE / 'data' / 'fmp_raw' / 'NVDA_q3fy27_20261117.json').read_text())
N16 = json.loads((H16 / 'data' / 'fmp_raw' / 'NVDA_20261116.json').read_text())
WEB = json.loads((HERE / 'data' / 'sources_web_20261117.json').read_text())['used_in_script']
EST = {r['date']: r for r in json.loads((H15 / 'data' / 'fmp_raw' / 'NVDA.json').read_text())['estimates_annual']}
PLAN = json.loads((ROOT / 'current_plan.json').read_text())
rule_text = PLAN['decision_rules_nvda_q3fy27_2026_11_17'][0]['if']
assert '$105.8B' in rule_text and '< 71%' in rule_text                      # thresholds below are the committed ones
assert WEB['rule_revenue_floor_B'] == 105.8 and WEB['rule_q4_gm_floor_pct'] == 71.0

# ------------------------------------------------------------------ 1. five quarters, newest first
inc = N17['income_quarter_latest'] + N16['income_quarter'][:4]
cfs = N17['cashflow_quarter_latest'] + N16['cashflow_quarter'][:4]
bal = N17['balance_sheet_quarter_5']
dates = [r['date'] for r in inc]
assert dates == [r['date'] for r in cfs] == [r['date'] for r in bal] == ['2026-10-25', '2026-07-26', '2026-04-26', '2026-01-25', '2025-10-26']
rows = []
for i, c, b in zip(inc, cfs, bal):
    rows.append(dict(quarter=f"{i['period']} FY{i['fiscalYear'][2:]}", date=i['date'], revenue_B=i['revenue'] / B,
                     gross_margin=i['grossProfit'] / i['revenue'], operating_income_B=i['operatingIncome'] / B,
                     nonop_B=(i['incomeBeforeTax'] - i['operatingIncome']) / B,
                     nonop_share_of_pretax=(i['incomeBeforeTax'] - i['operatingIncome']) / i['incomeBeforeTax'],
                     net_income_B=i['netIncome'] / B, ocf_B=c['operatingCashFlow'] / B, ocf_to_ni=c['operatingCashFlow'] / i['netIncome'],
                     fcf_B=c['freeCashFlow'] / B, receivables_B=b['accountsReceivables'] / B, inventory_B=b['inventory'] / B,
                     dso_days=b['accountsReceivables'] / i['revenue'] * DAYS_Q, dio_days=b['inventory'] / i['costOfRevenue'] * DAYS_Q,
                     investments_total_B=b['totalInvestments'] / B, lt_investments_B=b['longTermInvestments'] / B,
                     long_term_debt_B=b['longTermDebt'] / B, diluted_shares_B=i['weightedAverageShsOutDil'] / B, eps_diluted=i['epsDiluted']))
QQ = pd.DataFrame(rows).set_index('quarter')
QQ['revenue_qoq'] = QQ.revenue_B / QQ.revenue_B.shift(-1) - 1
QQ['receivables_qoq'] = QQ.receivables_B / QQ.receivables_B.shift(-1) - 1
QQ['inventory_qoq'] = QQ.inventory_B / QQ.inventory_B.shift(-1) - 1
QQ.to_csv(OUT / 'nvda_quarterly_quality.csv')
now, prev = QQ.iloc[0], QQ.iloc[1]
assert abs(now.dso_days - WEB['dso_reported_days']) < 0.5 and abs(prev.dso_days - WEB['dso_reported_prior_days']) < 0.5   # our DSO = company DSO


def ttm(df):
    return dict(ocf_to_ni=df.ocf_B.sum() / df.net_income_B.sum(), nonop_share_of_pretax=df.nonop_B.sum() / (df.operating_income_B.sum() + df.nonop_B.sum()),
                fcf_B=df.fcf_B.sum(), revenue_B=df.revenue_B.sum(), net_income_B=df.net_income_B.sum())


TTM = {'ttm_to_q3_fy27': ttm(QQ.iloc[:4]), 'ttm_to_q2_fy27': ttm(QQ.iloc[1:5])}

# ------------------------------------------------------------------ 2. the committed gate
q4_gm_mid = (WEB['q4_gm_guide_low_pct'] + WEB['q4_gm_guide_high_pct']) / 2
GATE = [
    dict(trigger='Q3 revenue < $105.8B', observed=f"${now.revenue_B:.1f}B", fired=bool(now.revenue_B < WEB['rule_revenue_floor_B']),
         margin=f"+${now.revenue_B - WEB['rule_revenue_floor_B']:.1f}B above the floor"),
    dict(trigger='Q4 gross-margin guide < 71%', observed=f"{WEB['q4_gm_guide_low_pct']:.1f}%-{WEB['q4_gm_guide_high_pct']:.1f}% (mid {q4_gm_mid:.1f}%)",
         fired=bool(q4_gm_mid < WEB['rule_q4_gm_floor_pct'] or WEB['q4_gm_guide_low_pct'] < WEB['rule_q4_gm_floor_pct']),
         margin=f"low end exactly at the floor; mid +{q4_gm_mid - WEB['rule_q4_gm_floor_pct']:.1f}pp; the dip to 71-72% was pre-announced in August"),
    dict(trigger='FY28 growth framework withdrawn or cut', observed=f"raised: about {WEB['fy28_growth_new']:.0%} from a higher FY27 base (was about {WEB['fy28_growth_prior']:.0%})",
         fired=bool(WEB['fy28_growth_new'] < WEB['fy28_growth_prior']), margin='raised, not cut'),
    dict(trigger='new US export restriction specifically on NVIDIA data-center sales', observed='none announced; Q4 guide again assumes no China data-center compute revenue; '
         'Senate Banking hearing requested for 12/03 (a hearing, not a restriction)', fired=False, margin='watch: 12/03 and 12/10 hearings'),
    dict(trigger='CEO search with roadmap or customer-commitment changes', observed='interim CEO says roadmap on track; Vera Rubin NVL72 shipped; board will not reinstate Huang; '
         f"supply commitments ${WEB['supply_commitments_prior_B']:.0f}B -> ${WEB['supply_commitments_B']:.0f}B, cloud/lease ${WEB['cloud_and_lease_commitments_prior_B']:.0f}B -> "
         f"${WEB['cloud_and_lease_commitments_B']:.0f}B", fired=False, margin='no roadmap or customer change disclosed'),
]
fired = [g['trigger'] for g in GATE if g['fired']]
DECISION = dict(fired=fired, outcome='hold NVDA at 12.5% until the 2026-12-31 review' if not fired else 'NVDA 12.5% -> 7.5%',
                rule_source='current_plan.json: decision_rules_nvda_q3fy27_2026_11_17')
assert not fired
(OUT / 'decision_gate.json').write_text(json.dumps(dict(gate=GATE, decision=DECISION), indent=2, ensure_ascii=False) + '\n')

# ------------------------------------------------------------------ 3. guidance-implied FY27/FY28 vs pre-earnings consensus (arithmetic, not a forecast)
c27, c28 = EST['2027-01-25'], EST['2028-01-25']
q1_3_rev = QQ.loc[['Q1 FY27', 'Q2 FY27', 'Q3 FY27'], 'revenue_B'].sum()
fy27_rev = q1_3_rev + WEB['q4_revenue_guide_mid_B']
fy28_rev = fy27_rev * (1 + WEB['fy28_growth_new'])
q4_ni = (WEB['q4_revenue_guide_mid_B'] * q4_gm_mid / 100 - WEB['q4_gaap_opex_B']) * (1 - WEB['fy27_tax_rate_mid'])   # other income set to 0
q4_eps = q4_ni / now.diluted_shares_B
fy27_q = QQ.loc[['Q1 FY27', 'Q2 FY27', 'Q3 FY27']]
fy27_nonop_ps = float((fy27_q.nonop_B * (1 - TAX_NONOP) / fy27_q.diluted_shares_B).sum())
fy27_eps = float(fy27_q.eps_diluted.sum()) + q4_eps
fy27_eps_clean = fy27_eps - fy27_nonop_ps
fy28_eps_scaled = c28['epsAvg'] * fy28_rev / (c28['revenueAvg'] / B)       # margin-neutral scaling of the pre-earnings consensus
w = (NTM_FY1_END - REPORT).days / 365.0
close17 = N17['quote_regular_close_2026_11_17'][0]
ah = [t[0]['price'] for t in N17['aftermarket_trades']]
mcap17 = close17['marketCap'] / B
pre_adj = float((QQ.loc[['Q1 FY27', 'Q2 FY27']].nonop_B * (1 - TAX_NONOP) / QQ.loc[['Q1 FY27', 'Q2 FY27']].diluted_shares_B).sum())
EPS_NTM = {'pre_earnings': w * (c27['epsAvg'] - pre_adj) + (1 - w) * c28['epsAvg'],           # same construction as the 11/16 clean NTM P/E
           'fy27_updated': w * fy27_eps_clean + (1 - w) * c28['epsAvg'],                         # FY1 = Q1-Q3 actual + Q4 guide, cleaned
           'fy27_updated_fy28_scaled': w * fy27_eps_clean + (1 - w) * fy28_eps_scaled}           # FY2 scaled by the new 75% revenue framework
VAL = []
for label, px in [('close 2026-11-17', close17['price']), ('after-hours 17:13 ET', ah[0]), ('after-hours 17:16 ET', ah[1])]:
    VAL.append(dict(price_basis=label, price=px, **{f'pe_ntm_{k}': px / v for k, v in EPS_NTM.items()}))
GUIDE = dict(fy27_revenue_implied_B=fy27_rev, fy27_revenue_consensus_pre_B=c27['revenueAvg'] / B, fy27_revenue_vs_consensus=fy27_rev / (c27['revenueAvg'] / B) - 1,
             fy28_revenue_implied_B=fy28_rev, fy28_revenue_consensus_pre_B=c28['revenueAvg'] / B, fy28_revenue_vs_consensus=fy28_rev / (c28['revenueAvg'] / B) - 1,
             fy28_revenue_old_framework_on_old_base_B=(c27['revenueAvg'] / B) * (1 + WEB['fy28_growth_prior']),
             q4_eps_implied=q4_eps, fy27_eps_implied=fy27_eps, fy27_eps_consensus_pre=c27['epsAvg'], fy27_nonop_after_tax_per_share=fy27_nonop_ps,
             fy27_eps_implied_clean=fy27_eps_clean, fy28_eps_consensus_pre=c28['epsAvg'], fy28_eps_scaled=fy28_eps_scaled, ntm_weight_fy1=w,
             fcf_yield_ttm_at_close=TTM['ttm_to_q3_fy27']['fcf_B'] / mcap17)
pd.DataFrame(VAL).to_csv(OUT / 'nvda_valuation_post_q3.csv', index=False)

# ------------------------------------------------------------------ 4. off-balance-sheet scale
OBS = dict(mcap_close_B=mcap17, guarantees_B=WEB['guarantee_max_gross_B'], guarantees_to_mcap=WEB['guarantee_max_gross_B'] / mcap17,
           guarantees_to_ttm_fcf=WEB['guarantee_max_gross_B'] / TTM['ttm_to_q3_fy27']['fcf_B'],
           guarantees_to_cash_and_securities=WEB['guarantee_max_gross_B'] / (bal[0]['cashAndShortTermInvestments'] / B),
           supply_commitments_B=WEB['supply_commitments_B'], supply_fy28_to_fy28_revenue_implied=WEB['supply_commitments_fy28_B'] / fy28_rev,
           cloud_and_lease_B=WEB['cloud_and_lease_commitments_B'], neocloud_contingent_B=WEB['neocloud_contingent_B'],
           shareholder_returns_q3_B=WEB['repurchases_q3_B'] + WEB['dividends_q3_B'], company_fcf_q3_B=WEB['company_fcf_q3_B'])

# ------------------------------------------------------------------ 5. portfolio consequence
P15 = json.loads((H15 / 'out' / 'summary.json').read_text())
monday = P15['plan']['monday']
S = dict(asof='Q3 FY27 release 2026-11-17 16:20 ET; call coverage to about 17:45 ET', decision=DECISION, gate=GATE,
         quarters={q: {k: (v if isinstance(v, str) else float(v)) for k, v in r.items()} for q, r in QQ.iterrows()}, ttm=TTM, guidance_arithmetic=GUIDE,
         valuation=VAL, off_balance_sheet=OBS,
         portfolio=dict(nvda_weight_after_rule=monday['NVDA'], nvda_dollars_on_7000=round(7000 * monday['NVDA'], 2), weights_changed=False),
         inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in [HERE / 'data' / 'fmp_raw' / 'NVDA_q3fy27_20261117.json', HERE / 'data' / 'sources_web_20261117.json',
                                                                  H16 / 'data' / 'fmp_raw' / 'NVDA_20261116.json', H15 / 'data' / 'fmp_raw' / 'NVDA.json',
                                                                  H15 / 'out' / 'summary.json', ROOT / 'current_plan.json']})
(OUT / 'summary.json').write_text(json.dumps(S, indent=2, ensure_ascii=False, default=float) + '\n')

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
print(QQ.round(3).T.to_string())
print(json.dumps(TTM, indent=1))
print(json.dumps(GUIDE, indent=1))
print(pd.DataFrame(VAL).round(2).to_string())
print(json.dumps(OBS, indent=1))
print(json.dumps(DECISION, indent=1))
