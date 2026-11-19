"""Verify received ZIP bytes, internal hash claims and overlaps with the previous GPT review."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

FOLDER = "gpt_archive_20261113"
REFRESH = "ai_portfolio_review_20261113_data_code.zip"
VALUATION = "ai_portfolio_valuation_data_and_code.zip"
PREFIX = "portfolio_refresh_20261113/"


def digest(payload):
    return sha256(payload).hexdigest()


def check(payload, expected, label, size=None):
    if digest(payload) != expected or (size is not None and len(payload) != size):
        raise ValueError(f"SHA-256 or length differs: {label}")


def inspect_archive(path):
    with ZipFile(path) as archive:
        records = [info for info in archive.infolist() if not info.is_dir()]
        files = {info.filename: archive.read(info) for info in records}  # read() validates CRC
        if len(files) != len(records):
            raise ValueError(f"Duplicate paths in {path.name}")
    meta = dict(sha256=digest(path.read_bytes()), bytes=path.stat().st_size, crc_members=len(files),
                members_by_root=dict(Counter(name.split("/")[0] for name in files)))
    return files, meta


def inspect_valuation(files):
    manifest = json.loads(files["MANIFEST.json"])
    listed = set()
    for entry in manifest["files"]:
        label = entry["path"]
        check(files[label], entry["sha256"], label, entry["bytes"])
        listed.add(label)
    if len(listed) != len(manifest["files"]):
        raise ValueError("Duplicate entries in original valuation manifest")
    raw_counts = {}
    for folder in ("market_data", "investment_plan_analysis", "ai_expansion_analysis"):
        if folder == "market_data":
            entries = json.loads(files[f"{folder}/provenance.json"])["series"]
        else:
            entries = json.loads(files[f"{folder}/new_data_sources.json"])
        for row in entries:
            label = f"{folder}/raw/{row['ticker']}.json"
            check(files[label], row["sha256"], label)
        raw_counts[folder] = len(entries)
    return dict(asof=manifest["asof"], price_end=manifest["price_end"], manifest_match=len(listed),
                not_in_manifest=sorted(files.keys()-listed), raw_provenance_match=raw_counts)


def inspect_refresh(files, old_review, inputs):
    def read(name):
        return json.loads(files[PREFIX+name])

    old_manifest_file = old_review.parent / "MANIFEST_SHA256.json"
    manifest_bytes = old_manifest_file.read_bytes()
    inputs["gpt_review_20261113/MANIFEST_SHA256.json"] = digest(manifest_bytes)
    old_manifest = json.loads(manifest_bytes)

    def prior(name):
        payload = (old_review / name).read_bytes()
        check(payload, old_manifest["data_audit/"+name], name)
        inputs[f"gpt_review_20261113/data_audit/{name}"] = digest(payload)
        return payload

    raw_counts = {}
    for folder in ("market_data", "market_data_extended"):
        entries = read(f"{folder}/provenance.json")["sources"]
        for ticker, row in entries.items():
            label = f"{folder}/raw/{ticker}.json"
            check(files[PREFIX+label], row["raw_sha256"], label, row["raw_bytes"])
        raw_counts[folder] = len(entries)

    ext = read("market_data_extended/provenance.json")
    for raw in ("adjusted", "close"):
        filename = "adjusted_close.csv" if raw == "adjusted" else "close.csv"
        check(files[PREFIX+"market_data/"+filename], ext[f"base_{raw}_csv_sha256"], filename)

    # Frozen selection in the pre-existing GPT review: 16 old names + 4 freshly fetched names.
    old_sources = json.loads(prior("provenance.json"))
    source_digest = digest(prior("original_16_asset_provenance.json"))
    check(files[PREFIX+"market_data_extended/provenance.json"], source_digest, "old full provenance")
    check(files[PREFIX+"market_data_extended/adjusted_close.csv"], old_sources["old_source_sha256"], "old extended CSV")
    old_names = sorted(p.stem for p in (old_review / "raw").glob("*.json") if p.stem not in old_sources["fresh"])
    if len(old_names) != 16:
        raise ValueError("Expected the frozen 16-name overlap from the earlier GPT review")
    for ticker in old_names:
        label = f"raw/{ticker}.json"
        check(files[PREFIX+"market_data_extended/"+label], digest(prior(label)), label)

    audits = {"independent_audit": ("portfolio_review", "market_data"),
              "conviction_independent_audit": ("portfolio_conviction_review", "market_data_extended")}
    for audit, (model, prices) in audits.items():
        report = read(f"analysis/{audit}.json")
        check(files[PREFIX+f"analysis/{model}.json"], report["audited_file_sha256"], model)
        check(files[PREFIX+f"{prices}/adjusted_close.csv"], report["source_adjusted_prices_sha256"], prices)
    workbook = read("analysis/workbook_verification.json")
    check(files[PREFIX+"analysis/portfolio_conviction_review.json"], workbook["modelSha256"], "workbook source model")
    brk = read("gemini_audit/brk_accounting_check.json")["sources"]
    if brk != read("analysis/portfolio_conviction_review.json")["berkshire_review"]["sources"]:
        raise ValueError("BRK provenance copies differ")
    known_digests = {digest(payload) for payload in files.values()}
    missing = {row["filename"]: row["sha256"] for row in brk.values()
               if "sha256" in row and row["sha256"] not in known_digests}
    return dict(raw_provenance_match=raw_counts, base_csv_hashes_match=2, prior_review_extended_csv_match=True,
                prior_review_extended_provenance_match=True, prior_review_raw_identical=old_names,
                audit_model_and_price_hashes_match=4, workbook_model_hash_match=True,
                berkshire_referenced_pdfs_absent=missing)


def main(root):
    folder = root / FOLDER
    refresh, rinfo = inspect_archive(folder / REFRESH)
    valuation, vinfo = inspect_archive(folder / VALUATION)
    inputs = {f"{FOLDER}/{REFRESH}": rinfo["sha256"], f"{FOLDER}/{VALUATION}": vinfo["sha256"]}
    rinfo.update(inspect_refresh(refresh, root/"gpt_review_20261113"/"data_audit", inputs))
    vinfo.update(inspect_valuation(valuation))
    common = sorted(refresh.keys() & valuation.keys())
    for member in common:
        check(refresh[member], digest(valuation[member]), member)
    data = dict(archives={REFRESH:rinfo, VALUATION:vinfo}, common_members_identical=common, inputs_sha256=inputs)
    out = folder / "out"
    out.mkdir(exist_ok=True)
    (out/"summary.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
