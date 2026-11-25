#!/usr/bin/env python3
"""Pre-entry check on 2026-11-25 (prices about 13:00 ET, intraday):
  A. rerun the 11/15 tilt rule (valuation x price position) at the latest prices;
  B. rule-based candlestick / trend status of each holding.
Run: python3 -I claude_analysis_20261125/entry_check_20261125.py <repo_root>
Reads data/ plus three files already on main (GPT price file through 11/13, the 11/15 timing table, the 11/14 ERC shares).
Nothing here estimates forward returns."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261125'
DATA, OUT = HERE / 'data', HERE / 'out'
OUT.mkdir(exist_ok=True)
GPT_CSV = ROOT / 'gpt_review_20261113' / 'data_audit' / 'adjusted_close.csv'
T15 = ROOT / 'claude_analysis_20261115' / 'out' / 'timing_table_ai8.csv'
H14 = ROOT / 'claude_analysis_20261114' / 'out' / 'summary.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
GATES = {}


def gate(name, ok, detail):
    GATES[name] = {'pass': bool(ok), 'detail': detail}


man = json.loads((ROOT / 'gpt_review_20261113' / 'MANIFEST_SHA256.json').read_text())
gate('gpt_price_file_hash', man['data_audit/adjusted_close.csv'] == sha(GPT_CSV), 'adjusted_close.csv matches GPT manifest')
P = pd.read_csv(GPT_CSV, index_col=0, parse_dates=True)
CH = json.loads((DATA / 'fmp_chart_20261125.json').read_text())['responses']
QP = json.loads((DATA / 'fmp_quotes_profiles_20261125.json').read_text())
WEB = json.loads((DATA / 'sources_web_20261125.json').read_text())
AI8 = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
HOLD = AI8 + ['VTI', 'BRK-B', 'XLV']
TODAY, PREV, D1120, D1123 = pd.Timestamp('2026-11-25'), pd.Timestamp('2026-11-24'), pd.Timestamp('2026-11-20'), pd.Timestamp('2026-11-23')

# ------------------------------------------------------------------ price series: GPT closes to 11/13, then newer rows
ohlc, closes, missing = {}, {}, {}
for t in HOLD:
    s = P[t].dropna().copy()
    if t in CH:
        df = pd.DataFrame(CH[t]).assign(date=lambda d: pd.to_datetime(d.date)).set_index('date').sort_index()
        ov = df.loc[:'2026-11-13', 'close']
        dev = float((ov / s.reindex(ov.index) - 1).abs().max())
        gate(f'fmp_vs_gpt_{t}', dev < 2e-4, f'max |FMP/GPT - 1| on {len(ov)} overlapping closes = {dev:.2e}')
        new = df.loc['2026-11-14':, 'close']
        ohlc[t] = df
    elif t in WEB:
        df = pd.DataFrame(WEB[t]['rows']).assign(date=lambda d: pd.to_datetime(d.date)).set_index('date').sort_index()
        ov = df.loc[:'2026-11-13', 'close']
        dev = float((ov / s.reindex(ov.index) - 1).abs().max())
        gate(f'web_vs_gpt_{t}', dev < 2e-4, f'max |web/GPT - 1| on {len(ov)} overlapping closes = {dev:.2e}')
        pr = QP['profiles'][t]
        new = pd.concat([df.loc['2026-11-14':, 'close'],
                         pd.Series({PREV: pr['price'] - pr['change'], TODAY: pr['price']})])
        ohlc[t] = df
    else:
        pr = QP['profiles'][t]
        new = pd.Series({PREV: pr['price'] - pr['change'], TODAY: pr['price']})
    s = pd.concat([s, new]).sort_index()
    closes[t] = s
    sessions = pd.bdate_range('2026-11-16', '2026-11-25')
    missing[t] = [str(d.date()) for d in sessions if d not in s.index]


def rsi(c, n=14):
    d = c.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    au, ad = up.ewm(alpha=1 / n, adjust=False).mean(), dn.ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + au.iloc[-1] / ad.iloc[-1]))


def macd_hist(c):
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    h = m - m.ewm(span=9, adjust=False).mean()
    return float(h.iloc[-1]), float(h.iloc[-2])


rows = []
for t in HOLD:
    s = closes[t]
    last, prev = float(s.loc[TODAY]), float(s.loc[PREV])
    hist = s.loc[:PREV]
    ma = {n: float(s.iloc[-n:].mean()) for n in (20, 50, 200)}
    hi52 = float(s.iloc[-252:].max())
    hi52_date = str(s.iloc[-252:].idxmax().date())
    low60_prior = float(hist.iloc[-60:].min())
    low60_prior_date = str(hist.iloc[-60:].idxmin().date())
    r = dict(t=t, last=last, prev_close=prev, day_pct=100 * (last / prev - 1), since_1113_pct=100 * (last / float(s.loc['2026-11-13']) - 1),
             ma20=ma[20], ma50=ma[50], ma200=ma[200], vs_ma200_pct=100 * (last / ma[200] - 1),
             hi52_close=hi52, hi52_date=hi52_date, dd_from_hi52_pct=100 * (last / hi52 - 1),
             low60_prior_close=low60_prior, low60_prior_date=low60_prior_date, missing_sessions=';'.join(missing[t]))
    complete = not missing[t]
    r['rsi14'] = rsi(s) if complete else np.nan
    if complete:
        h1, h0 = macd_hist(s)
        r['macd_hist'], r['macd_hist_prev'] = h1, h0
    else:
        r['macd_hist'] = r['macd_hist_prev'] = np.nan
    # trend and fresh-low tests
    r['T1_downtrend'] = last < ma[20] < ma[50]
    fresh = last < low60_prior
    if t in CH:
        df = ohlc[t]
        today = df.loc[TODAY]
        prior20_low = float(df.loc[:PREV, 'low'].iloc[-20:].min())
        r.update(open=float(today.open), high=float(today.high), low=float(today.low), prior20_low=prior20_low,
                 gap_open_pct=100 * (float(today.open) / prev - 1),
                 close_pos_in_range=(last - float(today.low)) / (float(today.high) - float(today.low)))
        fresh = fresh or float(today.low) < prior20_low
        body = last - float(today.open)
        lower = min(last, float(today.open)) - float(today.low)
        r['long_lower_shadow'] = lower >= 2 * abs(body) and r['close_pos_in_range'] >= 0.75
    elif t == 'AVGO':
        lo52 = float(QP['profiles'][t]['range'].split('-')[0])
        prior_intraday_low = float(ohlc[t]['low'].min())
        r['range_low_52w'] = lo52
        fresh = fresh or lo52 < prior_intraday_low
        r['note'] = f'52w range low {lo52} is below every intraday low through 11/20 (min {prior_intraday_low}): new low set after 11/20'
    r['T2_fresh_low'] = bool(fresh)
    if D1120 in s.index:
        reb = s.loc[D1123:PREV]
        top = float(reb.max()) if len(reb) else np.nan
        base = float(s.loc[D1120])
        r['rebound_retrace'] = (top - last) / (top - base) if top > base else np.nan
        r['below_1120_close'] = last < base
    else:
        r['rebound_retrace'] = np.nan
        r['below_1120_close'] = np.nan
    r['T3_failed_rebound'] = bool((r['rebound_retrace'] >= 0.618) if not np.isnan(r['rebound_retrace']) else (r['below_1120_close'] is True))
    r['T4_heavy_down_day'] = r['day_pct'] <= -4.0
    r['T5_higher_high'] = bool(D1120 in s.index and last > float(s.loc[D1120:PREV].max()))
    if r['T1_downtrend'] and (r['T2_fresh_low'] or r['T3_failed_rebound'] or r['T4_heavy_down_day']) and not r['T5_higher_high']:
        v = 'wait'
    elif not (r['T2_fresh_low'] or r['T3_failed_rebound'] or r['T4_heavy_down_day']) and (not r['T1_downtrend'] or r['T5_higher_high']):
        v = 'ok'
    else:
        v = 'watch'
    r['verdict'] = v
    rows.append(r)
K = pd.DataFrame(rows).set_index('t')
K.round(4).to_csv(OUT / 'kline_status.csv')
for t in ['NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSM']:
    q = QP['quotes'][t][0]
    dev = abs(K.loc[t, 'ma200'] / q['priceAvg200'] - 1)
    gate(f'ma200_vs_fmp_{t}', dev < 0.01, f'computed MA200 {K.loc[t, "ma200"]:.2f} vs FMP priceAvg200 {q["priceAvg200"]} ({100 * dev:.2f}%)')

# ------------------------------------------------------------------ A. tilt rule at latest prices (11/16 consensus EPS frozen)
TT = pd.read_csv(T15).set_index('t')
A = TT[['price', 'pe_ntm', 'ebit_op_yield', 'peg_fy3_vs_fy2', 'cyclical_peak_flag', 'value_bucket', 'price_bucket', 'action']].copy()
A.columns = ['price_1113', 'pe_1113', 'ebit_yield_1113', 'peg_1113', 'cyclical', 'value_1113', 'price_bucket_1113', 'action_1113']
A['price_now'] = [K.loc[t, 'last'] for t in A.index]
f = A.price_now / A.price_1113
A['pe_now'], A['ebit_yield_now'], A['peg_now'] = A.pe_1113 * f, A.ebit_yield_1113 / f, A.peg_1113 * f
nc = A[~A.cyclical.astype(bool)]
RK = pd.DataFrame({'rank_pe': nc.pe_now.rank(), 'rank_ebit': (-nc.ebit_yield_now).rank(), 'rank_peg': nc.peg_now.rank()})
A = A.join(RK)
A['value_score_now'] = RK.mean(axis=1)
A['value_now'] = pd.cut(A.value_score_now, [0, 3.0, 5.0, 8], labels=['cheap', 'mid', 'expensive']).astype(object)
A.loc[A.cyclical.astype(bool), 'value_now'] = 'cyclical-peak'
A['dd_now'] = [K.loc[t, 'dd_from_hi52_pct'] / 100 for t in A.index]
A['vs_ma200_now'] = [K.loc[t, 'vs_ma200_pct'] / 100 for t in A.index]
A['price_bucket_now'] = np.where((A.dd_now <= -0.20) & (A.vs_ma200_now < 0), 'relative-low',
                                 np.where((A.dd_now >= -0.10) & (A.vs_ma200_now > 0), 'relative-high', 'middle'))


def action(v, p):
    if v == 'cyclical-peak':
        return 'underweight (cycle-adjusted)'
    if v == 'cheap' and p == 'relative-low':
        return 'overweight'
    if v == 'expensive' and p == 'relative-high':
        return 'underweight'
    return 'at target (expensive, no add)' if v == 'expensive' else 'at target'


A['action_now'] = [action(v, p) for v, p in zip(A.value_now, A.price_bucket_now)]
A.round(4).to_csv(OUT / 'tilt_recheck.csv')

LT = {'VTI': .25, 'NVDA': .10, 'MSFT': .08, 'GOOGL': .07, 'AMZN': .06, 'META': .05, 'TSM': .04, 'AVGO': .04, 'MU': .03,
      'BRK-B': .11, 'XLV': .06, 'SGOV': .11}
PLAN = dict(LT, NVDA=.125, MSFT=.07, MU=.015)
ERC = json.loads(H14.read_text())['construction']['erc7_weights']
upd = dict(LT)
upd['MU'] = LT['MU'] - 0.015 if A.loc['MU', 'action_now'].startswith('underweight') else LT['MU']
upd['MSFT'] = LT['MSFT'] - 0.010 if A.loc['MSFT', 'action_now'].startswith('underweight') else LT['MSFT']
upd['NVDA'] = LT['NVDA'] + (LT['MU'] - upd['MU']) + (LT['MSFT'] - upd['MSFT']) if A.loc['NVDA', 'action_now'] == 'overweight' else LT['NVDA']
bis = dict(upd)
cut = upd['NVDA'] - 0.075
bis['NVDA'] = 0.075
for k, w in ERC.items():
    bis[k] = upd[k] + cut * w
ant = dict(bis, VTI=bis['VTI'] - 0.02, **{'BRK-B': bis['BRK-B'] - 0.01}, ANT=0.03)


def dollars(w, total=7000):
    raw = {k: total * v for k, v in w.items()}
    flo = {k: int(np.floor(v + 1e-9)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: (-(raw[k] - flo[k]), k))[:total - sum(flo.values())]:
        flo[k] += 1
    return flo


V = pd.DataFrame({'plan_1115': PLAN, 'rule_update_now': upd, 'update_plus_nvda_7_5': bis, 'update_plus_nvda_7_5_ant_3': ant}).fillna(0.0)
for c in list(V.columns):
    assert abs(V[c].sum() - 1) < 1e-9, c
    V[c + '_usd'] = pd.Series(dollars(V[c].to_dict()))
order = ['VTI', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSM', 'AVGO', 'MU', 'ANT', 'BRK-B', 'XLV', 'SGOV']
V = V.loc[order]
V.round(6).to_csv(OUT / 'weights_versions.csv', index_label='t')

if not all(g['pass'] for g in GATES.values()):
    print(json.dumps(GATES, indent=1))
    raise SystemExit('gate failure')
S = {'as_of': '2026-11-25 about 13:00 ET (intraday; candles for today are incomplete)', 'gates': GATES,
     'kline': {t: {k: (None if isinstance(v, float) and np.isnan(v) else (round(v, 4) if isinstance(v, float) else v))
                   for k, v in K.loc[t].items()} for t in K.index},
     'kline_verdicts': {v: list(K.index[K.verdict == v]) for v in ('wait', 'watch', 'ok')},
     'tilt_actions': {t: {'1113': A.loc[t, 'action_1113'], 'now': A.loc[t, 'action_now'], 'value_now': A.loc[t, 'value_now'],
                          'price_bucket_now': A.loc[t, 'price_bucket_now']} for t in A.index},
     'weights': {c: {t: round(float(V.loc[t, c]), 6) for t in V.index} for c in V.columns if not c.endswith('_usd')},
     'dollars': {c: {t: int(V.loc[t, c]) for t in V.index} for c in V.columns if c.endswith('_usd')},
     'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(DATA.glob('*.json')) + [GPT_CSV, T15, H14]}}
(OUT / 'summary.json').write_text(json.dumps(S, indent=1, ensure_ascii=False, sort_keys=True, default=str) + '\n')
pd.set_option('display.width', 250)
print(K[['last', 'day_pct', 'since_1113_pct', 'ma20', 'ma50', 'ma200', 'dd_from_hi52_pct', 'low60_prior_close', 'rsi14', 'rebound_retrace',
         'T1_downtrend', 'T2_fresh_low', 'T3_failed_rebound', 'T4_heavy_down_day', 'T5_higher_high', 'verdict', 'missing_sessions']].round(2).to_string())
print(K[['gap_open_pct', 'close_pos_in_range', 'long_lower_shadow', 'prior20_low', 'low']].round(3).to_string())
print(A[['price_now', 'pe_now', 'value_score_now', 'value_now', 'dd_now', 'vs_ma200_now', 'price_bucket_now', 'action_1113', 'action_now']].round(3).to_string())
print(V.round(4).to_string())
print({k: v['pass'] for k, v in GATES.items()})
