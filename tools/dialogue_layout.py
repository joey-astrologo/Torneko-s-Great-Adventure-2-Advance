"""Compile reviewed English pages for the observed two-row story reader."""

import re

from tools.compact_font import encode, load_font, measure
from tools.rom import require

AT = re.compile(r'@[ABC]@')
COMMAND = re.compile(r'@[ABC]@|\{player\}|\{initial\}|\{color:[56]\}|\{/color\}|\{heart\}|\{center\}')
HEART = 0x874E
HEART_WIDTH = 13
PLAYER_WIDTH = 98  # Seven original Japanese glyphs at the verified maximum 14 px.
INITIAL_WIDTH = 14  # Native 7F reads the first two-byte player-name glyph.
WIDTH = 216  # 224-pixel native window, retaining an eight-pixel right margin.


def width(text, font):
    return (measure(COMMAND.sub('', text), font) + text.count('{player}') * PLAYER_WIDTH
            + text.count('{heart}') * HEART_WIDTH + text.count('{initial}') * INITIAL_WIDTH)


def compile_dialogue(english, source_tokens):
    require(isinstance(english, str) and english.strip(), 'Missing English dialogue')
    require(all(c == '\n' or 32 <= ord(c) <= 126 for c in english), 'Unsupported English character/control')
    original_commands = []
    colored = False
    for token in source_tokens:
        if token['kind'] == 'command' and token.get('name') != 'newline':
            if token.get('code') == 0x7E and token['raw_hex'] == '7e':
                original_commands.append('{player}')
            elif token.get('code') == 0x7F and token['raw_hex'] == '7f':
                original_commands.append('{initial}')
            elif token['raw_hex'] == '14':
                original_commands.append('{center}')
            elif token['raw_hex'] in ('0305', '0306'):
                require(not colored, 'Nested source colour is not insertion-ready')
                colored = True
                original_commands.append('{color:' + token['raw_hex'][-1] + '}')
            elif token['raw_hex'] == '05':
                require(colored, 'Unpaired source colour restore')
                colored = False
                original_commands.append('{/color}')
            else:
                require(token.get('name') == 'at-command' and token['raw_hex'] in ('404140', '404240', '404340'),
                        'Dialogue command family is not insertion-ready')
                original_commands.append(bytes.fromhex(token['raw_hex']).decode('ascii'))
        require(token['kind'] != 'glyph', 'Unresolved source glyph')
        if token['kind'] == 'text':
            # CP932's circled-15 identity is a native heart in this ROM. Walk
            # code boundaries so a matching byte pair inside other glyphs is
            # never treated as a symbol. Retain its place among commands.
            raw, cursor = bytes.fromhex(token['raw_hex']), 0
            while cursor < len(raw):
                size = 2 if raw[cursor] > 0x80 and not 0xA0 <= raw[cursor] <= 0xDF else 1
                if raw[cursor:cursor + size] == HEART.to_bytes(2, 'big'):
                    original_commands.append('{heart}')
                cursor += size
    require(not colored, 'Unclosed source colour span')
    require(COMMAND.findall(english) == original_commands and not any(c in COMMAND.sub('', english) for c in '@{}'),
            'English changes or introduces event commands')
    font = load_font()
    pages = []
    # A blank line is an editorial page boundary; wrapping within each section
    # can add pages but never joins a new speaker to the preceding section.
    for paragraph in english.split('\n\n'):
        if '{center}' in paragraph:
            lines = paragraph.split('\n')
            require(all(line.startswith('{center}') and line.count('{center}') == 1
                        and width(line, font) <= WIDTH for line in lines),
                    'Each centered line must start with one center command and fit')
            pages.extend([lines[i:i + 2] for i in range(0, len(lines), 2)])
            continue
        lines, line = [], ''
        for word in paragraph.split():
            require(width(word, font) <= WIDTH, 'English word exceeds dialogue width')
            candidate = f'{line} {word}' if line else word
            if width(candidate, font) > WIDTH:
                lines.append(line)
                line = word
            else:
                line = candidate
        require(line, 'Empty dialogue paragraph')
        lines.append(line)
        pages.extend([lines[i:i + 2] for i in range(0, len(lines), 2)])
    # Each intermediate page contains two row terminators. The reader skips
    # surplus newlines after its clear, so one-line pages are padded once.
    text = ''
    for number, page in enumerate(pages):
        text += '\n'.join(page)
        if number + 1 < len(pages):
            text += '\n' * (3 - len(page))
    payload = bytearray()
    controls = {'{player}': b'\x7e', '{initial}': b'\x7f', '{heart}': HEART.to_bytes(2, 'big'), '{center}': b'\x14',
                '{color:5}': b'\x03\x05', '{color:6}': b'\x03\x06', '{/color}': b'\x05'}
    for part in re.split('(' + COMMAND.pattern + ')', text):
        payload.extend(controls[part] if part in controls else part.encode('ascii') if AT.fullmatch(part) else encode(part)[:-1])
    payload.append(0)
    return bytes(payload), {'pages': pages, 'line_widths': [[width(line, font) for line in page] for page in pages],
                            'encoded_bytes': len(payload), 'maximum_width': WIDTH, 'native_width': 224,
                            'commands': original_commands}
