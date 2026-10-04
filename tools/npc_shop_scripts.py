"""Repair two original bank-2 NPC selectors using existing service scripts."""
import struct

from tools.lz77 import decompress, pack_literals
from tools.rom import digest, require

BANK_POINTER = 0x14CD70
SOURCE = 0x43ADE0
DECODED_SHA256 = 'b040347437cfd8bb31c2252f572409adee50f7e63f19d98848691a807f9e6c00'


def selectors(data):
    header = struct.unpack_from('<5I', data)
    rows = []
    for node in range(32):
        relative = struct.unpack_from('<I', data, header[0]+4*node)[0]
        first, count = struct.unpack_from('<HH', data, header[1]+4*node)
        if relative == 0xFFFFFFFF or first == 0xFFFF:
            continue
        for ordinal in range(count):
            record = data[header[4]+8*(first+ordinal):header[4]+8*(first+ordinal+1)]
            require(len(record) == 8, 'NPC actor record out of bounds')
            selector = record[4]
            if selector == 255:
                continue
            index = first-1+selector
            slot = header[2]+4*index
            require(header[2] <= slot <= header[3]-4, 'NPC script offset outside table')
            root = header[3]+relative+struct.unpack_from('<I', data, slot)[0]
            rows.append(dict(map=node, actor=ordinal, selector=selector, index=index,
                             slot=slot, root=root, record_hex=record.hex(),
                             record_offset=header[4]+8*(first+ordinal)))
    return rows


def add_npc_shop_scripts(build):
    require(build.original[BANK_POINTER:BANK_POINTER+4] == bytes.fromhex('e0ad4308'),
            'Reinspect original NPC loader pointer')
    original, end = decompress(build.original, SOURCE)
    require(end == 0x43B296 and len(original) == 2072 and digest(original) == DECODED_SHA256,
            'Reinspect original NPC bank')
    rows = selectors(original)
    changed = bytearray(original)
    repairs = []
    for node, selector_at, root, script in (
            (26, 0x794, 0x575, bytes.fromhex('170215')),
            (27, 0x804, 0x5CE, bytes.fromhex('17001415'))):
        owners = [r for r in rows if r['record_offset']+4 == selector_at]
        require(len(owners) == 1 and owners[0]['map'] == node and owners[0]['actor'] == 0,
                'NPC actor record has unexpected consumers')
        require(original[selector_at] == 1 and original[root:root+len(script)] == script,
                'NPC repair source or service script differs')
        hidden = [r for r in rows if r['map'] == node and r['selector'] == 2]
        require(hidden and all(r['root'] == root for r in hidden), 'Existing service target differs')
        changed[selector_at] = 2
        repairs.append(dict(map=node, selector_offset=selector_at, before_hex='01', after_hex='02',
                            original_root=owners[0]['root'], replacement_root=root,
                            service_script_hex=script.hex(), consumers=owners))
    changed = bytes(changed)
    current = selectors(changed)
    for before, after in zip(rows, current):
        if before['record_offset']+4 not in (0x794, 0x804):
            require(before == after, 'Unrelated NPC selector changed')
        require(0x318 <= after['root'] < 0x5E0, 'NPC target outside declared instructions')
    packed = pack_literals(changed)
    require(decompress(packed)[0] == changed, 'NPC replacement LZ77 round trip failed')
    at = build.allocate('npc-bank-2-shop-selector-repair', packed, 'npc-shop-scripts')
    build.patch('npc-bank-2-loader', BANK_POINTER, bytes.fromhex('e0ad4308'),
                struct.pack('<I', 0x08000000+at), 'npc-shop-scripts')
    return dict(bank=2, source_range=[SOURCE,end], source_decoded_sha256=digest(original),
                decoded_sha256=digest(changed), decoded_bytes=len(changed),
                allocation=at, compressed_bytes=len(packed), repairs=repairs,
                selectors=current, new_text_resources=0,
                scope='Two actor selectors share existing native service scripts. '
                      'All other decoded bytes and selectors preserved; no new RAM/save storage.')
