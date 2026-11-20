"""Render the sourced chronology and verify filing and post times in New York."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

folder = Path(sys.argv[1]).resolve() / "codex_analysis_20261120"
data = folder / "data"
out = folder / "out"
out.mkdir(exist_ok=True)
events_file = data / "events.json"
sources_file = data / "sources_web_20261120.json"
metadata_file = data / "filing_metadata.json"
events = json.loads(events_file.read_text())
sources = json.loads(sources_file.read_text())
meta = json.loads(metadata_file.read_text())
index = {record["id"]: record for record in sources}
assert len(index) == len(sources)
lines = ["# 黄仁勋离职及寻求回任时间线", "", "日期按纽约时间。每行的证据说明标明是谁披露的。", "",
         "| 美东日期 | 证据 | 经过及来源 |", "|---|---|---|"]
for event in events:
    refs = [index[key] for key in event["sources"]]
    assert refs and all(r.get("claim") and r.get("retrieved_at") and r["url"].startswith("https://") for r in refs)
    links = " · ".join(f'[{r["source"]}]({r["url"]})' for r in refs)
    lines.append(f'| {event["date_et"]} | {event["evidence"]} | {event["detail"]} {links} |')
(out / "timeline.md").write_text("\n".join(lines) + "\n")

ny = ZoneInfo("America/New_York")
def eastern(utc):
    return datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(ny).isoformat()

records = {r["accessionNumber"]: r for r in meta["sec_submissions"]["rows"]}
officer_change = records["0001045810-26-000082"]
results = records["0001045810-26-000088"]
post = meta["x_syndication"]["fields"]
assert "5.02" in officer_change["items"].split(",") and post["user"]["screen_name"] == "JensenHuang"
times = dict(change_effective_date=officer_change["reportDate"],
             personnel_8k_accepted_et=eastern(officer_change["acceptanceDateTime"]),
             huang_statement_et=eastern(post["created_at"]), earnings_8k_accepted_et=eastern(results["acceptanceDateTime"]))
assert times["change_effective_date"] == "2026-11-11" and times["personnel_8k_accepted_et"][:10] == "2026-11-12"
assert times["huang_statement_et"] < times["earnings_8k_accepted_et"]
summary = dict(as_of="2026-11-20T16:00:00-05:00", verified_times=times, chronology_rows=len(events),
               inputs_sha256={str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (events_file, sources_file, metadata_file)})
(out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
