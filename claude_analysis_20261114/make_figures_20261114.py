#!/usr/bin/env python3
"""Figures for claude_analysis_20261114. Reads out/*.csv + out/summary.json only.
Run: python3 -I claude_analysis_20261114/make_figures_20261114.py <repo_root>
Palette: validated categorical slots (blue, orange, aqua, yellow, magenta); muted gray for reference series.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / 'claude_analysis_20261114'
OUT, FIG = HERE / 'out', HERE / 'figures'
FIG.mkdir(exist_ok=True)
S = json.loads((OUT / 'summary.json').read_text())

BLUE, ORANGE, AQUA, YELLOW, MAGENTA = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'
MUTED, INK, INK2, GRID, BASE, SURF = '#898781', '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
plt.rcParams.update({
    'font.family': 'Noto Sans CJK SC', 'axes.unicode_minus': False, 'figure.facecolor': SURF,
    'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2,
    'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9.5,
    'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})
pct = lambda v, d=1: f'{v * 100:+.{d}f}%'
NAMES = {'entry': 'GPT 初始版', 'conviction8': 'GPT conviction8', 'Claude_1113': 'Claude 11/13 版',
         'Hybrid_Lite': 'Hybrid-稳', 'Hybrid_Core': 'Hybrid-核心', 'Hybrid_Plus': 'Hybrid-进取', 'VTI': 'VTI'}


def save(fig, name):
    fig.savefig(FIG / name, dpi=200, bbox_inches='tight')
    plt.close(fig)


# F1 ---------------------------------------------------------------- event path
E = pd.read_csv(OUT / 'event_window_index_nov3eq1.csv', index_col=0, parse_dates=True)
xi = np.arange(len(E))
pos = {d.strftime('%Y-%m-%d'): i for i, d in enumerate(E.index)}
fig, ax = plt.subplots(figsize=(9.2, 4.8))
series = [('NVDA', 'NVDA', ORANGE, 2.4), ('AIx7_EW', '其余7家AI等权', BLUE, 2.0), ('AVGO', 'AVGO', AQUA, 1.5),
          ('VTI', 'VTI', MUTED, 1.5)]
ends = []
for col, lab, c, lw in series:
    y = (E[col] - 1) * 100
    ax.plot(xi, y, color=c, lw=lw, label=lab, zorder=3)
    ax.scatter(xi[-1], y.iloc[-1], color=c, s=22, zorder=4, edgecolor=SURF, linewidth=1.2)
    ends.append([y.iloc[-1], lab, c, y.iloc[-1]])
ends.sort(key=lambda r: r[0])
for i in range(1, len(ends)):
    if ends[i][0] - ends[i - 1][0] < 2.4:
        ends[i][0] = ends[i - 1][0] + 2.4
for yv, lab, c, real in ends:
    ax.annotate(f'{lab} {real:+.1f}%', (xi[-1], yv), xytext=(8, 0), textcoords='offset points',
                va='center', color=INK, fontsize=9)
ax.axhline(0, color=BASE, lw=1)
ax.axvspan(pos['2026-11-03'] + 0.5, pos['2026-11-05'] + 0.15, color=GRID, alpha=0.7, lw=0, zorder=1)
ax.text(pos['2026-11-04'] + 0.3, 13.6, '大选结果\n11/4–11/5', ha='center', va='top', fontsize=8.5, color=INK2)
for d, txt, yy in [('2026-11-09', '11/9 董事会\n独立调查后首日', 13.6), ('2026-11-11', '11/11 盘后\nWSJ：董事会拟撤换', -26.2),
                   ('2026-11-12', '11/12 黄仁勋\n辞职（8-K）', 13.6)]:
    ax.axvline(pos[d], color=MUTED, lw=0.9, ls=(0, (3, 3)), zorder=2)
    ax.text(pos[d] - (0.08 if d == '2026-11-11' else 0), yy, txt, ha='right' if d == '2026-11-11' else 'center',
            va='top' if yy > 0 else 'bottom', fontsize=8.5, color=INK2, bbox=dict(boxstyle='round,pad=0.2', fc=SURF, ec='none'))
ax.set_ylim(-27, 14.5)
ax.set_xlim(-0.3, len(E) - 0.7)
ax.set_xticks(xi, [d.strftime('%m/%d') for d in E.index], fontsize=8.3)
ax.set_ylabel('相对 11/3 收盘 (%)')
ax.set_title('选举两天：AI 半导体普跌；调查→辞职这一周：只有 NVDA 继续跌，其余 AI 反涨')
ax.text(0, -0.15, '复权收盘价（交易日等距），2026-10-26 至 11-13；AIx7 = TSM/AVGO/MU/GOOGL/META/MSFT/AMZN 日度等权。'
        '数据：GPT 包内 Yahoo 原始 JSON（SHA-256 已核验）。', transform=ax.transAxes, fontsize=7.8, color=INK2)
save(fig, 'f1_event_path.png')

# F2 ---------------------------------------------------------------- event study CAR
EV = pd.read_csv(OUT / 'event_study_ai8.csv').set_index('t')
order = ['NVDA', 'TSM', 'AVGO', 'MU', 'GOOGL', 'META', 'MSFT', 'AMZN']
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, (key, ttl) in zip(axes, [('election_11_04_05', '大选：11/4–11/5（2 日）'), ('scandal_11_09_13', '调查→辞职：11/9–11/13（5 日）')]):
    v = EV.loc[order, 'CAR_' + key] * 100
    tt = EV.loc[order, 't_' + key]
    cols = [ORANGE if t == 'NVDA' else BLUE for t in order]
    ax.bar(range(8), v, color=cols, width=0.62, edgecolor=SURF, linewidth=1.5, zorder=3)
    ax.axhline(0, color=BASE, lw=1, zorder=2)
    for i, (val, t) in enumerate(zip(v, tt)):
        lab = f'{val:+.1f}%' + (f'\nt={t:+.1f}' if abs(t) >= 2 else '')
        ax.text(i, val + (0.8 if val >= 0 else -0.8), lab, ha='center', va='bottom' if val >= 0 else 'top', fontsize=8.2, color=INK)
    ax.set_xticks(range(8), order)
    ax.set_title(ttl, fontsize=10.5)
    ax.set_ylim(-27, 17)
axes[0].set_ylabel('累计异常收益 CAR (%)')
fig.suptitle('异常收益：选举冲击是"半导体 vs 平台"；CEO 事件只打在 NVDA 身上（AVGO 反而 +11%）', x=0.01, ha='left',
             fontsize=11.5, fontweight='bold')
fig.text(0.01, -0.07, '模型：R_i = a + b1·R_VTI + b2·AI因子 + e；NVDA 的 AI 因子 = 其余 7 家等权，其余公司用剔除自身与 NVDA 的 6 家等权。估计窗 2023-11-14→2026-10-30（不含事件日）。'
         '\n|t|≥2 标出 t 值；t = CAR /(σ_e·√天数)。仅描述历史价格反应，不是预测。', fontsize=7.8, color=INK2)
fig.tight_layout()
save(fig, 'f2_event_study_car.png')

# F3 ---------------------------------------------------------------- rolling decoupling
RO = pd.read_csv(OUT / 'nvda_rolling126_factor.csv', parse_dates=['Date']).set_index('Date')
fm = S['nvda_factor_model']['three_year']
fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True)
for ax, col, ref, ttl, fmt in [(axes[0], 'idio_share', 1 - fm['r2'], 'NVDA 特有风险占比 = 1 − R²（126 日滚动）', '{:.0%}'),
                                (axes[1], 'beta_AIx7', fm['beta_AIx7'], 'NVDA 对"其余 7 家 AI"的 beta（126 日滚动）', '{:.2f}')]:
    ax.plot(RO.index, RO[col], color=ORANGE, lw=2.0, zorder=3)
    ax.axhline(ref, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(pd.Timestamp('2025-03-01' if col == 'idio_share' else '2026-02-15'), ref, '3 年全样本 ' + fmt.format(ref),
            va='bottom', fontsize=8.2, color=INK2,
            bbox=dict(boxstyle='round,pad=0.15', fc=SURF, ec='none'))
    ax.axvline(pd.Timestamp('2026-01-01'), color=BASE, lw=1)
    ax.set_title(ttl, fontsize=10.5)
    last = RO[col].iloc[-1]
    ax.annotate('11/13: ' + fmt.format(last), (RO.index[-1], last), xytext=(-14, 22), textcoords='offset points',
                ha='right', fontsize=8.5, color=INK, arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8),
                bbox=dict(boxstyle='round,pad=0.15', fc=SURF, ec='none'))
axes[0].set_ylim(0, 0.8)
axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
axes[1].text(pd.Timestamp('2026-01-10'), 1.7, '2026 →', fontsize=8.5, color=INK2)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
fig.suptitle('2025 年底起 NVDA 与其余 AI 公司"脱钩"：价格越来越由公司自身因素决定', x=0.01, ha='left', fontsize=11.5, fontweight='bold')
fig.text(0.01, -0.02, '模型 R_NVDA = a + b1·R_VTI + b2·AIx7 + e，126 交易日滚动 OLS，简单日收益，2023-11-14→2026-11-13。', fontsize=7.8, color=INK2)
fig.tight_layout()
save(fig, 'f3_nvda_decoupling.png')

# F4 ---------------------------------------------------------------- look-through exposure
RP = pd.read_csv(OUT / 'risk_profile_issuer_level.csv').set_index('portfolio')
W = S['weights']
porder = ['entry', 'Hybrid_Lite', 'conviction8', 'Hybrid_Core', 'Claude_1113', 'Hybrid_Plus', 'VTI']
cats = [('其余 7 家 AI（含 VTI 穿透）', BLUE), ('NVDA（含 VTI 穿透）', ORANGE), ('非 AI 股票/ETF', AQUA), ('现金 SGOV', YELLOW), ('BTAL', MAGENTA)]
rows = []
for p in porder:
    w = W[p]
    nv, ai = RP.loc[p, 'nvda_lt'], RP.loc[p, 'ai8_lt']
    cash, btal = w.get('SGOV', 0) + w.get('BIL', 0), w.get('BTAL', 0)
    rows.append([ai - nv, nv, 1 - ai - cash - btal, cash, btal])
M = np.array(rows) * 100
fig, ax = plt.subplots(figsize=(9.6, 5.0))
ypos = np.array([8.2, 7.4, 6.0, 5.2, 3.8, 3.0, 1.6])
left = np.zeros(len(porder))
for j, (lab, c) in enumerate(cats):
    ax.barh(ypos, M[:, j], left=left, color=c, height=0.66, edgecolor=SURF, linewidth=2, label=lab, zorder=3)
    for i in range(len(porder)):
        if M[i, j] >= 6:
            ax.text(left[i] + M[i, j] / 2, ypos[i], f'{M[i, j]:.1f}', ha='center', va='center', fontsize=8.2,
                    color=INK if c == YELLOW else '#ffffff')
    left += M[:, j]
ax.set_yticks(ypos, [NAMES[p] for p in porder])
ax.set_xlim(0, 100)
ax.set_xlabel('占组合 %（2026-11-13，VTI 按 9/30 官方持仓随价格漂移估算）')
for (a, b), txt in zip([(0, 1), (2, 3), (4, 5)], ['≈15.8%', '≈17.7%', '≈18.3%']):
    ax.text(100.8, (ypos[a] + ypos[b]) / 2, f'3 年波动\n{txt}', va='center', fontsize=8, color=INK2)
ax.legend(ncol=5, loc='lower left', bbox_to_anchor=(0, 1.0), frameon=False, fontsize=8.3, handlelength=1.2, columnspacing=1.0)
ax.grid(axis='y', visible=False)
fig.suptitle('同等历史波动下，Hybrid 把 NVDA 穿透敞口从 16.8% 降到 11.3%，AI 总敞口基本不变', x=0.01, ha='left',
             fontsize=11.5, fontweight='bold', y=1.03)
save(fig, 'f4_lookthrough_exposure.png')

# F5 ---------------------------------------------------------------- matched-risk comparison
EVL = pd.read_csv(OUT / 'unified_quarterly_metrics.csv')
po = ['entry', 'Hybrid_Lite', 'conviction8', 'Hybrid_Core', 'Claude_1113', 'Hybrid_Plus']
g = lambda win, col: EVL[(EVL.window == win)].set_index('portfolio').loc[po, col]
panels = [(g('three_year', 'vol'), '3 年实现波动（季度再平衡）', False),
          (RP.loc[po, 'rc_nvda_issuer'], 'NVDA 发行人风险贡献（含 VTI 穿透）', False),
          (RP.loc[po, 'scen_nvda_idio_minus30'], '情景：NVDA 特有 −30%，其他不变', True),
          (g('scandal_nov6_13', 'cum'), '历史：11/6→11/13 调查→辞职周', True)]
fig, axes = plt.subplots(2, 2, figsize=(10, 6.2))
xpos = np.array([0, 1, 2.5, 3.5, 5, 6])
for ax, (vals, ttl, signed) in zip(axes.ravel(), panels):
    cols = [BLUE if p.startswith('Hybrid') else MUTED for p in po]
    ax.bar(xpos, vals * 100, color=cols, width=0.78, edgecolor=SURF, linewidth=1.5, zorder=3)
    ax.axhline(0, color=BASE, lw=1, zorder=2)
    for x, v in zip(xpos, vals * 100):
        ax.text(x, v + (0.25 if v >= 0 else -0.25) * (1 if not signed else 0.6), f'{v:+.1f}' if signed else f'{v:.1f}',
                ha='center', va='bottom' if v >= 0 else 'top', fontsize=8.2)
    ax.set_xticks(xpos, ['GPT\n初始版', 'Hybrid\n稳', 'GPT\nconv8', 'Hybrid\n核心', 'Claude\n11/13', 'Hybrid\n进取'], fontsize=8.2)
    ax.set_title(ttl, fontsize=10)
    lo, hi = min(0, (vals * 100).min()), max(0, (vals * 100).max())
    ax.set_ylim(lo * 1.25 - (0.6 if lo < 0 else 0), hi * 1.18 + 0.6)
    ax.set_ylabel('%')
fig.suptitle('三组"同风险替换"：灰 = 现有方案，蓝 = 同历史波动的 Hybrid', x=0.01, ha='left', fontsize=11.5, fontweight='bold')
fig.text(0.01, -0.02, '历史与情景数字，非预测。Claude 11/13 版含 8% BTAL（基金内部做空/互换），Hybrid 均不含杠杆或做空工具。', fontsize=7.8, color=INK2)
fig.tight_layout()
save(fig, 'f5_matched_risk.png')

# F6 ---------------------------------------------------------------- NVDA dial at iso-risk
D6 = pd.read_csv(OUT / 'nvda_dial_iso_risk.csv')
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
x = D6.nvda_direct * 100
axes[0].plot(x, D6.rc_nvda * 100, color=ORANGE, lw=2.2, marker='o', ms=6, zorder=3)
for xi, yi in zip(x, D6.rc_nvda * 100):
    axes[0].annotate(f'{yi:.0f}%', (xi, yi), xytext=(0, 8), textcoords='offset points', ha='center', fontsize=8.3)
axes[0].set_title('NVDA 占组合风险', fontsize=10.5)
axes[0].set_ylim(0, 45)
axes[1].plot(x, D6.ai8_lt * 100, color=BLUE, lw=2.2, marker='o', ms=6, label='AI 8 家穿透总敞口', zorder=3)
axes[1].plot(x, D6.ai7_direct * 100, color=AQUA, lw=2.2, marker='s', ms=6, label='其余 7 家直接持仓', zorder=3)
for col, c, dy in [('ai8_lt', BLUE, 8), ('ai7_direct', AQUA, -14)]:
    for xi, yi in zip(x, D6[col] * 100):
        axes[1].annotate(f'{yi:.0f}', (xi, yi), xytext=(0, dy), textcoords='offset points', ha='center', fontsize=8.2)
axes[1].set_ylim(20, 62)
axes[1].legend(frameon=False, fontsize=8.5, loc='lower left')
axes[1].set_title('同风险预算下，留给 AI 广度的空间', fontsize=10.5)
for ax in axes:
    ax.axvline(10, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.set_xlabel('NVDA 直接权重 (%)')
    ax.set_xticks(x)
axes[0].text(10.2, 41, '所选 10%', fontsize=8.5, color=INK2)
fig.suptitle('NVDA 旋钮：总波动固定在 GPT conviction8 的 17.7%，NVDA 每 +2.5pp 约多占 6pp 组合风险', x=0.01, ha='left',
             fontsize=11.5, fontweight='bold')
fig.tight_layout()
save(fig, 'f6_nvda_dial.png')

# F7 ---------------------------------------------------------------- who rises on NVDA-specific bad days
SS = pd.read_csv(OUT / 'share_shift_partial_corr.csv')
ss = SS[SS.window == 'pre_event'].set_index('t').sort_values('mean_resid_on_NVDA_worst10pct_bp')
fig, ax = plt.subplots(figsize=(8.6, 3.9))
v = ss.mean_resid_on_NVDA_worst10pct_bp
ax.barh(range(len(v)), v, color=[AQUA if x > 0 else BLUE for x in v], height=0.62, edgecolor=SURF, linewidth=1.5, zorder=3)
ax.axvline(0, color=BASE, lw=1)
for i, (t, val) in enumerate(v.items()):
    pc = ss.loc[t, 'partial_corr']
    ax.text(val + (4 if val >= 0 else -4), i, f'{val:+.0f} bp（偏相关 {pc:+.2f}）', va='center',
            ha='left' if val >= 0 else 'right', fontsize=8.3)
ax.set_yticks(range(len(v)), v.index)
ax.set_xlim(-185, 95)
ax.set_xlabel('NVDA 特有收益最差 10% 的日子里，该股票的平均特有收益 (bp)')
ax.set_title('NVDA 自身出事的日子：TSM/MU/AVGO 往往跟跌，GOOGL 略涨，AMZN 基本持平', fontsize=11)
ax.text(0, -0.25, '2023-11-14→2026-10-30（事件前）。两只股票都对 VTI 与剔除二者后的 AI 等权因子回归取残差；n=743，最差 10% = 75 天。'
        '\n例外：11/9–11/13 这一周 AVGO 特有收益 +11%（见 f2），说明"份额转移"叙事在本次事件中被定价。', transform=ax.transAxes, fontsize=7.8, color=INK2)
ax.grid(axis='y', visible=False)
save(fig, 'f7_share_shift.png')
print('figures:', sorted(p.name for p in FIG.glob('*.png')))
