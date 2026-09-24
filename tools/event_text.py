"""Enumerate the relative text tables consumed at 0804F938 and 080502A4."""

import struct

from tools.opening_text import BANK_RAM, banks
from tools.rom import require
from tools.text_codec import tokenize


def table_entries(bank):
    data = bank['data']
    count, groups, offsets, strings = struct.unpack_from('<4I', data)
    require(0 < count <= 32 and 16 + count <= groups, 'Invalid event group counts')
    counts = data[16:16 + count]
    require(groups + count * 4 == offsets and offsets + sum(counts) * 4 == strings,
            'Event table layout differs')
    rows, number = [], 0
    for group, size in enumerate(counts):
        group_offset = struct.unpack_from('<I', data, groups + group * 4)[0]
        for index in range(size):
            slot = offsets + number * 4
            relative = struct.unpack_from('<I', data, slot)[0]
            start = strings + group_offset + relative
            tokens, end = tokenize(data, start)
            rows.append({'id': f"{bank['id']}.{start:04x}", 'group': group, 'index': index,
                         'slot': slot, 'relative': relative, 'group_offset': group_offset,
                         'strings_offset': strings, 'start': start, 'end_exclusive': end,
                         'tokens': tokens})
            number += 1
    return rows


def opening_entries():
    return table_entries(banks()[0])
