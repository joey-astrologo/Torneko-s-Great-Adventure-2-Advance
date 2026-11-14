"""Bind unknown-actor and False priest branches to existing reviewed names."""

import struct

from tools.compact_font import encode
from tools.extract_shared_text import START, END
from tools.rom import require

SLOT = 0x414
SOURCE = 0x08062DCC
READERS = ((0x9B38, 0x9B48, '0348044bc01800685ce0'),
           (0x9B68, 0x9B78, '034804494018006844e0'))
PRIEST_SLOT = 0x10
PRIEST_SOURCE = 0x080648B4
PRIEST_READER = (0x9BAA, 0x9BB4, '0248006925e0')


def add_actor_fallback(build, results):
    # The raw result-table name is reviewed separately from dungeon ID0/Torneko.
    row = next(r for r in results['entries'] if r['id'] == 0)
    payload = encode('Someone')
    require(row['english'] == 'Someone' and row['source']['offset'] == SOURCE-0x08000000
            and row['source']['raw_hex'] == '89bd8ed282a900'
            and row['encoded_hex'] == payload.hex()
            and build.data[row['offset']:row['offset']+len(payload)] == payload,
            'Unknown actor must reuse the reviewed result name')
    table = bytearray(build.original[START:END])
    require(struct.unpack_from('<I', table, SLOT)[0] == SOURCE,
            'Unknown-actor shared source changed')
    struct.pack_into('<I', table, SLOT, row['offset']+0x08000000)
    # Raw results ID131 is False priest; dungeon ID131 is a different identity.
    priest = next(r for r in results['entries'] if r['id'] == 131)
    priest_payload = encode('False priest')
    require(priest['english'] == 'False priest'
            and priest['source']['offset'] == PRIEST_SOURCE-0x08000000
            and priest['source']['raw_hex'] == '82c982b9905f958300'
            and priest['encoded_hex'] == priest_payload.hex()
            and build.data[priest['offset']:priest['offset']+len(priest_payload)] == priest_payload
            and struct.unpack_from('<I', table, PRIEST_SLOT)[0] == PRIEST_SOURCE,
            'False priest must reuse the reviewed result name')
    struct.pack_into('<I', table, PRIEST_SLOT, priest['offset']+0x08000000)
    private = build.allocate('actor-fallback-table', table, 'actor-fallback')
    bindings = []
    for entry, literal, expected in READERS:
        require(build.original[entry:entry+10].hex() == expected
                and build.data[entry:entry+10].hex() == expected
                and struct.unpack_from('<I', build.original, literal+4)[0] == SLOT,
                'Unknown-actor selector or reader changed')
        build.patch('actor-fallback-reader-'+hex(literal), literal,
                    struct.pack('<I', START+0x08000000),
                    struct.pack('<I', private+0x08000000), 'actor-fallback')
        bindings.append(dict(load=entry+6+0x08000000, literal=literal, table_offset=SLOT))
    entry, literal, expected = PRIEST_READER
    require(build.original[entry:entry+6].hex() == expected
            and build.data[entry:entry+6].hex() == expected,
            'False-priest selector or reader changed')
    build.patch('actor-fallback-reader-'+hex(literal), literal,
                struct.pack('<I', START+0x08000000),
                struct.pack('<I', private+0x08000000), 'actor-fallback')
    bindings.append(dict(load=entry+2+0x08000000, literal=literal, table_offset=PRIEST_SLOT))
    return dict(table_offset=private, bindings=bindings, source_pointer=SOURCE,
                name_offset=row['offset'], english=row['english'], encoded_hex=payload.hex(),
                false_priest=dict(source_pointer=PRIEST_SOURCE, name_offset=priest['offset'],
                                  english=priest['english'], encoded_hex=priest_payload.hex()),
                new_text_resources=0,
                scope='The two unknown-actor returns and False priest return in getter08009ACC. '
                      'Reuses reviewed results ID0/Someone and ID131/False priest; original selectors, instructions, other names, '
                      'shared table, gameplay and save layout are preserved.')
