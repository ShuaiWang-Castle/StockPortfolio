"""Portfolio analysis: AI value chain vs hedges/diversifiers.
Data: Yahoo Finance chart API adjusted closes (2021-11-15..2026-11-13), statistics computed in-browser
(see data/meta.json for SHA-256 of raw data and of the transcribed blocks). Window for estimation:
753 daily log returns 2023-11-14..2026-11-13.
"""
import json
import numpy as np
import pandas as pd
import networkx as nx
from scipy.cluster.hierarchy import linkage, leaves_list, fcluster
from scipy.spatial.distance import squareform
from scipy.optimize import minimize, brentq

pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 40)
D = 'data/'

# ------------------------------------------------------------------ load
A = pd.read_csv(D + 'stats_daily.csv').set_index('t')
L = open(D + 'matrix_block.txt').read().rstrip('\n').split('\n')
tick = L[0].split(' ', 1)[1].split(',')
N = len(tick)
ix = {t: i for i, t in enumerate(tick)}
kv = dict(s.split('=') for s in L[1].split(' ')[1:])
delta, rbar, T = float(kv['delta']), float(kv['rbar']), int(kv['T'])
vol = np.array([float(x) for x in L[2].split(' ', 1)[1].split(',')])
meanlog = np.array([float(x) for x in L[3].split(' ', 1)[1].split(',')])
assert L[4] == 'CORR'
C = np.eye(N)
for i in range(1, N):
    v = [float(x) for x in L[4 + i].split(',')]
    assert len(v) == i
    C[i, :i] = v
    C[:i, i] = v
ewvol = np.array([float(x) for x in L[56].split(' ', 1)[1].split(',')])
rolldates = L[57].split(' ', 1)[1].split(',')
roll = {}
for s in L[58:]:
    _, name, vals = s.split(' ', 2)
    roll[name] = [float(x) for x in vals.split(',')]
assert list(A.index) == tick

# ------------------------------------------------------------------ gates
# (1) CORR columns must round to the independently computed 2-dp columns in stats table
for ref, col in [('NVDA', 'cNVDA'), ('SMH', 'cSMH'), ('SPY', 'cSPY')]:
    dev = np.abs(np.round(C[:, ix[ref]], 2) - A[col].values)
    assert dev.max() <= 0.0101, (ref, dev.max())
# (2) vols must agree with stats table
assert np.abs(np.round(vol, 3) - A['vol'].values).max() <= 0.0011
eig = np.linalg.eigvalsh(C)
print(f'gates ok | min eig(sample corr)={eig.min():.4f}  LW delta={delta}  rbar={rbar}  T={T}')

# ------------------------------------------------------------------ covariance
S = C * np.outer(vol, vol)
F = rbar * np.outer(vol, vol)
np.fill_diagonal(F, vol ** 2)
SIG = delta * F + (1 - delta) * S            # Ledoit-Wolf (2004) constant-correlation shrinkage, annualized
CL = SIG / np.outer(np.sqrt(np.diag(SIG)), np.sqrt(np.diag(SIG)))
print(f'min eig LW cov={np.linalg.eigvalsh(SIG).min():.2e}')

# ------------------------------------------------------------------ PCA / random matrix theory
ev, evec = np.linalg.eigh(C)
ev, evec = ev[::-1], evec[:, ::-1]
q = N / T
lam_plus = (1 + np.sqrt(q)) ** 2
n_sig = int((ev > lam_plus).sum())
pc = {f'PC{k+1}': evec[:, k] * np.sign(evec[ix['SPY'], k] if k == 0 else evec[ix['NVDA'], k]) for k in range(3)}
pca_info = dict(lam=ev[:6].round(3).tolist(), share=(ev[:6] / N).round(3).tolist(), lam_plus=round(lam_plus, 3), n_sig=n_sig)
print('PCA', pca_info)
pc2 = pd.Series(pc['PC2'], index=tick).sort_values()
print('PC2 most negative:', pc2.head(8).round(2).to_dict())
print('PC2 most positive:', pc2.tail(8).round(2).to_dict())

# ------------------------------------------------------------------ clustering + MST (Mantegna distance)
Dm = np.sqrt(np.clip(2 * (1 - C), 0, None))
np.fill_diagonal(Dm, 0)
Z = linkage(squareform(Dm, checks=False), method='average')
order = leaves_list(Z)
clusters = fcluster(Z, t=7, criterion='maxclust')
clus = pd.Series(clusters, index=tick)
for c in sorted(clus.unique()):
    print('cluster', c, list(clus[clus == c].index))
G = nx.Graph()
for i in range(N):
    for j in range(i + 1, N):
        G.add_edge(tick[i], tick[j], weight=Dm[i, j], rho=C[i, j])
MST = nx.minimum_spanning_tree(G, weight='weight')
deg = dict(MST.degree())
print('MST hubs:', sorted(deg.items(), key=lambda x: -x[1])[:6])

# ------------------------------------------------------------------ hedge diagnostics vs NVDA
def pair_vol(a, b, wa=0.5):
    i, j = ix[a], ix[b]
    w = np.zeros(N); w[i] = wa; w[j] = 1 - wa
    return float(np.sqrt(w @ SIG @ w))

hedge_names = ['AMZN', 'SBUX', 'GOOGL', 'MSFT', 'COST', 'WMT', 'KO', 'PG', 'XLP', 'JNJ', 'LLY', 'XOM', 'GLD', 'TLT', 'IEF', 'DBMF', 'BTAL', 'BIL']
rows = []
sN = vol[ix['NVDA']]
for h in hedge_names:
    j = ix[h]
    rho = C[ix['NVDA'], j]
    rows.append(dict(asset=h, rho3y=rho, rho1y=A.loc[h, 'cNVDA1y'], rhoEWMA=A.loc[h, 'cNVDAewm'],
                     h_star=rho * sN / vol[j], effectiveness=rho ** 2,
                     vol5050=pair_vol('NVDA', h), betaDown=A.loc[h, 'dbSMH'], betaUp=A.loc[h, 'ubSMH'],
                     lamL10=A.loc[h, 'lamL10'], tailSMH=A.loc[h, 'tailSMH'], r2022=A.loc[h, 'r22'],
                     rElection=A.loc[h, 'rE1'], rNov3_13=A.loc[h, 'rE2']))
H = pd.DataFrame(rows).set_index('asset')
print(f"\nNVDA alone vol={sN:.3f}")
print(H.round(3).to_string())

# ------------------------------------------------------------------ valuation (stockanalysis.com statistics pages; page prices rescaled to 2026-11-13 close)
last = dict(x.split(':') for x in 'NVDA:162.85,AMD:534.06,AVGO:347.01,INTC:59.66,MU:778.31,TSM:398.73,META:641.69,ANET:197.29,MRVL:156.76,GOOGL:295.77,ASML:1495.16,MSFT:523.88,AMZN:266.66,VRT:202.07,CEG:280.20,VST:133.01,AAPL:356.27,ORCL:125.35,PLTR:167.99,SBUX:106.44,NOW:102.25,COST:1106.21,ETN:352.97,MCD:271.97,WMT:128.09,KO:99.25,PG:169.80,UNH:407.46,LLY:1443.50,JNJ:285.75,ABBV:295.03,BRK-B:592.94,V:425.76,JPM:346.19,XOM:170.59,CVX:219.89,SMH:486.75,XLV:188.85,QQQ:679.89,XLP:92.35,SPY:754.37,LMT:596.04,GLD:355.45,BIL:91.53,XLU:44.04,IEF:90.04,TLT:79.38,XLE:64.96,BTAL:13.33,DBMF:32.42,USMV:104.10,BTC-USD:68311.32'.split(','))
last = {k: float(v) for k, v in last.items()}
# fields: page_price, page_date, mcap($B), fwdPE, PE, rev, opinc, ebitda, ni, ocf, capex, fcf, netcash, roic(%)
V = {
 'NVDA': (186.64, '11-06', 4510, 15.43, 23.60, 302.97, 0.6521*302.97, 201.27, 192.88, 134.36, 7.35, 127.01, 23.61, 92.0),
 'AMD':  (449.04, '11-06', 736.46, 29.85, 97.33, 45.44, 8.10, 11.14, 7.62, 9.12, 2.07, 7.06, 6.57, 12.8),
 'AVGO': (293.69, '11-06', 1400, 16.88, 37.49, 89.10, 43.50, 52.26, 38.27, 40.65, 1.25, 39.40, -35.44, 30.7),
 'TSM':  (395.00, '11-10', 1830, 18.88, 26.74, 155.16, 89.93, 113.32, 79.31, 94.80, 49.92, 44.88, 100.36, 60.3),
 'MU':   (690.00, '11-06', 780.68, 3.91, 9.28, 133.19, 99.34, 108.84, 84.97, 89.68, 30.71, 58.96, 68.27, 93.4),
 'ASML': (1424.75, '11-06', 547.27, 22.47, 36.55, 44.98, 17.34, 18.44, 15.36, 25.33, 1.74, 23.59, 12.28, 92.1),
 'ANET': (170.80, '11-06', 215.79, 30.34, 45.79, 11.89, 5.21, 5.30, 4.75, 5.24, 0.2219, 5.02, 14.36, 239.9),
 'VRT':  (182.86, '11-06', 70.41, 19.77, 34.18, 13.12, 2.77, 3.19, 2.10, 3.67, 0.5183, 3.15, 0.3548, 43.8),
 'INTC': (56.28, '11-06', 299.13, 40.44, np.nan, 59.89, 6.18, 19.14, -12.03, 17.47, 13.70, 3.77, 4.18, 4.9),
 'PLTR': (160.38, '11-06', 386.44, 69.79, 112.98, 7.29, 3.33, 3.36, 3.67, 4.10, 0.04324, 4.05, 10.34, np.nan),
 'GOOGL':(284.78, '11-06', 3500, 20.66, 14.87, 471.10, 156.98, 185.52, 235.69, 179.55, 159.80, 19.75, 114.77, 23.8),
 'META': (610.15, '11-06', 1560, 18.52, 20.81, 241.61, 91.27, 116.19, 75.25, 133.09, 104.44, 28.65, -32.39, 29.6),
 'MSFT': (545.18, '11-09', 4050, 26.27, 28.47, 346.45, 163.19, 205.69, 142.63, 195.88, 135.92, 59.96, -69.42, 25.4),
 'AMZN': (259.30, '11-06', 2800, 26.22, 20.96, 797.46, 104.37, 183.72, 134.78, 168.30, 215.19, -46.89, -190.62, 10.9),
 'SBUX': (102.73, '10-26', 117.09, 34.93, 59.01, 38.34, 3.98, 5.64, 1.98, 4.99, 1.34, 3.64, -18.84, 13.7),
 'COST': (1053.56, '11-06', 466.86, 46.15, 50.75, 303.15, 11.51, 14.19, 9.23, 15.82, 6.44, 9.38, 11.12, 37.3),
 'WMT':  (125.52, '11-06', 995.84, 41.78, 45.48, 735.84, 28.98, 44.07, 22.08, 42.92, 29.41, 13.51, -63.56, 13.3),
 'KO':   (94.08, '10-30', 404.72, 27.13, 27.75, 51.05, 16.43, 17.44, 14.63, 16.23, 1.95, 14.28, -25.88, 20.6),
 'LLY':  (1354.00, '11-06', 1210, 28.86, 43.94, 86.46, 44.32, 46.49, 27.58, 30.65, 10.98, 19.66, -43.86, 42.7),
 'XOM':  (165.87, '11-06', 676.62, 11.70, 17.10, 388.23, 49.99, 77.96, 40.62, 70.59, 27.63, 42.96, -22.10, 13.0),
 'JNJ':  (271.04, '10-28', 652.48, 24.36, 41.16, 99.34, 26.41, 34.50, 16.10, 26.16, 5.57, 20.59, -27.42, 21.6),
}
RF, ERP, GT = 0.0486, 0.045, 0.03    # 10y UST 2026-11-06 close; ERP assumption; terminal growth

def implied_g_two_stage(price_to_cash, r, years=10, gT=GT):
    """Solve g s.t. sum_{t=1..10} (1+g)^t/(1+r)^t + (1+g)^10 (1+gT)/((r-gT)(1+r)^10) = price/cashflow."""
    def f(g):
        pv = sum(((1 + g) / (1 + r)) ** t for t in range(1, years + 1))
        tv = ((1 + g) ** years) * (1 + gT) / ((r - gT) * (1 + r) ** years)
        return pv + tv - price_to_cash
    try:
        return brentq(f, -0.5, 1.5)
    except ValueError:
        return np.nan

vrows = []
for t, (pp, pdte, mc, fpe, pe, rev, oi, ebitda, ni, ocf, capex, fcf, nc, roic) in V.items():
    k = last[t] / pp
    mcap = mc * k
    fpe_n = fpe * k
    pe_n = pe * k if not np.isnan(pe) else np.nan
    beta = A.loc[t, 'bSPY']
    beta_adj = 0.67 * beta + 0.33
    r = RF + beta_adj * ERP
    ey = 1 / fpe_n
    da = ebitda - oi
    g_e = implied_g_two_stage(fpe_n, r)                         # base = forward earnings (assumes earnings ~ distributable FCF)
    g_f = implied_g_two_stage((mcap - nc) / fcf, r) if fcf > 0 else np.nan   # base = TTM FCF, equity value net of net cash
    vrows.append(dict(t=t, price=last[t], page=f'{pp}@{pdte}', mcapB=mcap, fwdPE=fpe_n, ttmPE=pe_n,
                      fcf_yield=fcf / mcap, earn_yield=ey, r_capm=r, no_growth_share=ey / r,
                      g_implied_E=g_e, g_implied_FCF=g_f, fcf_to_ni=fcf / ni if ni > 0 else np.nan,
                      ni_to_opinc=ni / oi if oi > 0 else np.nan, capex_to_da=capex / da if da > 0 else np.nan,
                      capex_to_rev=capex / rev, net_cash_B=nc, roic=roic, op_margin=oi / rev))
VAL = pd.DataFrame(vrows).set_index('t')
print('\nVALUATION (rescaled to 2026-11-13 close)')
print(VAL.drop(columns=['page']).round(3).to_string())

# ------------------------------------------------------------------ portfolio construction
AI = ['NVDA', 'AVGO', 'TSM', 'AMD', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN', 'VRT']
HEDGE = ['BTAL', 'XOM', 'KO', 'XLP', 'JNJ', 'LLY', 'COST', 'WMT', 'GLD']
cap_h = {'BTAL': 0.08, 'XOM': 0.07, 'KO': 0.06, 'XLP': 0.10, 'JNJ': 0.06, 'LLY': 0.06, 'COST': 0.05, 'WMT': 0.05, 'GLD': 0.06}

def sub(names):
    ii = [ix[n] for n in names]
    return SIG[np.ix_(ii, ii)]

def erc(Sig):
    n = len(Sig)
    f = lambda y: 0.5 * y @ Sig @ y - np.sum(np.log(y)) / n
    g = lambda y: Sig @ y - 1 / (n * y)
    res = minimize(f, np.ones(n) / np.sqrt(np.diag(Sig)), jac=g, bounds=[(1e-9, None)] * n, method='L-BFGS-B', options=dict(ftol=1e-15, gtol=1e-12, maxiter=5000))
    w = res.x / res.x.sum()
    return w

def full(wdict):
    w = np.zeros(N)
    for k, v in wdict.items():
        w[ix[k]] += v
    return w

def risk_contrib(w):
    s2 = w @ SIG @ w
    return w * (SIG @ w) / s2

w_ai = erc(sub(AI))
rc_ai = w_ai * (sub(AI) @ w_ai); rc_ai /= rc_ai.sum()
print('\nERC AI sleeve:', dict(zip(AI, w_ai.round(4))), ' RC spread', rc_ai.min().round(4), rc_ai.max().round(4))

def hedge_sleeve(s, w_ai=w_ai, names=HEDGE, caps=cap_h, floors=None):
    floors = floors or {}
    a = full(dict(zip(AI, s * w_ai)))
    ii = [ix[n] for n in names]
    Hs = 1 - s
    def obj(h):
        w = a.copy(); w[ii] += h
        return w @ SIG @ w
    def grad(h):
        w = a.copy(); w[ii] += h
        return 2 * (SIG @ w)[ii]
    cons = [dict(type='eq', fun=lambda h: h.sum() - Hs, jac=lambda h: np.ones_like(h))]
    bnds = [(min(floors.get(n, 0), Hs), min(caps[n], Hs)) for n in names]
    h0 = np.array([max(floors.get(n, 0), min(caps[n], Hs / len(names))) for n in names]); h0 *= Hs / h0.sum()
    res = minimize(obj, h0, jac=grad, bounds=bnds, constraints=cons, method='SLSQP', options=dict(ftol=1e-14, maxiter=1000))
    assert res.success, res.message
    return dict(zip(names, res.x))

def describe(wvec):
    s2 = wvec @ SIG @ wvec
    sp = np.sqrt(s2)
    out = dict(vol=sp)
    for ref in ['SPY', 'SMH', 'NVDA']:
        j = ix[ref]
        cov = (SIG @ wvec)[j]
        out[f'beta_{ref}'] = cov / SIG[j, j]
        out[f'rho_{ref}'] = cov / (sp * np.sqrt(SIG[j, j]))
    out['div_ratio'] = (wvec @ np.sqrt(np.diag(SIG))) / sp
    out['div_return'] = 0.5 * (wvec @ np.diag(SIG) - s2)   # rebalancing / diversification return (log)
    rc = risk_contrib(wvec)
    out['RC_AI'] = rc[[ix[n] for n in AI]].sum()
    out['ewma_vol_proxy'] = np.sqrt((wvec * ewvol) @ CL @ (wvec * ewvol))   # current vols, long-run corr
    return out

dial = {}
for s in [0.5, 0.6, 0.65, 0.7, 0.8, 1.0]:
    h = hedge_sleeve(s) if s < 1 else {}
    wd = {**dict(zip(AI, s * w_ai)), **h}
    dial[s] = wd
    d = describe(full(wd))
    print(f's={s:.2f}', {k: round(v, 3) for k, v in d.items()}, '| hedge:', {k: round(v, 3) for k, v in h.items() if v > 1e-4})

# reference portfolios
REF = {
    'NVDA only': {'NVDA': 1.0},
    'SMH': {'SMH': 1.0},
    'SPY': {'SPY': 1.0},
    'QQQ': {'QQQ': 1.0},
    'EW AI10': {n: 0.1 for n in AI},
}
for k, wd in REF.items():
    d = describe(full(wd))
    print(f'{k:10s}', {kk: round(v, 3) for kk, v in d.items()})

json.dump(dict(AI=AI, HEDGE=HEDGE, w_ai=dict(zip(AI, w_ai.tolist())), dial={str(k): v for k, v in dial.items()}, ref=REF,
               pca=pca_info, clusters=clus.to_dict(), order=[tick[i] for i in order]),
          open('out_portfolios.json', 'w'), indent=1)
VAL.to_csv('out_valuation.csv')
H.to_csv('out_hedges.csv')

# ================================================================== FINAL CONSTRUCTION
# Rule-based screen (from valuation + risk diagnostics above):
#  - drop AMD (implied 10y earnings CAGR 22%, P/FCF>100, EWMA vol ~95%) and VRT (downside beta 1.42 vs upside 0.94,
#    implied CAGR 15.5%, direct exposure to data-center permitting risk) from the core AI sleeve
#  - ERC on remaining 8 names, then valuation tilt x1.5 for names with implied CAGR<=10% AND FCF/NI>=0.5 (NVDA, TSM)
AI8 = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
w8 = erc(sub(AI8))
# negative implied growth = market pricing an earnings decline (cyclical peak, e.g. MU at 75% op margin) -> no tilt
tilt = np.array([1.5 if (0 <= VAL.loc[n, 'g_implied_E'] <= 0.10 and VAL.loc[n, 'fcf_to_ni'] >= 0.5) else 1.0 for n in AI8])
w8t = w8 * tilt / (w8 * tilt).sum()
print('\nERC AI8:', dict(zip(AI8, w8.round(4))))
print('tilted AI8:', dict(zip(AI8, w8t.round(4))), 'tilt applied to', [n for n, t in zip(AI8, tilt) if t > 1])
AI = AI8  # downstream describe() uses AI for RC
HEDGE5 = ['BTAL', 'XLP', 'KO', 'JNJ', 'XOM', 'LLY', 'COST', 'WMT', 'GLD']
dial2 = {}
print('\nRISK DIAL (final sleeve)')
for s in [0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 1.0]:
    h = hedge_sleeve(s, w_ai=w8t, names=HEDGE5, caps=cap_h, floors={'XOM': 0.04}) if s < 1 else {}
    wd = {**dict(zip(AI8, s * w8t)), **{k: v for k, v in h.items() if v > 1e-6}}
    dial2[s] = wd
    d = describe(full(wd))
    capm = RF + d['beta_SPY'] * ERP
    print(f's={s:.2f} vol={d["vol"]:.3f} ewmaProxy={d["ewma_vol_proxy"]:.3f} bSPY={d["beta_SPY"]:.2f} bSMH={d["beta_SMH"]:.2f} '
          f'rhoNVDA={d["rho_NVDA"]:.2f} DR={d["div_ratio"]:.2f} divRet={d["div_return"]:.3f} RC_AI={d["RC_AI"]:.3f} capmER={capm:.3f}',
          '| hedge', {k: round(v, 3) for k, v in h.items() if v > 1e-4})

# HRP cross-check (Lopez de Prado 2016) on the same 17-asset universe
def hrp(names):
    ii = [ix[n] for n in names]
    cov = SIG[np.ix_(ii, ii)]; cor = CL[np.ix_(ii, ii)]
    dist = np.sqrt(np.clip((1 - cor) / 2, 0, None)); np.fill_diagonal(dist, 0)
    link = linkage(squareform(dist, checks=False), 'single')
    srt = list(leaves_list(link))
    w = pd.Series(1.0, index=srt)
    clusters_ = [srt]
    while clusters_:
        clusters_ = [c[j:k] for c in clusters_ for j, k in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for a in range(0, len(clusters_), 2):
            c0, c1 = clusters_[a], clusters_[a + 1]
            def cvar(c):
                cc = cov[np.ix_(c, c)]; ivp = 1 / np.diag(cc); ivp /= ivp.sum(); return ivp @ cc @ ivp
            v0, v1 = cvar(c0), cvar(c1)
            al = 1 - v0 / (v0 + v1)
            w[c0] *= al; w[c1] *= 1 - al
    return {names[i]: float(w[i]) for i in w.index}
w_hrp = hrp(AI8 + ['BTAL', 'XLP', 'KO', 'JNJ', 'XOM'])
print('\nHRP (13 assets):', {k: round(v, 3) for k, v in sorted(w_hrp.items(), key=lambda x: -x[1])}, ' AI share', round(sum(w_hrp[n] for n in AI8), 3))
d = describe(full(w_hrp)); print('HRP describe', {k: round(v, 3) for k, v in d.items()})

# pairs that answer the user's original question (NVDA + X, 50/50 and 70/30)
PAIRS = {'NVDA+SBUX 50/50': {'NVDA': .5, 'SBUX': .5}, 'NVDA+AMZN 50/50': {'NVDA': .5, 'AMZN': .5},
         'NVDA+KO 50/50': {'NVDA': .5, 'KO': .5}, 'NVDA+BTAL 70/30': {'NVDA': .7, 'BTAL': .3}}
for k, wd in PAIRS.items():
    d = describe(full(wd)); print(f'{k:18s} vol={d["vol"]:.3f} bSPY={d["beta_SPY"]:.2f} rhoNVDA={d["rho_NVDA"]:.2f}')

ports = {f'AI{int(s*100)}': v for s, v in dial2.items()}
ports.update({'HRP13': w_hrp, **REF, **PAIRS})
mu = {k: RF + describe(full(v))['beta_SPY'] * ERP for k, v in ports.items()}
json.dump(dict(ports=ports, mu=mu, AI8=AI8, w8=dict(zip(AI8, w8.tolist())), w8t=dict(zip(AI8, w8t.tolist()))), open('out_final.json', 'w'), indent=1)
print('\nJS payload:', json.dumps({k: {kk: round(vv, 5) for kk, vv in v.items()} for k, v in ports.items()}, separators=(',', ':')))
print('MU:', json.dumps({k: round(v, 5) for k, v in mu.items()}, separators=(',', ':')))

# ------------------------------------------------------------------ practical rounded portfolio (s = 0.70)
FINAL = {'NVDA': .09, 'TSM': .10, 'AVGO': .06, 'MU': .05, 'GOOGL': .11, 'META': .08, 'MSFT': .12, 'AMZN': .09,
         'BTAL': .08, 'XLP': .06, 'KO': .06, 'JNJ': .06, 'XOM': .04}
assert abs(sum(FINAL.values()) - 1) < 1e-9
wF = full(FINAL); dF = describe(wF)
rcF = risk_contrib(wF)
print('\nFINAL', {k: round(v, 4) for k, v in dF.items()}, 'CAPM ER', round(RF + dF['beta_SPY'] * ERP, 4))
print('RC%', {n: round(rcF[ix[n]] * 100, 1) for n in FINAL})
dev = {n: round(FINAL[n] - dial2[0.7].get(n, 0), 4) for n in FINAL}
print('rounding deviation vs optimizer (s=0.70):', dev)
json.dump(dict(FINAL=FINAL, describe=dF, rc={n: float(rcF[ix[n]]) for n in FINAL}, mu=RF + dF['beta_SPY'] * ERP), open('out_FINAL.json', 'w'), indent=1)
