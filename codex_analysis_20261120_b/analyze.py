"""Rebuild price moves, valuation sensitivities and portfolio risk from saved inputs."""
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

repo = Path(sys.argv[1]).resolve()
folder = repo / "codex_analysis_20261120_b"
raw = folder / "data/raw"
out = folder / "out"
out.mkdir(exist_ok=True)
ny = ZoneInfo("America/New_York")
inputs = []


def read_json(path):
    inputs.append(path)
    return json.loads(path.read_text())


plan = read_json(repo / "current_plan.json")
construction = read_json(repo / "claude_analysis_20261114/out/summary.json")
history_file = repo / "gpt_review_20261113/data_audit/adjusted_close.csv"
inputs.append(history_file)
with history_file.open() as handle:
    history = {r["Date"]: {k: float(v) for k, v in r.items() if k != "Date"} for r in csv.DictReader(handle)}
assert max(history) == "2026-11-13"
initial = plan["initial_purchase_2026_11_16"]["weights"]
ai = ["NVDA", "TSM", "AVGO", "MU", "GOOGL", "META", "MSFT", "AMZN"]
names = ai + ["BRK-B", "XLV", "SGOV", "VTI_rest"]
anchor = construction["vti_lookthrough"]["weights_2026_09_30"]
budget = plan["budget_usd"]

# At the common close, chain the new adjusted price relatives onto the frozen levels.
for ticker in initial:
    chart = read_json(raw / f"{ticker}_chart.json")["chart"]["result"][0]
    days = [datetime.fromtimestamp(t, ny).date().isoformat() for t in chart["timestamp"]]
    prices = chart["indicators"]["adjclose"][0]["adjclose"]
    assert days == ["2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    assert len(prices) == len(days) and all(p > 0 for p in prices)
    for day, price in zip(days[1:], prices[1:]):
        history.setdefault(day, {})[ticker] = history[days[0]][ticker] * price / prices[0]
dates = sorted(history)


def drift(row):
    ref = history["2026-09-30"]
    return {k: w * (row[k] / ref[k]) / (row["VTI"] / ref["VTI"]) for k, w in anchor.items()}


def issuer_covariance(first, last):
    series = {k: [] for k in names + ["AI_factor"]}
    for prev, day in zip(dates, dates[1:]):
        if not first <= day <= last:
            continue
        p, q = history[prev], history[day]
        returns = {k: q[k] / p[k] - 1 for k in initial}
        w = drift(p)
        returns["VTI_rest"] = (returns["VTI"] - sum(w[k]*returns[k] for k in w)) / (1 - sum(w.values()))
        returns["AI_factor"] = statistics.mean(returns[k] for k in ai)
        for k in series:
            series[k].append(returns[k])
    cov = {i: {j: 252 * statistics.covariance(series[i], series[j]) for j in series} for i in series}
    return cov, len(series["NVDA"])


def measure(cov, within_vti, nvda, ant):
    direct = initial.copy()
    direct["NVDA"] = nvda
    for ticker, fraction in construction["construction"]["erc7_weights"].items():
        direct[ticker] += (initial["NVDA"] - nvda) * fraction
    direct["VTI"] -= 2*ant/3
    direct["BRK-B"] -= ant/3
    e = {k: direct.get(k, 0.) + direct["VTI"] * within_vti.get(k, 0.) for k in names}
    e["VTI_rest"] = direct["VTI"] * (1-sum(within_vti.values()))
    assert abs(sum(e.values())+ant-1) < 1e-10 and min(direct.values()) >= 0
    ant_cov = {k: 1.25 * cov[k]["AI_factor"] for k in e}
    assert .70**2 > 1.25**2 * cov["AI_factor"]["AI_factor"]
    marginal = {i: sum(cov[i][j]*e[j] for j in e) + ant*ant_cov[i] for i in e}
    variance = sum(e[k]*marginal[k] for k in e) + ant*(sum(ant_cov[k]*e[k] for k in e) + ant*.70**2)
    risks = dict(volatility=math.sqrt(variance), nvda_risk_share=e["NVDA"]*marginal["NVDA"]/variance,
                 nvda_issuer_weight=e["NVDA"], ai8_issuer_weight=sum(e[k] for k in ai),
                 nvda_only_minus30_loss_usd=.30*e["NVDA"]*budget,
                 ai8_minus30_ant_minus60_loss_usd=(.30*sum(e[k] for k in ai)+.60*ant)*budget)
    direct["ANT"] = ant
    assert abs(sum(direct.values()) - 1) < 1e-10
    return dict(nvda_direct=nvda, ant_direct=ant, direct_target_usd=nvda*budget, **risks, direct_weights=direct)


portfolio = {}
for first, last in [("2023-11-14", "2026-11-13"), ("2023-11-21", "2026-11-20")]:
    covariance, observations = issuer_covariance(first, last)
    within_vti = drift(history[last])
    targets = [measure(covariance, within_vti, n, a) for a in (0., .03) for n in (.075, .10, .125)]
    portfolio[last] = dict(first=first, observations=observations, vti_estimated_nvda=within_vti["NVDA"], targets=targets)
base = portfolio["2026-11-13"]["targets"][2]
assert round(100*base["volatility"], 2) == 17.62 and round(100*base["nvda_risk_share"], 1) == 30.3

market = {}
for ticker in ("NVDA", "SOXX", "QQQ", "SPY", "VTI"):
    snap = read_json(raw / f"{ticker}_info.json")["data"]["secondaryData"]
    assert snap["lastTradeTimestamp"] == "Closed at Nov 20, 2026 4:00 PM ET"
    close = float(snap["lastSalePrice"].strip("$"))
    previous = round(close-float(snap["netChange"]), 2)
    market[ticker] = dict(close=close, previous=previous, day_return=close/previous-1)
nv_close = market["NVDA"]["close"]
nv_dates = read_json(raw / "NVDA_historical.json")["data"]["tradesTable"]["rows"]
moves = {r["date"]: nv_close / float(r["close"].strip("$")) - 1 for r in nv_dates}
assert abs(moves["11/19/2026"]-market["NVDA"]["day_return"]) < 1e-12
# Previous events must have a fully observed 20-session window as of today's close.
events = []
for i in range(1, len(dates)-20):
    day, prior = dates[i], dates[i-1]
    p = history[day]["NVDA"]
    loss = p/history[prior]["NVDA"]-1
    if loss <= -.10:
        events.append(dict(date=day, event_return=loss, after_5=history[dates[i+5]]["NVDA"]/p-1,
                           after_20=history[dates[i+20]]["NVDA"]/p-1))

forecasts = read_json(raw / "earnings_forecast.json")["data"]["yearlyForecast"]
eps = {r["fiscalEnd"]: r["consensusEPSForecast"] for r in forecasts["rows"]}
w = (date(2027,1,31)-date(2026,11,20)).days / 365
ntm = w*eps["Jan 2027"] + (1-w)*eps["Jan 2028"]
prices = [{"eps_change": a, "multiple_change": b, "price": nv_close*(1+a)*(1+b)}
          for a, b in [(-.10,-.10), (-.20,-.15), (0.,.15)]]
market_contract = read_json(raw / "next_ceo_market.json")["market"]
assert market_contract["ticker"] == "KXNVDACEO-29JAN-JENS"
summary = dict(market=market, nvda_return_to_close_by_start=moves,
               prior_10pct_down_days=events,
               valuation=dict(fy27=eps["Jan 2027"], fy28=eps["Jan 2028"], first_year_fraction=w,
                              ntm_eps=ntm, ntm_pe=nv_close/ntm, scenarios=prices),
               portfolio=portfolio,
               ceo_market={k:market_contract[k] for k in ("ticker","yes_bid_dollars","yes_ask_dollars","last_price_dollars")},
               inputs_sha256={str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
(out/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n")
