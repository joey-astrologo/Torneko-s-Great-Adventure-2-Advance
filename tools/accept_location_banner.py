"""Bind the complete menu checks to the one owned location-table redirect."""
import argparse
import json
import struct
from pathlib import Path

from tools.extract_graphics_audition import save_json
from tools.location_banner import LITERAL, OWNER
from tools.rom import ROOT, digest, load_base, require
from tools.verify_location_banner import OUT


def run(source, baseline=None):
    rom = (source / 'torneko-2-english.gba').read_bytes()
    build = json.loads((source / 'build.json').read_text())
    native = json.loads((OUT / 'report.json').read_text())
    require(build['output_sha256'] == native['rom_sha256'] == digest(rom) and native['passed'],
            'Dungeon banner native evidence is stale')
    require(native['generator_sha256'] == digest((ROOT / 'tools/verify_location_banner.py').read_bytes()),
            'Dungeon banner verifier changed')
    require({(r['selector'], r['mode']) for r in native['cases']} ==
            {(selector, mode) for selector in range(13) for mode in range(3)}, 'Incomplete menu matrix')
    patches = [p for p in build['patches'] if p['owner'] == OWNER]
    require(len(patches) == 1 and patches[0]['start'] == LITERAL and
            patches[0]['end_exclusive'] == LITERAL + 4 and
            patches[0]['before_hex'] == struct.pack('<I', 0x08140D68).hex(), 'Unexpected banner patch')
    require(not any(a['owner'] == OWNER for a in build['allocations']), 'Unexpected new location allocation')
    require(rom[LITERAL:LITERAL + 4] == struct.pack('<I', build['results']['shared_table'] + 0x08000000),
            'Banner table pointer differs')
    for case in native['cases']:
        require(len(case['captures']) == len(case['banner_reads']) == 3 and
                case['width_px'] <= case['budget_px'] == 168, 'Incomplete banner layout check')
        require(case['battery_and_dungeon_identity_unchanged'], 'Changed native identity/save')
        if case['natural']:
            require(not case['overrides'], 'Ordinary menu case used controlled inputs')
        for image in case['captures']:
            path = OUT / 'native' / f'{case["selector"]:02}-mode-{case["mode"]}' / (image['phase'] + '.png')
            require(image['all_five_fields_checked'] and digest(path.read_bytes()) == image['png_sha256'],
                    'Native menu capture changed')
    delta = None
    if baseline:
        old = (baseline / 'torneko-2-english.gba').read_bytes()
        prior = json.loads((baseline / 'build.json').read_text())
        restored = bytearray(rom)
        restored[LITERAL:LITERAL + 4] = old[LITERAL:LITERAL + 4]
        require(bytes(restored) == old and digest(old) == prior['output_sha256'], 'Unrelated ROM bytes changed')
        require(build['allocations'] == prior['allocations'] and
                [p for p in build['patches'] if p['owner'] != OWNER] == prior['patches'],
                'Existing ownership changed')
        require(build['reviewed_resource_counts'] == prior['reviewed_resource_counts'], 'Text counts changed')
        require(native['negative_control'] and native['negative_control']['rejected'] and
                native['negative_control']['rom_sha256'] == digest(old), 'Old untranslated menu was not rejected')
        delta = {'baseline_sha256': digest(old), 'only_changed_range': [LITERAL, LITERAL + 4],
                 'all_other_bytes_and_allocations_unchanged': True, 'old_rom_rejected': True}
    receipt = {'passed': True, 'rom_sha256': digest(rom), 'source_sha256': digest(load_base()),
               'native_report_sha256': digest((OUT / 'report.json').read_bytes()), 'patches': patches,
               'locations': 13, 'cases': 39, 'menu_openings': 117, 'text_resources': build['total_reviewed_inserted_resources'],
               'delta': delta, 'scope': native['scope']}
    save_json(OUT / 'acceptance.json', receipt)
    print('Location banner accepted: 13 names, 39 cases, one pointer patch; no new text resources.')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    run(args.source.resolve(), args.baseline.resolve() if args.baseline else None)
