"""Independent reconstruction of PR #4's six reallocation options and accounting checks."""
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
HERE = ROOT / "codex_review_20261119"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
inputs = {}


def read(path):
    path = ROOT / path
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return raw.decode()


def read_json(path):
    return json.loads(read(path))


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


pr = read_json(HERE / "data/equities_pr4_fields.json")
sec = read_json(HERE / "data/equities_sec_fields.json")
web = {k: v for row in read_json(HERE / "data/sources_web_20261119.json")
       if row["section"] == "equities" for k, v in row.get("used_in_script", {}).items()}
plan = read_json("current_plan.json")
entry = plan["initial_purchase_2026_11_16"]["weights"]
long_term = plan["weights"]
holdings = read_json("claude_analysis_20261114/out/summary.json")["vti_lookthrough"]["weights_2026_09_30"]
price_rows = csv.DictReader(read("gpt_review_20261113/data_audit/adjusted_close.csv").splitlines())
prices = {r["Date"]: {k: float(r[k]) for k in entry} for r in price_rows
          if r["Date"] >= "2023-11-13"}
anchor = prices["2026-09-30"]
dates = sorted(k for k in prices if k <= "2026-11-13")
assert dates[0] == "2023-11-13" and dates[-1] == "2026-11-13"


def drift(p):
    return {k: w * (p[k] / anchor[k]) / (p["VTI"] / anchor["VTI"]) for k, w in holdings.items()}


issuer_returns = []
for previous, current in zip(dates, dates[1:]):
    old, new = prices[previous], prices[current]
    w = drift(old)
    r = {k: new[k] / old[k] - 1 for k in entry}
    r["VTI_rest"] = (r.pop("VTI") - sum(w[k] * r[k] for k in w)) / (1 - sum(w.values()))
    issuer_returns.append(r)
current_components = drift(prices[dates[-1]])


def exposure(weights):
    e = dict(weights)
    fund = e.pop("VTI")
    for k, w in current_components.items():
        e[k] += fund * w
    e["VTI_rest"] = fund * (1 - sum(current_components.values()))
    return e


def risk(weights):
    e = exposure(weights)
    daily = [sum(e[k] * r[k] for k in e) for r in issuer_returns]
    variance = statistics.variance(daily)
    contributions = {}
    for k in e:
        returns = [r[k] for r in issuer_returns]
        contributions[k] = e[k] * statistics.covariance(returns, daily) / variance
    assert math.isclose(sum(contributions.values()), 1)
    return e, daily, contributions


_, base_returns, base_rc = risk(entry)
assert round(statistics.stdev(base_returns) * math.sqrt(252) * 100, 2) == 17.62
assert round(100 * base_rc["NVDA"], 1) == 30.3
_, lt_returns, _ = risk(long_term)
base = "claude_analysis_20261115/data/fmp_raw/"
consensus = {
    "MSFT": read_json(base + "estimates_MSFT_AMZN_META_TSM.json")["MSFT"],
    "GOOGL": read_json(base + "estimates_GOOGL.json")["GOOGL"],
    "NVDA": read_json(base + "NVDA.json")["estimates_annual"],
}
fiscal = {"MSFT": ("2026-07-01", "2027-06-30"), "GOOGL": ("2026-01-01", "2026-12-31"),
          "NVDA": ("2026-01-26", "2027-01-25")}
accounting = []
marks = []
yields = {}
for sym, fields in pr["companies"].items():
    start, end = fiscal[sym]
    fy = sorted(
        (r for r in consensus[sym] if r["date"] >= end), key=lambda r: r["date"])
    assert fy[0]["date"] == end
    share_price = fields["quote"]["price"]
    cap = fields["quote"]["marketCap"] / 1e9
    bs = fields["balance"]
    ev = cap + (bs["totalDebt"] + bs["preferredStock"] - bs["cashAndShortTermInvestments"]
                - bs["longTermInvestments"]) / 1e9
    quarters = fields["quarters"]
    adj = sum((r["incomeBeforeTax"] - r["operatingIncome"]) / r["weightedAverageShsOutDil"] * .79
              for r in quarters if r["date"] >= start)
    wt = (date.fromisoformat(end) - date(2026, 11, 16)).days / 365
    eps = (fy[0]["epsAvg"] - adj) * wt + fy[1]["epsAvg"] * (1 - wt)
    fcf = sum(fields["fcf_quarters"]) / 1e9
    oi = sum(r["operatingIncome"] for r in quarters) / 1e9
    yields[sym] = (eps / share_price, fcf / cap)
    row = {"symbol": sym, "price_close_1116": share_price, "mcap_B": cap, "fmp_ev_B": ev,
           "fmp_oper_EV_EBIT": ev / oi, "fy1_adjustment_per_share": adj, "fmp_clean_PE": share_price / eps,
           "ttm_ebit_B": oi, "fmp_fcf_B": fcf, "sec_fcf_B": None, "sec_nonop_frac_pretax": None,
           "sec_ev_B": None, "sec_ev_ebit": None, "sec_pe_21pct": None}
    if sym in sec:
        q = sec[sym]
        b = {k: x["record"]["val"] / 1e9 for k, x in q["balance"].items()}
        ttm = {}
        for k, span in q["ttm"].items():
            prior_fy, current_ytd, old_ytd = [r["val"] / 1e9 for r in span["prior_fy_current_ytd_prior_ytd"]]
            ttm[k] = prior_fy + current_ytd - old_ytd
        sec_ev = cap + b["current_debt"] + b["lt_debt"] + b["finance_leases"] + b.get(
            "preferred", 0) - b["cash_sti"] - b["lt_invest"]
        sec_adj = sum((x["pretax"]["record"]["val"] - x["oi"]["record"]["val"]) * .79
                      / x["shares"]["record"]["val"] for x in q["eps_quarters"])
        sec_clean = (fy[0]["epsAvg"] - sec_adj) * wt + fy[1]["epsAvg"] * (1 - wt)
        row.update(sec_fcf_B=ttm["ocf"] - ttm["capex"], sec_ev_B=sec_ev,
                   sec_nonop_frac_pretax=1 - ttm["operating"] / ttm["pretax"],
                   sec_ev_ebit=sec_ev / ttm["operating"], sec_pe_21pct=share_price / sec_clean)
        if sym == "MSFT":
            for name in ["march_post_money_B", "november_round_B"]:
                implied = web["openai_share"] * web[name]
                marks.append(dict(value_proxy=name, hypothetical_stake_B=implied,
                                  multiple_low=(sec_ev - implied) / ttm["operating"],
                                  multiple_high=(sec_ev - implied + b["equity_method_total"]) / ttm["operating"],
                                  restricted_addback_multiple=web["restricted_investments_B"] / ttm["operating"]))
    accounting.append(row)
write_csv("equities_accounting.csv", accounting)

ai = ("NVDA", "GOOGL", "MSFT", "AVGO", "TSM", "MU", "AMZN", "META")
options = []
worst_error = 0
for i, (nv, go) in enumerate([(0, 0), (.035, .035), (0, .07), (.07, 0), (0, .035), (0, .02)]):
    w = dict(entry)
    w["NVDA"] += nv
    w["GOOGL"] += go
    w["MSFT"] = round(w["MSFT"] - nv - go, 6)
    assert min(w.values()) >= 0 and math.isclose(sum(w.values()), 1)
    e, daily, rc = risk(w)
    delta_ep, delta_fcf = [sum((w[sym] - entry[sym]) * y[j] for sym, y in yields.items())
                          for j in (0, 1)]
    budget = plan["budget_usd"]
    row = {"option": chr(65 + i), "NVDA_w": w["NVDA"], "MSFT_w": w["MSFT"], "GOOGL_w": w["GOOGL"],
           "vol": statistics.stdev(daily) * math.sqrt(252),
           "te_vs_long_term": statistics.stdev([a - b for a, b in zip(daily, lt_returns)]) * math.sqrt(252),
           "ai8_lt": sum(e[k] for k in ai), "rc_ai8": sum(rc[k] for k in ai),
           "d_fwd_ep_bp": delta_ep * 1e4, "d_fcf_yield_bp": delta_fcf * 1e4}
    for k in ("NVDA", "GOOGL", "MSFT"):
        row[k.lower() + "_lt"] = e[k]
        row["rc_" + k.lower()] = rc[k]
    largest = max((k for k in e if k != "VTI_rest"), key=e.get)
    row.update(largest_issuer=largest, largest_issuer_lt=e[largest],
               loss_if_nvda_minus30_usd=-.30 * e["NVDA"] * budget,
               loss_if_googl_minus30_usd=-.30 * e["GOOGL"] * budget,
               nvda_report_day_move_usd=.106 * e["NVDA"] * budget)
    published = pr["published_options"][i]
    assert row.keys() == published.keys() and largest == published["largest_issuer"]
    errors = [abs(float(published[k]) - v) for k, v in row.items() if isinstance(v, (int, float))]
    worst_error = max(worst_error, *errors)
    row.update(lookthrough_earnings_change_usd=delta_ep * budget,
               lookthrough_fcf_change_usd=delta_fcf * budget)
    options.append(row)
assert worst_error < 1e-9
write_csv("equities_options.csv", options)
g = pr["nvda_q3_guidance_model"]
wt = (date.fromisoformat(web["fiscal_end"]) - date(2026, 11, 17)).days / 365
nvda = {"last_day_FY27": web["fiscal_end"], "fy1_weight_1117": wt}
for key in ["fy28_eps_consensus_pre", "fy28_eps_scaled"]:
    nvda["pe_at_155_46_" + key] = 155.46 / (wt * g["fy27_eps_implied_clean"] + (1 - wt) * g[key])
for t in (2, 3):
    nvda[f"q{t}_ar_qoq"] = web[f"q{t}_ar_B"] / web[f"q{t-1}_ar_B"] - 1
    nvda[f"q{t}_sales_qoq"] = web[f"q{t}_rev_B"] / web[f"q{t-1}_rev_B"] - 1
    nvda[f"q{t}_DSO_91"] = 91 * web[f"q{t}_ar_B"] / web[f"q{t}_rev_B"]
liquid = web["cash_B"] + web["marketable_debt_B"]
nvda["guarantees_to_cash_and_debt_securities"] = web["guarantees_B"] / liquid
nvda["guarantees_to_cash_debt_and_equity_securities"] = web["guarantees_B"] / (liquid + web["marketable_equity_B"])
result = dict(inputs_sha256=inputs, risk_observations=len(dates)-1, largest_difference_six_options=worst_error,
              openai_sensitivities=marks, nvda=nvda)
(OUT / "equities_checks.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
