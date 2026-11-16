#!/usr/bin/env python3
"""Figures for claude_analysis_20261115 (reads out/ only). Run: python3 -I claude_analysis_20261115/make_figures_20261115.py <repo_root>"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261115'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
S = json.loads((OUT / 'summary.json').read_text())
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'
MUTED, INK, INK2, GRID, BASE, SURF = '#898781', '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'savefig.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})


def save(fig, name):
    fig.savefig(FIG / name, dpi=200, bbox_inches='tight')
    plt.close(fig)


# F1 timing map ---------------------------------------------------------------
T = pd.read_csv(OUT / 'timing_table_ai8.csv').set_index('t')
ACT = {'buy at target': ('按目标买入', BLUE), 'overweight': ('加码', ORANGE), 'stage': ('分批（估值偏贵）', AQUA),
       'underweight + stage': ('减配 + 分批', YELLOW), 'underweight (cycle-adjusted)': ('减配（周期顶部）', MAGENTA)}
fig, ax = plt.subplots(figsize=(9.2, 5.2))
ax.axhspan(-45, -20, color=GRID, alpha=0.45, lw=0, zorder=0)
ax.axhspan(-10, 2, color=GRID, alpha=0.45, lw=0, zorder=0)
ax.text(26.6, -44, '相对低位：距 52 周高点 ≥20% 且低于 200 日均线', ha='right', va='bottom', fontsize=8.2, color=INK2)
ax.text(26.6, 1.2, '相对高位：距高点 ≤10% 且高于 200 日均线', ha='right', va='top', fontsize=8.2, color=INK2)
off = {'NVDA': (8, -4), 'TSM': (-10, -10), 'AVGO': (8, -4), 'MU': (8, 0), 'GOOGL': (-8, -12), 'META': (9, 9), 'MSFT': (-10, 8), 'AMZN': (10, -10)}
SIZE = {'AMZN': 170, 'MSFT': 55}
Z = {'AMZN': 3, 'MSFT': 4}
for t, r in T.iterrows():
    lab, c = ACT[r.action]
    hollow = r.action.startswith('underweight (cycle')
    ax.scatter(r.pe_ntm, 100 * r.dd_from_hi52, s=SIZE.get(t, 90), color=SURF if hollow else c, edgecolor=SURF if not hollow else c,
               linewidth=2.2 if hollow else 1.0, zorder=Z.get(t, 3))
    dx, dy = off[t]
    ax.annotate(f'{t}  {lab}', (r.pe_ntm, 100 * r.dd_from_hi52), xytext=(dx, dy), textcoords='offset points',
                ha='left' if dx > 0 else 'right', va='center', fontsize=8.8, color=INK)
ax.set_xlim(0, 27)
ax.set_ylim(-45, 2)
ax.set_xlabel('NTM 市盈率（一致预期；AVGO、MU 为 11/13 快照）  ← 更便宜 · 更贵 →')
ax.set_ylabel('距 52 周收盘高点 (%)')
ax.set_title('只有 NVDA 同时满足"估值最便宜 + 价格相对低位"；MU 的低市盈率来自周期顶部的利润率')
ax.text(0, -0.17, '价格截至 2026-11-13 收盘（复权）。估值分档按 NTM 市盈率、经营利润/EV、PEG 三项排名平均；MU 毛利率 86.8%（一年前 44.7%），不参与估值排名。',
        transform=ax.transAxes, fontsize=7.8, color=INK2)
save(fig, 'f1_timing_map.png')

# F2 NVDA own history ---------------------------------------------------------
H = pd.read_csv(OUT / 'nvda_own_history.csv').set_index('fiscalYear')
xl = ['FY22', 'FY23', 'FY24', 'FY25', 'FY26', 'TTM\n11/13']
x = np.arange(len(H))
fig, axes = plt.subplots(2, 2, figsize=(10, 6.2))
panels = [(axes[0, 0], [('evToEBITDA', 'EV/EBITDA', ORANGE, '{:.1f}')], '估值：EV/EBITDA 为 5 个财年来最低', None),
          (axes[0, 1], [('freeCashFlowYield', '自由现金流收益率', ORANGE, '{:.1%}')], '估值：自由现金流收益率为 5 年最高', 'pct'),
          (axes[1, 0], [('incomeQuality', '经营现金流 / 净利润', BLUE, '{:.2f}')], '质量：现金转化为 5 年最差', None),
          (axes[1, 1], [('daysOfSalesOutstanding', '应收天数 DSO', BLUE, '{:.0f}'), ('daysOfInventoryOutstanding', '存货天数 DIO', AQUA, '{:.0f}')],
           '质量：应收与存货天数都在上升', None)]
for ax, series, ttl, fmt in panels:
    for col, lab, c, f in series:
        y = H[col].to_numpy()
        ax.plot(x, y, color=c, lw=2, marker='o', ms=5, label=lab, zorder=3)
        for xi, yi in zip(x, y):
            ax.annotate(f.format(yi), (xi, yi), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=7.8)
    ax.axvspan(len(H) - 1.5, len(H) - 0.5, color=GRID, alpha=0.5, lw=0)
    ax.set_xticks(x, xl, fontsize=8.2)
    ax.set_title(ttl, fontsize=10)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + (hi - lo) * 0.12)
    if fmt == 'pct':
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=1))
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8.2, loc='center', bbox_to_anchor=(0.27, 0.33))
fig.suptitle('NVDA：按自身历史，估值是 5 年来最便宜；但盈利的现金含量也是 5 年来最差', x=0.01, ha='left', fontsize=11.5, fontweight='bold')
fig.text(0.01, -0.02, 'FMP key-metrics：FY 为各财年末（1 月底）的市场数据，TTM 为 2026-11-13 收盘价配最近 4 个季度。', fontsize=7.8, color=INK2)
fig.tight_layout()
save(fig, 'f2_nvda_own_history.png')

# F3 deployment plan ------------------------------------------------------------
pl = S['plan']
order = ['NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSM', 'AVGO', 'MU', 'VTI', 'BRK-B', 'XLV', 'SGOV']
d0 = np.array([pl['day0'][t] for t in order]) * 100
tg = np.array([pl['tilt_target'][t] for t in order]) * 100
bs = np.array([pl['base'][t] for t in order]) * 100
fig, ax = plt.subplots(figsize=(9.4, 5.4))
y = np.arange(len(order))[::-1]
ax.barh(y, d0, color=BLUE, height=0.62, label='11/16 买入（SGOV 含暂缓资金）', zorder=3, edgecolor=SURF, linewidth=1.5)
dfr = np.where(np.array(order) == 'SGOV', 0, tg - d0)
ax.barh(y, dfr, left=d0, color=AQUA, height=0.62, label='按规则暂缓的部分', zorder=3, edgecolor=SURF, linewidth=1.5)
ax.scatter(bs, y, marker='|', s=260, color=INK, linewidth=2, zorder=4, label='Hybrid-核心原目标')
for yi, t, a, b, c in zip(y, order, d0, tg, bs):
    txt = f'{a:.1f}%' if t == 'SGOV' else (f'{a:.1f} → {b:.1f}%' if b - a > 1e-9 else f'{b:.1f}%')
    if abs(b - c) > 1e-9 and t != 'SGOV':
        txt += f'（原 {c:.0f}%）'
    ax.text(max(a, b, c) + 0.6, yi, txt, va='center', fontsize=8.6)
ax.set_yticks(y, order)
ax.set_xlim(0, 33)
ax.set_xlabel('占 $7,000 的比例 (%)')
ax.grid(axis='y', visible=False)
ax.legend(frameon=False, fontsize=8.3, loc='lower right')
ax.set_title('部署方案：NVDA 加到 12.5%（财报前先 7.5%），MSFT、MU 减配，AVGO、MSFT 分批')
save(fig, 'f3_deployment_plan.png')
print(sorted(p.name for p in FIG.glob('*.png')))
