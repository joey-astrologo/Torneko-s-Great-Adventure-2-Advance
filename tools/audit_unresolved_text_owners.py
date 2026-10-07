"""Census exact source-start pointers for the 62 unresolved shared/town records.

This checks literal ownership, not computed/interior pointers or code reachability.
It does not authorize insertion into unowned or context-unknown consumers.
"""
import json
from pathlib import Path
import struct

from tools.extract_shared_text import START, END
from tools.rom import ROOT, digest, load_base, require
from tools.town_text import RAM, LINK_BASE, COUNT, resource


def occurrences(data, value):
    needle, cursor, found = struct.pack('<I', value), 0, []
    while (cursor := data.find(needle, cursor)) >= 0:
        found.append(cursor)
        cursor += 1
    return found


def run():
    original = load_base()
    inventory_path = ROOT/'build/text-inventory/catalog.json'
    inventory = json.loads(inventory_path.read_text())['entries']
    town = resource()
    results = []
    for source in inventory:
        if source['family'] not in ('shared-system', 'town') or source['language_status'] != 'untranslated':
            continue
        raw = bytes.fromhex(source['raw_hex'])
        require(digest(raw) == source['source_sha256'], 'Catalog source digest differs')
        if source['family'] == 'shared-system':
            offset = int(source['id'][4:], 16)
            require(original[offset:offset+len(raw)] == raw, 'Shared source differs')
            hits = occurrences(original, 0x08000000+offset)
            require(hits and all(START <= p < END and (p-START) % 4 == 0 for p in hits),
                    'Additional shared literal owner needs investigation: '+source['id'])
            row = dict(id=source['id'], exact_pointer=0x08000000+offset,
                       rom_occurrences=hits, shared_indexes=[(p-START)//4 for p in hits],
                       disposition='Exact pointers occur only in the original shared table.')
        else:
            offset = int(source['id'].split('.')[1], 16)
            require(town['data'][offset:offset+len(raw)] == raw, 'Town source differs')
            linked, runtime = LINK_BASE+offset, RAM+offset
            slots = occurrences(town['data'], linked)
            raw_linked, raw_runtime = occurrences(original, linked), occurrences(original, runtime)
            require(slots and all(p < COUNT*4 and p % 4 == 0 for p in slots),
                    'Town pointer outside its original 300-word table')
            require(not raw_runtime and all(town['rom_offset'] <= p < town['rom_end_exclusive']
                                           for p in raw_linked), 'Additional town literal owner')
            row = dict(id=source['id'], linked_pointer=linked, runtime_pointer=runtime,
                decoded_table_slots=slots, table_indexes=[p//4 for p in slots],
                rom_linked_occurrences=raw_linked, rom_runtime_occurrences=raw_runtime,
                disposition='Exact decoded pointers occur only in the town table; raw-ROM '
                            'linked matches, if any, are within that compressed resource.')
        results.append(row)
    require(len(results) == 62 and sum(r['id'].startswith('rom.') for r in results) == 52,
            'Unresolved source cohort changed')
    report = dict(passed=True, source_sha256=digest(original),
        inventory_sha256=digest(inventory_path.read_bytes()),
        tool_sha256=digest(Path(__file__).read_bytes()), sources=results,
        scope=__doc__+' Whole 8 MiB original ROM, unaligned exact matches included. '
              'No extra source-start pointer owner found. Other compressed resources, '
              'interior pointers, arithmetic selectors and unknown code remain outside '
              'this exact-pointer census; no globally-unused classification or ROM change.')
    out = ROOT/'build/oct07-text/unresolved-pointer-owners.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print('Unresolved exact-pointer owners:', len(results), 'sources; no additional owner')


if __name__ == '__main__':
    run()
