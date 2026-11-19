"""Verify pinned Git trees and, with --rerun, rebuild PR 4 on a case-sensitive temporary volume."""
import argparse
import csv
from decimal import Decimal
from hashlib import sha256
import io
import json
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile

MAIN = "f9c4e5481742a828f7e548d0ad0ce6c99d613247"
PR4 = "d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64"
GPT = "gpt_review_20261113"
RUNS = {
    "claude_analysis_20261116": ("msft_reallocation_20261116.py", "make_figures_20261116.py"),
    "claude_analysis_20261117": ("nvda_q3fy27_check.py", "make_figures_20261117.py"),
    "claude_analysis_20261119": ("ant_ipo_sizing_20261119.py", "make_figures_20261119.py"),
}
TOL = Decimal("1e-9")


def archive(root, commit):
    data = subprocess.check_output(["git", "-C", str(root), "archive", "--format=tar", commit])
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        return {member.name: tar.extractfile(member).read() for member in tar if member.isfile()}


def verify(files, path, digest, size=None):
    payload = files[path]
    if sha256(payload).hexdigest() != digest or (size is not None and len(payload) != size):
        raise ValueError(f"Frozen file differs from recorded SHA-256 or size: {path}")


def check_tree(files):
    counts = {}
    for path in sorted(files):
        if not path.endswith("/manifest.json"):
            continue
        folder = path.rsplit("/", 1)[0]
        manifest = json.loads(files[path])
        entries = manifest["files"]
        if isinstance(entries, list):
            entries = {entry["path"]: entry for entry in entries}
        for rel, entry in entries.items():
            verify(files, f"{folder}/{rel}", entry["sha256"], entry["bytes"])
        inputs = manifest.get("inputs", {})
        for rel, digest in inputs.items():
            verify(files, rel, digest)
        summary_path = f"{folder}/out/summary.json"
        embedded = json.loads(files[summary_path])["inputs_sha256"] if summary_path in files else {}
        for rel, digest in embedded.items():
            verify(files, rel, digest)
        counts[folder] = dict(files_with_sha256_and_size=len(entries), manifest_inputs=len(inputs),
                              summary_inputs=len(embedded))

    imported = json.loads(files[f"{GPT}/MANIFEST_SHA256.json"])
    for rel, digest in imported.items():
        verify(files, f"{GPT}/{rel}", digest)
    import_note = files[f"{GPT}/README_IMPORT.md"].decode()
    chat_hash = re.search(r"GPT_chat_review_20261113\.md.*?SHA-256 `([0-9a-f]{64})`", import_note)[1]
    verify(files, f"{GPT}/GPT_chat_review_20261113.md", chat_hash)
    plan = json.loads(files["current_plan.json"])["source"]["sha256"]
    for path, digest in plan.items():
        verify(files, path, digest)

    csv_path = f"{GPT}/data_audit/adjusted_close.csv"
    pricing = json.loads(files["claude_analysis_20261114/out/summary.json"])["prices"]
    verify(files, csv_path, pricing["gpt_csv_sha256"])
    method = json.loads(files[f"{GPT}/review_results/methodology.json"])
    verify(files, csv_path, method["price_input_sha256"])

    for folder in ("claude_analysis_20261113", f"{GPT}/reference_inputs"):
        meta = json.loads(files[f"{folder}/data/meta.json"])
        for rel, digest in meta["blocks"].items():
            payload = files[f"{folder}/{rel}"]
            if not payload.endswith(b"\n") or sha256(payload[:-1]).hexdigest() != digest:
                raise ValueError(f"Browser block differs, after removing one final LF: {folder}/{rel}")

    base = f"{GPT}/data_audit"
    older = json.loads(files[f"{base}/original_16_asset_provenance.json"])
    fresher = json.loads(files[f"{base}/provenance.json"])
    missing_raw = []
    for ticker, original in older["sources"].items():
        path = f"{base}/raw/{ticker}.json"
        if path in files:
            verify(files, path, original["raw_sha256"], original["raw_bytes"])
        else:
            missing_raw.append(ticker)
    for ticker, fresh in fresher["fresh"].items():
        verify(files, f"{base}/raw/{ticker}.json", fresh["sha256"])
    known_blobs = {sha256(payload).hexdigest() for payload in files.values()}
    old_csvs = (older["base_adjusted_csv_sha256"], older["base_close_csv_sha256"], fresher["old_source_sha256"])
    browser_hash = json.loads(files["claude_analysis_20261113/manifest.json"])["raw_price_data_sha256"]
    zip_hash = re.search(r"zip SHA-256.*?`([0-9a-f]{64})`", import_note)[1]
    return dict(manifests=counts, gpt_manifest_files=len(imported), gpt_chat_file=1,
                plan_sources=len(plan), extra_adjusted_close_references=2, browser_blocks_per_copy=4,
                old_raw_present=len(older["sources"]) - len(missing_raw), fresh_raw_present=len(fresher["fresh"]),
                provenance_only_tickers=sorted(missing_raw), missing_older_csv_hashes=sum(digest not in known_blobs for digest in old_csvs),
                missing_browser_price_array=browser_hash not in known_blobs, missing_import_zip=zip_hash not in known_blobs)


def difference(left, right, where, is_csv=False):
    """Require equal schema, row order and text. Max absolute error uses decimal file values."""
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            raise ValueError(f"Object keys differ at {where}")
        return max((difference(v, right[k], f"{where}.{k}") for k, v in left.items()), default=Decimal(0))
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise ValueError(f"Length differs at {where}")
        return max((difference(x, y, f"{where}[{i}]", is_csv) for i, (x, y) in enumerate(zip(left, right))),
                   default=Decimal(0))
    if type(left) != type(right):
        raise ValueError(f"Types differ at {where}")
    if left == right:
        return Decimal(0)
    if is_csv:
        try:
            left, right = Decimal(left), Decimal(right)
        except ArithmeticError as error:
            raise ValueError(f"Non-numeric text differs at {where}") from error
    if isinstance(left, Decimal) and isinstance(right, Decimal):
        if left.is_nan() and right.is_nan():
            return Decimal(0)
        if left.is_finite() and right.is_finite():
            return abs(left - right)
    raise ValueError(f"Values differ at {where}")


def compare_run(files, tree):
    records = {}
    for folder in RUNS:
        entries = json.loads(files[f"{folder}/manifest.json"])["files"]
        actual = {str(f.relative_to(tree/folder)) for sub in ("out", "figures")
                  for f in (tree/folder/sub).rglob("*") if f.is_file()}
        expected = {p for p in entries if p.startswith(("out/", "figures/"))}
        if actual != expected:
            raise ValueError(f"Generated file inventory differs: {folder}")
        result = {}
        for rel, entry in entries.items():
            original = files[f"{folder}/{rel}"]
            payload = (tree / folder / rel).read_bytes()
            same = sha256(payload).hexdigest() == entry["sha256"] and len(payload) == entry["bytes"]
            if rel not in expected:
                if not same:
                    raise ValueError(f"Static file changed: {folder}/{rel}")
                continue
            row = dict(byte_identical=same, actual_sha256=sha256(payload).hexdigest(), actual_bytes=len(payload))
            if rel.endswith(".png"):
                row["original_dimensions"] = struct.unpack(">II", original[16:24])
                row["rebuilt_dimensions"] = struct.unpack(">II", payload[16:24])
            else:
                if rel.endswith(".csv"):
                    a, b = (list(csv.reader(io.StringIO(x.decode()))) for x in (original, payload))
                    if a[0] != b[0]:
                        raise ValueError(f"CSV column headers differ: {rel}")
                    error = difference(a[1:], b[1:], rel, is_csv=True)
                elif rel.endswith(".json"):
                    a, b = (json.loads(x, parse_int=Decimal, parse_float=Decimal, parse_constant=Decimal)
                            for x in (original, payload))
                    error = difference(a, b, rel)
                else:
                    raise ValueError(f"Unsupported output format: {rel}")
                row["max_abs_error"] = str(error)
                if error > TOL:
                    raise ValueError(f"Numeric error {error} exceeds {TOL} in {folder}/{rel}")
            result[rel] = row
        records[folder] = dict(static_files=len(entries)-len(expected), rebuilt=result)
    return records


def clean_rerun(files):
    from importlib.metadata import version
    from matplotlib import font_manager
    env = dict(os=platform.system(), release=platform.mac_ver()[0] or platform.release(),
               architecture=platform.machine(), python=platform.python_version(),
               packages={p: version(p) for p in ("numpy", "pandas", "scipy", "matplotlib")})
    fonts = {}
    for weight in ("normal", "bold"):
        prop = font_manager.FontProperties(family="Noto Sans CJK SC", weight=weight)
        selected = Path(font_manager.findfont(prop))
        fonts[weight] = dict(filename=selected.name, sha256=sha256(selected.read_bytes()).hexdigest())
    env["font_files"] = fonts
    with tempfile.TemporaryDirectory() as temp:
        tree = Path(temp)
        (tree / "lower").touch()
        if (tree / "LOWER").exists():
            raise RuntimeError("Use a case-sensitive TMPDIR to preserve out_FINAL.json and out_final.json")
        (tree / "lower").unlink()
        for rel, payload in files.items():
            dest = tree / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
        for folder in RUNS:
            for sub in ("out", "figures"):
                shutil.rmtree(tree / folder / sub)
        for folder, scripts in RUNS.items():
            for script in scripts:
                subprocess.run([sys.executable, "-I", f"{folder}/{script}", "."], cwd=tree, check=True,
                               stdout=subprocess.DEVNULL)
        return dict(environment=env, absolute_tolerance=str(TOL), results=compare_run(files, tree))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()
    result = {}
    for commit in (MAIN, PR4):
        tree = archive(args.repo, commit)
        result[commit] = check_tree(tree)
    if args.rerun:
        result["clean_export"] = clean_rerun(tree)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
