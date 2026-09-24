"""The 300 relocated pointers in the shared town text resource."""

import struct
from functools import lru_cache

from tools.lz77 import decompress
from tools.rom import digest, load_base, require
from tools.text_codec import tokenize

ID = 'town-common'
ROM = 0x438938
POINTER = 0x4D7A8
RAM = 0x020141AC
LINK_BASE = 0x801AC000
RELOCATION = (RAM - LINK_BASE) & 0xFFFFFFFF
COUNT = 300


@lru_cache(maxsize=1)
def resource():
    data, end = decompress(load_base(), ROM)
    require(end == 0x43A420 and len(data) == 16695 and
            digest(data) == '203e93102709632d06402027ba3903ce84103b19c522c95e6c074e91400f4eff',
            'Shared town text resource differs')
    return {'id': ID, 'rom_offset': ROM, 'rom_end_exclusive': end,
            'pointer_offset': POINTER, 'runtime_start': RAM, 'decoded_bytes': len(data),
            'decoded_sha256': digest(data), 'compressed_sha256': digest(load_base()[ROM:end]), 'data': data}


def entries():
    data, rows = resource()['data'], []
    for index in range(COUNT):
        linked = struct.unpack_from('<I', data, index * 4)[0]
        start = linked - LINK_BASE
        require(COUNT * 4 <= start < len(data), 'Town pointer outside text resource')
        tokens, end = tokenize(data, start)
        rows.append({'id': f'{ID}.{start:04x}', 'index': index, 'slot': index * 4,
                     'linked_pointer': linked, 'start': start, 'end_exclusive': end,
                     'tokens': tokens})
    return rows


def relocate(data):
    result = bytearray(data)
    for slot in range(0, COUNT * 4, 4):
        word = struct.unpack_from('<I', data, slot)[0]
        struct.pack_into('<I', result, slot, (word + RELOCATION) & 0xFFFFFFFF)
    return bytes(result)
