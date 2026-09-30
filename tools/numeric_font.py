"""Compact numeric aliases for native decimal, item and bank formatters."""
import struct
from tools.compact_font import pack_glyph
from tools.rom import load_base,require

# Native code order is not numeric order. Keep equipped/curse/button icons out.
ALIASES = {**{0x824f+i: str(i) for i in range(10)},
           **{0x8740+i: str((i+1)%10) for i in range(10)},
           **{0x8755+i: str((i+1)%10) for i in range(10)},
           **{0x875f+i: str(10+i) for i in range(6)},
           **{0x876c+i: str(16+i) for i in range(5)},
           **{0x8771+i: '('+str(i+1)+')' for i in range(3)},
           0x8196: '*', 0x8266: 'G'}


def glyph(font, code):
    text = ALIASES[code]
    parts = [font['glyphs'][c] for c in text]
    if 0x8771 <= code <= 0x8773:
        # These are single native glyphs, whose packed advance must fit four
        # bits. Remove only empty exterior columns from the parentheses;
        # preserve every ink pixel and the digit's normal six-pixel advance.
        for part in (parts[0], parts[2]):
            require(all(not any(c == '#' for c in row[:1]+row[4:]) for row in part['rows']),
                    'Compound parentheses would crop ink')
        rows = [parts[0]['rows'][y][1:4]+parts[1]['rows'][y]+parts[2]['rows'][y][1:4]+'.'
                for y in range(14)]
        return {'origin':'new','advance':13,'rows':rows}
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
    # Independent original sequence tables establish the compound values.
    for offset, codes, values in [
            (0x644c8, [0x874f]+list(range(0x8755,0x875e))+list(range(0x875f,0x8765))+list(range(0x876c,0x8771)),
             [str(i) for i in range(1,21)]),
            (0x60770, [0x874f,0x8771,0x8772,0x8773], ['(1)','(2)','(3)'])]:
        raw=b''.join(c.to_bytes(2,'big') for c in codes)+b'\0'
        require(original[offset:offset+len(raw)]==raw,'Native compound number table changed')
        require([ALIASES[c] for c in codes[1:]]==values,'Compound number aliases change original values')


def record_offset(code, offset):
    return offset+(len(ALIASES)+1)*8+sorted(ALIASES).index(code)*32
