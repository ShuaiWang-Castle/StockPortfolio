"""Builds the dashboard's attached datasets (JSON {rows, meta}) from analysis.py outputs and the browser blocks.
Run: python3 build_datasets.py  (writes ds/<id>.json)."""
import io, json, os, runpy, contextlib, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path('analysis.py')
A, C, ix, tick, VAL, H, SIG = G['A'], G['C'], G['ix'], G['tick'], G['VAL'], G['H'], G['SIG']
describe, full, risk_contrib = G['describe'], G['full'], G['risk_contrib']
FINAL, dial2, last = G['FINAL'], G['dial2'], G['last']
BT = json.load(open('data/backtest.json'))
BT60 = json.load(open('data/backtest_ai60.json')) if os.path.exists('data/backtest_ai60.json') else None
META = json.load(open('data/meta.json'))

NAME = {'NVDA': '英伟达', 'TSM': '台积电', 'AVGO': '博通', 'MU': '美光', 'GOOGL': 'Alphabet', 'META': 'Meta', 'MSFT': '微软',
        'AMZN': '亚马逊', 'BTAL': '反贝塔 ETF', 'XLP': '必需消费 ETF', 'KO': '可口可乐', 'JNJ': '强生', 'XOM': '埃克森美孚',
        'AMD': 'AMD', 'ASML': '阿斯麦', 'ANET': 'Arista', 'VRT': '维谛', 'INTC': '英特尔', 'PLTR': 'Palantir', 'SBUX': '星巴克',
        'COST': '好市多', 'WMT': '沃尔玛', 'LLY': '礼来', 'GLD': '黄金 ETF', 'TLT': '20年+美债 ETF', 'IEF': '7-10年美债 ETF',
        'DBMF': '管理期货 ETF', 'BIL': '短期国库券 ETF', 'SMH': '半导体 ETF', 'SPY': '标普500 ETF', 'QQQ': '纳指100 ETF', 'PG': '宝洁',
        'MCD': '麦当劳', 'BRK-B': '伯克希尔', 'CEG': '星座能源', 'VST': 'Vistra', 'ETN': '伊顿', 'MRVL': '迈威尔', 'ORCL': '甲骨文'}
ROLE = {**{t: 'AI 供应商' for t in ['NVDA', 'TSM', 'AVGO', 'MU', 'AMD', 'ASML', 'ANET', 'VRT', 'INTC', 'MRVL', 'CEG', 'VST', 'ETN']},
        **{t: 'AI 平台' for t in ['GOOGL', 'META', 'MSFT', 'AMZN', 'ORCL', 'PLTR']},
        **{t: '防御/对冲' for t in ['BTAL', 'XLP', 'KO', 'JNJ', 'XOM', 'SBUX', 'COST', 'WMT', 'LLY', 'GLD', 'TLT', 'IEF', 'DBMF', 'BIL', 'PG', 'MCD', 'BRK-B']},
        **{t: '指数' for t in ['SMH', 'SPY', 'QQQ']}}

def code(path, lang):
    return {'label': os.path.basename(path), 'value': open(path).read(), 'type': 'code', 'lang': lang}

PY = [code('build_datasets.py', 'python'), code('analysis.py', 'python')]
JS_STATS = [code('js/01_fetch.js', 'javascript'), code('js/02_stats.js', 'javascript')]
JS_MAT = [code('js/03_matrix.js', 'javascript')]
JS_BT = [code('js/04_backtest.js', 'javascript')]
INPUT_PRICES = {'label': 'Input: prices', 'value': META['price_source'] + '; raw SHA-256 ' + META['raw_data_sha256'] + '; ' + META['calendar']}
INPUT_A = {'label': 'Input: stats_daily.csv', 'value': 'SHA-256 ' + META['blocks']['data/stats_daily.csv'] + ' (verified against the browser-side hash)'}
INPUT_B = {'label': 'Input: matrix_block.txt', 'value': 'SHA-256 ' + META['blocks']['data/matrix_block.txt'] + ' (verified against the browser-side hash)'}
INPUT_BT = {'label': 'Input: backtest.json', 'value': 'SHA-256 ' + META['blocks']['data/backtest.json'] + ' (verified against the browser-side hash)'}
INPUT_FUND = {'label': 'Input: fundamentals', 'value': META['fundamentals_source']}
ASSUME = {'label': 'Assumptions', 'value': json.dumps(META['assumptions'], ensure_ascii=False)}

def r(x, d=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)

def write(name, rows, meta):
    os.makedirs('ds', exist_ok=True)
    json.dump({'rows': rows, 'meta': meta}, open(f'ds/{name}.json', 'w'), ensure_ascii=False, allow_nan=False)

# 1 holdings -------------------------------------------------------------------------------
wF = full(FINAL); rcF = risk_contrib(wF)
rows = []
for t, w in FINAL.items():
    usd7 = round(w * 7000); usd10 = round(w * 10000)
    rows.append(dict(ticker=t, name=NAME[t], role=ROLE[t], weight=w, usd7k=usd7, usd10k=usd10, rc=r(rcF[ix[t]]),
                     price=last[t], shares7k=round(usd7 / last[t], 3)))
write('holdings', rows, PY + [INPUT_A, INPUT_B, ASSUME])

# 2 compare (backtests) --------------------------------------------------------------------------
LABEL = {'FINAL': '本方案 70/30', 'AI100': '纯 AI 篮子（8 只）', 'NVDA': '单押 NVDA', 'SMH': '半导体 ETF', 'SPY': '标普 500',
         'QQQ': '纳指 100', 'EW_AI10': 'AI 10 只等权', 'NVDA_SBUX': 'NVDA+SBUX 各半', 'NVDA_AMZN': 'NVDA+AMZN 各半',
         'NVDA_KO': 'NVDA+KO 各半', 'NVDA_BTAL': 'NVDA 70 + BTAL 30', 'HRP13': 'HRP 风险平价（AI 27%）', 'AI80': 'AI 80%', 'AI60': 'AI 60%'}
keys = ['FINAL', 'NVDA', 'SMH', 'SPY', 'QQQ', 'EW_AI10', 'AI100', 'NVDA_SBUX', 'NVDA_AMZN', 'NVDA_KO', 'NVDA_BTAL', 'HRP13']
rows = []
for k in keys:
    m = BT['res'][k]
    rows.append(dict(key=k, label=LABEL[k], **{f: m[f] for f in ['cagr', 'vol', 'sharpe', 'mdd', 'r22', 'e1', 'e2', 'e3', 'b05', 'b50', 'b95', 'pL20', 'mdd05', 'ewmaVol']}))
write('compare', rows, JS_BT + [INPUT_PRICES, INPUT_BT, {'label': 'Note', 'value': '3y window 2023-11-13..2026-11-13 is in-sample for the weights; the 2022 window (2022-01-03..2022-10-12) is out-of-sample. Bootstrap: de-meaned daily log returns + CAPM drift rf+beta*ERP.'}])

# 3 dial ------------------------------------------------------------------------------------------
drows = []
src = {'AI60': (dial2[0.6], BT60['res']['AI60'] if BT60 else None), 'FINAL': (FINAL, BT['res']['FINAL']),
       'AI80': (dial2[0.8], BT['res']['AI80']), 'AI100': (dial2[1.0], BT['res']['AI100'])}
share = {'AI60': 0.6, 'FINAL': 0.7, 'AI80': 0.8, 'AI100': 1.0}
for k, (wd, bt) in src.items():
    if bt is None:
        continue
    d = describe(full(wd))
    drows.append(dict(key=k, label='本方案（AI 70%）' if k == 'FINAL' else LABEL.get(k, k), ai_share=share[k], vol_lw=r(d['vol']), ewma_proxy=r(d['ewma_vol_proxy']),
                      beta_spy=r(d['beta_SPY'], 3), beta_smh=r(d['beta_SMH'], 3), rho_nvda=r(d['rho_NVDA'], 3),
                      capm_er=r(G['RF'] + d['beta_SPY'] * G['ERP']), vol_bt=bt['vol'], cagr3y=bt['cagr'], r22=bt['r22'], e1=bt['e1'], e3=bt['e3'],
                      b05=bt['b05'], b50=bt['b50'], b95=bt['b95'], pL20=bt['pL20'], mdd05=bt['mdd05']))
write('dial', drows, PY + JS_BT + [INPUT_A, INPUT_B, INPUT_BT, ASSUME])

# 4 events -------------------------------------------------------------------------------------
EV = ['NVDA', 'AMD', 'AVGO', 'MU', 'TSM', 'ASML', 'VRT', 'INTC', 'PLTR', 'GOOGL', 'META', 'MSFT', 'AMZN',
      'SBUX', 'COST', 'WMT', 'KO', 'JNJ', 'XOM', 'GLD', 'TLT', 'BTAL', 'SPY', 'QQQ', 'SMH']
rows = [dict(ticker=t, name=NAME.get(t, t), group=ROLE[t], e1=r(A.loc[t, 'rE1']), e2=r(A.loc[t, 'rE2']), e3=r(A.loc[t, 'rOct6']),
             r22=r(A.loc[t, 'r22'])) for t in EV]
write('events', rows, JS_STATS + [INPUT_PRICES, INPUT_A])

# 5 hedges ------------------------------------------------------------------------------------
rows = []
for t in H.index:
    h = H.loc[t]
    rows.append(dict(ticker=t, name=NAME.get(t, t), rho3y=r(h['rho3y'], 3), rho1y=r(h['rho1y'], 2), rhoEWMA=r(h['rhoEWMA'], 2),
                     h_star=r(h['h_star'], 3), effectiveness=r(h['effectiveness'], 3), vol5050=r(h['vol5050'], 3),
                     lamL10=r(h['lamL10'], 2), r2022=r(h['r2022'], 3), rElection=r(h['rElection'], 3)))
write('hedges', rows, PY + JS_STATS + JS_MAT + [INPUT_A, INPUT_B, {'label': 'Definitions', 'value': 'h* = rho*sigma_NVDA/sigma_X (min-variance hedge ratio); effectiveness = rho^2 (share of NVDA variance an optimal hedge removes); vol5050 = Ledoit-Wolf vol of a 50/50 NVDA+X mix; lamL10 = P(X in its worst 10% | SMH in its worst 10%), independence = 0.10.'}])

# 6 rolling ------------------------------------------------------------------------------------
RO = ['AMZN', 'SBUX', 'COST', 'KO', 'BTAL', 'GLD']
rows = [dict(date=dte, asset=a, rho=G['roll'][a][k]) for a in RO for k, dte in enumerate(G['rolldates'])]
write('rolling', rows, JS_MAT + [INPUT_PRICES, INPUT_B, {'label': 'Definition', 'value': '63-trading-day Pearson correlation of daily log returns, NVDA vs asset, sampled every 5 trading days.'}])

# 7 corr (clustered subset) -------------------------------------------------------------------------
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
SUBS = ['NVDA', 'AMD', 'AVGO', 'MU', 'TSM', 'ASML', 'VRT', 'GOOGL', 'META', 'MSFT', 'AMZN', 'PLTR', 'SBUX', 'COST', 'WMT', 'KO', 'PG',
        'JNJ', 'LLY', 'XOM', 'GLD', 'TLT', 'BTAL', 'SPY']
ii = [ix[t] for t in SUBS]
Cs = C[np.ix_(ii, ii)]
Dm = np.sqrt(np.clip(2 * (1 - Cs), 0, None)); np.fill_diagonal(Dm, 0)
order = leaves_list(linkage(squareform(Dm, checks=False), 'average'))
ORD = [SUBS[i] for i in order]
rows = []
for a_i, a in enumerate(ORD):
    for b_i, b in enumerate(ORD):
        rows.append(dict(a=a, b=b, i=a_i, j=b_i, rho=r(C[ix[a], ix[b]], 3)))
write('corr', rows, PY + JS_MAT + [INPUT_B, {'label': 'Order', 'value': 'average-linkage clustering on Mantegna distance sqrt(2(1-rho)): ' + ','.join(ORD)}])

# 8 valuation ---------------------------------------------------------------------------------
rows = []
for t in VAL.index:
    v = VAL.loc[t]
    rows.append(dict(ticker=t, name=NAME.get(t, t), role=ROLE[t], price=r(v['price'], 2), fwdPE=r(v['fwdPE'], 1), fcf_yield=r(v['fcf_yield']),
                     earn_yield=r(v['earn_yield']), r_capm=r(v['r_capm']), no_growth_share=r(v['no_growth_share'], 3),
                     g_implied_E=r(v['g_implied_E']), fcf_to_ni=r(v['fcf_to_ni'], 2), ni_to_opinc=r(v['ni_to_opinc'], 2),
                     capex_to_da=r(v['capex_to_da'], 2), source_page=v['page']))
write('valuation', rows, PY + [INPUT_FUND, INPUT_A, ASSUME, {'label': 'Definitions', 'value': 'r_capm = rf + (0.67*beta_3y+0.33)*ERP; no_growth_share = (1/fwdPE)/r: share of price explained by forward earnings held flat; g_implied_E: 10y growth that makes a 2-stage model (terminal 3%) match the price with forward earnings as distributable cash; fcf_to_ni = TTM FCF / TTM net income; ni_to_opinc = net income / operating income (>0.9 flags non-operating gains); capex_to_da = capex / (EBITDA - operating income).'}])

# 9 curves -----------------------------------------------------------------------------------
rows = []
for s in ['FINAL', 'NVDA', 'SMH', 'SPY']:
    for dte, v in zip(BT['dates'], BT['curves'][s]):
        rows.append(dict(window='3y', date=dte, series=s, value=v))
    for dte, v in zip(BT['d22'], BT['c22'][s]):
        rows.append(dict(window='2022', date=dte, series=s, value=v))
write('curves', rows, JS_BT + [INPUT_PRICES, INPUT_BT])

# 10 params ----------------------------------------------------------------------------------
pca = G['pca_info']
rows = [dict(key='T', value=G['T'], label='估计窗口日收益数'), dict(key='N', value=G['N'], label='资产数'),
        dict(key='lw_delta', value=G['delta'], label='Ledoit-Wolf 收缩强度'), dict(key='rbar', value=G['rbar'], label='平均相关'),
        dict(key='lam_plus', value=round(float(pca['lam_plus']), 3), label='Marchenko-Pastur 上界'),
        dict(key='n_sig', value=pca['n_sig'], label='超出 MP 上界的特征值个数'),
        dict(key='pc1_share', value=pca['share'][0], label='PC1 方差占比'), dict(key='pc2_share', value=pca['share'][1], label='PC2 方差占比'),
        dict(key='rf', value=G['RF'], label='无风险利率（10 年美债）'), dict(key='erp', value=G['ERP'], label='股权风险溢价假设'),
        dict(key='g_terminal', value=G['GT'], label='永续增长'), dict(key='rf3y_bil', value=BT['rf3y'], label='BIL 三年年化')]
write('params', rows, PY + JS_MAT + [INPUT_B, ASSUME])

for f in sorted(os.listdir('ds')):
    p = 'ds/' + f
    print(f, os.path.getsize(p), hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12])
