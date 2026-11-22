"""Offline calculations. Run from the checkout with the repository root as argument."""
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def change(new, old):
    return round(100 * (new / old - 1), 4)


def history(events):
    previous_monday = None
    rows = []
    for row in events:
        day = date.fromisoformat(row["event"]["day"])
        monday = day - timedelta(days=day.weekday())
        isolated = previous_monday is None or (monday - previous_monday).days > 28
        previous_monday = monday
        current = row["event"]["close"]
        entry = {"day": day.isoformat(), "weekly_return_pct": change(current, row["previous"]["close"]),
                 "no_signal_in_prior_four_weeks": isolated}
        for term in ("next_week", "four_weeks_later"):
            observation = row[term]
            entry[term] = change(observation["close"], current) if observation else None
        rows.append(entry)
    sample = [r for r in rows if r["no_signal_in_prior_four_weeks"] and r["four_weeks_later"] is not None]
    return {"events": rows, "completed_episodes": len(sample),
            "next_week_up": sum(r["next_week"] > 0 for r in sample),
            "four_weeks_later_up": sum(r["four_weeks_later"] > 0 for r in sample)}


def analyze(root):
    folder = root / "codex_analysis_20261122"
    data = folder / "data"
    plan = root / "current_plan.json"
    registry = read(data / "sources_web_20261122.json")
    summary = {"inputs_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [plan, *sorted(data.glob("*.json"))]}}
    indexes = {}
    for name in ("GSPC", "IXIC", "RUT", "SOX"):
        quote = registry[name]["script_inputs"]
        close = quote["close_1120"]
        indexes[name] = {"close": close, "day_pct": change(close, quote["close_1119"]),
                         "week_pct": change(close, quote["close_1113"]),
                         "drawdown_pct": change(close, quote["peak_close"]), "peak_day": quote["peak_day"]}
    summary["indices"] = indexes
    summary["vix_close"] = registry["VIX"]["script_inputs"]
    summary["oas_bp"] = {}
    for name in ("HY", "IG"):
        rates = registry[name]["script_inputs"]
        summary["oas_bp"][name] = {"nov19": round(100 * rates["2026-11-19"]),
                                   "change_since_nov13": round(100 * (rates["2026-11-19"] - rates["2026-11-13"]))}
    overnight = {}
    for series in ("sofr", "effr"):
        overnight[series] = {r["effectiveDate"]: r["percentRate"] for r in read(data / (series + ".json"))["refRates"]}
    summary["sofr_less_effr_bp"] = {day: round(100 * (rate - overnight["effr"][day]))
                                    for day, rate in overnight["sofr"].items()}
    operations = read(data / "repoops.json")["repo"]["operations"]
    summary["nov20_srf_accepted_usd"] = {r["closeTime"]: r["totalAmtAccepted"] for r in operations
                                         if r["operationDate"] == "2026-11-20"}
    summary["sp500_history"] = history(read(data / "weekly_events.json"))
    settings = read(plan)
    equity = settings["budget_usd"] * (1 - settings["initial_purchase_2026_11_16"]["weights"]["SGOV"])
    summary["hypothetical_equity_usd"] = round(equity, 2)
    summary["hypothetical_loss_usd"] = {str(pct): round(equity * pct / 100, 2) for pct in [10, 20]}
    out = folder / "out"
    out.mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    analyze(Path(sys.argv[1]).resolve())
