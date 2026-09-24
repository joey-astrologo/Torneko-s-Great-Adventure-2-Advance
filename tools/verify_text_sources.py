"""Check all seven bank decodes against native BIOS execution and retained sources."""

import json

import mgba.log
from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.extract_text import CATALOG
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import source_bytes, tokenize
from tools.town_text import resource as town_resource

OUTPUT = ROOT / "build/text-extraction/verification"


def verify():
    mgba.log.silence()
    original = load_base()
    save = default_rom().with_suffix(".sav")
    save_hash = digest(save.read_bytes()) if save.exists() else None
    results = []
    with Session(original, OUTPUT) as game:
        # Resume immediately before the real loader's BL to the BIOS wrapper,
        # retaining its CPU mode, stack and return context. Only the source
        # resource argument changes for the additional controlled cases.
        checkpoint = Snapshot.load(ROOT / "build/opening-text/fixtures/bank-load")
        game.restore(checkpoint)
        for bank in banks():
            before = bytes(game.core.memory[BANK_RAM - 64:BANK_RAM])
            end = BANK_RAM + len(bank["data"])
            after = bytes(game.core.memory[end:end + 64])
            try:
                cpu = game.core.cpu
                callee = [int(cpu.gprs[i]) & 0xFFFFFFFF for i in range(4, 12)]
                stack = int(cpu.gprs[13]) & 0xFFFFFFFF
                cpu.gprs[0] = 0x08000000 + bank["rom_offset"]
                cpu.gprs[1] = BANK_RAM
                with Debugger(game) as debugger:
                    debugger.breakpoint(0x0804D726)
                    # The built-in BIOS executes a stall loop proportional to
                    # decompression work; the default 100k-step probe budget is
                    # shorter than these valid calls, even for the first bank.
                    debugger.run_until(lambda events: bool(events), max_steps=3000000)
                result = debugger.events[-1]["registers"]
                require(result[4:12] == callee and result[13] == stack, "Decoder changed preserved registers/SP")
                native = bytes(game.core.memory[BANK_RAM:end])
                require(native == bank["data"], "Native LZ77 output differs")
                require(bytes(game.core.memory[BANK_RAM - 64:BANK_RAM]) == before, "Leading guard changed")
                require(bytes(game.core.memory[end:end + 64]) == after, "Trailing guard changed")
                results.append({"bank": bank["id"], "bytes": len(native), "sha256": digest(native),
                                "native_output_matches": True, "guards_and_registers_preserved": True})
            finally:
                game.restore(checkpoint)
    catalog = json.loads(CATALOG.read_text())
    require(catalog["source_rom_sha256"] == digest(original), "Catalog base mismatch")
    resources = {b["id"]: b["data"] for b in (*banks(), town_resource())}
    for row in catalog["entries"]:
        src = row["source"]
        data = original if src["kind"] == "rom" else resources[src["bank"]]
        tokens, end = tokenize(data, src["offset"], src["end_exclusive"])
        require(end == src["end_exclusive"] and tokens == row["tokens"], "Catalog token boundaries differ")
        require(source_bytes(tokens).hex() == row["raw_hex"] and digest(source_bytes(tokens)) == row["source_sha256"],
                "Catalog source round trip differs")
    require(digest(load_base()) == digest(original) and (digest(save.read_bytes()) if save.exists() else None) == save_hash,
            "Original inputs changed")
    report = {"passed": True, "emulator": version(), "bios": BIOS, "source_rom_sha256": digest(original),
              "source_save_sha256": save_hash, "original_files_unchanged": True, "bank_cases": results,
              "catalog_sources": len(catalog["entries"]), "catalog_sha256": digest(CATALOG.read_bytes()),
              "scope": "Controlled BIOS calls for seven event resources and source round trips for the entire catalog. The eighth/shared-town resource's native load and relocations are checked separately by tools.verify_town_text. Natural reachability is established only by documented route traces."}
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "native_bank_decodes": len(results), "catalog_round_trips": len(catalog["entries"])}))
    return report


if __name__ == "__main__":
    verify()
