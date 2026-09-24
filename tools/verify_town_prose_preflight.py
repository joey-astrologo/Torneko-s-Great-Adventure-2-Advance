"""Render reviewed plain town prose without changing any town pointer binding.

Reuses the verified native two-row reader reached by an ordinary dungeon
resume. This is a rendering preflight, not proof of a town caller's geometry,
question flow, formatting capacity or service progression.
"""
import json
from tools.rom import ROOT, digest, require
from tools.town_text import entries, resource
from tools.dialogue_layout import compile_dialogue

OUT = ROOT / 'build/town-prose-preflight'
CATALOG = ROOT / 'translations/town-prose-review.json'


def candidate():
    import tools.build_english as english
    previous = english.add_combat
    catalog = json.loads(CATALOG.read_text())
    sources = {r['id']: r for r in entries()}
    rows = []

    def add(build):
        combat = previous(build)
        require(catalog['base_rom_sha256'] == digest(build.original), 'Town prose base differs')
        require(len({r['id'] for r in catalog['entries']}) == len(catalog['entries']), 'Duplicate town prose')
        for row in catalog['entries']:
            source = sources[row['id']]
            raw = resource()['data'][source['start']:source['end_exclusive']]
            require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Town prose source differs')
            require(row['status'] == 'reviewed' and row['prose_review'], 'Missing town prose review')
            require(b'%' not in raw and not any(c in row['english'] for c in ('@A@', '@B@', '@C@')), 'Town special consumer excluded')
            payload, layout = compile_dialogue(row['english'], source['tokens'])
            offset = build.allocate('preflight-' + row['id'], payload, 'town-prose-rendering-preflight')
            rows.append(row | {'rom_offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
        return combat

    try:
        english.add_combat = add
        rom, build = english.build_rom(include_story=False, include_extra_consumers=False)
    finally:
        english.add_combat = previous
    build['preflight'] = {'entries': rows, 'excluded': [], 'catalog_sha256': digest(CATALOG.read_bytes())}
    build['scope'] = catalog['scope'] + ' Controlled rendering uses the ordinary resume reader; no town consumer binding or branch outcomes are claimed.'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'game.gba').write_bytes(rom)
    (OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
    return rom, build


def run():
    from tools import verify_prose_preflight as shared
    previous = shared.candidate, shared.OUT
    try:
        shared.candidate, shared.OUT = candidate, OUT
        shared.run()
    finally:
        shared.candidate, shared.OUT = previous


if __name__ == '__main__':
    run()
