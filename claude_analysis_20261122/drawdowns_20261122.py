"""Nasdaq Composite declines of 10% or more since 1971, what followed a first close
18% below the peak, and how other assets moved in each episode.

Usage (from the repository root):
    python3 -I claude_analysis_20261122/drawdowns_20261122.py .

Reads only files inside this folder; writes out/*.csv and out/summary.json.
"""
import csv
import glob
import hashlib
import json
import pathlib
import statistics
import sys
from datetime import date

ROOT = pathlib.Path(sys.argv[1]).resolve()
HERE = ROOT / "claude_analysis_20261122"
DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

WINDOW = 252          # trailing window for the 52-week closing high
START_DD = -0.10      # an episode starts at a close 10% below the 52-week high
HORIZONS = (21, 63, 126, 252)

# NBER US business-cycle reference dates (peak month, trough month).
# Source: https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions
NBER = [("1969-12", "1970-11"), ("1973-11", "1975-03"), ("1980-01", "1980-07"),
        ("1981-07", "1982-11"), ("1990-07", "1991-03"), ("2001-03", "2001-11"),
        ("2007-12", "2009-06"), ("2020-02", "2020-04")]


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


inputs = sorted(DATA.glob("fmp_raw/*.json")) + [
    DATA / "treasury_rates_points_fmp_20261122.json",
    DATA / "btc_extract_fmp_20261122.json",
    ROOT / "current_plan.json",
]
STAGES = (0, 15, 30)   # three equal tranches, in trading days after the first -18% close


def load_series(prefix):
    """Merge the FMP pages of one symbol; overlapping dates must agree."""
    rows = {}
    for f in sorted(glob.glob(str(DATA / "fmp_raw" / f"{prefix}*.json"))):
        for r in json.loads(pathlib.Path(f).read_text()):
            d, p = r["date"], float(r["price"])
            if d in rows:
                assert abs(rows[d] - p) <= 1e-9 * max(1.0, abs(p)), (prefix, d, rows[d], p)
            rows[d] = p
    return dict(sorted(rows.items()))


IXIC = load_series("IXIC")
GSPC = load_series("GSPC")
GOLD = load_series("GCUSD")
VIX = load_series("VIX")
EUR = load_series("EURUSD")
TSY = {d: v[0] for d, v in json.loads((DATA / "treasury_rates_points_fmp_20261122.json").read_text())["responses"].items()}
BTC = {r["date"]: r["price"] for r in json.loads((DATA / "btc_extract_fmp_20261122.json").read_text())["rows"]}

dates = list(IXIC)
px = [IXIC[d] for d in dates]
n = len(px)


def asof(series, d):
    """Last value on or before date d (None if the series starts later)."""
    keys = [k for k in series if k <= d]
    return series[keys[-1]] if keys else None


def pct(a, b):
    return None if a is None or b is None else b / a - 1


def month_start_after(ym):
    y, m = map(int, ym.split("-"))
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01"


def month_end(ym):
    return ym + "-31"


RECESSIONS = [(month_start_after(p), month_end(t)) for p, t in NBER]


def in_recession(d0, d1):
    return any(not (d1 < a or d0 > b) for a, b in RECESSIONS)


# ---------------------------------------------------------------- episodes
episodes = []
in_ep = False
for t in range(1, n):
    lo = max(0, t - WINDOW + 1)
    win = px[lo:t + 1]
    m = max(win)
    if not in_ep:
        if px[t] <= (1 + START_DD) * m:
            ep = {"peak_i": lo + win.index(m), "start_i": t}
            in_ep = True
    elif px[t] >= m and t > ep["peak_i"]:
        seg = px[ep["peak_i"]:t]
        ep["trough_i"] = ep["peak_i"] + seg.index(min(seg))
        ep["end_i"] = t
        episodes.append(ep)
        in_ep = False
if in_ep:
    seg = px[ep["peak_i"]:]
    ep["trough_i"] = ep["peak_i"] + seg.index(min(seg))
    ep["end_i"] = None
    episodes.append(ep)

current = episodes[-1]
assert current["end_i"] is None and dates[-1] == "2026-11-20"
CUR_DD = px[-1] / px[current["peak_i"]] - 1          # -18.05% at the 11/20 close
assert dates[current["peak_i"]] == "2026-10-06"


def first_cross(ep, level):
    stop = ep["end_i"] if ep["end_i"] is not None else n
    pk = px[ep["peak_i"]]
    for t in range(ep["peak_i"], stop):
        if px[t] / pk - 1 <= level + 1e-12:
            return t
    return None


ep_rows = []
for k, ep in enumerate(episodes):
    pk, tr = ep["peak_i"], ep["trough_i"]
    c18 = first_cross(ep, CUR_DD)
    c20 = first_cross(ep, -0.20)
    d_pk, d_tr = dates[pk], dates[tr]
    row = {
        "peak_date": d_pk, "peak": px[pk], "trough_date": d_tr, "trough": px[tr],
        "max_drawdown": px[tr] / px[pk] - 1,
        "td_peak_to_trough": tr - pk,
        "new_52w_high_date": dates[ep["end_i"]] if ep["end_i"] is not None else "",
        "status": "ongoing" if ep["end_i"] is None else "completed",
        "recession_overlap": in_recession(d_pk, d_tr),
        "first_close_at_current_dd": dates[c18] if c18 is not None else "",
        "td_peak_to_current_dd": (c18 - pk) if c18 is not None else "",
        "reached_minus20": c20 is not None,
        "spx_change": pct(asof(GSPC, d_pk), asof(GSPC, d_tr)),
        "gold_change": pct(GOLD.get(d_pk) or asof(GOLD, d_pk), asof(GOLD, d_tr)) if d_pk >= "1975-01-02" else None,
        "eurusd_change": pct(asof(EUR, d_pk), asof(EUR, d_tr)) if d_pk >= "1988-07-22" else None,
        "vix_at_peak": VIX.get(d_pk) if d_pk >= "1990-01-02" else None,
        "vix_max": max(v for d, v in VIX.items() if d_pk <= d <= d_tr) if d_pk >= "1990-01-02" else None,
        "ust10y_change_bp": (round((TSY[d_tr]["year10"] - TSY[d_pk]["year10"]) * 100)
                             if d_pk in TSY and d_tr in TSY else None),
        "ust2y_change_bp": (round((TSY[d_tr]["year2"] - TSY[d_pk]["year2"]) * 100)
                            if d_pk in TSY and d_tr in TSY else None),
    }
    ep_rows.append(row)

completed = [r for r in ep_rows if r["status"] == "completed"]
cur_row = ep_rows[-1]

# ------------------------------------------- what followed the first close at -18.05%
after = []
for ep, row in zip(episodes, ep_rows):
    if row["status"] != "completed" or not row["first_close_at_current_dd"]:
        continue
    t = first_cross(ep, CUR_DD)
    fwd = {h: (px[t + h] / px[t] - 1 if t + h < n else None) for h in HORIZONS}
    rec = next((u for u in range(t, n) if px[u] >= px[ep["peak_i"]]), None)
    after.append({
        "peak_date": row["peak_date"], "cross_date": dates[t],
        "td_peak_to_cross": t - ep["peak_i"],
        "recession_overlap": row["recession_overlap"],
        "final_max_drawdown": row["max_drawdown"],
        "further_decline_to_trough": px[ep["trough_i"]] / px[t] - 1,
        "td_cross_to_trough": ep["trough_i"] - t,
        "min_next_252d": min(px[t:t + 253]) / px[t] - 1,
        **{f"ret_{h}d": fwd[h] for h in HORIZONS},
        "td_cross_to_peak_recovery": (rec - t) if rec is not None else "",
    })


def q(xs, p):
    xs = sorted(xs)
    pos = (len(xs) - 1) * p
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def describe(rows, key):
    xs = [r[key] for r in rows if r[key] not in (None, "")]
    if not xs:
        return None
    return {"n": len(xs), "median": q(xs, 0.5), "p25": q(xs, 0.25), "p75": q(xs, 0.75),
            "min": min(xs), "max": max(xs),
            "share_positive": sum(x > 0 for x in xs) / len(xs)}


groups = {
    "all": after,
    "recession": [r for r in after if r["recession_overlap"]],
    "no_recession": [r for r in after if not r["recession_overlap"]],
    "fast_le40d": [r for r in after if r["td_peak_to_cross"] <= 40],
}
after_stats = {g: {k: describe(rows, k) for k in
                   ["final_max_drawdown", "further_decline_to_trough", "td_cross_to_trough",
                    "min_next_252d"] + [f"ret_{h}d" for h in HORIZONS]}
               for g, rows in groups.items()}

# --------------------------------------------- base rates across all completed episodes
years = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days / 365.25
depths = [r["max_drawdown"] for r in completed]
base = {
    "n_completed": len(completed), "years": years, "per_year": len(completed) / years,
    "share_reaching": {f"{th:.0%}": sum(d <= th for d in depths) / len(depths)
                       for th in (-0.15, -0.20, -0.30, -0.40, -0.50)},
    "n_reaching_current_dd": len(after),
    "of_those_share_reaching": {f"{th:.0%}": sum(r["final_max_drawdown"] <= th for r in after) / len(after)
                                for th in (-0.20, -0.25, -0.30, -0.40, -0.50)},
}

# ------------------------------------------------ cross-asset signature, current window
P0, P1 = "2026-10-06", "2026-11-20"
current_window = {
    "nasdaq": pct(IXIC[P0], IXIC[P1]),
    "spx": pct(GSPC[P0], GSPC[P1]),
    "gold": pct(GOLD[P0], GOLD[P1]),
    "gold_from_2026_high": pct(max(v for d, v in GOLD.items() if d >= "2026-01-01"), GOLD[P1]),
    "gold_2026_high_date": max((v, d) for d, v in GOLD.items() if d >= "2026-01-01")[1],
    "bitcoin": pct(BTC[P0], BTC[P1]),
    "eurusd": pct(EUR[P0], EUR[P1]),
    "usd_vs_eur": pct(1 / EUR[P0], 1 / EUR[P1]),
    "ust10y_bp": round((TSY[P1]["year10"] - TSY[P0]["year10"]) * 100),
    "ust2y_bp": round((TSY[P1]["year2"] - TSY[P0]["year2"]) * 100),
    "ust10y_level": TSY[P1]["year10"], "ust2y_level": TSY[P1]["year2"],
    "vix_p0": VIX[P0], "vix_p1": VIX[P1],
    "day_1120": {"nasdaq": pct(IXIC["2026-11-19"], IXIC[P1]), "spx": pct(GSPC["2026-11-19"], GSPC[P1]),
                 "gold": pct(GOLD["2026-11-19"], GOLD[P1]), "eurusd": pct(EUR["2026-11-19"], EUR[P1])},
}

# Episodes with a 10-year yield on both dates: compare the signatures by group.
sig = [r for r in ep_rows if r["ust10y_change_bp"] is not None and r["status"] == "completed"]
signature = {}
for name, rows in {"recession": [r for r in sig if r["recession_overlap"]],
                   "no_recession": [r for r in sig if not r["recession_overlap"]]}.items():
    signature[name] = {
        "episodes": [r["peak_date"][:7] for r in rows],
        **{k: describe(rows, k) for k in ["max_drawdown", "spx_change", "gold_change",
                                          "eurusd_change", "vix_max", "ust10y_change_bp"]}}

# ------------------------------- lump sum vs three tranches after the first -18% close
# Uninvested cash earns 0 here (SGOV's ~4%/yr over six weeks is about 0.5% and is ignored).
stage_rows = []
for ep, row in zip(episodes, ep_rows):
    if row["status"] != "completed" or not row["first_close_at_current_dd"]:
        continue
    t0 = first_cross(ep, CUR_DD)
    if t0 + 252 >= n:
        continue

    def v_lump(u, t0=t0):
        return px[u] / px[t0]

    def v_staged(u, t0=t0):
        return sum((px[u] / px[t0 + s] if u >= t0 + s else 1.0) for s in STAGES) / len(STAGES)

    stage_rows.append({
        "peak_date": row["peak_date"], "cross_date": dates[t0],
        "recession_overlap": row["recession_overlap"],
        "lump_value_252d": v_lump(t0 + 252), "staged_value_252d": v_staged(t0 + 252),
        "staged_minus_lump_252d": v_staged(t0 + 252) - v_lump(t0 + 252),
        "worst_mark_lump_126d": min(v_lump(u) for u in range(t0, t0 + 127)) - 1,
        "worst_mark_staged_126d": min(v_staged(u) for u in range(t0, t0 + 127)) - 1,
    })
staging = {
    "tranches_td": STAGES,
    "n": len(stage_rows),
    "staged_better_count": sum(r["staged_minus_lump_252d"] > 0 for r in stage_rows),
    **{k: describe(stage_rows, k) for k in ["staged_minus_lump_252d", "worst_mark_lump_126d",
                                            "worst_mark_staged_126d"]},
}

# ------------------------------ what a further leg down would mean for the $7,000 plan
plan = json.loads((ROOT / "current_plan.json").read_text())
eq_share = 1 - plan["weights"]["SGOV"]
budget = plan["budget_usd"]
fd = {r["peak_date"][:4]: r["further_decline_to_trough"] for r in after}
scen = {"assumption": "uniform shock: every non-SGOV holding falls by the Nasdaq's further decline; SGOV flat",
        "equity_share": eq_share, "budget_usd": budget, "rows": []}
for label, shock in [("median of 17 cases", after_stats["all"]["further_decline_to_trough"]["median"]),
                     ("worse quartile of 17 cases", after_stats["all"]["further_decline_to_trough"]["p25"]),
                     ("2022 rate shock", fd["2021"]), ("2007-09 financial crisis", fd["2007"])]:
    scen["rows"].append({"case": label, "nasdaq_further": shock,
                         "portfolio": eq_share * shock, "usd": round(budget * eq_share * shock)})

# ------------------------------------------------------------------ write outputs
def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})


write_csv(OUT / "episodes.csv", ep_rows)
write_csv(OUT / "after_first_close_at_current_dd.csv", after)
write_csv(OUT / "lump_vs_staged.csv", stage_rows)

paths = {}
for ep, row in zip(episodes, ep_rows):
    if row["first_close_at_current_dd"] and row["status"] == "completed":
        t = first_cross(ep, CUR_DD)
        paths[row["peak_date"]] = [px[u] / px[t] - 1 for u in range(t, min(t + 253, n))]

summary = {
    "folder": "claude_analysis_20261122",
    "data_cutoff": {"prices": "2026-11-20 close (US)", "news": "2026-11-22 22:30 ET"},
    "definition": {"episode": "starts at the first close >=10% below the trailing 252-day closing high; "
                              "peak = that high; ends at the next new 252-day closing high; trough = lowest close in between",
                   "current_drawdown": CUR_DD, "horizons_trading_days": HORIZONS},
    "current_episode": cur_row,
    "base_rates": base,
    "after_first_close_at_current_dd": after_stats,
    "current_window_2026_10_06_to_11_20": current_window,
    "signature_by_group": signature,
    "lump_vs_staged": staging,
    "portfolio_scenarios": scen,
    "paths_after_cross": paths,
    "inputs_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in inputs},
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n")

# Console digest
print(f"episodes completed={len(completed)} over {years:.1f}y ({len(completed)/years:.2f}/yr); current dd={CUR_DD:.4f}")
print("reached current dd:", len(after), {g: len(v) for g, v in groups.items()})
for g in groups:
    s = after_stats[g]
    print(g, "final dd median", round(s["final_max_drawdown"]["median"], 3),
          "further median", round(s["further_decline_to_trough"]["median"], 3),
          "ret252 median", s["ret_252d"] and round(s["ret_252d"]["median"], 3),
          "share>0", s["ret_252d"] and round(s["ret_252d"]["share_positive"], 2))
print("staging:", json.dumps(staging, default=str)[:700])
print("scenarios:", json.dumps(scen["rows"]))
