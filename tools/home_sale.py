"""The first-home item-sale template, with its original bounded formatter field."""

from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.rom import require

BUFFER = 0x0202F44C
TEMPLATE = 0x6C424
POINTER = 0x51660
ORIGINAL = bytes.fromhex('0a144041407e82cd0305252d6c6405478ee882c993fc82ea82bd81490a0a00')
ENGLISH = '{player}\ngot {color:5}{amount}{/color}G!'


def compile_sale(english):
    require(english == ENGLISH, 'Sale notification requires its reviewed two-row layout')
    payload = (b'\x0a\x14@A@\x7e\r\x14' + encode('got ')[:-1] + b'\x03\x05%-ld\x05'
               + encode('G!')[:-1] + b'\x0a\x0a\0')
    require(payload.count(b'%-ld') == ORIGINAL.count(b'%-ld') == 1 and len(payload) <= len(ORIGINAL),
            'Sale template exceeds the original formatter footprint')
    # Native decimal digits use the original seven-pixel font. A nonnegative
    # signed-long amount has at most ten digits. Player expansion stays in the
    # reader; the formatter never copies the player's name into this buffer.
    widths = [PLAYER_WIDTH, measure('got G!') + 10 * 7]
    require(max(widths) <= 216, 'Sale notification exceeds its story window')
    return payload, {'pages': [['{player}', 'got {color:5}{amount}{/color}G!']],
                     'line_widths': [widths], 'encoded_bytes': len(payload),
                     'maximum_width': 216, 'native_width': 224,
                     'commands': ['@A@', '{player}', '{color:5}', '{/color}'],
                     'format_directive': '%-ld', 'original_template_bytes': len(ORIGINAL),
                     'output_never_longer_for_same_argument': True, 'new_ram_bytes': 0}


def materialize(template, amount):
    require(0 <= amount <= 0x7FFFFFFF, 'Sale amount outside nonnegative signed-long range')
    require(template.count(b'%-ld') == 1, 'Sale directive missing or repeated')
    return template.replace(b'%-ld', str(amount).encode('ascii'))
