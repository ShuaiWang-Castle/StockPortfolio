#!/usr/bin/env python3
"""Figure for claude_analysis_20261117 (reads out/ only). Run: python3 -I claude_analysis_20261117/make_figures_20261117.py <repo_root>"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261117'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
BLUE, ORANGE = '#2a78d6', '#eb6834'                       # validated: validate_palette.js --mode light --surface #fcfcfb
INK, INK2, GRID, BASE, SURF = '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'savefig.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 10.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})

Q = pd.read_csv(OUT / 'nvda_quarterly_quality.csv').iloc[::-1].reset_index(drop=True)      # oldest first
x = np.arange(len(Q))
fig, (a, b) = plt.subplots(1, 2, figsize=(10.4, 4.3))
wbar = 0.36
a.bar(x - wbar / 2, Q.net_income_B, wbar, color=ORANGE, label='净利润', zorder=3)
a.bar(x + wbar / 2, Q.ocf_B, wbar, color=BLUE, label='经营现金流', zorder=3)
for i, r in Q.iterrows():
    a.text(i, max(r.net_income_B, r.ocf_B) + 2.0, f'{r.ocf_to_ni:.2f}', ha='center', va='bottom', fontsize=8.6, color=INK)
a.text(-0.55, 74, '柱顶数字 = 经营现金流 / 净利润', fontsize=8.2, color=INK2, va='top')
a.set_xticks(x, Q.quarter)
a.set_ylim(0, 76)
a.set_ylabel('十亿美元')
a.set_title('Q3 经营现金流回到净利润的 0.74 倍（Q2 只有 0.40 倍）')
a.legend(loc='upper left', bbox_to_anchor=(0.0, 0.93), frameon=False, fontsize=8.5)
a.grid(axis='x', visible=False)

b.plot(x, Q.dso_days, color=BLUE, lw=2, marker='o', ms=6, mec=SURF, mew=1.2, zorder=3, label='应收账款天数 DSO')
b.plot(x, Q.dio_days, color=ORANGE, lw=2, marker='o', ms=6, mec=SURF, mew=1.2, zorder=3, label='存货天数 DIO')
for col, dy in [('dso_days', -11), ('dio_days', 9)]:
    b.annotate(f'{Q[col].iloc[-1]:.0f} 天', (x[-1], Q[col].iloc[-1]), xytext=(8, dy), textcoords='offset points', fontsize=8.8, color=INK, va='center')
b.set_xticks(x, Q.quarter)
b.set_xlim(-0.4, len(Q) - 0.4)
b.set_ylim(30, 140)
b.set_ylabel('天（按 91 天季度）')
b.set_title('应收账款天数从 45 天升到 64 天，公司解释为大额多季度合同的付款期延长')
b.legend(loc='center left', frameon=False, fontsize=8.5)
fig.suptitle('NVDA 五个季度的盈利质量：现金转化回升，但更多利润挂在应收账款上', x=0.01, ha='left', fontsize=11, fontweight='bold', y=1.03)
fig.text(0.01, -0.04, 'DSO = 季末应收 ÷ 当季收入 × 91，与公司披露的 64 天 / 60 天一致；DIO = 季末存货 ÷ 当季销售成本 × 91。数据：FMP 季度报表，Q3 FY27 于 2026-11-17 发布。',
         fontsize=7.8, color=INK2)
fig.tight_layout()
fig.savefig(FIG / 'f1_nvda_quality_5q.png', dpi=200, bbox_inches='tight')
print('ok')
