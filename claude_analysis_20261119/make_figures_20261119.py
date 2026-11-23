#!/usr/bin/env python3
"""Figure for claude_analysis_20261119 (reads data/ and out/ only). Run: python3 -I claude_analysis_20261119/make_figures_20261119.py <repo_root>"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261119'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'          # validated: validate_palette.js --mode light --surface #fcfcfb
INK, INK2, GRID, BASE, SURF, MUTED = '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb', '#898781'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'savefig.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 10.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})

F = json.loads((HERE / 'data' / 'ant_ipo_facts_20261119.json').read_text())['financials_musd']
S = json.loads((OUT / 'summary.json').read_text())
q = [x.replace(' 20', "'") for x in F['quarters']]
rev, comp, oi = (np.array(F[k]) / 1e3 for k in ('revenue', 'compute', 'operating_income'))
fig, (a, b) = plt.subplots(1, 2, figsize=(10.6, 4.4))
x = np.arange(len(q))
w = 0.38
a.bar(x - w / 2, rev, w, color=BLUE, label='收入', zorder=3)
a.bar(x + w / 2, comp, w, color=ORANGE, label='算力与基础设施成本', zorder=3)
a.plot(x, oi, color=INK, lw=1.4, marker='o', ms=5, mfc=SURF, mec=INK, mew=1.4, zorder=4, label='经营利润（GAAP）')
a.axhline(0, color=BASE, lw=1)
for i in (len(q) - 1,):
    a.annotate(f'{rev[i]:.1f}', (x[i] - w / 2, rev[i]), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8.4)
    a.annotate(f'{comp[i]:.1f}', (x[i] + w / 2, comp[i]), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8.4)
a.set_xticks(x, q)
a.set_ylabel('十亿美元')
a.set_ylim(-4, 19)
a.set_title('收入一年涨了约 12 倍；算力成本从收入的 2.5 倍降到 58%')
a.legend(loc='upper left', frameon=False, fontsize=8.4)
a.grid(axis='x', visible=False)

C = pd.read_csv(OUT / 'rc_curve_new_money.csv')
for s, col, lab in [(0.5, AQUA, 'ANT 年化波动 50%'), (0.7, BLUE, 'ANT 年化波动 70%（基准）'), (0.9, ORANGE, 'ANT 年化波动 90%')]:
    c = C[C.sigma == s]
    b.plot(100 * c.ant_weight, 100 * c.rc_ant, color=col, lw=2.2 if s == 0.7 else 1.6, zorder=3, label=lab)
rg = 100 * S['risk_model']['rc_googl_in_monday_plan']
b.axhline(rg, color=INK2, lw=1, ls=(0, (4, 3)), zorder=2)
b.text(9.85, rg - 0.6, f'GOOGL 现在占组合风险 {rg:.1f}%', fontsize=8.2, color=INK2, va='top', ha='right')
b.axhline(30.3, color=INK2, lw=1, ls=(0, (1, 2)), zorder=2)
b.text(0.2, 30.9, 'NVDA 现在占组合风险 30.3%', fontsize=8.2, color=INK2, va='bottom')
for wv in (3, 5):
    r = C[(C.sigma == 0.7) & (np.isclose(100 * C.ant_weight, wv))].iloc[0]
    b.scatter([wv], [100 * r.rc_ant], s=40, color=BLUE, edgecolor=SURF, linewidth=1.2, zorder=4)
    b.annotate(f'{wv}% → {100 * r.rc_ant:.1f}%', (wv, 100 * r.rc_ant), xytext=(10, -10), textcoords='offset points', ha='left', va='top', fontsize=8.4)
b.set_xlim(0, 10)
b.set_ylim(0, 34)
b.set_xlabel('ANT 占组合比例 (%)，新增资金买入')
b.set_ylabel('ANT 占组合风险 (%)')
b.set_title('3–4% 的 ANT，风险相当于一只 GOOGL')
b.legend(loc='upper left', bbox_to_anchor=(0.0, 0.86), frameon=False, fontsize=8.4)
fig.suptitle('Anthropic：增长和算力成本的拐点已经出现，但新股的波动决定了仓位要小', x=0.01, ha='left', fontsize=11, fontweight='bold', y=1.03)
fig.text(0.01, -0.05, '左：S-1/A 季度数据（第三方摘要转录）。右：ANT 没有历史价格，假设其收益 = 1.25 × AI8 等权组合 + 独立噪声，年化波动取 50/70/90%；'
         '其余资产用与 11/15 方案相同的 3 年协方差。', fontsize=7.8, color=INK2)
fig.tight_layout()
fig.savefig(FIG / 'f1_ant_growth_and_sizing.png', dpi=200, bbox_inches='tight')
print('ok')
