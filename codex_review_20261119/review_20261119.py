"""Rebuild this review solely from the repository's frozen inputs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
folder = root / "codex_review_20261119"
out = folder / "out"
scripts = ["ant_valuation_20261119.py", "equities_20261119.py", "portfolio_20261119.py"]
for script in scripts:
    subprocess.run([sys.executable, "-I", str(folder / script), str(root)], cwd=root, check=True)

ant = json.loads((out / "ant_valuation.json").read_text())
equities = json.loads((out / "equities_checks.json").read_text())
portfolio = json.loads((out / "portfolio.json").read_text())
history_file = folder / "data/history_audit_20261119.json"
inputs = {**equities["inputs_sha256"], **portfolio["inputs_sha256"]}
# Include the methodology and the separate, observed historical audit snapshot.
for item in [Path(__file__), history_file] + [folder / name for name in scripts]:
    inputs[str(item.resolve().relative_to(root))] = hashlib.sha256(item.read_bytes()).hexdigest()
for path, expected in inputs.items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected, path

intraday = next(row for row in ant["valuations"] if row["label"] == "nasdaq_1535_ET")
central = next(row for row in ant["reverse_dcf"] if row["quote"] == "nasdaq_1535_ET"
               and row["model"] == "gaap_q3_annualized" and row["discount"] == 0.11
               and row["terminal_fcf_margin"] == 0.25)
result = {
    "reviewed_main": "f9c4e5481742a828f7e548d0ad0ce6c99d613247",
    "reviewed_pr4": "d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64",
    "ant_asof_et": "2026-11-19 15:35 intraday",
    "ant_valuation": intraday,
    "ant_reverse_dcf_central": central,
    "ant_proposed_weight": {"low": 0.015, "central": 0.02, "high": 0.025,
                            "assumed_direct_loss_fraction": 0.60,
                            "max_direct_loss_fraction_of_portfolio": 0.015},
    "entry_portfolio": portfolio["entry"],
    "six_options_largest_abs_difference": equities["largest_difference_six_options"],
    "nvda_export_condition": "新许可已生效，专门针对的范围待决",
    "inputs_sha256": dict(sorted(inputs.items())),
}
(out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
