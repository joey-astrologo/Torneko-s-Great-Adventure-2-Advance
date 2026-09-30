"""Separate the amount and English gold name in the native item formatter."""
import struct

from tools.compact_font import encode, measure
from tools.rom import require


def add_gold_spacing(build):
    source = bytes.fromhex('032563256425730500')  # colour, signed amount, name, reset
    require(build.original[0x6B458:0x6B461] == source, 'Original gold template changed')
    require(build.original[0xF43C:0xF444] == bytes.fromhex('01490420335e42e0'),
            'Gold amount reader changed')
    payload = b'\x03%c%d' + encode(' ')[:-1] + b'%s\x05\0'
    offset = build.allocate('item-gold-spaced-format', payload, 'gold-spacing')
    build.patch('item-gold-format-reader', 0xF444, struct.pack('<I', 0x0806B458),
                struct.pack('<I', offset+0x08000000), 'gold-spacing')
    # The native branch loads a signed halfword. The reviewed name reserve is
    # 30 content bytes / 80px. Keep room for colour/reset and the outer row marker.
    maximum_bytes = 2+6+2+30+1+1
    maximum_width = 6*7+measure(' ')+80
    require(maximum_bytes+2 <= 64 and maximum_width+12 <= 162,
            'Spaced gold name exceeds existing item-row reserves')
    return {'literal': 0xF444, 'offset': offset, 'source_hex': source.hex(),
            'encoded_hex': payload.hex(), 'maximum_name_bytes': maximum_bytes,
            'maximum_name_width': maximum_width,
            'scope': 'One private format and reader literal; existing reviewed names, '
                     'amounts, colour, 64-byte output and original shared template retained.'}
