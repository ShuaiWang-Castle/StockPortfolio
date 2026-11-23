#!/usr/bin/env python3
"""Figures for claude_analysis_20261116 (reads out/ only). Run: python3 -I claude_analysis_20261116/make_figures_20261116.py <repo_root>"""
import sys, json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261116'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
S = json.loads((OUT / 'summary.json').read_text())
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'          # validated: validate_palette.js --mode light --surface #fcfcfb
MUTED, INK, INK2, GRID, BASE, SURF = '#898781', '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'savefig.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.size': 9.5, 'axes.titlesize': 10.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})


def save(fig, name):
    fig.savefig(FIG / name, dpi=200, bbox_inches='tight')
    plt.close(fig)


# F1 own history: EV/EBIT and FCF yield, FY ends plus TTM at the 11/16 close ---------------------------------
H = pd.read_csv(OUT / 'own_history_ev_ebit.csv', parse_dates=['date'])
COL = {'MSFT': BLUE, 'GOOGL': ORANGE}
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3))
for ax, col, fmt, title, ylab in [(axes[0], 'ev_ebit', '{:.1f}x', 'EV / 经营利润（年末 EV ÷ 当年经营利润；TTM 用 11/16 市值）', '倍'),
                                  (axes[1], 'fcf_yield', '{:.1%}', '自由现金流收益率（FCF ÷ 市值）', '')]:
    for t in ['MSFT', 'GOOGL']:
        h = H[H.t == t].sort_values('date')
        fy, now = h[h.period != 'TTM 11/16'], h[h.period == 'TTM 11/16'].iloc[0]
        y = 100 * fy[col] if col == 'fcf_yield' else fy[col]
        yn = 100 * now[col] if col == 'fcf_yield' else now[col]
        ax.plot(fy.date, y, color=COL[t], lw=2, marker='o', ms=6, mec=SURF, mew=1.2, zorder=3, label=f'{t}（财年末）')
        ax.plot([fy.date.iloc[-1], now.date], [y.iloc[-1], yn], color=COL[t], lw=1.4, ls=(0, (3, 2)), zorder=2)
        ax.scatter([now.date], [yn], s=70, facecolor=SURF, edgecolor=COL[t], linewidth=2.2, zorder=4)
        dy = {('ev_ebit', 'MSFT'): 9, ('ev_ebit', 'GOOGL'): -11, ('fcf_yield', 'MSFT'): 8, ('fcf_yield', 'GOOGL'): -10}[(col, t)]
        ax.annotate(f'{t} {fmt.format(now[col])}', (now.date, yn), xytext=(7, dy), textcoords='offset points', fontsize=8.8,
                    color=INK, va='center', ha='left')
    ax.set_title(title)
    ax.set_ylabel(ylab)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_xlim(pd.Timestamp('2021-09-01'), pd.Timestamp('2027-07-01'))
axes[0].set_ylim(10, 36)
axes[1].set_ylim(0, 6)
axes[1].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.0f}%'))
handles = [Line2D([], [], color=BLUE, lw=2, marker='o', ms=6, mec=SURF, label='MSFT'),
           Line2D([], [], color=ORANGE, lw=2, marker='o', ms=6, mec=SURF, label='GOOGL'),
           Line2D([], [], color=INK2, lw=0, marker='o', ms=7, mfc=SURF, mec=INK2, mew=2, label='TTM（2026-11-16 收盘）')]
axes[0].legend(handles=handles, loc='upper left', frameon=False, fontsize=8.5)
o = S['own_history']
fig.suptitle(f"MSFT 的 EV/经营利润 {o['MSFT']['ev_ebit_ttm']:.1f}x，低于自己 FY22–26 的中位数 {o['MSFT']['ev_ebit_fy_median']:.1f}x；"
             f"GOOGL {o['GOOGL']['ev_ebit_ttm']:.1f}x，略高于自己 FY21–25 的中位数 {o['GOOGL']['ev_ebit_fy_median']:.1f}x",
             x=0.01, ha='left', fontsize=11, fontweight='bold', y=1.03)
fig.text(0.01, -0.04, 'EV 采用 FMP 口径（市值 + 总债务 − 现金），与 FMP 的历史年末 EV 一致；经营利润不含投资收益。两家的自由现金流收益率都在 5 年最低，'
         '因为资本开支/收入升到 39%（MSFT）和 34%（GOOGL）。', fontsize=7.8, color=INK2)
fig.tight_layout()
save(fig, 'f1_own_history_msft_googl.png')

# F2 options: valuation pickup vs NVDA concentration --------------------------------------------------------
O = pd.read_csv(OUT / 'reallocation_options.csv').set_index('option')
LAB = {'A': 'A 现方案（MSFT 7%）', 'B': 'B 清 MSFT → NVDA、GOOGL 各 3.5', 'C': 'C 清 MSFT → 全给 GOOGL', 'D': 'D 清 MSFT → 全给 NVDA',
       'E': 'E MSFT 7→3.5，差额给 GOOGL', 'F': 'F MSFT 7→5，差额给 GOOGL', 'l': '长期理论比例（参照）'}
CLR = {'A': BLUE, 'B': AQUA, 'C': ORANGE, 'D': AQUA, 'E': ORANGE, 'F': ORANGE, 'l': MUTED}
# label anchor in data units (x bp, y %) and alignment; leader lines for the crowded cluster around x = 0..7
POSN = {'A': (-1.5, 32.4, 'right'), 'F': (2.5, 34.6, 'left'), 'E': (5.5, 32.6, 'left'), 'C': (8.5, 27.4, 'left'),
        'B': (19.5, 39.6, 'right'), 'D': (33.5, 44.6, 'right'), 'l': (-17.2, 24.3, 'left')}
fig, ax = plt.subplots(figsize=(9.2, 5.0))
c8 = 36.1
ax.axhline(c8, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
ax.text(-21.3, c8 + 0.35, 'conviction8 的 NVDA 风险占比 36.1%（11/14 被 Hybrid-核心取代的方案）', fontsize=8.2, color=INK2, va='bottom', ha='left')
for k, r in O.iterrows():
    key = k[0]
    hollow = key == 'l'
    x, y = r.d_fwd_ep_bp, 100 * r.rc_nvda
    ax.scatter(x, y, s=80, color=SURF if hollow else CLR[key], edgecolor=CLR[key], linewidth=2 if hollow else 1, zorder=3)
    tx, ty, ha = POSN[key]
    usd = 7000 * r.d_fwd_ep_bp / 1e4
    lead = key in ('A', 'F', 'E', 'C')
    ax.annotate(f'{LAB[key]}  {r.d_fwd_ep_bp:+.0f}bp（{usd:+.0f} 美元/年）', (x, y), xytext=(tx, ty), textcoords='data', ha=ha, va='center',
                fontsize=8.2, color=INK,
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.7, shrinkA=2, shrinkB=5, relpos=(0, 0.5) if ha == 'left' else (1, 0.5)) if lead else None)
ax.set_xlim(-22, 42)
ax.set_ylim(20, 48)
ax.set_xlabel('相对现方案，组合前瞻盈利收益率的变化（bp/年；剔除非经营收益后的 NTM E/P，描述估值，不是收益预测）')
ax.set_ylabel('NVDA 占组合风险 (%)')
ax.set_title('把 MSFT 换成 GOOGL 几乎不改变估值；换成 NVDA 估值更便宜，但 NVDA 风险占比越过 36%')
handles = [Line2D([], [], lw=0, marker='o', ms=8, color=BLUE, label='保留 MSFT'), Line2D([], [], lw=0, marker='o', ms=8, color=ORANGE, label='钱给 GOOGL'),
           Line2D([], [], lw=0, marker='o', ms=8, color=AQUA, label='钱给 NVDA（含一半）'),
           Line2D([], [], lw=0, marker='o', ms=8, mfc=SURF, mec=MUTED, mew=2, label='参照')]
ax.legend(handles=handles, loc='lower right', frameon=False, fontsize=8.5)
ax.text(0, -0.2, '风险：发行人层面（VTI 穿透），3 年日收益协方差，与 11/15 方案同一口径；A 复现 11/15 的 17.62% 波动和 30.3% NVDA 风险占比。'
        '估值：11/16 收盘价；一致预期抓取于 11/16。', transform=ax.transAxes, fontsize=7.8, color=INK2)
save(fig, 'f2_reallocation_options.png')
print('ok')
