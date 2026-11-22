"""Revalue ANT and balance the proposed dollar allocation against the adopted entry plan."""
import hashlib
import json
import math
import sys
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def cash_flow_value(revenue, growth):
    annual_fcff = 0.0
    present = 0.0
    for year in range(1, 11):
        revenue *= 1 + growth
        annual_fcff = revenue * .25 * year / 10
        present += annual_fcff / 1.11**year
    return present + annual_fcff * 1.025 / (.11 - .025) / 1.11**10


def ant(filing, close, added_shares):
    offer = filing['offering']
    increments = filing['incremental_to_legal_economic_shares'].copy()
    exercise_b = increments.pop('option_treasury_reduction_at_83') * offer['price'] / 1e9
    gross_b = (offer['legal_a'] + offer['legal_n'] + sum(increments.values()) + added_shares) / 1e9
    cash_b = filing['capital']['cash_short_pf_adjusted_b'] + added_shares * offer['price'] / 1e9
    net_cash_b = cash_b - filing['capital']['finance_lease_b']
    diluted_b = gross_b - exercise_b / close
    ev_b = diluted_b * close - net_cash_b
    sales_b = filing['financials']['quarterly_revenue_m_from_2025q1'][-1] * 4 / 1000
    lo, hi = 0., 1.
    assert cash_flow_value(sales_b, lo) < ev_b < cash_flow_value(sales_b, hi)
    for _ in range(65):
        mid = (lo + hi) / 2
        if cash_flow_value(sales_b, mid) < ev_b:
            lo = mid
        else:
            hi = mid
    return dict(close=close, diluted_shares_b=diluted_b, pro_forma_cash_and_sti_b=cash_b,
                net_cash_b=net_cash_b, ev_b=ev_b, ev_to_q3_annualized=ev_b/sales_b,
                implied_sales_cagr=(lo+hi)/2, value_if_growth_30pct=(cash_flow_value(sales_b,.30)+net_cash_b+exercise_b)/gross_b)


def calculate(root):
    folder = root/'codex_analysis_20261122_b'
    data = folder/'data'
    plan_path = root/'current_plan.json'
    erc_path = root/'claude_analysis_20261114/out/summary.json'
    plan = read(plan_path)
    weights = plan['initial_purchase_2026_11_16']['weights'].copy()
    freed = weights['NVDA'] - .075
    weights['NVDA'] = .075
    for symbol, fraction in read(erc_path)['construction']['erc7_weights'].items():
        weights[symbol] += freed * fraction
    weights['VTI'] -= .02
    weights['BRK-B'] -= .01
    weights['ANT'] = .03
    budget = plan['budget_usd']
    amounts = {s: w*budget for s,w in weights.items()}
    dollars = {s: math.floor(round(x, 8)) for s,x in amounts.items()}
    for symbol in sorted(dollars, key=lambda s: amounts[s]-dollars[s], reverse=True)[:budget-sum(dollars.values())]:
        dollars[symbol] += 1
    assert math.isclose(sum(weights.values()), 1) and sum(dollars.values()) == budget
    risk = read(data/'risk_extract.json')
    assert all(math.isclose(w,risk[0]['direct_weights'][s]) for s,w in weights.items())
    sources = read(data/'sources_web_20261122.json')
    inputs = [s['script_inputs'] for s in sources if isinstance(s['script_inputs'],dict)]
    extra = next(s['extra_shares_issuer'] for s in inputs if 'extra_shares_issuer' in s)
    filing = read(data/'ant_filing_inputs.json')
    assert extra == filing['offering']['greenshoe_a']
    closes = {r['date']:float(r['close'].lstrip('$')) for r in read(data/'ant_close.json')['data']['tradesTable']['rows']}
    credit = {s['class']: {date:round(100*rate) for date,rate in s['oas_pct'].items()} for s in inputs if 'class' in s}
    rates = {s['series']:s['rate_pct'] for s in inputs if 'series' in s}
    results = dict(inputs_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in [plan_path,erc_path,*sorted(data.glob('*.json'))]},
                   allocation_weight=weights, whole_dollar_targets=dollars, reference_oas_bp=credit,
                   nov19_sofr_less_effr_bp=round(100*(rates['sofr']-rates['effr'])),
                   ant_prior_no_shoe_assumption=ant(filing,closes['11/19/2026'],0),
                   ant_friday_full_shoe=ant(filing,closes['11/20/2026'],extra),
                   ant_direct_loss_if_down_60pct=round(.6*amounts['ANT'],2),
                   risk_cases=[{k:v for k,v in row.items() if k!='direct_weights'} for row in risk])
    (folder/'out').mkdir(exist_ok=True)
    (folder/'out/summary.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')


if __name__ == '__main__':
    calculate(Path(sys.argv[1]).resolve())
