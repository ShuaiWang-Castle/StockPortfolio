#!/usr/bin/env python3
"""Figure for claude_analysis_20261124 (reads out/ only).
Run: python3 -I claude_analysis_20261124/make_figures_20261124.py <repo_root>"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261124'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'   # validate_palette.js --mode light --surface #fcfcfb: pass (AQUA contrast warn -> direct labels)
INK, INK2, GRID, BASE, SURF, MUTED = '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb', '#898781'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': BASE,
                     'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 10.5,
                     'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'path.simplify': False})

S = json.loads((OUT / 'summary.json').read_text())
INF = pd.read_csv(OUT / 'inflation_monthly.csv')
GDP = pd.read_csv(OUT / 'gdp_quarterly.csv')
LAB = pd.read_csv(OUT / 'labor_monthly.csv')
RAT = pd.read_csv(OUT / 'rates_monthly.csv')
MKT = pd.read_csv(OUT / 'markets.csv')
for df in (INF, LAB, RAT):
    df['t'] = pd.to_datetime(df['month'] + '-15')
RAT.loc[RAT.month == '2026-11', 't'] = pd.Timestamp('2026-11-23')
X0, X1 = pd.Timestamp('2024-11-20'), pd.Timestamp('2027-01-25')


def month_axis(ax):
    ax.set_xlim(X0, X1)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))


def end_label(ax, t, y, txt, col, dy=0):
    ax.annotate(txt, (t, y), xytext=(5, dy), textcoords='offset points', va='center', fontsize=8.4, color=INK2)
    ax.scatter([t], [y], s=22, color=col, zorder=4, edgecolor=SURF, linewidth=0.8)


fig, axs = plt.subplots(2, 3, figsize=(14.2, 8.4))
(a, b, c), (d, e, f) = axs

# (a) inflation: realized vs market-implied
a.axhline(2.0, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
a.text(X0 + pd.Timedelta(days=8), 1.93, '2% 目标', fontsize=8.2, color=INK2, va='top')
a.plot(INF.t, INF.cpi_yoy_pct, color=BLUE, lw=2, zorder=3, label='CPI 同比（实际）')
a.plot(RAT.t, RAT.t10yie, color=ORANGE, lw=2, zorder=3, label='10 年 breakeven（市场预期）')
last = INF.dropna(subset=['cpi_yoy_pct']).iloc[-1]
end_label(a, last.t, last.cpi_yoy_pct, f'{last.cpi_yoy_pct:.1f}%（9 月）', BLUE, 4)
t10 = S['inflation']['t10yie_now']
end_label(a, pd.Timestamp(t10['date']), t10['value'], f"{t10['value']:.2f}%（11/23）", ORANGE, -2)
pk = S['inflation']['cpi_yoy_peak_2026']
a.annotate(f'5 月 {pk[0]:.1f}%', (pd.Timestamp(pk[1] + '-15'), pk[0]), xytext=(6, 0), textcoords='offset points',
           ha='left', va='center', fontsize=8.2, color=INK2)
a.annotate('2025-10 无数据（停摆）', (pd.Timestamp('2025-10-15'), 2.85), xytext=(0, 26), textcoords='offset points',
           ha='center', fontsize=7.8, color=MUTED, arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7))
a.set_ylim(1.4, 4.6)
a.set_ylabel('%')
month_axis(a)
a.set_title('通胀：实际 3.7%，市场预期 2.1% 且在回落')
a.legend(loc='upper left', frameon=False, fontsize=8.3)

# (b) growth
g = GDP[GDP.quarter >= '2025Q1'].reset_index(drop=True)
xs = np.arange(len(g) + 1)
b.bar(xs[:-1], g.saar_pct, width=0.62, color=BLUE, zorder=3)
q4 = S['growth']['gdpnow_q4']
b.bar(xs[-1], q4, width=0.62, color=SURF, edgecolor=BLUE, hatch='////', linewidth=1.2, zorder=3)
for x, v in zip(xs, list(g.saar_pct) + [q4]):
    b.text(x, v + 0.08, f'{v:.1f}', ha='center', va='bottom', fontsize=8.4, color=INK2)
b.axhline(2.1, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
b.legend(handles=[Line2D([], [], color=MUTED, lw=1, ls=(0, (4, 3)), label='CBO 潜在增速 2.1%（2026–30 年均）'),
                  Patch(facecolor=SURF, edgecolor=BLUE, hatch='////', label='Q4：Atlanta Fed GDPNow 追踪值（11/18）')],
         loc='upper left', frameon=False, fontsize=8.1)
b.set_xticks(xs, [q.replace('20', '', 1) for q in g.quarter] + ['26Q4\nGDPNow'])
b.text(3, 0.75, '停摆', ha='center', fontsize=7.8, color=MUTED)
b.set_ylim(0, 5.6)
b.set_ylabel('实际 GDP 环比折年率 (%)')
b.set_title('增长：2026 年三个季度都在潜在增速以上')
b.grid(axis='x', visible=False)

# (c) labor
c.plot(LAB.t, LAB.unrate, color=BLUE, lw=2, zorder=3)
c.scatter(LAB.t, LAB.unrate, s=10, color=BLUE, zorder=3)
trig = S['labor']['sahm_gap_oct2026']
lvl = LAB.unrate_3m_avg.iloc[-1] - trig + 0.5
c.axhline(lvl, color=MUTED, lw=1, ls=(0, (4, 3)))
c.text(X0 + pd.Timedelta(days=8), lvl + 0.02, f'Sahm 触发线 ≈ {lvl:.2f}%（3 个月均值高于近 12 个月低点 0.5）',
       fontsize=8.0, color=INK2, va='bottom')
end_label(c, LAB.t.iloc[-1], LAB.unrate.iloc[-1], f'{LAB.unrate.iloc[-1]:.1f}%（10 月）', BLUE, -2)
nov = LAB[LAB.month == '2025-11'].iloc[0]
c.annotate(f'{nov.unrate:.1f}%（2025-11）', (nov.t, nov.unrate), xytext=(0, 8), textcoords='offset points',
           ha='center', fontsize=8.2, color=INK2)
c.set_ylim(3.8, 4.85)
c.set_ylabel('失业率 (%)')
month_axis(c)
c.set_title(f"就业：失业率 4.5%→4.1%，Sahm 差值 {trig:.1f}，没有衰退信号")

# (d) rates
d.plot(RAT.t, RAT.ust10y, color=BLUE, lw=2, label='10 年期国债（月末）')
d.plot(RAT.t, RAT.real10y, color=ORANGE, lw=2, label='10 年实际利率 = 10 年 − breakeven')
eff = RAT.dropna(subset=['effr_monthly_avg'])
d.plot(eff.t, eff.effr_monthly_avg, color=AQUA, lw=2, drawstyle='steps-mid', label='联邦基金有效利率（月均）')
lr = RAT.iloc[-1]
end_label(d, lr.t, lr.ust10y, f'{lr.ust10y:.2f}%', BLUE, 3)
end_label(d, lr.t, lr.real10y, f'{lr.real10y:.2f}%', ORANGE, -3)
end_label(d, eff.t.iloc[-1], eff.effr_monthly_avg.iloc[-1], f'{eff.effr_monthly_avg.iloc[-1]:.2f}%', AQUA, -7)
d.annotate('9/16 加息', (pd.Timestamp('2026-09-15'), 3.75), xytext=(-6, -22), textcoords='offset points', ha='right',
           fontsize=8.2, color=INK2, arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7))
d.set_ylim(1.4, 6.25)
d.set_ylabel('%')
month_axis(d)
d.set_title('利率：Fed 重新加息，长端实际利率升到 ~2.8%')
d.legend(loc='upper left', frameon=False, fontsize=8.1, ncol=1)

# (e) markets
order = ['^GSPC', '^IXIC', 'BZUSD', 'GCUSD', 'BTCUSD']
names = {'^GSPC': 'S&P 500', '^IXIC': '纳斯达克', 'BZUSD': '布伦特原油', 'GCUSD': '黄金', 'BTCUSD': '比特币'}
mk = MKT.set_index('symbol').loc[order]
ys = np.arange(len(order))[::-1]
e.barh(ys, mk.drawdown_from_52w_high_pct, height=0.58, color=BLUE, zorder=3)
for y, v in zip(ys, mk.drawdown_from_52w_high_pct):
    e.text(v - 0.8, y, f'{v:.1f}%'.replace('-', '−'), ha='right', va='center', fontsize=8.4, color=INK2, zorder=4,
           bbox=dict(boxstyle='square,pad=0.12', fc=SURF, ec='none'))
for xv, txt, dx, ha in [(-10, '−10% 回调', 0.6, 'left'), (-20, '熊市 −20%', -0.6, 'right')]:
    e.axvline(xv, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
    e.text(xv + dx, ys[0] + 0.52, txt, fontsize=8.0, color=INK2, va='bottom', ha=ha)
e.set_yticks(ys, [names[s] for s in order])
e.set_xlim(-58, 2)
e.set_ylim(-0.6, len(order) - 0.1)
e.set_xlabel('距 52 周高点 (%)；股指为 11/23 收盘，其余 11/24 凌晨报价')
e.set_title('资产价格：股市回调，金/油/币跌 26–48%')
e.grid(axis='y', visible=False)

# (f) valuation
pe = S['valuation_credit']['sp500_forward_pe']
labs = ['2025 年底', '5 年均值', '10 年均值', '2026-11-05']
vals = [pe['forward_pe_end_2025'], pe['avg_5y'], pe['avg_10y'], pe['sp500_forward_pe']]
ys = np.arange(4)[::-1]
f.barh(ys, vals, height=0.58, color=[BLUE, BLUE, BLUE, ORANGE], zorder=3)
for y, v in zip(ys, vals):
    f.text(v + 0.25, y, f'{v:.1f}x', va='center', fontsize=8.4, color=INK2)
f.set_yticks(ys, labs)
f.set_xlim(0, 25.5)
f.set_xlabel('S&P 500 远期 12 个月市盈率（FactSet）')
f.set_title('估值：远期 P/E 17.7，低于 5/10 年均值（盈利预期上修）')
f.grid(axis='y', visible=False)

fig.suptitle('美国宏观与市场温度（截至 2026-11-23）：经济偏热，市场降温，没有通缩或萧条信号',
             x=0.01, ha='left', fontsize=12.5, fontweight='bold')
fig.text(0.01, 0.006, '数据：FMP（FRED/BLS/BEA/美国财政部报价）、BEA、Atlanta Fed GDPNow、ISM、FactSet、CBO；'
         '计算见 macro_regime_20261124.py 与 out/*.csv。', fontsize=8.0, color=INK2)
fig.tight_layout(rect=(0, 0.02, 1, 0.965), h_pad=2.2, w_pad=2.0)
fig.savefig(FIG / 'f1_macro_market_dashboard.png', dpi=150)
print('wrote', FIG / 'f1_macro_market_dashboard.png')
