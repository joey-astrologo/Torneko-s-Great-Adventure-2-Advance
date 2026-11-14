"""Bind the two unknown-actor name branches to the reviewed English name."""

import struct

from tools.compact_font import encode
from tools.extract_shared_text import START, END
from tools.rom import require

SLOT = 0x414
SOURCE = 0x08062DCC
READERS = ((0x9B38, 0x9B48, '0348044bc01800685ce0'),
           (0x9B68, 0x9B78, '034804494018006844e0'))


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
    return dict(table_offset=private, bindings=bindings, source_pointer=SOURCE,
                name_offset=row['offset'], english=row['english'], encoded_hex=payload.hex(),
                new_text_resources=0,
                scope='Only the two unknown-actor returns in getter08009ACC. Reuses reviewed '
                      'results ID0/Someone; original selectors, instructions, other names, '
                      'shared table, gameplay and save layout are preserved.')
