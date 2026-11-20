"""Value NVDA from the frozen November 20 public data and explicit assumptions."""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

folder = Path(sys.argv[1]).resolve() / "codex_analysis_20261120_c"
inputs = {}

def load(name):
    contents = (folder / "data" / name).read_bytes()
    inputs["data/" + name] = hashlib.sha256(contents).hexdigest()
    return json.loads(contents)

sources = load("sources_web_20261120.json")
facts = {record["data_group"]: record["values"] for record in sources if "data_group" in record}
params = load("scenarios.json")
q3, q4 = facts["fy27_q3"], facts["fy26_q4"]
shares = q3["diluted_q"]
quote = load("regular_price.json")["chart"]["result"][0]["meta"]
price = quote["regularMarketPrice"]
second_quote = load("cnbc_quote.json")["FormattedQuoteResult"]["FormattedQuote"][0]
assert price == float(second_quote["last"]) and quote["symbol"] == second_quote["symbol"] == "NVDA"
forecasts = load("earnings_forecast.json")["data"]
analysts = load("street_targets.json")["data"]["consensusOverview"]
eps = {r["fiscalEnd"]: r["consensusEPSForecast"] for r in forecasts["yearlyForecast"]["rows"]}

def fiscal_fraction(as_of, fiscal_end):
    days = (date.fromisoformat(fiscal_end) - date.fromisoformat(as_of)).days
    assert 0 < days < 365
    return days / 365

now_weight = fiscal_fraction(params["as_of"], facts["calendar"]["fy27_end"])
later_weight = fiscal_fraction(params["horizon"], facts["calendar"]["fy28_end"])
ntm = now_weight * eps["Jan 2027"] + (1 - now_weight) * eps["Jan 2028"]
quarterly = forecasts["quarterlyForecast"]["rows"]
assert [r["fiscalEnd"] for r in quarterly[:4]] == ["Jan 2027","Apr 2027","Jul 2027","Oct 2027"]
four_quarter_eps = sum(r["consensusEPSForecast"] for r in quarterly[:4])
reported_eps = q3["gaap_eps_9m"] + q4["gaap_eps"]
reported_quarters = [q4, facts["fy27_q1"], facts["fy27_q2"], dict(q3, diluted=shares)]
quarter_core_eps = [(q["net_income"] - q["other_income"] * (1 - params["nonoperating_tax_normalization"]))
                    / q["diluted"] for q in reported_quarters]
core_eps = sum(quarter_core_eps)
ttm_fcf = q3["fcf_9m"] + q4["fcf"]
cash_per_share = ttm_fcf / shares
r = params["equity_return"]
g = params["terminal_growth"]
years = params["dcf_cash_years"]
assert r > g and years >= 1

def cash_value(first_cash, growth):
    flows = [first_cash * (1 + growth) ** year for year in range(years)]
    explicit = sum(cash / (1 + r) ** t for t, cash in enumerate(flows, start=1))
    terminal = flows[-1] * (1 + g) / (r - g) / (1 + r) ** years
    return explicit + terminal

fy27_sales = q3["revenue_9m"] + q3["q4_revenue_mid"]
dividends = params["dividend_quarters"] * q3["quarter_dividend"]
cases = {}
for name, case in params["cases"].items():
    revenue = fy27_sales * (1 + case["fy28_sales_growth"])
    fy28 = revenue * case["after_tax_operating_margin"] / shares
    fy29 = fy28 * (1 + case["fy29_eps_growth"])
    forward_eps = later_weight * fy28 + (1 - later_weight) * fy29
    multiple = cash_value(case["cash_conversion"], case["years_2_to_5_eps_growth"])
    target = forward_eps * multiple
    cases[name] = dict(fy28_revenue_bn=revenue, fy28_eps=fy28, fy29_eps=fy29,
                       horizon_ntm_eps=forward_eps, exit_ntm_pe=multiple, target=target,
                       price_return=target/price-1, fair_today=(target+dividends)/(1+r))

# Invert the same five-year discounted cash model starting from actual TTM cash per share.
low, high = -.5, 1.0
assert cash_value(cash_per_share*(1+low),low) < price < cash_value(cash_per_share*(1+high),high)
for _ in range(80):
    mid = (low + high) / 2
    if cash_value(cash_per_share * (1 + mid), mid) < price:
        low = mid
    else:
        high = mid
implied_growth = (low + high) / 2
assert abs(cash_value(cash_per_share*(1+implied_growth),implied_growth)-price) < 1e-9
cash_checks = {str(next_growth): cash_value(cash_per_share*(1+params["cash_check_first_year_growth"]),next_growth)
               for next_growth in params["cash_check_following_growth"]}
current = dict(price=price, market_cap_vendor=second_quote["mktcapView"], ntm_eps=ntm,
               ntm_pe=price/ntm, four_quarter_eps=four_quarter_eps, four_quarter_pe=price/four_quarter_eps,
               gaap_eps_ttm=reported_eps, pe_gaap=price/reported_eps, core_eps_ttm=core_eps,
               pe_core=price/core_eps, ttm_fcf_bn=ttm_fcf, ttm_fcf_per_share=cash_per_share,
               price_to_fcf=price/cash_per_share, fcf_yield=cash_per_share/price,
               fcf_to_gaap_ni_ttm=ttm_fcf/(q3["ni_9m"]+q4["net_income"]),
               fcf_to_company_adjusted_ni_9m=q3["fcf_9m"]/q3["adjusted_ni_9m"])
base = cases["base"]
q4_mid_margin = (q3["q4_gm_low"] + q3["q4_gm_high"]) / 2
q4_operating_profit = q3["q4_revenue_mid"] * q4_mid_margin - q3["q4_gaap_opex"]
q4_core_eps = q4_operating_profit * (1 - q3["tax_mid"]) / shares
own_fy27_eps = sum(quarter_core_eps[1:]) + q4_core_eps
own_ntm = now_weight * own_fy27_eps + (1 - now_weight) * base["fy28_eps"]
own_pe = price / own_ntm
summary = dict(as_of=params["as_of"], current=current, fy27_revenue_at_guide_bn=fy27_sales,
               next_year_street_ntm=later_weight*eps["Jan 2028"]+(1-later_weight)*eps["Jan 2029"],
               analysts=analysts, cases=cases, expected_annual_dividend_assumed=dividends,
               today_discount_to_base_fair=1-price/base["fair_today"],
               own_fy27_eps=own_fy27_eps, own_base_ntm_eps=own_ntm, own_base_ntm_pe=own_pe,
               base_without_multiple_expansion=base["horizon_ntm_eps"]*own_pe,
               cash_checks=cash_checks, reverse_five_year_cash_growth=implied_growth, inputs_sha256=inputs)
output = folder / "out"
output.mkdir(exist_ok=True)
(output/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
