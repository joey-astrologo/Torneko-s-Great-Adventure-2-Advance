"""Compact numeric aliases for native decimal, item and bank formatters."""
import struct
from tools.compact_font import pack_glyph
from tools.rom import load_base,require

# Native code order is not numeric order. Keep equipped/curse/button icons out.
ALIASES = {**{0x824f+i: str(i) for i in range(10)},
           **{0x8740+i: str((i+1)%10) for i in range(10)},
           **{0x8755+i: str((i+1)%10) for i in range(10)},
           **{0x875f+i: str(10+i) for i in range(6)},
           0x8196: '*', 0x8266: 'G'}


def glyph(font, code):
    text = ALIASES[code]
    parts = [font['glyphs'][c] for c in text]
    rows = [''.join(p['rows'][y] for p in parts) for y in range(14)]
    # Retain the inverse numeric family, at the compact font's cap height.
    if 0x8740 <= code <= 0x8749:
        rows = [(''.join('.' if bit == '#' else '#' for bit in row))
                if 3 <= y <= 13 else '.'*len(row) for y,row in enumerate(rows)]
    return {'origin':'new','advance':sum(p['advance'] for p in parts),'rows':rows}


def resource(font, offset):
    validate_native_digits(load_base())
    table_size = (len(ALIASES)+1)*8
    table, records = bytearray(), bytearray()
    for code in sorted(ALIASES):
        table.extend(struct.pack('<II',code,0x08000000+offset+table_size+len(records)))
        records.extend(pack_glyph(glyph(font,code)))
    table.extend(bytes(8))
    return bytes(table+records)


def validate_native_digits(original):
    # The native formatters index these tables with decimal 0..9. This is an
    # independent semantic oracle: bitmap/lookup agreement alone is insufficient.
    for offset,expected in [(0x648d0,'8749874087418742874387448745874687478748'),
                            (0x6b423,'875e87558756875787588759875a875b875c875d')]:
        raw=original[offset:offset+20]
        require(raw.hex()==expected,'Native decimal conversion table changed')
        require([ALIASES[int.from_bytes(raw[i:i+2],'big')] for i in range(0,20,2)]==list('0123456789'),
                'Compact digit aliases change native numeric values')


def record_offset(code, offset):
    return offset+(len(ALIASES)+1)*8+sorted(ALIASES).index(code)*32
