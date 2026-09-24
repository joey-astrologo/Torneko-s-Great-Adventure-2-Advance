"""Insert reviewed text through owned direct pointers and per-bank offsets."""

import json
import struct

from tools.compact_font import encode, measure
from tools.book_text import (BANK_STARTS as BOOK_STARTS, COMMON_STARTS, DIRECT as BOOK_DIRECT,
                             compile_menu, compile_overwrite)
from tools.dialogue_layout import compile_dialogue
from tools.event_text import table_entries
from tools.home_sale import ORIGINAL as SALE_ORIGINAL, compile_sale
from tools.lz77 import decompress, pack_literals
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, require
from tools.text_codec import tokenize
from tools.town_text import (RELOCATION, resource as town_resource, entries as town_entries)

OWNER = 'opening-dialogue'
CATALOG = ROOT / 'translations/master.json'
DIRECT = {'rom.0006309c': 0x14110C, 'rom.0006b0e8': 0x147238,
          'rom.00061cf8': 0x141318, 'rom.00061cec': 0x14131C, 'rom.00061cdc': 0x141320,
          'rom.00061db0': 0x1412F8, 'rom.000617ec': 0x1413B4,
          'rom.0006b080': 0x14723C, 'rom.0006b03c': 0x147240, 'rom.0006b570': 0x178C0,
          'rom.0006c524': 0x14D718, 'rom.0006c14c': 0x14BEA0,
          'rom.0014c8f4': 0x51648, 'rom.0006c424': 0x51660}
DIRECT.update(BOOK_DIRECT)
DIRECT.update({'rom.0006afe0': 0x147244, 'rom.00061a08': 0x141378,
               'rom.00061978': 0x141384, 'rom.0006155c': 0x141444})
DIRECT['rom.00061998'] = 0x141380
HOLY_FLAME_STARTS = {0x691E,0x6ED5,0x69B8,0x6A06,0x6A74,0x6C40,0x6E07,
                    0x0D86,0x256D,0x2613,0x268E,0x26A9,0x288D,0x4F16,
                    0x2A64,0x3878,0x2B04,0x2B5F,0x2C1E,0x2C82,0x2D46,
                    0x2F37,0x2F78,0x331B,0x32CA,0x0FE0,0x1001,0x0AB5}
MANSION_STARTS = {0xD4E, 0xD6B, 0x172E, 0x1745, 0x1785, 0x17C1, 0x1803,
                  0x1BDF, 0x1CA5, 0x1D53, 0x1DA3, 0x1E74, 0x1E97, 0x202D,
                  0x2081, 0x2414, 0x24FA, 0x252E, 0x47B9}
MANSION_COMMON = {0x4B0, 0x527}
BANK_OWNERS = {
    'event-bank-0': ('opening-bank', OWNER),
    'event-bank-1': ('home-bank', 'home-return'),
    **{f'event-bank-{i}': (f'story-bank-{i}', 'event-prose') for i in range(2,7)},
}
HOME_STARTS = {0x400, 0x557, 0x56E, 0x121E, 0x1249, 0x128A, 0x12BE, 0x146E, 0x149C,
               0x292E, 0x3622, 0x3790, 0x3846, 0x388D, 0x4022}
MENU_ROWS = {'rom.00061cf8', 'rom.00061cec', 'rom.00061cdc'}


def add_dialogue(build, include_story=True):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['source_rom_sha256'] == digest(build.original), 'Dialogue catalog base differs')
    require(len({e['id'] for e in catalog['entries']}) == len(catalog['entries']), 'Duplicate dialogue ID')
    owned_banks = {b['id']: b for b in banks() if b['id'] in BANK_OWNERS}
    bank_data = {ident: bytearray(b['data']) for ident, b in owned_banks.items()}
    tables = {}
    for bank in owned_banks.values():
        for entry in table_entries(bank):
            tables.setdefault(entry['id'], []).append(entry)
    entries, changed_by_bank = [], {ident: [] for ident in owned_banks}
    for row in catalog['entries']:
        if row.get('batch') not in (OWNER, 'first-dungeon', 'castle-arrival', 'castle-conversations', 'destination-menu', 'home-return', 'home-books', 'mansion-quest', 'holy-flame-quest'):
            continue
        owner = row['batch']
        require(row['english'] and row['language_status'] == 'reviewed', 'Missing reviewed English text')
        source = row['source']
        if source.get('bank') == 'town-common':
            continue  # Its 300 linked pointers have a distinct native relocation rule.
        is_bank = source['kind'] == 'compressed-bank'
        require((is_bank and source['bank'] in owned_banks and row['id'] in tables)
                or (source['kind'] == 'rom' and row['id'] in DIRECT), 'Unowned dialogue source')
        if is_bank:
            bank = owned_banks[source['bank']]
            data, changed = bank_data[bank['id']], changed_by_bank[bank['id']]
            require((bank['index'] == 0 and owner not in ('home-return', 'home-books', 'mansion-quest')) or
                    (bank['index'] == 1 and ((owner == 'home-return' and source['offset'] in HOME_STARTS)
                     or (owner == 'home-books' and source['offset'] in BOOK_STARTS)
                     or (owner == 'mansion-quest' and source['offset'] in MANSION_STARTS)
                     or (owner == 'holy-flame-quest' and source['offset'] in HOLY_FLAME_STARTS))),
                    'Unowned bank/batch selection')
        raw = (bank['data'] if is_bank else build.original)[source['offset']:source['end_exclusive']]
        require(raw.hex() == row['raw_hex'] and digest(raw) == row['source_sha256'], 'Dialogue source changed')
        require(tokenize(raw)[0] == row['tokens'], 'Dialogue source tokens changed')
        if row['id'] == 'rom.00148304':
            require(owner == 'home-books' and raw.count(b'%s') == 1, 'Unowned overwrite format')
            payload, layout = compile_overwrite(row['english'])
        elif row['id'] == 'rom.0006c424':
            require(raw == SALE_ORIGINAL and owner == 'home-return', 'Unowned sale template')
            payload, layout = compile_sale(row['english'])
        elif row['id'] in ('rom.0006c524', 'rom.0006c14c', 'rom.0006c144', 'rom.0006c154'):
            payload, layout = compile_dialogue(row['english'], row['tokens'])
            require(len(layout['pages']) == 1 and len(layout['pages'][0]) == 1, 'Destination label must stay on one row')
            inset, native_width = (0, 56) if row['id'] == 'rom.0006c524' else (12, 152)
            require(layout['line_widths'][0][0] + inset <= native_width, 'Destination label exceeds its window')
            if inset:
                payload = bytes((6, inset)) + payload
            layout.update(left_inset=inset, native_width=native_width, encoded_bytes=len(payload))
        elif row['id'] in MENU_ROWS:
            require('\n' not in row['english'] and measure(row['english']) <= 88, 'Initial-menu row overflows')
            payload = b'\x06\x08' + encode(row['english'])
            layout = {'pages': [[row['english']]], 'positions': [8], 'native_width': 96,
                      'encoded_bytes': len(payload), 'commands': []}
        elif row['id'] == 'rom.0006b570':
            lines = row['english'].split('\n')
            require(len(lines) == 3 and all(measure(line) <= 90 for line in lines), 'Stair-menu layout differs')
            payload = encode(row['english'])
            layout = {'pages': [lines], 'left_inset': 6, 'native_width': 96,
                      'encoded_bytes': len(payload), 'commands': []}
        elif row['id'] == 'rom.0006309c':
            require(row['english'] == 'Yes / No', 'Choice labels require their measured layout')
            payload = b'\x06\x08' + encode('Yes')[:-1] + b'\x06\x28' + encode('No')
            layout = {'pages': [['Yes', 'No']], 'positions': [8, 40], 'native_width': 80,
                      'encoded_bytes': len(payload), 'commands': []}
        else:
            payload, layout = compile_dialogue(row['english'], row['tokens'])
        if row['id'] == 'rom.0006155c':
            require(len(layout['pages']) == 1 and len(layout['pages'][0]) == 1
                    and layout['line_widths'][0][0] <= 212, 'Quest result exceeds its single native row')
        allocated = build.allocate(row['id'], payload, owner)
        record = {'id': row['id'], 'rom_offset': allocated, 'source_sha256': row['source_sha256'],
                  'encoded_hex': payload.hex(), 'layout': layout, 'language_status': row['language_status'],
                  'batch': owner}
        if is_bank:
            record['bank'] = bank['id']
            record['slots'] = []
            for entry in tables[row['id']]:
                require(entry['start'] == source['offset'] and entry['end_exclusive'] == source['end_exclusive'],
                        'Table source boundaries differ')
                slot = entry['slot']
                relative = 0x08000000 + allocated - (BANK_RAM + entry['strings_offset'] + entry['group_offset'])
                require(0 <= relative <= 0xFFFFFFFF, 'Relative ROM target out of range')
                require(data[slot:slot + 4] == struct.pack('<I', entry['relative']), 'Offset slot already changed')
                data[slot:slot + 4] = struct.pack('<I', relative)
                record['slots'].append({k: entry[k] for k in ('group', 'index', 'slot', 'relative')}
                                       | {'replacement': relative})
                changed.append(slot)
        else:
            build.patch(row['id'] + '-pointer', DIRECT[row['id']],
                        struct.pack('<I', 0x08000000 + source['offset']),
                        struct.pack('<I', 0x08000000 + allocated), owner)
        entries.append(record)
    destinations = {row['id'] for row in entries if row['batch'] == 'destination-menu'}
    if destinations:
        require(destinations == {'rom.0006c524', 'rom.0006c14c'}, 'Destination question and home label must be inserted together')
        for ident, offset, expected, replacement in (
                ('question-width', 0x4CB20, '0c22', '0722'),
                ('list-x', 0x4CB36, '0f20', '0a20'),
                ('list-width', 0x4CB3A, '0c22', '1322')):
            build.patch('destination-' + ident, offset, bytes.fromhex(expected), bytes.fromhex(replacement),
                        'destination-menu')
    require(entries and changed_by_bank['event-bank-0'], 'No opening dialogue selected')
    story_consumers = {}
    prose_review = None
    if include_story:
        from tools.event_prose_text import add_prose
        from tools.floor_progress_text import add_progress
        from tools.well_level_text import add_well_level
        from tools.village_prose_text import add_village_prose
        from tools.medal_text import add_medals
        from tools.story_command_text import add_commands
        prose_rows, prose_review = add_prose(build, bank_data, changed_by_bank)
        entries.extend(prose_rows)
        for family, insert in (('floor_progress',add_progress),('well_level',add_well_level),
                               ('village_prose',add_village_prose),('medals',add_medals)):
            report = insert(build, bank_data, changed_by_bank)
            story_consumers[family] = report
            for row in report['entries']:
                source_bank = next(ident for ident in owned_banks if row['id'].startswith(ident+'.'))
                entries.append(row | {'rom_offset':row['offset'], 'bank':source_bank,
                                      'language_status':'reviewed', 'batch':family})
        commands = add_commands(build, bank_data, changed_by_bank)
        story_consumers['story_commands'] = commands
        entries.extend(row | {'batch':'story_commands'} for row in commands['entries'])
        require(len({r['id'] for r in entries}) == len(entries), 'Overlapping dialogue families')
    bank_reports = []
    for ident, bank in owned_banks.items():
        data, changed = bank_data[ident], changed_by_bank[ident]
        if not changed:
            continue
        restored = bytearray(data)
        for slot in changed:
            restored[slot:slot + 4] = bank['data'][slot:slot + 4]
        require(bytes(restored) == bank['data'], 'Unowned decoded-bank modification')
        require(len(changed) == len(set(changed)), 'Duplicate changed offset slot')
        packed = pack_literals(data)
        decoded, end = decompress(packed)
        require(decoded == data and end == len(packed), 'Packed event bank does not round-trip')
        resource, owner = BANK_OWNERS[ident]
        allocated = build.allocate(resource + '-offsets', packed, owner)
        build.patch(resource + '-pointer', bank['pointer_offset'],
                    struct.pack('<I', 0x08000000 + bank['rom_offset']),
                    struct.pack('<I', 0x08000000 + allocated), owner)
        bank_reports.append({'id': ident, 'bank_rom_offset': allocated, 'bank_decoded_bytes': len(data),
                             'bank_decoded_sha256': digest(data), 'changed_slots': sorted(changed),
                             'original_decoded_bytes_except_slots_preserved': True, 'new_ram_bytes': 0})
    # Existing opening consumers retain their bank-zero fields. New consumers
    # select the named record; another bank can never silently stand in for it.
    town_rows, town_report = add_town_dialogue(build, catalog)
    entries.extend(town_rows)
    if include_story:
        offsets = {r['id']:r['bank_rom_offset'] for r in bank_reports}
        for family in ('floor_progress','medals'):
            bank_id = 'event-bank-5' if family == 'floor_progress' else 'event-bank-6'
            story_consumers[family]['bank_rom_offset'] = offsets[bank_id]
        for family in ('well_level','village_prose'):
            for bank in story_consumers[family]['banks']:
                bank['offset'] = offsets[bank['id']]
    opening = next(r for r in bank_reports if r['id'] == 'event-bank-0')
    return {'catalog_sha256': digest(CATALOG.read_bytes()), 'entries': entries,
            'banks': bank_reports, 'town_resource': town_report,
            'event_prose_review_sha256':prose_review, 'story_consumers':story_consumers,
            **{k: v for k, v in opening.items() if k != 'id'}}


def add_town_dialogue(build, catalog):
    bank = town_resource()
    decoded = bytearray(bank['data'])
    rows, changed = [], []
    for row in catalog['entries']:
        source = row['source']
        if source.get('bank') != bank['id'] or row.get('batch') not in ('home-books', 'mansion-quest'):
            continue
        owner = row['batch']
        starts = COMMON_STARTS if owner == 'home-books' else MANSION_COMMON
        require(row['language_status'] == 'reviewed' and source['offset'] in starts,
                'Unreviewed or unowned shared-town entry')
        raw = bank['data'][source['offset']:source['end_exclusive']]
        require(raw.hex() == row['raw_hex'] and digest(raw) == row['source_sha256'] and
                tokenize(raw)[0] == row['tokens'], 'Shared-town source changed')
        payload, layout = (compile_menu(row['english']) if source['offset'] == 0x3DEC else
                           compile_dialogue(row['english'], row['tokens']))
        require(len(layout['pages']) == 1, 'Shared-town book message must fit its native window')
        allocated = build.allocate(row['id'], payload, owner)
        slots = []
        for entry in town_entries():
            if entry['id'] != row['id']:
                continue
            require((entry['start'], entry['end_exclusive']) == (source['offset'],source['end_exclusive']),
                    'Town table/source bounds differ')
            slot = entry['slot']
            require(decoded[slot:slot + 4] == struct.pack('<I', entry['linked_pointer']), 'Town slot already changed')
            replacement = (0x08000000 + allocated - RELOCATION) & 0xFFFFFFFF
            struct.pack_into('<I', decoded, slot, replacement)
            slots.append({'index': entry['index'], 'slot': slot, 'original': entry['linked_pointer'],
                          'replacement': replacement})
            changed.append(slot)
        require(slots, 'Town source has no owned pointers')
        rows.append({'id': row['id'], 'rom_offset': allocated, 'source_sha256': row['source_sha256'],
                     'encoded_hex': payload.hex(), 'layout': layout, 'batch': owner,
                     'language_status': 'reviewed', 'bank': bank['id'], 'slots': slots})
    require(len(rows) == len(COMMON_STARTS) + len(MANSION_COMMON)
            and len(changed) == len(set(changed)), 'Incomplete shared-town batch')
    from tools.bank_text import insert_bank
    service_entries, service_slots, service_review = insert_bank(build, decoded, bank)
    changed.extend(service_slots)
    from tools.storage_text import insert_storage
    storage_entries, storage_slots, storage_review = insert_storage(build, decoded, bank)
    changed.extend(storage_slots)
    from tools.bakery_text import insert_bakery
    bakery_entries, bakery_slots, bakery_review = insert_bakery(build, decoded, bank)
    changed.extend(bakery_slots)
    require(len(changed)==len(set(changed)), 'Overlapping town service slots')
    restored = bytearray(decoded)
    for slot in changed:
        restored[slot:slot + 4] = bank['data'][slot:slot + 4]
    require(restored == bank['data'] and len(decoded) == len(bank['data']), 'Unowned town resource change')
    packed = pack_literals(decoded)
    require(decompress(packed) == (bytes(decoded), len(packed)), 'Town compression round trip differs')
    allocated = build.allocate('town-common-pointers', packed, 'home-books')
    build.patch('town-common-pointer', bank['pointer_offset'], struct.pack('<I', 0x08000000 + bank['rom_offset']),
                struct.pack('<I', 0x08000000 + allocated), 'home-books')
    return rows, {'id': bank['id'], 'rom_offset': allocated, 'decoded_bytes': len(decoded),
                  'bakery_entries':bakery_entries, 'bakery_review_sha256':bakery_review,
                  'storage_entries':storage_entries, 'storage_review_sha256':storage_review, 'service_entries':service_entries,'service_review_sha256':service_review,
                  'decoded_sha256': digest(decoded), 'changed_slots': sorted(changed),
                  'original_decoded_bytes_except_slots_preserved': True, 'new_ram_bytes': 0}
