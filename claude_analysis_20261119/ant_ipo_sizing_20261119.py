#!/usr/bin/env python3
"""Anthropic (ANT) on its first trading day, 2026-11-19: valuation arithmetic and position sizing inside the $7,000 Hybrid plan.

Inputs (read-only):
  claude_analysis_20261119/data/ant_ipo_facts_20261119.json  IPO terms, first-day prints, S-1/A financials, holders, lock-up, base rates (sources per block)
  gpt_review_20261113/data_audit/adjusted_close.csv          daily closes through 2026-11-13 (SHA-256 checked vs GPT manifest)
  claude_analysis_20261114/out/summary.json                  VTI look-through weights
  claude_analysis_20261115/out/summary.json                  Monday one-shot weights
  claude_analysis_20261116/data/fmp_raw/quotes_close_20261116.json   AMZN and GOOGL market caps (latest saved closes, 11/16)
Outputs: claude_analysis_20261119/out/
Run: python3 -I claude_analysis_20261119/ant_ipo_sizing_20261119.py <repo_root>
Descriptive only: no price target. ANT has no return history, so its risk enters through a stated factor assumption (section 4).
"""
import sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
GPT, H14, H15, H16 = ROOT / 'gpt_review_20261113', ROOT / 'claude_analysis_20261114', ROOT / 'claude_analysis_20261115', ROOT / 'claude_analysis_20261116'
HERE = ROOT / 'claude_analysis_20261119'
OUT = HERE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
B = 1e9
F = json.loads((HERE / 'data' / 'ant_ipo_facts_20261119.json').read_text())
ipo, fin, hold = F['ipo'], F['financials_musd'], F['holders']
PRICE_NOW = F['first_day_prints'][-1]['price']            # 100.18 at 12:12:58 ET
S = {}

# ------------------------------------------------------------------ 1. share count, cash, revenue bases
fd_estimates = [v['valuation_T'] * 1e12 / v['price'] for v in ipo['reported_fully_diluted_valuations']]
fd_estimates.append(ipo['public_benefit_fund_class_n_shares'] / ipo['public_benefit_fund_pct_fully_diluted_pre_ipo']
                    + ipo['primary_shares'] + ipo['private_placement_shares'])
FD = float(np.mean(fd_estimates))                          # three routes agree within about 1.5%
assert max(fd_estimates) / min(fd_estimates) - 1 < 0.02
OUTSTANDING = float(ipo['shares_outstanding_s1a_basis'])
cash_pf = (fin['cash_and_equivalents_2026_09_30'] + fin['short_term_investments_2026_09_30']) / 1e3 + ipo['net_proceeds_incl_placement_B']
rev = pd.Series(fin['revenue'], index=fin['quarters']) / 1e3
comp = pd.Series(fin['compute'], index=fin['quarters']) / 1e3
assert abs(rev.iloc[-3:].sum() * 1e3 - fin['nine_months_2026']['revenue']) < 1
ttm_rev, q3_ann, run_rate = rev.iloc[-4:].sum(), rev.iloc[-1] * 4, fin['run_rate_revenue_2026_10_31'] / 1e3
adj_op_q3_ann = fin['q3_2026_adjusted_operating_margin'] * rev.iloc[-1] * 4
S['bases'] = dict(fully_diluted_shares_B=FD / B, fd_estimates_B=[x / B for x in fd_estimates], outstanding_shares_s1a_B=OUTSTANDING / B,
                  cash_pro_forma_B=cash_pf, revenue_ttm_B=ttm_rev, revenue_q3_annualized_B=q3_ann, run_rate_revenue_B=run_rate,
                  q3_revenue_qoq=rev.iloc[-1] / rev.iloc[-2] - 1, q3_revenue_yoy=rev.iloc[-1] / rev.iloc[-5] - 1,
                  compute_to_revenue_q3=comp.iloc[-1] / rev.iloc[-1], compute_to_revenue_q1_2025=comp.iloc[0] / rev.iloc[0],
                  ocf_margin_9m=fin['nine_months_2026']['operating_cash_flow'] / fin['nine_months_2026']['revenue'],
                  sbc_to_revenue_9m=fin['nine_months_2026']['stock_based_comp'] / fin['nine_months_2026']['revenue'],
                  commitments_before_2031_to_run_rate=F['commitments_B']['before_2031'] / run_rate)

# ------------------------------------------------------------------ 2. valuation grid
PRICES = [83.0, 90.0, PRICE_NOW, 111.5, 114.99]
VG = []
for p in PRICES:
    mc = p * FD / B
    ev = mc - cash_pf
    VG.append(dict(price=p, vs_ipo=p / ipo['ipo_price'] - 1, mcap_fd_B=mc, mcap_outstanding_B=p * OUTSTANDING / B, ev_fd_B=ev,
                   ev_to_run_rate=ev / run_rate, ev_to_q3_annualized=ev / q3_ann, ps_ttm_fd=mc / ttm_rev, ps_ttm_outstanding=p * OUTSTANDING / B / ttm_rev,
                   ev_to_q3_adj_operating_income_annualized=ev / adj_op_q3_ann))
VG = pd.DataFrame(VG)
VG.to_csv(OUT / 'valuation_grid.csv', index=False)


# ------------------------------------------------------------------ 3. reverse DCF: 10-year revenue CAGR the price requires
def dcf(r, m_term, g, R0=run_rate, m0=0.08, years=10, g_term=0.03):
    v, R = 0.0, R0
    for t in range(1, years + 1):
        R *= 1 + g
        v += R * (m0 + (m_term - m0) * t / years) / (1 + r) ** t   # FCF margin after SBC ramps linearly from m0 to m_term
    return v + R * (1 + g_term) * m_term / (r - g_term) / (1 + r) ** years


def implied_g(ev, r, m):
    lo, hi = -0.5, 3.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if dcf(r, m, mid) < ev else (lo, mid)
    return mid


RD = []
for p in [83.0, PRICE_NOW, 111.5]:
    ev = p * FD / B - cash_pf
    for r in (0.10, 0.12):
        for m in (0.25, 0.35):
            g = implied_g(ev, r, m)
            RD.append(dict(price=p, discount_rate=r, terminal_fcf_margin=m, implied_10y_revenue_cagr=g, implied_revenue_2036_B=run_rate * (1 + g) ** 10))
RD = pd.DataFrame(RD)
RD.to_csv(OUT / 'reverse_dcf.csv', index=False)

# ------------------------------------------------------------------ 4. risk: the 11/15 issuer-level model plus ANT through an AI-basket factor
man = json.loads((GPT / 'MANIFEST_SHA256.json').read_text())
assert man['data_audit/adjusted_close.csv'] == sha(GPT / 'data_audit' / 'adjusted_close.csv')
P = pd.read_csv(GPT / 'data_audit' / 'adjusted_close.csv', index_col=0, parse_dates=True)
L = json.loads((H14 / 'out' / 'summary.json').read_text())['vti_lookthrough']
om_now, w0930 = pd.Series(L['drifted_2026_11_13']), pd.Series(L['weights_2026_09_30'])
k7 = list(om_now.index)
R = P.pct_change().iloc[1:]
rel = (P[k7] / P.loc['2026-09-30', k7]).div(P['VTI'] / P.loc['2026-09-30', 'VTI'], axis=0)
OM = rel.mul(w0930, axis=1).shift(1).loc[R.index]
RI = R.copy()
RI['VTI_rest'] = (R['VTI'] - (OM * R[k7]).sum(axis=1)) / (1 - OM.sum(axis=1))
AI8 = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
WIN = slice('2023-11-14', '2026-11-13')
X = RI.loc[WIN].drop(columns=['VTI'])
X['AI_BASKET'] = R.loc[WIN, AI8].mean(axis=1)              # equal-weight AI8 daily return: the factor ANT loads on
C = X.cov() * 252
SIG0 = C.drop(index='AI_BASKET', columns='AI_BASKET')
var_b, cov_b = C.loc['AI_BASKET', 'AI_BASKET'], C.loc['AI_BASKET'].drop('AI_BASKET')


def sig_with_ant(beta, sigma):
    assert sigma ** 2 > beta ** 2 * var_b                    # idiosyncratic variance must be positive
    Sg = SIG0.copy()
    Sg['ANT'] = beta * cov_b
    Sg.loc['ANT'] = list(beta * cov_b) + [sigma ** 2]
    return Sg


plan = json.loads((H15 / 'out' / 'summary.json').read_text())['plan']
monday = plan['monday']
Q16 = json.loads((H16 / 'data' / 'fmp_raw' / 'quotes_close_20261116.json').read_text())
stake_share = {'AMZN': hold['amazon_shares'] * PRICE_NOW / Q16['AMZN'][0]['marketCap'],
               'GOOGL': hold['google_shares'] * PRICE_NOW / Q16['GOOGL'][0]['marketCap']}


def exposure(w, index):
    e = {}
    for k, v in w.items():
        if k == 'VTI':
            for kk, o in om_now.items():
                e[kk] = e.get(kk, 0) + v * o
            e['VTI_rest'] = e.get('VTI_rest', 0) + v * (1 - om_now.sum())
        else:
            e[k] = e.get(k, 0) + v
    return pd.Series(e).reindex(index, fill_value=0.0)


def weights(w_ant, mode):
    w = dict(monday)
    if mode == 'new money':
        w = {k: v * (1 - w_ant) for k, v in w.items()}
    elif mode == 'from SGOV':
        w['SGOV'] -= w_ant
    elif mode == 'from MSFT':
        w['MSFT'] -= w_ant
    w['ANT'] = w_ant
    assert min(w.values()) > -1e-12 and abs(sum(w.values()) - 1) < 1e-9
    return w


SHOCK = {'ANT': -0.50, **{t: -0.30 for t in AI8}, 'VTI_rest': -0.15, 'BRK-B': -0.10, 'XLV': -0.05, 'SGOV': 0.0}


def evaluate(w_ant, mode, beta=1.25, sigma=0.70):
    Sg = sig_with_ant(beta, sigma)
    w = weights(w_ant, mode)
    e = exposure(w, Sg.index)
    cv = Sg @ e
    var = float(e @ cv)
    rc = e * cv / var
    value = 7000 / (1 - w_ant) if mode == 'new money' else 7000.0
    indirect = sum(e[t] * stake_share[t] for t in ('AMZN', 'GOOGL'))
    return dict(mode=mode, ant_weight=w_ant, ant_usd=w_ant * value, portfolio_usd=value, vol=np.sqrt(var), rc_ant=float(rc['ANT']),
                rc_nvda=float(rc['NVDA']), rc_googl=float(rc['GOOGL']), rc_ai_incl_ant=float(rc[AI8 + ['ANT']].sum()),
                ant_indirect_via_amzn_googl=indirect, ant_total_exposure=w_ant + indirect,
                loss_if_ant_minus50_usd=-0.5 * (w_ant + indirect) * value,
                ai_unwind_stress_usd=float(sum(e[k] * SHOCK.get(k, 0) for k in e.index)) * value)


base0 = evaluate(0.0, 'from SGOV')
assert abs(base0['vol'] - 0.1762) < 6e-5 and abs(base0['rc_nvda'] - 0.3031) < 6e-5     # reproduces the Monday plan
SZ = pd.DataFrame([evaluate(w, m) for m in ('new money', 'from SGOV', 'from MSFT') for w in (0.0, 0.02, 0.03, 0.05, 0.07, 0.10)
                   if not (m == 'from MSFT' and w > 0.07)])
SZ.to_csv(OUT / 'sizing_base.csv', index=False)
SENS = pd.DataFrame([dict(beta=b, sigma=s, ant_weight=w, **{k: v for k, v in evaluate(w, 'new money', b, s).items() if k in ('vol', 'rc_ant', 'rc_nvda')})
                     for b in (1.0, 1.25, 1.5) for s in (0.5, 0.7, 0.9) for w in (0.03, 0.05, 0.07) if s ** 2 > b ** 2 * var_b])
SENS.to_csv(OUT / 'sizing_sensitivity.csv', index=False)
CURVE = pd.DataFrame([dict(sigma=s, ant_weight=w, **{k: v for k, v in evaluate(w, 'new money', 1.25, s).items() if k in ('vol', 'rc_ant', 'rc_nvda')})
                      for s in (0.5, 0.7, 0.9) for w in np.round(np.arange(0, 0.1001, 0.0025), 4)])
CURVE.to_csv(OUT / 'rc_curve_new_money.csv', index=False)


def weight_for_rc(target, mode='new money', beta=1.25, sigma=0.70):
    lo, hi = 0.0, 0.10 if mode != 'from MSFT' else 0.07
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if evaluate(mid, mode, beta, sigma)['rc_ant'] < target else (lo, mid)
    return mid


rc_googl_now = base0['rc_googl']
S['risk_model'] = dict(ai_basket_vol=float(np.sqrt(var_b)), ant_beta_base=1.25, ant_sigma_base=0.70,
                       ant_corr_with_basket_base=1.25 * np.sqrt(var_b) / 0.70, rc_googl_in_monday_plan=rc_googl_now,
                       weight_where_rc_ant_equals_googl={m: weight_for_rc(rc_googl_now, m) for m in ('new money', 'from SGOV', 'from MSFT')},
                       weight_where_rc_ant_is_15pct={m: weight_for_rc(0.15, m) for m in ('new money', 'from SGOV')},
                       stake_share_of_market_cap=stake_share, stress_shocks=SHOCK)

# ------------------------------------------------------------------ 5. lock-up calendar (days counted from the prospectus date)
pd0 = pd.Timestamp(F['lockup']['prospectus_date'])
S['lockup_dates'] = [dict(date=str((pd0 + pd.Timedelta(days=x['day_after_prospectus'])).date()), pct_of_other_holders=x['pct'])
                     for x in F['lockup']['other_holders_staged_pct']]
S['lockup_unlock_vs_float'] = F['lockup']['up_to_unlocked_within_76_days'] / ipo['shares_offered']
S['valuation_grid'] = VG.to_dict(orient='records')
S['reverse_dcf'] = RD.to_dict(orient='records')
S['sizing_base'] = SZ.to_dict(orient='records')
S['price_now'] = dict(price=PRICE_NOW, time_et=F['first_day_prints'][-1]['time_et'])
S['inputs_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in [HERE / 'data' / 'ant_ipo_facts_20261119.json', GPT / 'data_audit' / 'adjusted_close.csv',
                                                               H14 / 'out' / 'summary.json', H15 / 'out' / 'summary.json',
                                                               H16 / 'data' / 'fmp_raw' / 'quotes_close_20261116.json']}
(OUT / 'summary.json').write_text(json.dumps(S, indent=2, ensure_ascii=False, default=float) + '\n')

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
print(json.dumps(S['bases'], indent=1))
print(VG.round(3).to_string())
print(RD.round(3).to_string())
print(SZ.round(4).to_string())
print(SENS.round(4).to_string())
print(json.dumps({k: S['risk_model'][k] for k in S['risk_model'] if k != 'stress_shocks'}, indent=1, default=float))
print(S['lockup_dates'], S['lockup_unlock_vs_float'])
