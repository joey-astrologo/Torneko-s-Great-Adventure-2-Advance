"""Bounded home-book menu and overwrite prompt; preserve native actions/format."""

from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.rom import require

BANK_STARTS = {0x073A, 0x28FC, 0x449E, 0x45FC, 0x4660, 0x469C, 0x48BD}
COMMON_STARTS = {0x2A76, 0x3DEC, 0x4090, 0x40F4}
DIRECT = {'rom.00148304': 0x1FB4C, 'rom.00061ffc': 0x1412D4,
          'rom.00061d38': 0x14130C, 'rom.0006c154': 0x14BE9C, 'rom.0006c144': 0x14BEA4}
OVERWRITE = 'Overwrite the Adventure Log\nfor {village} Village?'
CAPACITY = 128


def compile_menu(english):
    lines = english.split('\n')
    require(lines == ['View items', 'Sell items', 'Save and continue', 'Save and quit'],
            'Blue-book actions/order differ')
    widths = [measure(line) for line in lines]
    require(max(widths) + 8 <= 120, 'Blue-book menu exceeds window')
    payload = b'\r'.join(b'\x06\x08' + encode(line)[:-1] for line in lines) + b'\0'
    return payload, {'pages': [lines], 'line_widths': [widths], 'native_width': 120,
                     'left_inset': 8, 'encoded_bytes': len(payload), 'commands': [], 'native_rows': 4}


def compile_overwrite(english):
    require(english == OVERWRITE, 'Overwrite prompt requires the reviewed two-row layout')
    prefix, suffix = english.split('{village}')
    payload = encode(prefix)[:-1] + b'%s' + encode(suffix)
    widths = [measure(english.split('\n')[0]), measure('for  Village?') + PLAYER_WIDTH]
    maximum_bytes = len(payload) - 2 + 14  # Seven two-byte name glyphs, no terminator in %s.
    require(max(widths) <= 216 and maximum_bytes <= CAPACITY, 'Overwrite prompt exceeds native bounds')
    return payload, {'pages': [english.split('\n')], 'line_widths': [widths],
                     'encoded_bytes': len(payload), 'native_width': 224, 'maximum_width': 216,
                     'format_directive': '%s', 'maximum_name_glyphs': 7,
                     'maximum_formatted_bytes': maximum_bytes, 'stack_buffer_bytes': CAPACITY,
                     'new_ram_bytes': 0, 'commands': ['{village}']}


def materialize(template, name):
    require(template.count(b'%s') == 1, 'Overwrite village directive missing/repeated')
    raw = name.rstrip(b'\0')
    require(0 < len(raw) <= 14 and len(raw) % 2 == 0 and b'\0' not in raw, 'Invalid seven-glyph village name')
    payload = template.replace(b'%s', raw)
    require(len(payload) <= CAPACITY, 'Overwrite message exceeds stack buffer')
    return payload
