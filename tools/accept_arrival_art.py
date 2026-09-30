"""Bind inserted arrival artwork to native evidence and optional prior-build delta."""
import argparse
import json
from pathlib import Path

from tools.arrival_art import ATLAS, ATLAS_END, CONFIG, FONT, DESCRIPTORS, DESCRIPTORS_END, OWNER, POINTERS
from tools.extract_graphics_audition import save_json
from tools.rom import ROOT, digest, load_base, require
from tools.verify_arrival_art import CASES, OUT


def run(source, baseline=None):
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    base = load_base()
    require(build['output_sha256'] == digest(rom) and build['source_sha256'] == digest(base), 'Arrival build identity differs')
    art = build['arrival_cards']
    require(art['font_sha256'] == digest(FONT.read_bytes()) and art['config_sha256'] == digest(CONFIG.read_bytes()) and
            art['generator_sha256'] == digest((ROOT/'tools/arrival_art.py').read_bytes()), 'Stale arrival build inputs')
    require(art['english_graphic_count'] == 14 and len(art['entries']) == 13, 'Arrival artwork coverage changed')
    patches = [p for p in build['patches'] if p['owner'] == OWNER]
    allocations = [a for a in build['allocations'] if a['owner'] == OWNER]
    require({p['start'] for p in patches} == set(POINTERS) and len(allocations) == 2, 'Arrival patch ownership differs')
    for at, end in ((ATLAS-32, ATLAS_END), (DESCRIPTORS, DESCRIPTORS_END), (0x585304, 0x58B269)):
        require(rom[at:end] == base[at:end], 'Original artwork, palette or descriptors were overwritten')
    for a in allocations:
        require(a['start'] >= len(base) and digest(rom[a['start']:a['end_exclusive']]) == a['sha256'], 'Arrival resource allocation changed')
    native_path = OUT/'report.json'
    native = json.loads(native_path.read_text())
    require(native['passed'] and native['complete_matrix'] and native['rom_sha256'] == digest(rom), 'Native arrival matrix is incomplete or stale')
    require(native['generator_sha256'] == digest((ROOT/'tools/verify_arrival_art.py').read_bytes()), 'Native verifier changed')
    require({(c['selector'], c['floor']) for c in native['cases']} == set(CASES) and len(native['cases']) == len(CASES), 'Native matrix differs')
    for c in native['cases']:
        require(c['pixels_compared'] == 38400 and c['abi_and_stack_guard_preserved'] and c['battery_unchanged'], 'Native case lacks complete checks')
        require(len(c['vram_checks']) == len(c['returned']) == 1 and c['vram_checks'][0]['vram_bytes_checked'] == 0x18000, 'Native case lacks VRAM/return proof')
        require(digest((OUT/c['id']/'card.png').read_bytes()) == c['png_sha256'], 'Native screenshot changed')
        require(all(o['address'] in (0x02003B6C, 0x02005674) for o in c['overrides']), 'Unexpected controlled override')
    natural = [c for c in native['cases'] if c['natural_fields_and_inputs']]
    require(len(natural) == 1 and natural[0]['id'] == '11-floor-001' and not natural[0]['overrides'] and natural[0]['movement'], 'Ordinary first arrival/movement not verified')
    require(max(c['vram_checks'][0]['tiles'] for c in native['cases']) == 108, 'Largest tile upload not exercised')
    delta = None
    if baseline:
        old = (baseline/'torneko-2-english.gba').read_bytes()
        previous = json.loads((baseline/'build.json').read_text())
        require(digest(old) == previous['output_sha256'] and len(old) == len(rom), 'Prior ROM identity/size differs')
        require([a for a in build['allocations'] if a['owner'] != OWNER] == previous['allocations'] and
                [p for p in build['patches'] if p['owner'] != OWNER] == previous['patches'], 'Prior allocations or patches changed')
        restored = bytearray(rom)
        for p in patches:restored[p['start']:p['end_exclusive']] = old[p['start']:p['end_exclusive']]
        for a in allocations:restored[a['start']:a['end_exclusive']] = old[a['start']:a['end_exclusive']]
        require(bytes(restored) == old, 'Unrelated ROM bytes changed')
        require(build['reviewed_resource_counts'] == previous['reviewed_resource_counts'], 'Text resource counts changed')
        delta = {'previous_rom_sha256': digest(old), 'all_prior_allocations_patches_and_other_bytes_preserved': True,
                 'new_allocation_count': 2, 'new_literal_patch_count': 6, 'text_resource_count_unchanged': True}
    report = {'passed': True, 'rom_sha256': digest(rom), 'source_rom_sha256': digest(base),
              'english_graphics': 14, 'locations': 13, 'native_cases': len(CASES),
              'native_pixels_compared': sum(c['pixels_compared'] for c in native['cases']),
              'original_credits_palette_atlas_descriptors_preserved': True,
              'native_report_sha256': digest(native_path.read_bytes()), 'delta': delta,
              'allocations': allocations, 'patches': patches,
              'scope': 'Inserted arrival artwork accepted for all identified selectors through native controlled rendering and return. Fresh opening/meadow/tutorial/movement uses ordinary inputs. Late-dungeon natural access, later story transitions and full-game localization remain unverified.'}
    save_json(OUT/'acceptance.json', report)
    print('Arrival artwork accepted: 13 cards + Level, 30 native cases, preserved original credits.')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/english')
    p.add_argument('--baseline', type=Path)
    a = p.parse_args();run(a.source.resolve(), a.baseline.resolve() if a.baseline else None)
