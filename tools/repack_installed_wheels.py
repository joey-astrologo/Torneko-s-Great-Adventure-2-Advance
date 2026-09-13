"""Recover pinned wheels offline from a matching reference venv's RECORD files.

Installed console scripts are excluded; pip regenerates them for the new venv.
Every copied payload is checked against its installed RECORD hash. This is an
offline recovery path, not a claim to reproduce upstream wheel archive bytes.
"""

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from tools.rom import ROOT, require


def repack(reference, output):
    site = reference.resolve() / ".venv/lib/python3.11/site-packages"
    output.mkdir(parents=True, exist_ok=True)
    recovered = []
    for line in (ROOT / "docs/python-toolchain.lock.txt").read_text().splitlines():
        name, version = line.split("==")
        stem = name.replace("-", "_") + "-" + version
        if list(output.glob(stem + "-*.whl")):
            continue
        info = site / (stem + ".dist-info")
        tags = [s[5:] for s in (info / "WHEEL").read_text().splitlines() if s.startswith("Tag: ")]
        require(len(tags) == 1, f"Expected one wheel tag for {stem}")
        records, payloads = [], {}
        for rel, expected_hash, size in csv.reader((info / "RECORD").read_text().splitlines()):
            if ".." in Path(rel).parts or not expected_hash:
                continue
            data = (site / rel).read_bytes()
            algorithm, expected = expected_hash.split("=", 1)
            actual = base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest()).decode().rstrip("=")
            require(actual == expected and len(data) == int(size), f"Installed payload changed: {rel}")
            payloads[rel] = data
            records.append((rel, expected_hash, size))
        record_path = info.name + "/RECORD"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerows(records)
        writer.writerow((record_path, "", ""))
        payloads[record_path] = buffer.getvalue().encode()
        target = output / f"{stem}-{tags[0]}.whl"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for rel, data in sorted(payloads.items()):
                entry = zipfile.ZipInfo(rel)
                entry.create_system = 3
                entry.external_attr = ((site / rel).stat().st_mode if rel != record_path else 0o100644) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
        recovered.append({"wheel": target.name, "verified_payloads": len(records),
                          "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    if recovered:
        receipt = output / "recovered-wheels.json"
        previous = json.loads(receipt.read_text()).get("wheels", []) if receipt.exists() else []
        combined = {entry["wheel"]: entry for entry in previous + recovered}
        receipt.write_text(json.dumps({
            "reference": str(reference.resolve()), "wheels": list(combined.values())}, indent=2) + "\n")
    print(json.dumps(recovered, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".tools/wheels")
    args = parser.parse_args()
    repack(args.reference, args.output)
