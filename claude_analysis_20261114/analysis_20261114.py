#!/usr/bin/env python3
"""Claude analysis 2026-11-14 (prices through the 2026-11-13 close).

1) Re-verify GPT's review inputs with independent code (raw Yahoo JSON -> prices -> CSV,
   cross-check against Claude's frozen 11/13 browser statistics and correlation matrix).
2) Re-implement GPT's unified quarterly method with a different algorithm and reproduce its paths.
3) NVDA "standing" diagnostics: factor model, event study around the CEO transition,
   share-shift partial correlations, rolling idiosyncratic share.
4) Issuer look-through (VTI drifted from the 2026-09-30 factsheet weights) and issuer-level risk.
5) A no-leverage "AI breadth + moderated NVDA" family, calibrated iso-risk to GPT's two plans.
6) Unified evaluation + transparent scenarios. 7) Corrected implied-growth timing.

Historical and scenario numbers only: no forward-return estimate anywhere.
Run:  python3 -I claude_analysis_20261114/analysis_20261114.py <repo_root>
"""
import sys, json, math, hashlib, datetime, zoneinfo
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize

ROOT = Path(sys.argv[1]).resolve()
GPT = ROOT / 'gpt_review_20261113'
OLD = ROOT / 'claude_analysis_20261113'
HERE = ROOT / 'claude_analysis_20261114'
OUT = HERE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
S = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(obj, name):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=float) + '\n')


# ---------------------------------------------------------------- 0. raw JSON -> prices
man = json.loads((GPT / 'MANIFEST_SHA256.json').read_text())
TICK = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN', 'BTAL', 'XLP', 'KO', 'JNJ',
        'XOM', 'VTI', 'SGOV', 'BRK-B', 'XLV', 'SPY', 'BIL', 'SMH']
cols = {}
for t in TICK:
    p = GPT / 'data_audit' / 'raw' / f'{t}.json'
    assert man[f'data_audit/raw/{t}.json'] == sha(p), f'raw hash mismatch {t}'
    d = json.loads(p.read_text())['chart']['result'][0]
    assert d['meta']['currency'] == 'USD' and d['meta']['symbol'] == t
    tz = zoneinfo.ZoneInfo(d['meta']['exchangeTimezoneName'])
    dates = [datetime.datetime.fromtimestamp(x, tz).date().isoformat() for x in d['timestamp']]
    s = pd.Series(d['indicators']['adjclose'][0]['adjclose'], index=pd.to_datetime(dates), dtype=float)
    assert s.index.is_unique and s.notna().all() and (s > 0).all(), t
    cols[t] = s
P = pd.concat(cols, axis=1).dropna().loc['2021-11-15':'2026-11-13']
G = pd.read_csv(GPT / 'data_audit' / 'adjusted_close.csv', index_col=0, parse_dates=True)
assert P.index.equals(G.index) and set(G.columns) == set(TICK)
S['prices'] = dict(
    n_dates=len(P), start=str(P.index[0].date()), end=str(P.index[-1].date()), n_assets=P.shape[1],
    raw_json_sha256_match_gpt_manifest=True,
    max_rel_diff_raw_vs_gpt_csv=float((P[G.columns] / G - 1).abs().max().max()),
    gpt_csv_sha256=sha(GPT / 'data_audit' / 'adjusted_close.csv'))
P = P[TICK]
R = P.pct_change().iloc[1:]
LR = np.log(P).diff().iloc[1:]
W3 = ('2023-11-13', '2026-11-13')
R3 = R.loc['2023-11-14':'2026-11-13']
assert len(R3) == 753

# ---------------------------------------------------------------- 1. cross-check vs Claude frozen 11/13
st = pd.read_csv(OLD / 'data' / 'stats_daily.csv').set_index('t')
L3 = LR.loc['2023-11-14':'2026-11-13']
px = lambda t, d: P.loc[d, t]
rows = []
for t in [x for x in TICK if x in st.index]:
    rec = dict(t=t, vol=L3[t].std(ddof=1) * np.sqrt(252),
               r22=px(t, '2022-10-12') / px(t, '2022-01-03') - 1,
               rE1=px(t, '2026-11-05') / px(t, '2026-11-03') - 1,
               rE2=px(t, '2026-11-13') / px(t, '2026-11-03') - 1,
               rOct6=px(t, '2026-11-13') / px(t, '2026-10-06') - 1,
               cNVDA=L3[t].corr(L3['NVDA']))
    for k in ['vol', 'r22', 'rE1', 'rE2', 'rOct6', 'cNVDA']:
        rec[k + '_frozen'] = float(st.loc[t, k])
        rec[k + '_absdiff'] = abs(rec[k] - float(st.loc[t, k]))
    rows.append(rec)
XC = pd.DataFrame(rows)
XC.to_csv(OUT / 'crosscheck_frozen_stats.csv', index=False)
tol = dict(vol=5.0001e-4, r22=5.0001e-4, rE1=5.0001e-4, rE2=5.0001e-4, rOct6=5.0001e-4, cNVDA=5.0001e-3)
fails = {k: XC.loc[XC[k + '_absdiff'] > v, 't'].tolist() for k, v in tol.items()}
Lm = (OLD / 'data' / 'matrix_block.txt').read_text().rstrip('\n').split('\n')
mt = Lm[0].split(' ', 1)[1].split(',')
Cm = np.eye(len(mt))
for i in range(1, len(mt)):
    v = list(map(float, Lm[4 + i].split(',')))
    Cm[i, :i] = v
    Cm[:i, i] = v
Cm = pd.DataFrame(Cm, index=mt, columns=mt)
volm = pd.Series(list(map(float, Lm[2].split(' ', 1)[1].split(','))), index=mt)
ov = [t for t in TICK if t in mt]
Cr = L3[ov].corr()
cdiff = (Cr - Cm.loc[ov, ov]).abs().to_numpy()[np.triu_indices(len(ov), 1)]
vdiff = (L3[ov].std(ddof=1) * np.sqrt(252) - volm[ov]).abs()
vdiff0 = (L3[ov].std(ddof=0) * np.sqrt(252) - volm[ov]).abs()
S['crosscheck_frozen'] = dict(
    overlap_assets=len(XC), displayed_precision_failures=fails,
    max_absdiff={k: float(XC[k + '_absdiff'].max()) for k in tol},
    corr_matrix_pairs=int(len(cdiff)), corr_matrix_max_absdiff=float(cdiff.max()),
    corr_pairs_within_rounding=int((cdiff <= 5.0001e-4).sum()),
    matrix_vol_line_vs_ddof1_max_absdiff=float(vdiff.max()),
    matrix_vol_line_vs_ddof0_max_absdiff=float(vdiff0.max()),
    note='matrix_block VOL/LW use 1/T (ddof=0); stats_daily vol uses 1/(T-1); both reproduced')


# ---------------------------------------------------------------- 2. unified quarterly engine
def nav(w, start, end, rule='quarterly'):
    names = list(w)
    z = P.loc[start:end, names]
    assert str(z.index[0].date()) == start and str(z.index[-1].date()) == end, (start, end)
    wv = np.array([w[k] for k in names], float)
    assert abs(wv.sum() - 1) < 1e-9 and (wv >= -1e-12).all()
    if rule == 'buy_hold':
        anchors = [0]
    else:
        per = z.index.to_period('Q' if rule == 'quarterly' else 'M')
        anchors = sorted({0} | {i - 1 for i in range(1, len(z)) if per[i] != per[i - 1]})
    anchors = anchors + [len(z) - 1]
    zv = z.to_numpy()
    v = np.empty(len(z))
    v[0] = 1.0
    for a, b in zip(anchors[:-1], anchors[1:]):
        if b > a:
            v[a:b + 1] = v[a] * ((zv[a:b + 1] / zv[a]) @ wv)
    return pd.Series(v, index=z.index)


def metrics(v):
    r = v.pct_change().iloc[1:]
    n = len(r)
    return dict(n=n, cum=float(v.iloc[-1] - 1), vol=float(r.std(ddof=1) * np.sqrt(252)) if n > 1 else float('nan'),
                mdd=float((v / v.cummax() - 1).min()), es5=float(r.nsmallest(math.ceil(0.05 * n)).mean()),
                worst=float(r.min()))


GW = json.loads((GPT / 'review_results' / 'weights.json').read_text())
gnav = pd.read_csv(GPT / 'review_results' / 'quarterly_nav_three_year.csv', index_col=0, parse_dates=True)
gm = pd.read_csv(GPT / 'review_results' / 'metrics.csv')
gwin = json.loads((GPT / 'review_results' / 'methodology.json').read_text())['windows']
navdiff = max(float((nav(w, *W3) - gnav[k]).abs().max()) for k, w in GW.items())
mrows = []
for _, row in gm[gm.rule.isin(['quarterly', 'buy_hold', 'monthly'])].iterrows():
    m = metrics(nav(GW[row.portfolio], *gwin[row.window], row.rule))
    mrows.append(max(abs(m['cum'] - row.cumulative_return), abs(m['mdd'] - row.max_drawdown),
                     abs(m['es5'] - row.es95_daily),
                     0 if math.isnan(m['vol']) else abs(m['vol'] - row.realized_vol)))
S['engine_vs_gpt'] = dict(portfolios=len(GW), nav_three_year_max_absdiff=navdiff,
                          metric_rows_compared=len(mrows), metric_max_absdiff=float(max(mrows)),
                          algorithm='segment-wise price relatives (Claude) vs daily holdings loop (GPT)')

# ---------------------------------------------------------------- 3. NVDA standing diagnostics
AI7 = ['TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
AI8 = ['NVDA'] + AI7
ew = lambda names: R[names].mean(axis=1)
AIx7 = ew(AI7)
AIx8 = ew(AI8)


def per_ret(series_r, a, b):
    return float((1 + series_r.loc[a:b].iloc[1:]).prod() - 1)


PERIODS = {'2024': ('2023-12-29', '2024-12-31'), '2025': ('2024-12-31', '2025-12-31'),
           '2026ytd': ('2025-12-31', '2026-11-13'), 'three_year': W3,
           'oct6_to_nov3': ('2026-10-06', '2026-11-03'), 'election_2d': ('2026-11-03', '2026-11-05'),
           'scandal_nov6_13': ('2026-11-06', '2026-11-13'), 'resign_nov11_13': ('2026-11-11', '2026-11-13')}
prow = []
for name, (a, b) in PERIODS.items():
    rec = dict(period=name, start=a, end=b, AIx7_EW=per_ret(AIx7, a, b))
    for t in ['NVDA'] + AI7 + ['SMH', 'VTI']:
        rec[t] = float(px(t, b) / px(t, a) - 1)
    prow.append(rec)
PT = pd.DataFrame(prow)
PT.to_csv(OUT / 'nvda_relative_performance.csv', index=False)
ewin = P.loc['2026-10-26':'2026-11-13', AI8 + ['SMH', 'VTI']].copy()
ewin['AIx7_EW'] = (1 + AIx7.loc['2026-10-27':'2026-11-13']).cumprod().reindex(ewin.index).fillna(1.0)
(ewin / ewin.loc['2026-11-03']).to_csv(OUT / 'event_window_index_nov3eq1.csv', index_label='Date')
n26 = P.loc['2026-01-01':, 'NVDA']
S['nvda_price'] = dict(close_2026_11_13=float(P.loc['2026-11-13', 'NVDA']),
                       high_2026=float(n26.max()), high_2026_date=str(n26.idxmax().date()),
                       drawdown_from_2026_high=float(n26.iloc[-1] / n26.max() - 1),
                       daily_nov=dict((str(d.date()), float(x)) for d, x in R.loc['2026-11-02':'2026-11-13', 'NVDA'].items()))


def ols(y, X):
    A = np.column_stack([np.ones(len(X)), X.to_numpy()])
    coef, *_ = np.linalg.lstsq(A, y.to_numpy(), rcond=None)
    res = y.to_numpy() - A @ coef
    return coef, res, 1 - res.var() / y.to_numpy().var()


EST = ('2023-11-14', '2026-10-30')   # ends before the 11/3 election: event days are out-of-estimation
EV = R.loc['2026-11-04':'2026-11-13'].index
CARW = {'election_11_04_05': ('2026-11-04', '2026-11-05'), 'scandal_11_09_13': ('2026-11-09', '2026-11-13'),
        'resign_11_12_13': ('2026-11-12', '2026-11-13')}
ev_rows, ar_daily = [], {}
for t in AI8:
    F = AIx7 if t == 'NVDA' else ew([x for x in AI7 if x != t])
    X = pd.concat([R['VTI'], F], axis=1)
    coef, res, r2 = ols(R.loc[EST[0]:EST[1], t], X.loc[EST[0]:EST[1]])
    sd = res.std(ddof=3)
    ar = R.loc[EV, t] - (coef[0] + X.loc[EV].to_numpy() @ coef[1:])
    ar_daily[t] = ar
    rec = dict(t=t, beta_VTI=coef[1], beta_AIfactor=coef[2], r2=r2, resid_vol_ann=sd * np.sqrt(252))
    for k, (a, b) in CARW.items():
        seg = ar.loc[a:b]
        rec['CAR_' + k] = float(seg.sum())
        rec['t_' + k] = float(seg.sum() / (sd * np.sqrt(len(seg))))
        rec['raw_' + k] = float((1 + R.loc[a:b, t]).prod() - 1)
        rec['factor_' + k] = float((1 + F.loc[a:b]).prod() - 1)
    ev_rows.append(rec)
EVT = pd.DataFrame(ev_rows)
EVT.to_csv(OUT / 'event_study_ai8.csv', index=False)
pd.DataFrame(ar_daily).to_csv(OUT / 'event_study_daily_AR.csv', index_label='Date')

ss_rows = []
for j in AI7:
    F = ew([x for x in AI7 if x != j])
    for win, (a, b) in {'pre_event': EST, 'three_year': ('2023-11-14', '2026-11-13')}.items():
        X = pd.concat([R['VTI'], F], axis=1).loc[a:b]
        _, eN, _ = ols(R.loc[a:b, 'NVDA'], X)
        _, ej, _ = ols(R.loc[a:b, j], X)
        eN, ej = pd.Series(eN, X.index), pd.Series(ej, X.index)
        lo, hi = eN <= eN.quantile(0.10), eN >= eN.quantile(0.90)
        lam, sxx, syy, sxy = 0.97, *(np.cov(eN.iloc[:60], ej.iloc[:60]).ravel()[[0, 3, 1]])
        for x, y in zip(eN.iloc[60:], ej.iloc[60:]):
            sxx, syy, sxy = lam * sxx + (1 - lam) * x * x, lam * syy + (1 - lam) * y * y, lam * sxy + (1 - lam) * x * y
        ss_rows.append(dict(t=j, window=win, n=len(eN), partial_corr=float(eN.corr(ej)),
                            partial_corr_ewma_end=float(sxy / np.sqrt(sxx * syy)),
                            mean_resid_on_NVDA_worst10pct_bp=float(ej[lo].mean() * 1e4),
                            share_positive_on_NVDA_worst10pct=float((ej[lo] > 0).mean()),
                            mean_resid_on_NVDA_best10pct_bp=float(ej[hi].mean() * 1e4)))
SS = pd.DataFrame(ss_rows)
SS.to_csv(OUT / 'share_shift_partial_corr.csv', index=False)

coef3, res3, r23 = ols(R3['NVDA'], pd.concat([R3['VTI'], AIx7.loc[R3.index]], axis=1))
roll = []
Xall = pd.concat([R['VTI'], AIx7], axis=1).loc['2023-11-14':'2026-11-13']
yall = R.loc['2023-11-14':'2026-11-13', 'NVDA']
for i in range(126, len(yall) + 1):
    c, e, r2 = ols(yall.iloc[i - 126:i], Xall.iloc[i - 126:i])
    roll.append(dict(Date=str(yall.index[i - 1].date()), r2=r2, idio_share=1 - r2,
                     resid_vol_ann=float(e.std(ddof=3) * np.sqrt(252)), beta_AIx7=float(c[2]), beta_VTI=float(c[1])))
ROLL = pd.DataFrame(roll)
ROLL.to_csv(OUT / 'nvda_rolling126_factor.csv', index=False)
S['nvda_factor_model'] = dict(
    three_year=dict(beta_VTI=float(coef3[1]), beta_AIx7=float(coef3[2]), r2=float(r23),
                    resid_vol_ann=float(res3.std(ddof=3) * np.sqrt(252)),
                    total_vol_ann=float(R3['NVDA'].std(ddof=1) * np.sqrt(252))),
    rolling126_last=ROLL.iloc[-1].to_dict(),
    rolling126_idio_share_median=float(ROLL.idio_share.median()),
    rolling126_idio_share_max=float(ROLL.idio_share.max()),
    rolling126_idio_share_max_date=ROLL.loc[ROLL.idio_share.idxmax(), 'Date'])

# ---------------------------------------------------------------- 4. issuer look-through
# VTI 2026-09-30 factsheet weights as transcribed in GPT REVIEW_ZH.txt section 5 (Vanguard F0970);
# Claude could not re-open that PDF this round. 2026-06-30 Vanguard FS970R snippet used as sensitivity.
VTI_0930 = pd.Series({'NVDA': .071, 'MSFT': .052, 'GOOGL': .049, 'AMZN': .033, 'AVGO': .023, 'META': .022, 'MU': .016})
VTI_0630 = pd.Series({'NVDA': .064, 'GOOGL': .052, 'MSFT': .038})
k7 = list(VTI_0930.index)
rel = (P[k7] / P.loc['2026-09-30', k7]).div(P['VTI'] / P.loc['2026-09-30', 'VTI'], axis=0)
OM = rel.mul(VTI_0930, axis=1)          # drifted constituent weights (price-relative approximation)
om_now = OM.loc['2026-11-13']
omp = OM.shift(1).loc[R.index]
R_rest = (R['VTI'] - (omp * R[k7]).sum(axis=1)) / (1 - omp.sum(axis=1))
RI = R.copy()
RI['VTI_rest'] = R_rest
RI3 = RI.loc['2023-11-14':'2026-11-13'].drop(columns=['VTI']).dropna()
SIG_I = RI3.cov() * 252
SIG_A = R3.cov() * 252
S['vti_lookthrough'] = dict(weights_2026_09_30=VTI_0930.to_dict(), drifted_2026_11_13=om_now.to_dict(),
                            sum_ai7_in_vti_now=float(om_now.sum()), sensitivity_2026_06_30=VTI_0630.to_dict(),
                            rest_corr_with_vti=float(R_rest.loc[R3.index].corr(R3['VTI'])))


def issuers(w):
    e = {}
    for k, v in w.items():
        if k == 'VTI':
            for kk, o in om_now.items():
                e[kk] = e.get(kk, 0) + v * o
            e['VTI_rest'] = e.get('VTI_rest', 0) + v * (1 - om_now.sum())
        else:
            e[k] = e.get(k, 0) + v
    return e


def risk_profile(w):
    e = pd.Series(issuers(w)).reindex(SIG_I.index, fill_value=0.0)
    cv = SIG_I @ e
    var = float(e @ cv)
    rc = e * cv / var
    wa = pd.Series(w).reindex(SIG_A.index, fill_value=0.0)
    rp = R3 @ wa
    rc_sec = wa * (SIG_A @ wa) / float(wa @ SIG_A @ wa)
    beta = lambda f: float(rp.cov(f.loc[R3.index]) / f.loc[R3.index].var())
    return dict(
        nvda_lt=float(e['NVDA']), ai8_lt=float(e[AI8].sum()), direct_ai8=float(sum(w.get(k, 0) for k in AI8)),
        max_other_ai_lt=float(e[AI7].max()), max_other_ai_name=str(e[AI7].idxmax()),
        n_ai_issuers_ge3pct=int((e[AI8] >= 0.03).sum()),
        rc_nvda_issuer=float(rc['NVDA']), rc_ai8_issuer=float(rc[AI8].sum()),
        rc_nvda_direct_security=float(rc_sec['NVDA']), enb_issuer=float(1 / (rc[rc > 0] ** 2).sum()),
        vol_fixed_target=float(np.sqrt(var)), beta_AIx8=beta(AIx8), beta_VTI=beta(R['VTI']),
        scen_nvda_idio_minus30=-0.30 * float(e['NVDA']), scen_ai8_minus30_mechanical=-0.30 * float(e[AI8].sum()),
        scen_ai_factor_minus30_beta=-0.30 * beta(AIx8))


# ---------------------------------------------------------------- 5. hybrid family
def erc(Sig):
    n = len(Sig)
    b = np.full(n, 1 / n)
    res = minimize(lambda x: 0.5 * x @ Sig @ x - b @ np.log(x), 1 / np.sqrt(np.diag(Sig)),
                   jac=lambda x: Sig @ x - b / x, method='L-BFGS-B', bounds=[(1e-10, None)] * n,
                   options=dict(ftol=1e-15, gtol=1e-13, maxiter=20000))
    w = res.x / res.x.sum()
    return w, w * (Sig @ w) / (w @ Sig @ w)


w7, rc7 = erc(R3[AI7].cov().to_numpy() * 252)
ERC7 = dict(zip(AI7, w7))
DEF = {'BRK-B': 0.40, 'XLV': 0.20, 'SGOV': 0.40}
V0, NV0 = 0.25, 0.10


def hybrid(A, V=V0, nv=NV0, base=None):
    base = ERC7 if base is None else base
    D = 1 - V - A
    w = {'VTI': V, 'NVDA': nv, **{k: (A - nv) * x for k, x in base.items()}, **{k: D * x for k, x in DEF.items()}}
    return {k: v for k, v in w.items() if v > 1e-12}


vol3 = lambda w: metrics(nav(w, *W3))['vol']


def calibrate(target, V=V0, nv=NV0):
    lo, hi = nv + 0.05, 1 - V - 0.125
    f = lambda A: vol3(hybrid(A, V, nv)) - target
    if f(lo) > 0 or f(hi) < 0:
        return float('nan')
    return brentq(f, lo, hi, xtol=1e-10)


def rounded(w, ai7_total=None):
    """Whole-percent weights that keep each sleeve total: largest remainder within sleeve."""
    sleeves = [['VTI'], ['NVDA'], AI7, list(DEF)]
    tot = [round(100 * sum(w.get(k, 0) for k in sl)) for sl in sleeves[:3]]
    if ai7_total is not None:
        tot[2] = ai7_total
    tot.append(100 - sum(tot))
    out = {}
    for sl, T in zip(sleeves, tot):
        raw = np.array([100 * w.get(k, 0) for k in sl])
        raw = raw * (T / raw.sum()) if raw.sum() > 0 else raw
        fl = np.floor(raw + 1e-9)
        for i in np.argsort(-(raw - fl), kind='stable')[:int(T - fl.sum())]:
            fl[i] += 1
        out.update({k: v / 100 for k, v in zip(sl, fl) if v > 0})
    assert abs(sum(out.values()) - 1) < 1e-9
    return out


T_CONV = metrics(nav(GW['conviction8'], *W3))['vol']
T_ENTRY = metrics(nav(GW['entry'], *W3))['vol']
def rounded_cal(w, target, volf=None):
    """Integer AI7 sleeve total (floor/ceil of exact) whose rounded portfolio is closest to the target vol."""
    volf = vol3 if volf is None else volf
    a = 100 * sum(w.get(k, 0) for k in AI7)
    c = [(abs(volf(rounded(w, T)) - target), T) for T in sorted({math.floor(a), math.ceil(a)})]
    return rounded(w, min(c)[1])


T_CL = metrics(nav(GW['Claude'], *W3))['vol']
A_core, A_lite, A_plus = calibrate(T_CONV), calibrate(T_ENTRY), calibrate(T_CL)
H_core_exact, H_lite_exact, H_plus_exact = hybrid(A_core), hybrid(A_lite), hybrid(A_plus)
H_core, H_lite, H_plus = (rounded_cal(H_core_exact, T_CONV), rounded_cal(H_lite_exact, T_ENTRY),
                          rounded_cal(H_plus_exact, T_CL))
H_core, H_lite, H_plus = ({k: float(v) for k, v in h.items()} for h in (H_core, H_lite, H_plus))
S['construction'] = dict(
    rule='VTI 25%; NVDA direct 10%; other 7 AI names split by equal risk contribution (3y simple-return '
         'covariance); remainder BRK-B/XLV/SGOV = 40/20/40; AI sleeve size A solved so 3y quarterly realized '
         'vol equals the GPT plan it is compared with; weights rounded to whole percent, residual to SGOV.',
    erc7_weights=ERC7, erc7_risk_contrib=dict(zip(AI7, rc7)),
    target_vol_conviction8=T_CONV, target_vol_entry=T_ENTRY, target_vol_claude1113=T_CL,
    A_core=A_core, A_lite=A_lite, A_plus=A_plus,
    H_core_exact=H_core_exact, H_lite_exact=H_lite_exact, H_plus_exact=H_plus_exact,
    H_core=H_core, H_lite=H_lite, H_plus=H_plus,
    dollars_7000={k: {t: round(7000 * v) for t, v in w.items()} for k, w in
                  {'Hybrid_Lite': H_lite, 'Hybrid_Core': H_core, 'Hybrid_Plus': H_plus}.items()})

# construction-rule holdout: ERC + calibration from 2023-11-14..2025-11-13 only, evaluated on the last year
Rh = R.loc['2023-11-14':'2025-11-13']
wh, _ = erc(Rh[AI7].cov().to_numpy() * 252)
ERC7h = dict(zip(AI7, wh))
vh = lambda w: metrics(nav(w, '2023-11-13', '2025-11-13'))['vol']
tc_h = vh(GW['conviction8'])
Ah = brentq(lambda A: vh(hybrid(A, base=ERC7h)) - tc_h, NV0 + 0.05, 1 - V0 - 0.125, xtol=1e-10)
Hh = {k: float(v) for k, v in rounded_cal(hybrid(Ah, base=ERC7h), tc_h, vh).items()}
last = ('2025-11-13', '2026-11-13')
S['holdout_rule_check'] = dict(
    fit_window='2023-11-13..2025-11-13', eval_window='2025-11-13..2026-11-13', A_fit=Ah, weights=Hh,
    eval={k: metrics(nav(w, *last)) for k, w in
          {'Hybrid_Core_holdout_rule': Hh, 'Hybrid_Core_full': H_core, 'conviction8': GW['conviction8'],
           'entry': GW['entry'], 'Claude_1113': GW['Claude']}.items()})

# ---------------------------------------------------------------- 6. unified evaluation
PORTS = {'conviction8': GW['conviction8'], 'entry': GW['entry'], 'Claude_1113': GW['Claude'],
         'Hybrid_Lite': H_lite, 'Hybrid_Core': H_core, 'Hybrid_Plus': H_plus, 'VTI': {'VTI': 1.0}}
REF = {'Hybrid_Core_BTAL5_ref': {**H_core, 'SGOV': round(H_core['SGOV'] - 0.05, 10), 'BTAL': 0.05}}
WIN = {'three_year': W3, 'stress2022': ('2022-01-03', '2022-10-12'), 'election_2d': ('2026-11-03', '2026-11-05'),
       'scandal_nov6_13': ('2026-11-06', '2026-11-13'), 'resign_nov11_13': ('2026-11-11', '2026-11-13'),
       'drawdown_oct6_nov13': ('2026-10-06', '2026-11-13'), 'risk_rebound': ('2025-06-30', '2026-06-30'),
       '2024': ('2023-12-29', '2024-12-31'), '2025': ('2024-12-31', '2025-12-31'), '2026ytd': ('2025-12-31', '2026-11-13')}
ev_rows = []
for name, w in {**PORTS, **REF}.items():
    for wn, (a, b) in WIN.items():
        ev_rows.append(dict(portfolio=name, window=wn, **metrics(nav(w, a, b))))
EVAL = pd.DataFrame(ev_rows)
EVAL.to_csv(OUT / 'unified_quarterly_metrics.csv', index=False)
RP = pd.DataFrame({k: risk_profile(w) for k, w in {**PORTS, **REF}.items()}).T
RP.to_csv(OUT / 'risk_profile_issuer_level.csv', index_label='portfolio')
S['weights'] = {k: w for k, w in {**PORTS, **REF}.items()}

grid = []
for nv in [0.05, 0.075, 0.10, 0.125, 0.15]:
    for A in [0.40, 0.45, 0.50, 0.55, 0.60, 0.625]:
        w = hybrid(A, nv=nv)
        m3, m22, msc = metrics(nav(w, *W3)), metrics(nav(w, *WIN['stress2022'])), metrics(nav(w, *WIN['scandal_nov6_13']))
        rp = risk_profile(w)
        grid.append(dict(nvda_direct=nv, A=A, vol3=m3['vol'], mdd3=m3['mdd'], es5=m3['es5'], stress2022=m22['cum'],
                         scandal=msc['cum'], nvda_lt=rp['nvda_lt'], ai8_lt=rp['ai8_lt'], rc_nvda=rp['rc_nvda_issuer'],
                         scen_nvda_idio=rp['scen_nvda_idio_minus30']))
pd.DataFrame(grid).to_csv(OUT / 'hybrid_dial_grid.csv', index=False)

# NVDA dial at iso-risk (conviction8 vol): how much AI breadth each NVDA level leaves room for
iso = []
for nv in [0.05, 0.075, 0.10, 0.125, 0.15]:
    A = calibrate(T_CONV, nv=nv)
    w = hybrid(A, nv=nv)
    rp = risk_profile(w)
    iso.append(dict(nvda_direct=nv, A=A, ai7_direct=A - nv, nvda_lt=rp['nvda_lt'], ai8_lt=rp['ai8_lt'],
                    rc_nvda=rp['rc_nvda_issuer'], stress2022=metrics(nav(w, *WIN['stress2022']))['cum'],
                    scandal=metrics(nav(w, *WIN['scandal_nov6_13']))['cum'],
                    scen_nvda_idio=rp['scen_nvda_idio_minus30']))
pd.DataFrame(iso).to_csv(OUT / 'nvda_dial_iso_risk.csv', index=False)

# paired stationary block bootstrap of 3y vol differences (same design as GPT; seed differs)
paths = pd.DataFrame({k: nav(w, *W3) for k, w in PORTS.items()}).pct_change().iloc[1:]
RR = paths.to_numpy()
names = list(paths.columns)
gen = np.random.default_rng(20261114)
pairs = [('Hybrid_Core', 'conviction8'), ('Hybrid_Lite', 'entry'), ('Hybrid_Plus', 'Claude_1113'), ('Hybrid_Core', 'entry')]
draws = {p: [] for p in pairs}
n = len(RR)
for _ in range(2000):
    idx = np.empty(n, dtype=int)
    idx[0] = gen.integers(n)
    restart = gen.random(n) < 1 / 20
    starts = gen.integers(n, size=n)
    for t in range(1, n):
        idx[t] = starts[t] if restart[t] else (idx[t - 1] + 1) % n
    sv = RR[idx].std(axis=0, ddof=1) * np.sqrt(252)
    for a, b in pairs:
        draws[(a, b)].append(sv[names.index(a)] - sv[names.index(b)])
S['bootstrap_vol_diff'] = [dict(a=a, b=b, estimate=float((RR[:, names.index(a)].std(ddof=1) - RR[:, names.index(b)].std(ddof=1)) * np.sqrt(252)),
                                lo=float(np.quantile(d, .025)), hi=float(np.quantile(d, .975)), n_boot=2000, mean_block=20)
                           for (a, b), d in draws.items()]

# ---------------------------------------------------------------- 7. implied-growth timing correction
val = pd.read_csv(OLD / 'out_valuation.csv').set_index('t')


def solve_g(m, r, first_exp, gT=0.03):
    f = lambda g: sum((1 + g) ** (t - 1 + first_exp) / (1 + r) ** t for t in range(1, 11)) + \
        (1 + g) ** (9 + first_exp) * (1 + gT) / ((r - gT) * (1 + r) ** 10) - m
    try:
        return brentq(f, -0.5, 1.5)
    except ValueError:
        return float('nan')


vr = []
for t, row in val.iterrows():
    if not (row.fwdPE > 0):
        continue
    g_old, g_new = solve_g(row.fwdPE, row.r_capm, 1), solve_g(row.fwdPE, row.r_capm, 0)
    vr.append(dict(t=t, price=row.price, fwdPE=row.fwdPE, r_capm=row.r_capm, g_EPS_frozen=row.g_implied_E,
                   g_EPS_recomputed_old_timing=g_old, g_EPS_corrected_timing=g_new, g_TTM_FCF=row.g_implied_FCF,
                   fcf_to_ni=row.fcf_to_ni, ni_to_opinc=row.ni_to_opinc,
                   tilt_old=bool(0 <= g_old <= 0.10 and row.fcf_to_ni >= 0.5),
                   tilt_corrected=bool(0 <= g_new <= 0.10 and row.fcf_to_ni >= 0.5)))
VR = pd.DataFrame(vr)
VR.to_csv(OUT / 'valuation_timing_corrected.csv', index=False)
S['valuation'] = dict(max_abs_diff_old_timing_vs_frozen=float((VR.g_EPS_recomputed_old_timing - VR.g_EPS_frozen).abs().max()),
                      tilt_old=VR.loc[VR.tilt_old, 't'].tolist(), tilt_corrected=VR.loc[VR.tilt_corrected, 't'].tolist(),
                      NVDA=VR.set_index('t').loc['NVDA'].to_dict(), TSM=VR.set_index('t').loc['TSM'].to_dict())

S['inputs_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in
                      [GPT / 'MANIFEST_SHA256.json', GPT / 'data_audit' / 'adjusted_close.csv', GPT / 'review_results' / 'weights.json',
                       GPT / 'review_results' / 'metrics.csv', GPT / 'review_results' / 'quarterly_nav_three_year.csv',
                       OLD / 'data' / 'stats_daily.csv', OLD / 'data' / 'matrix_block.txt', OLD / 'out_valuation.csv']}
jdump(S, 'summary.json')

pd.set_option('display.width', 220)
print(json.dumps({k: S[k] for k in ['prices', 'crosscheck_frozen', 'engine_vs_gpt']}, indent=1, default=float))
print('\nERC7', {k: round(float(v), 4) for k, v in ERC7.items()}, 'A', round(A_lite, 4), round(A_core, 4), round(A_plus, 4))
print('H_lite', H_lite, '\nH_core', H_core, '\nH_plus', H_plus)
print('\nEVENT STUDY\n', EVT.round(4).to_string(index=False))
print('\nSHARE SHIFT\n', SS.round(3).to_string(index=False))
print('\nPERIODS\n', PT.round(4).to_string(index=False))
piv = EVAL.pivot(index='portfolio', columns='window', values='cum')
print('\nCUM\n', piv.round(4).to_string())
print('\n3Y\n', EVAL[EVAL.window == 'three_year'].set_index('portfolio')[['cum', 'vol', 'mdd', 'es5']].round(4).to_string())
print('\nRISK\n', RP.drop(columns=['max_other_ai_name']).astype(float).round(4).T.to_string())
print('\nISO DIAL\n', pd.DataFrame(iso).round(4).to_string(index=False))
print('\nBOOT', json.dumps(S['bootstrap_vol_diff'], indent=1))
print('\nHOLDOUT', json.dumps(S['holdout_rule_check'], indent=1, default=float))
print('\nVAL\n', VR.round(4).to_string(index=False))
print('\nNVDA factor', json.dumps(S['nvda_factor_model'], indent=1, default=float), json.dumps(S['nvda_price'], indent=1))
