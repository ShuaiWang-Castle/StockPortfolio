"""Reprice the prospectus and compare hypothetical, fully funded portfolios offline."""
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
FOLDER = ROOT / "codex_analysis_20261119"
OUT = FOLDER / "out"
OUT.mkdir(exist_ok=True)
PLAN = ROOT / "current_plan.json"
HISTORY = ROOT / "gpt_review_20261113/data_audit/adjusted_close.csv"
CONSTRUCTION = ROOT / "claude_analysis_20261114/out/summary.json"
FILING = FOLDER / "data/ant_filing_inputs.json"
QUOTE = FOLDER / "data/nasdaq_close.json"
SOURCES = FOLDER / "data/sources_web_20261119.json"
AI = ["NVDA", "TSM", "AVGO", "MU", "GOOGL", "META", "MSFT", "AMZN"]
NAMES = AI + ["BRK-B", "XLV", "SGOV", "VTI_rest"]


def read_json(path):
    return json.loads(path.read_text())


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: round(v, 10) if isinstance(v, float) else v for k, v in row.items()})


def growth_required(enterprise_value, cash_flow_value):
    lo, hi = 0., 1.
    assert cash_flow_value(lo) < enterprise_value < cash_flow_value(hi)
    for _ in range(80):
        mid = (lo + hi) / 2
        if cash_flow_value(mid) < enterprise_value:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def valuation():
    filing = read_json(FILING)
    offering = filing["offering"]
    capital = filing["capital"]
    quarter_revenue = filing["financials"]["quarterly_revenue_m_from_2025q1"][-1] / 1000
    start = 4 * quarter_revenue
    increments = filing["incremental_to_legal_economic_shares"]
    gross = (offering["legal_a"] + offering["legal_n"] + sum(
        qty for key, qty in increments.items() if key != "option_treasury_reduction_at_83"
    )) / 1e9
    proceeds = increments["option_treasury_reduction_at_83"] * offering["price"] / 1e9
    net_cash = capital["cash_short_pf_adjusted_b"] - capital["finance_lease_b"]
    quote = read_json(QUOTE)["data"]["secondaryData"]
    assert quote["lastTradeTimestamp"] == "Closed at Nov 19, 2026 4:00 PM ET"
    close = float(quote["lastSalePrice"].lstrip("$"))
    shares = gross - proceeds / close
    ev = shares * close - net_cash

    def dcf(growth, margin, later_growth=None):
        revenue, explicit, rate, perpetual = start, 0., .11, .025
        for year in range(1, 11):
            revenue *= 1 + (growth if later_growth is None or year <= 5 else later_growth)
            fcff = revenue * margin * year / 10
            explicit += fcff / (1 + rate) ** year
        terminal = fcff * (1 + perpetual) / (rate - perpetual) / (1 + rate) ** 10
        return explicit + terminal, terminal

    rows = []
    for growth in (.25, .30, .35, .40):
        for margin in (.20, .25, .30):
            value, terminal = dcf(growth, margin)
            fair_price = (value + net_cash + proceeds) / gross
            rows.append(dict(growth=growth, mature_fcff_margin=margin, modeled_ev_usd_b=value,
                             implied_price_today=fair_price, relative_to_close=fair_price/close-1,
                             share_of_ev_from_terminal=terminal/value))
    write_csv("valuation_scenarios.csv", rows)
    g = growth_required(ev, lambda g: dcf(g, .25)[0])
    five = growth_required(ev, lambda g: dcf(g, .25, .15)[0])
    return dict(close=close, diluted_shares_b=shares, diluted_cap_usd_b=shares*close,
                pro_forma_net_cash_usd_b=net_cash, ev_usd_b=ev,
                ev_over_q3_annualized=ev/start, ev_over_oct_run_rate=ev/filing["financials"]["run_rate_oct31_b_approx"],
                required_growth_10y=g, year10_revenue_usd_b=start*(1+g)**10,
                terminal_share=dcf(g, .25)[1]/ev, required_first5_if_last5_grow_15pct=five)


def historical_risk(anchor):
    with HISTORY.open() as handle:
        prices = {row["Date"]: {k: float(v) for k, v in row.items() if k != "Date"}
                  for row in csv.DictReader(handle)}
    reference = prices["2026-09-30"]

    def drift(row):
        return {k: w * (row[k] / reference[k]) / (row["VTI"] / reference["VTI"]) for k, w in anchor.items()}

    series = {k: [] for k in NAMES + ["factor"]}
    dates = sorted(prices)
    for prior, date in zip(dates, dates[1:]):
        if not "2023-11-14" <= date <= "2026-11-13":
            continue
        p, q = prices[prior], prices[date]
        day = {k: q[k] / p[k] - 1 for k in p}
        old = drift(p)
        day["VTI_rest"] = (day["VTI"] - sum(w*day[k] for k, w in old.items())) / (1-sum(old.values()))
        day["factor"] = statistics.mean(day[k] for k in AI)
        for k in series:
            series[k].append(day[k])
    assert len(series["factor"]) == 753
    cov = {i: {j: 252*statistics.covariance(series[i], series[j]) for j in series} for i in series}
    return drift(prices["2026-11-13"]), cov


def portfolio(close):
    plan, construction = read_json(PLAN), read_json(CONSTRUCTION)
    initial = plan["initial_purchase_2026_11_16"]["weights"]
    budget = plan["budget_usd"]
    holders = read_json(FILING)["holders"]["post_placement_n_total_shares"]
    caps = next(r for r in read_json(SOURCES) if r.get("id") == "market_caps")["numeric_inputs"]["market_cap_usd"]
    vti, cov = historical_risk(construction["vti_lookthrough"]["weights_2026_09_30"])
    factor_vol = math.sqrt(cov["factor"]["factor"])

    def evaluate(post, ant, beta, sigma):
        assert min(post.values()) >= 0 and abs(sum(post.values()) + ant - 1) < 1e-10
        e = {k: post.get(k, 0.) + post["VTI"] * vti.get(k, 0.) for k in NAMES}
        e["VTI_rest"] = post["VTI"] * (1 - sum(vti.values()))
        assert abs(sum(e.values())+ant-1) < 1e-10 and sigma >= beta*factor_vol
        ant_cov = {k: beta * cov[k]["factor"] for k in NAMES}
        marginal = {i: sum(e[j]*cov[i][j] for j in NAMES) + ant*ant_cov[i] for i in NAMES}
        ant_risk = ant * (sum(e[k]*ant_cov[k] for k in NAMES) + ant*sigma*sigma)
        variance = sum(e[k]*marginal[k] for k in NAMES) + ant_risk
        joint_loss = .30*e["NVDA"] + .60*ant
        indirect = sum(e[k] * holders[k] * close / caps[k] for k in holders)
        return dict(vti=post["VTI"], brk=post["BRK-B"], xlv=post["XLV"], sgov=post["SGOV"],
                    msft=post["MSFT"], nvda_direct=post["NVDA"], nvda_lookthrough=e["NVDA"],
                    ai9=ant+sum(e[k] for k in AI), vol=math.sqrt(variance),
                    rc_nvda=e["NVDA"]*marginal["NVDA"]/variance, rc_ant=ant_risk/variance,
                    indirect_ant_via_amzn_googl=indirect,
                    ant_plus_two_holders_loss_at_minus60_usd=budget*.60*(ant+indirect),
                    ant_only_loss_at_minus60_usd=budget*.60*ant,
                    joint_loss_usd_nvda_minus30_ant_minus60=budget*joint_loss)

    base = evaluate(initial, 0, 1.25, .70)
    assert round(base["vol"]*100, 2) == 17.62 and round(base["rc_nvda"]*100, 1) == 30.3
    reduced = initial.copy()
    reduced["NVDA"] -= .05
    for issuer, fraction in construction["construction"]["erc7_weights"].items():
        reduced[issuer] += .05*fraction
    sources = {k: {k: 1.} for k in ["VTI", "BRK-B", "XLV", "SGOV", "MSFT"]}
    sources["VTI_2_BRK_1"] = {"VTI": 2/3, "BRK-B": 1/3}
    results, sensitivity = [], []
    for rule, direct in [("entry", initial), ("export_cut", reduced)]:
        for source, splits in sources.items():
            for ant in (.00, .015, .02, .025, .03, .04, .05):
                post = direct.copy()
                for k, part in splits.items():
                    post[k] -= part*ant
                case = dict(rule=rule, funding=source, ant=ant)
                results.append(dict(**case, **evaluate(post, ant, 1.25, .70)))
                if source == "VTI_2_BRK_1" and ant == .03:
                    assumptions = [(b, s) for b in (1., 1.25, 1.5) for s in (.50, .70, .90)]
                    assumptions.append((.85*.90/factor_vol, .90))
                    for beta, sigma in assumptions:
                        sensitivity.append(dict(**case, beta=beta, sigma=sigma, corr=beta*factor_vol/sigma,
                                                **evaluate(post, ant, beta, sigma)))
    joint = initial.copy()
    joint["NVDA"] += .01
    joint["VTI"] -= .02
    joint["BRK-B"] -= .02
    results.append(dict(rule="entry_plus_nvda_1pp", funding="VTI_2_BRK_2", ant=.03,
                        **evaluate(joint, .03, 1.25, .70)))
    write_csv("funding.csv", results)
    write_csv("ant_risk_sensitivity.csv", sensitivity)
    return dict(baseline=base, issuer_drift_in_vti=vti, factor_volatility=factor_vol,
                assumed_ant_corr=1.25*factor_vol/.70, return_observations=753, budget=budget)


inputs = [PLAN, HISTORY, CONSTRUCTION, FILING, QUOTE, SOURCES]
value = valuation()
summary = dict(valuation=value, risk=portfolio(value["close"]),
               inputs_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
