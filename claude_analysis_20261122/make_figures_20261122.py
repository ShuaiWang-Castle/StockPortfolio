#!/usr/bin/env python3
"""Figures for claude_analysis_20261122 (reads out/ only).
Run: python3 -I claude_analysis_20261122/make_figures_20261122.py <repo_root>"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261122'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'   # validated: validate_palette.js --mode light --surface #fcfcfb
INK, INK2, GRID, BASE, SURF, MUTED = '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb', '#898781'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': BASE,
                     'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 10.5,
                     'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'svg.hashsalt': 'fixed',
                     'path.simplify': False})

S = json.loads((OUT / 'summary.json').read_text())
E = pd.read_csv(OUT / 'episodes.csv')
A = pd.read_csv(OUT / 'after_first_close_at_current_dd.csv')
E['year'] = pd.to_datetime(E.peak_date).dt.year + pd.to_datetime(E.peak_date).dt.dayofyear / 366
cur_dd = 100 * S['definition']['current_drawdown']

# ---------------------------------------------------------------- figure 1
fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 4.5), gridspec_kw={'width_ratios': [1.05, 1]})
done = E[E.status == 'completed']
for rec, col, lab in [(False, BLUE, '与衰退不重叠'), (True, ORANGE, '与 NBER 衰退重叠')]:
    d = done[done.recession_overlap == rec]
    a.scatter(d.year, 100 * d.max_drawdown, s=34, color=col, edgecolor=SURF, linewidth=1.0, zorder=3,
              label=f'{lab}（{len(d)} 次）')
c = E[E.status == 'ongoing'].iloc[0]
a.scatter([c.year], [100 * c.max_drawdown], s=70, color=AQUA, edgecolor=INK, linewidth=0.8, zorder=4,
          label=f'本轮（10/6→11/20，{100 * c.max_drawdown:.1f}%，未结束）')
a.axhline(cur_dd, color=INK2, lw=1, ls=(0, (1, 2)), zorder=2)
a.text(1987.6, cur_dd - 1.0, '−18.05%：本轮目前的位置', fontsize=8.2, color=INK2, va='top')
for pk, txt, dx, dy in [('1973-01-11', '1973–74', 8, -2), ('2000-03-10', '2000–02', -8, 2),
                        ('2007-10-31', '2007–09', 8, -2), ('1987-08-27', '1987', 6, -2),
                        ('2021-11-19', '2022', 6, -10), ('2020-02-19', '2020', -6, -12)]:
    r = E[E.peak_date == pk].iloc[0]
    a.annotate(txt, (r.year, 100 * r.max_drawdown), xytext=(dx, dy), textcoords='offset points',
               ha='left' if dx > 0 else 'right', fontsize=8.2, color=INK2)
a.set_xlim(1970, 2028)
a.set_ylim(-82, -5)
a.set_ylabel('从高点到低点的最大跌幅 (%)')
a.set_title(f'1971 年以来纳指 {len(done)} 次 ≥10% 下跌，17 次跌到本轮位置')
a.legend(loc='upper left', bbox_to_anchor=(0.0, 0.53), frameon=False, fontsize=8.4)

paths = S['paths_after_cross']
x = np.arange(253)
meds = {}
for rec, col in [(False, BLUE), (True, ORANGE)]:
    keys = [r.peak_date for r in A.itertuples() if bool(r.recession_overlap) == rec]
    mat = np.full((len(keys), 253), np.nan)
    for i, k in enumerate(keys):
        p = 100 * np.array(paths[k])
        mat[i, :len(p)] = p
        b.plot(x[:len(p)], p, color=col, lw=0.8, alpha=0.45, zorder=2)
    meds[rec] = np.nanmedian(mat, axis=0)
    b.plot(x, meds[rec], color=col, lw=2.4, zorder=3,
           label=f'{"与衰退重叠" if rec else "与衰退不重叠"}：中位数（{len(keys)} 次）')
b.axhline(0, color=BASE, lw=1)
for k, txt in [('2000-03-10', '2000'), ('2007-10-31', '2008'), ('2021-11-19', '2022'), ('1998-07-20', '1998')]:
    p = 100 * np.array(paths[k])
    b.annotate(txt, (len(p) - 1, p[-1]), xytext=(3, 0), textcoords='offset points', va='center', fontsize=8.2,
               color=INK2)
b.set_xlim(0, 275)
b.set_xlabel('第一次收在 −18.05% 之后的交易日')
b.set_ylabel('相对那一天的涨跌 (%)')
nr = S['after_first_close_at_current_dd']['no_recession']['ret_252d']
rr = S['after_first_close_at_current_dd']['recession']['ret_252d']
b.set_title(f'之后一年：不重叠衰退的 {nr["n"]} 次中 {round(nr["share_positive"] * nr["n"])} 次为正，'
            f'重叠的 {rr["n"]} 次中 {round(rr["share_positive"] * rr["n"])} 次')
b.legend(loc='upper left', frameon=False, fontsize=8.4)
fig.tight_layout()
fig.savefig(FIG / 'f1_nasdaq_drawdowns_since_1971.png', dpi=150, metadata={'Software': None})
plt.close(fig)

# ---------------------------------------------------------------- figure 2
sig = E[E.ust10y_change_bp.notna() & (E.status == 'completed')]
cur = E[E.status == 'ongoing'].iloc[0]
sig = sig.assign(usd_change=1 / (1 + sig.eurusd_change) - 1)
cur = cur.copy()
cur['usd_change'] = 1 / (1 + cur.eurusd_change) - 1
panels = [('ust10y_change_bp', '10 年期美债收益率变化 (bp)', 1),
          ('gold_change', '黄金涨跌 (%)', 100),
          ('usd_change', '美元兑欧元涨跌 (%)', 100),
          ('vix_max', '期间 VIX 最高收盘', 1)]
fig, axs = plt.subplots(1, 4, figsize=(11.2, 3.7))
rng = np.random.default_rng(7)
for ax, (col, title, mult) in zip(axs, panels):
    for xpos, rec, color in [(0, True, ORANGE), (1, False, BLUE)]:
        v = mult * sig[sig.recession_overlap == rec][col].to_numpy(dtype=float)
        ax.bar(xpos, np.median(v), width=0.6, color=color, alpha=0.85, zorder=2)
        ax.scatter(xpos + rng.uniform(-0.17, 0.17, len(v)), v, s=16, color=INK2, zorder=3, linewidths=0)
    cv = mult * float(cur[col])
    ax.bar(2, cv, width=0.6, color=AQUA, zorder=2)
    ax.annotate(f'{cv:+.1f}' if col in ('gold_change', 'usd_change') else (f'{cv:+.0f}' if col != 'vix_max' else f'{cv:.1f}'), (2, cv),
                xytext=(0, 3 if cv >= 0 else -3), textcoords='offset points', ha='center',
                va='bottom' if cv >= 0 else 'top', fontsize=8.6)
    allv = np.concatenate([mult * sig[col].to_numpy(dtype=float), [cv]])
    lo, hi = min(0, allv.min()), max(0, allv.max())
    ax.set_ylim(0 if col == 'vix_max' else lo - 0.18 * (hi - lo), hi + 0.12 * (hi - lo))
    ax.axhline(0, color=BASE, lw=1)
    ax.set_xticks([0, 1, 2], ['衰退型\n中位数(3)', '非衰退\n中位数(7)', '本轮\n10/6→11/20'], fontsize=8.4)
    ax.set_title(title, fontsize=9.6)
    ax.grid(axis='x', visible=False)
fig.suptitle('同一窗口（纳指高点→低点）的其他资产：本轮黄金大跌、美债只小幅上涨，与 2000、2008、2020 的避险模式不同',
             x=0.01, ha='left', fontsize=10.5, fontweight='bold')
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(FIG / 'f2_cross_asset_signature.png', dpi=150, metadata={'Software': None})
plt.close(fig)
print('figures written')
