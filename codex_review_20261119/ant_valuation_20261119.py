"""Rebuild Anthropic's IPO share bridge and reverse DCF from frozen prospectus data."""
import json
import sys
from pathlib import Path


def present_value(start_revenue, growth, rate, initial_margin, mature_margin, perpetual):
    revenue = start_revenue
    operating_value = 0.0
    for year in range(1, 11):
        revenue *= 1 + growth
        margin = initial_margin + (mature_margin - initial_margin) * year / 10
        operating_value += revenue * margin / (1 + rate) ** year
    terminal = revenue * mature_margin * (1 + perpetual) / (rate - perpetual)
    terminal_pv = terminal / (1 + rate) ** 10
    return operating_value + terminal_pv, terminal_pv, revenue


def reverse_dcf(ev, revenue, rate, initial_margin, mature_margin, perpetual):
    low, high = 0.0, 1.0
    inputs = (rate, initial_margin, mature_margin, perpetual)
    assert present_value(revenue, low, *inputs)[0] < ev < present_value(revenue, high, *inputs)[0]
    for _ in range(80):
        growth = (low + high) / 2
        if present_value(revenue, growth, *inputs)[0] < ev:
            low = growth
        else:
            high = growth
    value, terminal_pv, last_revenue = present_value(revenue, growth, *inputs)
    assert abs(value - ev) < 1e-8
    return {"initial_revenue_b": revenue, "discount": rate, "initial_fcf_margin": initial_margin,
            "terminal_fcf_margin": mature_margin, "perpetual_growth": perpetual,
            "implied_10y_cagr": growth, "year10_revenue_b": last_revenue,
            "terminal_pv_fraction": terminal_pv / ev}


def main():
    folder = Path(sys.argv[1]).resolve() / "codex_review_20261119"
    data = folder / "data"
    facts = json.loads((data / "ant_filing_inputs.json").read_text())
    quote = json.loads((data / "ant_nasdaq_quote_1535.json").read_text())["data"]["primaryData"]
    prices = {"offer": facts["offering"]["price"], "opening_cross": facts["opening_price"],
              "claude_matched_only": facts["claude_comparison_price"],
              "nasdaq_1535_ET": float(quote["lastSalePrice"].strip("$"))}
    offering, capital = facts["offering"], facts["capital"]
    adjustments = facts["incremental_to_legal_economic_shares"]
    financials = facts["financials"]
    legal_economic = offering["legal_a"] + offering["legal_n"]
    accounting_basic = offering["legal_a"] + offering["accounting_n"]
    assert legal_economic - accounting_basic == offering["subsidiary_public_benefit_n"]
    gross_diluted = legal_economic + sum(value for key, value in adjustments.items()
                                        if key != "option_treasury_reduction_at_83")
    treasury_cash = offering["price"] * adjustments["option_treasury_reduction_at_83"]
    assert gross_diluted - adjustments["option_treasury_reduction_at_83"] == 18137587873
    assert sum(facts["holders"]["placement_increment_shares"].values()) == offering["placement_n"]
    greenshoe_proceeds_b = offering["price"] * offering["greenshoe_a"] / 1e9 - offering["greenshoe_incremental_underwriting_b"]
    full_shoe_cash_b = capital["cash_short_pf_adjusted_b"] + greenshoe_proceeds_b
    assert round(full_shoe_cash_b, 1) == capital["cash_short_full_shoe_b_rounded"]
    net_estimate = (offering["price"] * (offering["issuer_a"] + offering["placement_n"]) / 1e9
                    - offering["issuer_underwriting_usd"] / 1e9 - offering["other_offering_costs_b_approx"])
    assert round(net_estimate, 1) == offering["issuer_net_with_placement_b_rounded"]
    tt_rev = sum(financials["quarterly_revenue_m_from_2025q1"][-4:]) / 1000
    quarter_ann = 4 * financials["quarterly_revenue_m_from_2025q1"][-1] / 1000
    rr = financials["run_rate_oct31_b_approx"]
    assert sum(financials["quarterly_revenue_m_from_2025q1"][-3:]) == financials["nine_months_revenue_m"]
    comparison = []
    valuations = []
    for label, price in prices.items():
        shares = gross_diluted - treasury_cash / price
        equity = price * shares / 1e9
        ev = equity - capital["cash_short_pf_adjusted_b"] + capital["finance_lease_b"]
        full_shoe_ev = (equity + price * offering["greenshoe_a"] / 1e9
                        - full_shoe_cash_b + capital["finance_lease_b"])
        valuations.append({"label": label, "price": price, "diluted_shares_b": shares / 1e9,
                           "diluted_equity_b": equity, "operating_ev_b": ev,
                           "ps_ttm_accounting_basic": price * accounting_basic / 1e9 / tt_rev,
                           "ps_ttm_legal_economic": price * legal_economic / 1e9 / tt_rev,
                           "ps_ttm_diluted": equity / tt_rev, "ev_ttm": ev / tt_rev,
                           "ev_q3_annualized": ev / quarter_ann, "ev_run_rate": ev / rr,
                           "full_greenshoe_ev_b_approx": full_shoe_ev,
                           "ev_if_partner_rights_deducted_b": ev - capital["partner_warrant_rights_b"] - capital["partner_financing_rights_b"]})
        for rate in (0.10, 0.11, 0.12):
            for margin in (0.20, 0.25, 0.30):
                comparison.append({"quote": label, "model": "gaap_q3_annualized",
                                   **reverse_dcf(ev, quarter_ann, rate, 0, margin, 0.025)})
        for base_name, base in (("base_ttm", tt_rev), ("base_run_rate", rr)):
            comparison.append({"quote": label, "model": base_name,
                               **reverse_dcf(ev, base, 0.11, 0, 0.25, 0.025)})
        for initial in (-0.05, 0.05):
            comparison.append({"quote": label, "model": "opening_margin_sensitivity",
                               **reverse_dcf(ev, quarter_ann, 0.11, initial, 0.25, 0.025)})
        for rate in (0.10, 0.12):
            for margin in (0.25, 0.35):
                comparison.append({"quote": label, "model": "claude_assumptions_updated_ev",
                                   **reverse_dcf(ev, rr, rate, 0.08, margin, 0.03)})
    raw_fcf = financials["nine_months_ocf_m"] - financials["nine_months_capex_cash_m"]
    cash_proxy = raw_fcf - financials["nine_months_prepaid_lease_equipment_m"] - financials["nine_months_sbc_m"]
    results = {"legal_including_non_economic": legal_economic + offering["non_economic_t_f"],
               "accounting_basic_economic": accounting_basic, "legal_economic": legal_economic,
               "cash_short_pf_adjusted_b": capital["cash_short_pf_adjusted_b"],
               "net_issuer_proceeds_estimated_b": net_estimate, "full_shoe_pf_cash_b": full_shoe_cash_b,
               "withholding_b": capital["shares_withheld_rsu"] * offering["price"] / 1e9,
               "nine_months_ocf_minus_ppe_m": raw_fcf,
               "nine_months_after_prepaid_capex_and_sbc_m": cash_proxy,
               "nine_months_proxy_ex_gross_interest_m": cash_proxy - financials["nine_months_interest_income_m"],
               "revenue_ttm_b": tt_rev, "revenue_q3_annualized_b": quarter_ann,
               "run_rate_oct_b": rr, "unlock_cumulative_m_through_feb2": sum(facts["unlock_caps_m"].values()),
               "valuations": valuations, "reverse_dcf": comparison}
    out = folder / "out"
    out.mkdir(exist_ok=True)
    (out / "ant_valuation.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
