"""Figures for the report (PNG, 200 dpi). Run after analysis.py/build_datasets.py: python3 make_figures.py"""
import io, os, json, runpy, contextlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import networkx as nx

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path('analysis.py')
A, C, ix, H, VAL = G['A'], G['C'], G['ix'], G['H'], G['VAL']
BT = json.load(open('data/backtest.json')); BT60 = json.load(open('data/backtest_ai60.json'))
DS = {n: json.load(open(f'ds/{n}.json'))['rows'] for n in ['events', 'hedges', 'rolling', 'corr', 'valuation', 'holdings', 'dial', 'curves']}
os.makedirs('figures', exist_ok=True)

# ---------------------------------------------------------------- style (dataviz reference palette, light)
BLUE, ORANGE, AQUA, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#898781'
INK, INK2, GRID, AXIS, SURF = '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
GROUPC = {'AI 供应商': BLUE, 'AI 平台': ORANGE, '防御/对冲': AQUA, '指数': GRAY}
plt.rcParams.update({
    'font.family': 'Noto Sans CJK SC', 'font.size': 9.5, 'axes.titlesize': 11, 'axes.titleweight': 'bold',
    'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.axisbelow': True,
    'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
    'savefig.facecolor': SURF, 'legend.frameon': False, 'axes.unicode_minus': False})
pct = matplotlib.ticker.PercentFormatter(1.0, decimals=0)

def save(fig, name):
    fig.savefig(f'figures/{name}.png', dpi=200, bbox_inches='tight')
    plt.close(fig)

def note(fig, text):
    fig.text(0.01, -0.01, text, ha='left', va='top', fontsize=7.5, color=INK2)

# ---------------------------------------------------------------- F1 election window
ev = pd.DataFrame(DS['events']).sort_values('e1')
fig, ax = plt.subplots(figsize=(7.2, 7.4))
y = np.arange(len(ev))
ax.barh(y, ev['e1'], height=0.62, color=[GROUPC[g] for g in ev['group']], zorder=2)
ax.scatter(ev['e2'], y, s=34, facecolor='white', edgecolor=INK, linewidth=1.1, zorder=3)
ax.set_yticks(y, [f"{t}  {n}" if n != t else t for t, n in zip(ev['ticker'], ev['name'])])
ax.axvline(0, color=AXIS, lw=1)
ax.xaxis.set_major_formatter(pct)
xr = max(ev['e2'].max(), ev['e1'].max()) + 0.03
for yi, v, v2 in zip(y, ev['e1'], ev['e2']):
    ax.text(xr + 0.035, yi, f'{v:+.1%}', va='center', ha='right', fontsize=7.5, color=INK)
    ax.text(xr + 0.085, yi, f'{v2:+.1%}', va='center', ha='right', fontsize=7.5, color=INK2)
ax.text(xr + 0.035, len(ev) - 0.3, '11/3→5', ha='right', va='bottom', fontsize=7.5, color=INK, fontweight='bold')
ax.text(xr + 0.085, len(ev) - 0.3, '→11/13', ha='right', va='bottom', fontsize=7.5, color=INK2, fontweight='bold')
ax.set_xlim(ev['e1'].min() - 0.02, xr + 0.09)
ax.set_xticks([-0.3, -0.2, -0.1, 0, 0.1])
ax.set_title('大选冲击：11/3 收盘 → 11/5 收盘（柱）与 → 11/13（圆点）')
h = [Patch(color=c, label=g) for g, c in GROUPC.items()] + [Line2D([], [], marker='o', ls='', mfc='white', mec=INK, label='11/3→11/13')]
ax.legend(handles=h, loc='upper left', fontsize=8)
ax.grid(axis='y', visible=False)
note(fig, '数据：Yahoo Finance 复权收盘价；收益为简单收益。')
save(fig, 'f1_election_window')

# ---------------------------------------------------------------- F2 hedge dumbbell
hd = pd.DataFrame(DS['hedges']).sort_values('rho3y')
fig, ax = plt.subplots(figsize=(7.2, 6.0))
y = np.arange(len(hd))
for yi, a, b in zip(y, hd['rho3y'], hd['rhoEWMA']):
    ax.plot([a, b], [yi, yi], color=AXIS, lw=2, zorder=1)
ax.scatter(hd['rho3y'], y, s=46, color=BLUE, zorder=3, label='3 年（2023-11 → 2026-11，日频）')
ax.scatter(hd['rhoEWMA'], y, s=46, color=ORANGE, marker='D', zorder=3, label='当前（EWMA λ=0.97，半衰期≈23 个交易日）')
ax.set_yticks(y, [f"{t}  {n}" for t, n in zip(hd['ticker'], hd['name'])])
ax.axvline(0, color=INK2, lw=1)
ax.set_xlim(-0.85, 0.65)
for yi, a, e in zip(y, hd['rho3y'], hd['effectiveness']):
    ax.text(0.63, yi, f'ρ²={e:.0%}', va='center', ha='right', fontsize=7.5, color=INK2)
ax.set_xlabel('与 NVDA 日收益的相关系数 ρ')
ax.set_title('谁能对冲 NVDA？与 NVDA 的相关系数：长期 vs 当前')
ax.legend(loc='upper left', fontsize=8)
ax.grid(axis='y', visible=False)
note(fig, 'ρ² = 最优（最小方差）对冲能消除的 NVDA 方差比例（用 3 年 ρ）。ρ>0 的资产只能“稀释”，不能“对冲”。')
save(fig, 'f2_hedge_dumbbell')

# ---------------------------------------------------------------- F3 rolling correlations
ro = pd.DataFrame(DS['rolling']); ro['date'] = pd.to_datetime(ro['date'])
assets = ['AMZN', 'SBUX', 'COST', 'KO', 'BTAL', 'GLD']
NAME = {r['ticker']: r['name'] for r in DS['hedges']}
fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.4), sharex=True, sharey=True)
for ax, a in zip(axes.flat, assets):
    s = ro[ro.asset == a]
    ax.axhline(0, color=INK2, lw=0.8)
    ax.plot(s['date'], s['rho'], color=BLUE, lw=1.8)
    ax.plot(s['date'].iloc[-1], s['rho'].iloc[-1], 'o', color=BLUE, ms=5)
    ax.text(s['date'].iloc[-1] + pd.Timedelta(days=25), s['rho'].iloc[-1], f"{s['rho'].iloc[-1]:+.2f}", ha='left', va='center', fontsize=8, color=INK)
    ax.set_xlim(s['date'].iloc[0] - pd.Timedelta(days=20), s['date'].iloc[-1] + pd.Timedelta(days=150))
    ax.set_title(f'NVDA vs {a}（{NAME.get(a, a)}）', fontsize=9.5)
    ax.set_ylim(-1, 1)
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig.suptitle('相关性会漂移：63 日滚动相关系数', fontweight='bold', y=1.0)
note(fig, '每 5 个交易日取样；窗口 63 个交易日（约一季度）。')
fig.tight_layout()
save(fig, 'f3_rolling_corr')

# ---------------------------------------------------------------- F4 clustered heatmap
cr = pd.DataFrame(DS['corr'])
order = cr.drop_duplicates('a').sort_values('i')['a'].tolist()
M = cr.pivot(index='a', columns='b', values='rho').loc[order, order].values
cmap = LinearSegmentedColormap.from_list('div', ['#184f95', '#6da7ec', '#f0efec', '#f19a99', '#b42d2d'])
fig, ax = plt.subplots(figsize=(8.2, 7.2))
im = ax.imshow(M, cmap=cmap, vmin=-1, vmax=1)
ax.set_xticks(range(len(order)), order, rotation=90, fontsize=8); ax.set_yticks(range(len(order)), order, fontsize=8)
ax.grid(False)
for s in ax.spines.values(): s.set_visible(False)
cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02); cb.set_label('相关系数 ρ（3 年日收益）', color=INK2); cb.outline.set_visible(False)
ax.set_title('相关结构（平均链接层次聚类排序）')
note(fig, '距离 d=√(2(1−ρ))（Mantegna 1999）；红=同涨同跌，蓝=反向。')
save(fig, 'f4_corr_heatmap')

# ---------------------------------------------------------------- F5 MST network
MST = G['MST']
role = {**{t: 'AI 供应商' for t in ['NVDA', 'TSM', 'AVGO', 'MU', 'AMD', 'ASML', 'ANET', 'VRT', 'INTC', 'MRVL', 'CEG', 'VST', 'ETN']},
        **{t: 'AI 平台' for t in ['GOOGL', 'META', 'MSFT', 'AMZN', 'ORCL', 'PLTR']},
        **{t: '指数' for t in ['SMH', 'SPY', 'QQQ']}}
pos = nx.kamada_kawai_layout(MST, weight='weight')
fig, ax = plt.subplots(figsize=(9.6, 7.6))
for u, v, d in MST.edges(data=True):
    ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color=AXIS if d['rho'] >= 0 else ORANGE, lw=0.8 + 2.2 * abs(d['rho']), zorder=1)
for n in MST.nodes():
    c = GROUPC[role.get(n, '防御/对冲')]
    ax.scatter(*pos[n], s=150, color=c, edgecolor=SURF, linewidth=1.5, zorder=2)
    ax.text(pos[n][0], pos[n][1] + 0.035, n, ha='center', va='bottom', fontsize=7.5, color=INK, zorder=3)
ax.set_axis_off()
h = [Patch(color=c, label=g if g != '防御/对冲' else '其他（含防御、商品、债券、BTAL、AAPL、NOW）') for g, c in GROUPC.items()] 
ax.legend(handles=h, loc='lower left', fontsize=8)
ax.set_title('最小生成树（52 个资产）：AI 簇挂在 SMH 上，防御簇挂在 USMV/XLP/XLV 上')
note(fig, '边权 d=√(2(1−ρ))，Kruskal 最小生成树；线越粗 ρ 越大。BTAL 与全部 AI 股负相关，树上只能挂在与它正相关最强的 KO（ρ=0.31）上。')
save(fig, 'f5_mst')

# ---------------------------------------------------------------- F6 valuation & accounting quality
vl = pd.DataFrame(DS['valuation'])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 5.4), gridspec_kw=dict(width_ratios=[1, 1.15]))
v1 = vl.dropna(subset=['g_implied_E']).sort_values('g_implied_E')
y = np.arange(len(v1))
a1.barh(y, v1['g_implied_E'], height=0.62, color=[GROUPC[r] for r in v1['role']], zorder=2)
a1.set_yticks(y, v1['ticker']); a1.axvline(0, color=INK2, lw=1)
for yi, g, pe in zip(y, v1['g_implied_E'], v1['fwdPE']):
    a1.text(g + (0.006 if g >= 0 else -0.006), yi, f'{g:+.0%}  (PE {pe:.0f})', va='center', ha='left' if g >= 0 else 'right', fontsize=7.2, color=INK2)
a1.xaxis.set_major_formatter(pct); a1.set_xlim(-0.2, 0.46)
a1.set_title('股价隐含的未来 10 年盈利年增速')
a1.grid(axis='y', visible=False)
a1.legend(handles=[Patch(color=GROUPC[g], label=g) for g in ['AI 供应商', 'AI 平台', '防御/对冲']], loc='lower right', fontsize=8)
v2 = vl.dropna(subset=['fcf_to_ni', 'capex_to_da'])
for _, r_ in v2.iterrows():
    a2.scatter(r_['fcf_to_ni'], r_['capex_to_da'], s=60, color=GROUPC[r_['role']], edgecolor=SURF, linewidth=1.2, zorder=3)
    off = {'WMT': (-5, -11, 'right'), 'COST': (-5, -11, 'right'), 'ANET': (5, 4, 'left'), 'NVDA': (5, 3, 'left'), 'TSM': (-5, 5, 'right')}.get(r_['ticker'], (4, 3, 'left'))
    a2.annotate(r_['ticker'], (r_['fcf_to_ni'], r_['capex_to_da']), xytext=off[:2], textcoords='offset points', fontsize=7.5, color=INK, ha=off[2])
a2.axvline(1, color=AXIS, lw=1); a2.axhline(1, color=AXIS, lw=1)
a2.set_xlabel('自由现金流 / 净利润（TTM）'); a2.set_ylabel('资本开支 / 折旧摊销（TTM）')
a2.set_title('会计质量：利润有多少变成了现金？')
a2.text(0.98, 0.06, '右下：现金多、再投资少', transform=a2.transAxes, ha='right', va='bottom', fontsize=8, color=INK2)
a2.text(0.02, 0.86, '左上：利润≫现金，未来折旧压力大', transform=a2.transAxes, ha='left', va='top', fontsize=8, color=INK2)
note(fig, '左：两阶段模型（10 年 g + 3% 永续），以远期 EPS 近似可分配现金，折现率 r=4.86%+β_Blume×4.5%。右：AMZN FCF 为负未画；GOOGL/AMZN 净利含大额投资公允价值收益。')
fig.tight_layout()
save(fig, 'f6_valuation')

# ---------------------------------------------------------------- F7 portfolio weights vs risk contributions
ho = pd.DataFrame(DS['holdings'])
ho = ho.iloc[::-1]
fig, ax = plt.subplots(figsize=(7.2, 5.6))
y = np.arange(len(ho))
ax.barh(y + 0.19, ho['weight'], height=0.36, color=BLUE, label='资金权重', zorder=2)
ax.barh(y - 0.19, ho['rc'], height=0.36, color=ORANGE, label='风险贡献（Euler 分解）', zorder=2)
ax.set_yticks(y, [f"{t}  {n}" for t, n in zip(ho['ticker'], ho['name'])])
ax.axvline(0, color=INK2, lw=1); ax.xaxis.set_major_formatter(pct)
for yi, w, rc in zip(y, ho['weight'], ho['rc']):
    ax.text(max(w, rc, 0) + 0.004, yi, f'{w:.0%} / {rc:+.1%}', va='center', fontsize=7.5, color=INK2)
ax.set_xlim(-0.08, 0.24)
ax.legend(loc='lower right', fontsize=8)
ax.grid(axis='y', visible=False)
ax.set_title('本方案：资金权重 vs 风险贡献（Ledoit-Wolf 协方差）')
note(fig, '风险贡献 RC_i = w_i·(Σw)_i / (w·Σw)，合计 100%。对冲腿的 RC 为负 = 它们在降低组合方差。')
save(fig, 'f7_portfolio')

# ---------------------------------------------------------------- F8 backtests
cv = pd.DataFrame(DS['curves']); cv['date'] = pd.to_datetime(cv['date'])
SC = {'FINAL': (BLUE, '本方案 70/30'), 'NVDA': (ORANGE, '单押 NVDA'), 'SMH': (AQUA, '半导体 ETF'), 'SPY': (GRAY, '标普 500')}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.6))
for ax, win, title in [(a1, '3y', '2023-11-13 → 2026-11-13（样本内，月度再平衡）'), (a2, '2022', '2022 加息熊市压力测试：2022-01-03 → 10-12（样本外）')]:
    d = cv[cv.window == win]
    for s, (c, lab) in SC.items():
        z = d[d.series == s]
        ax.plot(z['date'], z['value'], color=c, lw=2 if s == 'FINAL' else 1.6, label=lab, zorder=3 if s == 'FINAL' else 2)
        ax.text(z['date'].iloc[-1], z['value'].iloc[-1], f"  {z['value'].iloc[-1] - 1:+.0%}", color=c, fontsize=8, va='center')
    ax.set_title(title, fontsize=10)
    ax.axhline(1, color=INK2, lw=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x', labelsize=8)
a1.set_yscale('log'); a1.set_yticks([0.8, 1, 1.5, 2, 3, 4, 5]); a1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.1f}×'))
a2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.1f}×'))
a1.legend(loc='upper left', fontsize=8)
a2.set_xlim(right=pd.Timestamp('2022-11-25'))
a2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 3, 5, 7, 9, 11])); a2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
note(fig, '左图为对数轴；权重来自同一窗口的协方差估计，属样本内，不代表未来收益。右图窗口不在估计期内。')
fig.tight_layout()
save(fig, 'f8_backtests')

# ---------------------------------------------------------------- F9 risk dial + bootstrap
dl = pd.DataFrame(DS['dial']).sort_values('ai_share')
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.4), gridspec_kw=dict(width_ratios=[1, 1.2]))
x = dl['ai_share']
for col, c, mk, lab in [('r22', ORANGE, 's', '2022 压力情景亏损（样本外）'), ('mdd05', AQUA, 'D', '一年内最大回撤，5% 最坏情形（自助法）'), ('vol_lw', BLUE, 'o', '事前年化波动（Ledoit-Wolf）')]:
    yv = dl[col].abs()
    a1.plot(x, yv, color=c, marker=mk, lw=2, ms=6, label=lab)
    for xi, vi in zip(x, yv):
        a1.annotate(f'{vi:.0%}', (xi, vi), xytext=(0, -14 if col == 'mdd05' else 7), textcoords='offset points', ha='center', fontsize=7.5, color=c)
a1.axvline(0.7, color=AXIS, lw=1); a1.text(0.705, 0.115, '本方案', fontsize=8, color=INK2, va='bottom')
a1.set_ylim(0.1, 0.5); a1.set_xlim(0.56, 1.04)
a1.xaxis.set_major_formatter(pct); a1.yaxis.set_major_formatter(pct)
a1.set_xlabel('AI 篮子资金占比'); a1.set_title('风险旋钮：AI 占比越高，尾部越厚（数值取绝对值）', fontsize=10)
a1.legend(loc='upper left', fontsize=8)
order = [('NVDA', '单押 NVDA'), ('SMH', '半导体 ETF'), ('AI100', '纯 AI 篮子'), ('QQQ', '纳指 100'), ('AI80', 'AI 80%'), ('FINAL', '本方案 70%'), ('AI60', 'AI 60%'), ('SPY', '标普 500')]
res = {**BT['res'], 'AI60': BT60['res']['AI60']}
for i, (k, lab) in enumerate(order):
    m = res[k]; c = BLUE if k == 'FINAL' else GRAY
    a2.plot([m['b05'], m['b95']], [i, i], color=c, lw=1.4)
    a2.plot([m['b25'], m['b75']], [i, i], color=c, lw=6, solid_capstyle='round')
    a2.plot(m['b50'], i, 'o', color='white', mec=c, ms=6, mew=1.6)
    a2.text(m['b95'] + 0.03, i, f"5%:{m['b05']:+.0%}  中位:{m['b50']:+.0%}  95%:{m['b95']:+.0%}", va='center', fontsize=7.2, color=INK2)
a2.set_yticks(range(len(order)), [l for _, l in order]); a2.axvline(0, color=INK2, lw=0.8)
a2.xaxis.set_major_formatter(pct); a2.set_xlim(-0.55, 2.35)
a2.grid(axis='y', visible=False)
a2.set_title('一年收益分布（平稳块自助法 4000 路径，漂移=CAPM 预期）', fontsize=10)
note(fig, '细线 5–95% 分位，粗线 25–75%，圆点中位数。自助法用去均值的 3 年日对数收益 + CAPM 漂移（rf+β×4.5%），只刻画风险形状，不外推过去三年的牛市回报。')
fig.tight_layout()
save(fig, 'f9_risk_dial')
print('figures:', sorted(os.listdir('figures')))
