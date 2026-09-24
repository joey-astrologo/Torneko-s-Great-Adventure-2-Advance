"""Retain verified Japanese sources and separately export broad scan candidates."""

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.opening_text import banks, manifest
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import readable, source_bytes, tokenize
from tools.town_text import resource as town_resource

OUTPUT = ROOT / "build/text-extraction"
CATALOG = ROOT / "translations/master.json"
TRACE = ROOT / "build/opening-text/trace.json"


def merge_catalog(previous, incoming, source_hash):
    require(previous.get("source_rom_sha256", source_hash) == source_hash, "Catalog base differs")
    entries = {e["id"]: dict(e) for e in previous.get("entries", [])}
    require(len(entries) == len(previous.get("entries", [])), "Duplicate existing source ID")
    require(len({e["id"] for e in incoming}) == len(incoming), "Duplicate incoming source ID")
    for row in incoming:
        existing = entries.get(row["id"], {})
        require(not existing or existing["source_sha256"] == row["source_sha256"], "Existing source bytes changed")
        # Translator-owned fields and unknown future editorial metadata survive.
        merged = dict(existing)
        merged.update(row)
        if "evidence" in row:
            observations = existing.get("evidence", []) + row["evidence"]
            merged["evidence"] = list({json.dumps(e, sort_keys=True): e for e in observations}.values())
        for field, default in (("english", None), ("notes", ""), ("language_status", "untranslated")):
            merged[field] = existing.get(field, default)
        entries[row["id"]] = merged
    # Legacy trace receipts mixed source certainty with then-pending insertion
    # work. Keep this field about source evidence; current builds have their own
    # allocation/acceptance reports, and editorial review remains separate.
    for row in entries.values():
        row['status'] = 'native-source-verified'
    return {"schema": 1, "source_rom_sha256": source_hash,
            "scope": "Verified native sources accumulated from documented routes; not all game text.",
            "entries": sorted(entries.values(), key=lambda row: row["id"])}


def japanese_count(text):
    return sum("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" or "\uff66" <= c <= "\uff9d" for c in text)


def scan(data, resource, verified):
    candidates, counts, start = [], Counter(), 0
    while start < len(data):
        counts["nul_boundary_starts"] += 1
        if data[start] != 0 and (data[start] in (1, 2, 3, 4, 6, 13, 14, 0x20, 0x40) or
                                 0x81 <= data[start] <= 0x9F or 0xE0 <= data[start] <= 0xFC):
            try:
                tokens, end = tokenize(data, start, min(len(data), start + 8192))
                text = "".join(t.get("text", "") for t in tokens)
                unresolved = sum(t.get("semantic_status") == "unresolved" for t in tokens)
                jp = japanese_count(text)
                if jp >= 4 and jp >= len(text) * 0.35 and not unresolved:
                    if any(lo <= start < hi for lo, hi in verified):
                        counts["inside_verified_source"] += 1
                    else:
                        raw = source_bytes(tokens)
                        candidates.append({"id": f"candidate.{resource}.{start:08x}", "resource": resource,
                                           "offset": start, "end_exclusive": end, "raw_hex": raw.hex(),
                                           "source_sha256": digest(raw), "japanese": readable(tokens),
                                           "status": "scan-candidate; source boundary and consumer unverified"})
                        counts["candidates"] += 1
                else:
                    counts["below_language_filter_or_unresolved_tokens"] += 1
            except ValueError:
                counts["decoder_rejected_or_bound_exceeded"] += 1
        next_zero = data.find(b"\0", start)
        if next_zero < 0:
            break
        start = next_zero + 1
    return candidates, dict(counts)


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 Japanese text inventory</title><style>
:root{color-scheme:dark;font:16px/1.5 system-ui;background:#101a2b;color:#eef3fa}body{max-width:1200px;margin:32px auto;padding:0 20px}
h1{font-size:30px}p{max-width:950px;color:#bdcde0}input,select{font:inherit;background:#1c2c43;color:inherit;border:1px solid #61728a;padding:10px;border-radius:6px}
input{width:min(65%,650px)}article{border-top:1px solid #34435a;padding:18px 0}.id{font:13px monospace;color:#91d8bd}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}
pre{font:15px/1.6 system-ui;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0}.status{color:#d8bd81;font-size:13px}a{color:#91d8bd}button{font:inherit;padding:8px 14px;margin:8px;background:#263b57;color:white;border:1px solid #61728a;border-radius:5px}
@media(max-width:700px){.columns{grid-template-columns:1fr}} img{image-rendering:pixelated;max-width:100%;width:480px}
</style><h1>Torneko 2 — Japanese text inventory</h1>
<p>Verified sources have been observed through the game's native reader or formatter and matched to original ROM bytes or a decompressed ROM bank.
Scan candidates are separate research leads. These counts do not measure the percentage of the whole game found or translated.</p>
<p id="totals"></p><input id="search" placeholder="Search Japanese, English, source ID or address" aria-label="Search text inventory">
<select id="scope" aria-label="Evidence filter"><option value="verified">Verified native sources</option><option value="candidates">Unverified scan candidates</option></select>
<p id="count"></p><main id="results"></main><button id="prev">Previous</button><button id="next">Next</button>
<p><a href="../../translations/master.json">Editable verified catalog</a> · <a href="candidates.json">Candidate leads</a> · <a href="report.json">Extraction report</a> ·
<a href="../opening-text/trace.json">Native source trace</a> · <a href="../../docs/OPENING_TEXT.md">Scope and reproduction</a></p>
<p>The view is a generated snapshot. Edit the verified catalog, then regenerate; browser searching does not change translations.</p>
<p>Language review is separate from insertion and gameplay acceptance. See the <a href="../../docs/OPENING_ENGLISH.md">current English build and tested scope</a>.</p>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent), search=document.getElementById('search'), scope=document.getElementById('scope'); let page=0;
document.getElementById('totals').textContent=data.verified.length+' verified sources; '+data.candidates.length+' scan candidates; '+data.bankCount+' decoded text-bank resources.';
function render(){const q=search.value.trim().toLowerCase().replace(/^0x/,''), rows=data[scope.value].filter(r=>{
const addresses=[r.offset,r.source?.offset,...(r.evidence||[]).map(e=>e.source)].filter(Number.isInteger).map(n=>n.toString(16));
return JSON.stringify([r.id,r.japanese,r.english,r.source,...addresses]).toLowerCase().includes(q);});
page=Math.max(0,Math.min(page,Math.max(0,Math.ceil(rows.length/30)-1)));const out=document.getElementById('results');out.replaceChildren();
document.getElementById('count').textContent=rows.length+' matches — page '+(page+1)+' of '+Math.max(1,Math.ceil(rows.length/30));
for(const r of rows.slice(page*30,page*30+30)){const article=document.createElement('article'),id=document.createElement('div'),status=document.createElement('div'),cols=document.createElement('div');
id.className='id';id.textContent=r.id;status.className='status';status.textContent=[r.status,r.language_status&&'language: '+r.language_status,r.batch&&'batch: '+r.batch].filter(Boolean).join(' · ');cols.className='columns';
for(const text of [r.japanese,r.english??(scope.value==='verified'?'English not drafted':'Candidate only; verify before translation/insertion')]){const pre=document.createElement('pre');pre.textContent=text;cols.append(pre);}
article.append(id,status,cols);out.append(article);}document.getElementById('prev').disabled=page===0;document.getElementById('next').disabled=(page+1)*30>=rows.length;}
for(const e of [search,scope])e.addEventListener('input',()=>{page=0;render();});document.getElementById('prev').addEventListener('click',()=>{page--;render();});document.getElementById('next').addEventListener('click',()=>{page++;render();});render();
</script></html>'''


def extract(output=OUTPUT, catalog_path=CATALOG, trace_path=TRACE):
    original = load_base()
    trace_bytes = trace_path.read_bytes()
    trace = json.loads(trace_bytes)
    require(trace["passed"] and trace["source_rom_sha256"] == digest(original), "Native trace is for another ROM")
    incoming = trace["entries"]
    bank_map = {b["id"]: b for b in (*banks(), town_resource())}
    for row in incoming:
        src = row["source"]
        data = original if src["kind"] == "rom" else bank_map[src["bank"]]["data"]
        raw = data[src["offset"]:src["end_exclusive"]]
        require(source_bytes(row["tokens"]) == raw == bytes.fromhex(row["raw_hex"]), "Japanese round trip differs")
        require(digest(raw) == row["source_sha256"], "Source hash differs")
    previous = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    catalog = merge_catalog(previous, incoming, digest(original))
    candidates, scans = [], []
    for resource, data in [("rom", original)] + [(b["id"], b["data"]) for b in bank_map.values()]:
        verified = [(e["source"]["offset"], e["source"]["end_exclusive"]) for e in catalog["entries"]
                    if ("rom" if e["source"]["kind"] == "rom" else e["source"]["bank"]) == resource]
        found, counts = scan(data, resource, verified)
        candidates.extend(found)
        scans.append({"resource": resource, "bytes": len(data), **counts})
    output.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    (output / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n")
    report = {"passed": True, "source_rom_sha256": digest(original), "native_trace_sha256": digest(trace_bytes),
              "catalog_sha256": digest(catalog_path.read_bytes()), "verified_sources": len(catalog["entries"]),
              "round_trip_sources_checked": len(incoming), "scan_candidates": len(candidates), "scans": scans,
              "bank_resources": [{k:v for k,v in b.items() if k != 'data'} for b in bank_map.values()], "source_and_editorial_fields_separate": True,
              "scan_limits": "NUL-boundary starts only; at least four Japanese characters and 35% Japanese text, no unresolved tokens, maximum 8192 source bytes. Rejected starts are not proven non-text. Relative/computed references, other compression families and graphics remain outside this scan.",
              "scope": "Verified catalog and heuristic candidate queue are separate; no whole-game coverage percentage."}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    payload = {"verified": catalog["entries"], "candidates": candidates, "bankCount": len(bank_map)}
    (output / "index.html").write_text(PAGE.replace("__DATA__", json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")))
    print(json.dumps({k: report[k] for k in ("passed", "verified_sources", "round_trip_sources_checked", "scan_candidates")}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--trace", type=Path, default=TRACE)
    args = parser.parse_args()
    extract(args.output.resolve(), trace_path=args.trace.resolve())
