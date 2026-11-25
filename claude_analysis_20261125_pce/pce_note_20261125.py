#!/usr/bin/env python3
"""October 2026 PCE (released 2026-11-25 08:30 ET): what it changes. Follow-up to
claude_analysis_20261124 (macro regime). Run from a checkout that has both folders:
    python3 -I claude_analysis_20261125_pce/pce_note_20261125.py <repo_root>
Reads this folder's data/ and two hash-gated files of claude_analysis_20261124; writes out/.
Exits non-zero if any gate fails."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261125_pce'
PREV = ROOT / 'claude_analysis_20261124'
DATA, OUT = HERE / 'data', HERE / 'out'
OUT.mkdir(exist_ok=True)
GATES = {}


def gate(name, ok, detail=''):
    GATES[name] = {'pass': bool(ok), 'detail': detail}


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text())


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---- inputs ---------------------------------------------------------------------------
INPUTS = ['fmp_rates_nasdaq_20261125_close.json', 'sources_web_20261125_pce.json', 'positions_main_20691c6.json']
FMP, WEB, POS = (load(DATA / n) for n in INPUTS)
PREV_USED = ['out/summary.json', 'data/fmp_treasury_rates_20261124.json']
prev_files = load(PREV / 'manifest.json')['files']
n_ok = sum(sha256(PREV / u) == prev_files[u]['sha256'] for u in PREV_USED)
gate('prev_package_files_match_its_manifest', n_ok == len(PREV_USED),
     f'{n_ok}/{len(PREV_USED)} files of claude_analysis_20261124 match its manifest.json')
PREV_SUM = load(PREV / 'out/summary.json')
PREV_RATES = load(PREV / 'data/fmp_treasury_rates_20261124.json')['responses']['treasury-rates|2025-11-01|2026-11-23']

# ---- 1. web values: all sources that report an item must agree -------------------------
V = {}
for key, it in WEB['items'].items():
    vals = list(it['by_source'].values())
    if it['unit'] == 'text':
        V[key] = it['by_source']
        continue
    gate(f'sources_agree:{key}', all(same(v, vals[0]) for v in vals),
         f"{len(vals)} source(s): {', '.join(sorted(it['by_source']))}")
    V[key] = vals[0]

# ---- 2. Treasury yields, close to close (FMP) -------------------------------------------
R = {r['date']: r for r in FMP['treasury-rates|2026-11-23|2026-11-25']}
old23 = next(r for r in PREV_RATES if r['date'] == '2026-11-23')
gate('fmp_rates_2026_11_23_same_in_both_pulls', R['2026-11-23'] == old23,
     'the 2026-11-23 row pulled on 11-25 equals the row pulled on 11-24 (12 tenors)')
TENORS = ['month1', 'month3', 'month6', 'year1', 'year2', 'year5', 'year10', 'year30']
rows = [{'tenor': t, 'yield_2026_11_24': R['2026-11-24'][t], 'yield_2026_11_25': R['2026-11-25'][t],
         'change_bp': round(100 * (R['2026-11-25'][t] - R['2026-11-24'][t]), 1)} for t in TENORS]
with open(OUT / 'rates_change_20261124_to_20261125.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
CHG = {r['tenor']: r['change_bp'] for r in rows}

# ---- 3. Nasdaq Composite: FMP quote vs news ---------------------------------------------
q = FMP['^IXIC'][0]
pc = q['previousClose']
IXIC = {'previous_close': pc, 'open': q['open'], 'low': q['dayLow'], 'close': q['price'],
        'open_vs_prev_pct': round(100 * (q['open'] / pc - 1), 2),
        'low_vs_prev_pct': round(100 * (q['dayLow'] / pc - 1), 2),
        'close_vs_prev_pct': round(100 * (q['price'] / pc - 1), 2)}
gate('nasdaq_close_matches_news',
     abs(q['price'] - V['nasdaq_close_20261125']) < 0.01 and IXIC['close_vs_prev_pct'] == V['nasdaq_close_pct_20261125'],
     f"FMP {q['price']:.2f} ({IXIC['close_vs_prev_pct']}%) vs news {V['nasdaq_close_20261125']:.2f} "
     f"({V['nasdaq_close_pct_20261125']}%)")
gate('nasdaq_intraday_low_matches_news', IXIC['low_vs_prev_pct'] == -V['nasdaq_max_intraday_drop_pct_20261125'],
     f"FMP low {IXIC['low_vs_prev_pct']}% vs news -{V['nasdaq_max_intraday_drop_pct_20261125']}%")

# ---- 4. what the release changes in the 2026-11-24 regime read --------------------------
tests = PREV_SUM['regime']['inflation_tests']
core_t, head_t = tests['core_pce_yoy_above_2pct_target'], tests['pce_yoy_above_2pct_target']
gate('prev_core_pce_sep_equals_prior_reported_today', core_t['value'] == V['pce_core_yoy_sep'],
     f"claude_analysis_20261124 used {core_t['value']}; today's sources give September core as {V['pce_core_yoy_sep']}")
gate('prev_headline_pce_sep_equals_first_print', head_t['value'] == V['pce_headline_yoy_sep_first_print'],
     f"claude_analysis_20261124 used {head_t['value']}; first print {V['pce_headline_yoy_sep_first_print']}, "
     f"revised {V['pce_headline_yoy_sep_revised']}")
new_true = {k: v['true'] for k, v in tests.items()}
new_true['core_pce_yoy_above_2pct_target'] = V['pce_core_yoy_oct'] > 2.0
new_true['pce_yoy_above_2pct_target'] = V['pce_headline_yoy_oct'] > 2.0
REGIME = {
    'updated_tests': {
        'core_pce_yoy_above_2pct_target': {'rule': core_t['rule'], 'before_sep': core_t['value'],
                                           'after_oct': V['pce_core_yoy_oct'],
                                           'true': new_true['core_pce_yoy_above_2pct_target']},
        'pce_yoy_above_2pct_target': {'rule': head_t['rule'], 'before_sep_first_print': head_t['value'],
                                      'after_oct': V['pce_headline_yoy_oct'],
                                      'true': new_true['pce_yoy_above_2pct_target']}},
    'unchanged_tests': sorted(k for k in tests if k not in ('core_pce_yoy_above_2pct_target', 'pce_yoy_above_2pct_target')),
    'inflation_hot_count_before': PREV_SUM['regime']['inflation_hot_count'],
    'inflation_hot_count_after': sum(new_true.values()),
    'inflation_tests_total': len(tests),
    'headline_pce_sep_first_print_to_revised': [V['pce_headline_yoy_sep_first_print'], V['pce_headline_yoy_sep_revised']],
    'core_pce_yoy_feb_to_sep_range': V['pce_core_yoy_feb_to_sep_range'],
}


# ---- 5. arithmetic ------------------------------------------------------------------------
def annualize(m):
    return round(100 * ((1 + m / 100) ** 12 - 1), 2)


target_monthly = 100 * (1.02 ** (1 / 12) - 1)
real_mom = 100 * ((1 + V['pce_spending_nominal_mom_oct'] / 100) / (1 + V['pce_headline_mom_oct'] / 100) - 1)
ARITH = {
    'core_mom_rounded_annualized_pct': annualize(V['pce_core_mom_oct']),
    'core_mom_unrounded_annualized_pct': annualize(V['pce_core_mom_oct_unrounded']),
    'monthly_pace_of_2pct_target_pct': round(target_monthly, 3),
    'core_mom_rounded_over_target_pace': round(V['pce_core_mom_oct'] / target_monthly, 2),
    'core_yoy_surprise_pp': round(V['pce_core_yoy_oct'] - V['pce_core_yoy_oct_consensus'], 2),
    'headline_yoy_surprise_pp': round(V['pce_headline_yoy_oct'] - V['pce_headline_yoy_oct_consensus'], 2),
    'real_spending_mom_from_rounded_inputs_pct': round(real_mom, 2),
    'note': 'monthly inputs are rounded to 0.1, so the real-spending estimate is only good to about +/-0.1 pp',
}
gate('real_spending_consistent_with_flat_report', abs(real_mom) <= 0.1 and V['real_spending_oct_flat'] is True,
     f'{real_mom:.2f}% from nominal {V["pce_spending_nominal_mom_oct"]}% and prices {V["pce_headline_mom_oct"]}%')

# ---- 6. exposure of the basket executed on 2026-11-25 ------------------------------------
amt = POS['amount_usd']
total = sum(amt.values())
gate('positions_total_7000', total == 7000, f'sum of amount_usd = {total}')
GROUPS = {'AI8': ['NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSM', 'AVGO', 'MU'], 'VTI': ['VTI'],
          'BRKB_XLV': ['BRK-B', 'XLV'], 'SGOV': ['SGOV']}
gate('groups_cover_each_ticker_once', sorted(x for g in GROUPS.values() for x in g) == sorted(amt),
     f'{len(amt)} tickers')
EXPO = {g: {'members': xs, 'usd': sum(amt[x] for x in xs), 'pct': round(100 * sum(amt[x] for x in xs) / total, 1)}
        for g, xs in GROUPS.items()}

# ---- outputs ------------------------------------------------------------------------------------
summary = {
    'as_of': 'October 2026 PCE (BEA, 2026-11-25 08:30 ET); market data at the 2026-11-25 close',
    'release': {k: V[k] for k in [
        'pce_headline_yoy_oct', 'pce_headline_mom_oct', 'pce_headline_yoy_oct_consensus',
        'pce_core_yoy_oct', 'pce_core_mom_oct', 'pce_core_mom_oct_unrounded', 'pce_core_yoy_oct_consensus',
        'pce_core_yoy_sep', 'pce_headline_yoy_sep_first_print', 'pce_headline_yoy_sep_revised',
        'pce_headline_yoy_aug_revised', 'pce_core_yoy_oct_is_highest_in_about_3_years',
        'personal_income_mom_oct', 'dpi_mom_oct', 'pce_spending_nominal_mom_oct', 'real_spending_oct_flat',
        'saving_rate_oct', 'next_pce_release']},
    'fed': {k: V[k] for k in [
        'fedwatch_dec_25bp_hike_prob', 'fedwatch_dec_25bp_hike_prob_week_earlier', 'fed_target_range_after_25bp',
        'fedwatch_after_oct_cpi_2026_11_10', 'waller_50bp_threshold_core_cpi_mom', 'waller_dec_options',
        'oxford_dec_call']},
    'market_20261125': {'treasury_change_bp_close_to_close': CHG, 'nasdaq_composite': IXIC,
                        'nvda_close': V['nvda_close_20261125'], 'mu_close': V['mu_close_20261125'],
                        'selloff_drivers_reported': V['selloff_drivers_20261125']},
    'regime_update_vs_claude_analysis_20261124': REGIME,
    'arithmetic': ARITH,
    'executed_basket_exposure': EXPO,
    'calendar': {'fomc': '2026-12-08/09', 'november_cpi': '2026-12-10 (claude_analysis_20261124/README.md)',
                 'november_pce': V['next_pce_release'], 'quarterly_review': '2026-12-31'},
    'inputs_sha256': {**{f'data/{n}': sha256(DATA / n) for n in INPUTS},
                      **{f'../claude_analysis_20261124/{u}': sha256(PREV / u) for u in PREV_USED}},
    'gates': GATES,
}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + '\n')

failed = [k for k, v in GATES.items() if not v['pass']]
print(f'gates: {len(GATES) - len(failed)}/{len(GATES)} pass')
for k in failed:
    print('  FAIL', k, GATES[k]['detail'])
print('core annualized', ARITH['core_mom_rounded_annualized_pct'], '| yields bp', CHG)
print('nasdaq', {k: IXIC[k] for k in ('open_vs_prev_pct', 'low_vs_prev_pct', 'close_vs_prev_pct')})
print('inflation tests', REGIME['inflation_hot_count_before'], '->', REGIME['inflation_hot_count_after'],
      '| exposure', {g: e['pct'] for g, e in EXPO.items()})
sys.exit(1 if failed else 0)
