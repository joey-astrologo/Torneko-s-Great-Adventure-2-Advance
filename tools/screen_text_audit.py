"""Observe every shared text read and glyph, without a resource-pointer filter.

This is a bounded screen audit, not a claim that all graphical text uses these
functions. Unknown glyphs are retained as failures, including unregistered reads.
"""

import re

from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks
from tools.name_entry import HERO
from tools.numeric_font import ALIASES
from tools.text_codec import readable, tokenize


def glyph_text(code):
    if 0xF020 <= code <= 0xF07E:
        return chr(code & 255)
    if code in ALIASES:
        return ALIASES[code]
    if code in (0x20, 0x8140):
        return ' '
    try:
        return code.to_bytes(1 if code < 256 else 2, 'big').decode('cp932')
    except UnicodeDecodeError:
        return f'{{glyph:{code:04x}}}'


def display_text(tokens, formatting=False):
    text = readable(tokens)
    # CP932 assigns the compact extension to private-use Unicode characters.
    text = ''.join(chr(ord(c) - 0xE000 + 0x40) if 0xE000 <= ord(c) <= 0xE03E else c
                   for c in text)
    text = re.sub(r'\{glyph:f0([0-9a-f]{2})\}', lambda m: chr(int(m[1], 16)), text)
    if formatting:
        text = re.sub(r'\{unclassified-control:(6[0-9a-f]|7[0-9a-f])\}',
                      lambda m: chr(int(m[1], 16)), text)
    return text


class ScreenTextAudit:
    ADDRESSES = tuple(sorted(set(Observer.ADDRESSES +
                                (0x0801588C, 0x080158CE, 0x08000FB8, 0x08001C14, 0x08024AD8))))

    def __init__(self, game):
        self.game = game
        self.metrics = TextChecks(game, {})
        self.observer = Observer(game)
        self.queues, self.formats, self.glyphs, self.pickups = [], [], [], []
        self.final_queues, self.exceptions = [], []
        self.unclassified, self.unreadable = [], []
        self.layout_violations = []
        self.pending = None
        self.phase = 'start'

    def stream(self, pointer, event):
        data = bytes(self.game.core.memory[pointer:pointer + 2048])
        try:
            tokens, end = tokenize(data)
            return {'raw_hex': data[:end].hex(),
                    'text': display_text(tokens, formatting=event['address'] == 0x08000FB8)}
        except ValueError as error:
            row = {'source': pointer, 'frame': event['frame'], 'error': str(error),
                   'sample_hex': data[:128].hex(), 'phase': self.phase}
            self.unreadable.append(row)
            return row

    def callback(self, event):
        a, r, m = event['address'], event['registers'], self.game.core.memory
        if a in self.observer.ADDRESSES:
            self.observer.callback(event)
        if a in (0x0801588C, 0x08000FB8):
            pointer = r[0] if a == 0x0801588C else r[1]
            row = {'frame': event['frame'], 'source': pointer, 'caller': r[14],
                   'phase': self.phase, **self.stream(pointer, event)}
            (self.queues if a == 0x0801588C else self.formats).append(row)
        if a == 0x080158CE:
            # Observe the payload AFTER the localization hook redirects static
            # Japanese pointers and joins combat fragments. Entry arguments alone
            # are not evidence of what the player actually sees.
            raw = self.stream(r[6], event)
            hero = bytes(m[HERO:HERO+16]).split(b'\0')[0]
            self.final_queues.append({'frame': event['frame'], 'source': r[6],
                'caller': m.u32[r[13]+12], 'phase': self.phase, **raw,
                'player_hex': hero.hex(), 'drawn_codes': []})
        if a == 0x08024AD8:
            from tools.name_entry_playtest import MAP, position
            x, y = position(self.game)
            pointer = m.u32[MAP + (x * 32 + y) * 28 + 16]
            self.pickups.append({'frame': event['frame'], 'position': [x, y],
                'floor': m.u16[0x02005674], 'dungeon': m.u32[0x02003B6C],
                'item_id': m.u8[0x020013D0 + m.u8[pointer + 8]],
                'item_hex': bytes(m[pointer:pointer + 120]).hex(), 'caller': r[14]})
        if a == 0x08001BC4:
            key = (r[0], r[1], r[13], r[14], m.u8[r[0]+2], m.u8[r[0]+3])
            if self.pending and self.pending['key'] == key:
                return
            context = bytes(m[r[0]:r[0]+24])
            row = {'frame': event['frame'], 'phase': self.phase, 'code': r[1],
                   'text': glyph_text(r[1]), 'caller': r[14], 'window': r[0],
                   'context_hex': context.hex(), 'reader_source':
                   self.observer.stack[-1]['source'] if self.observer.stack else None,
                   'last_queue': len(self.queues)-1 if self.queues else None,
                   'final_queue': len(self.final_queues)-1 if self.final_queues else None,
                   'x': context[2], 'row': context[3]}
            self.glyphs.append(row)
            self.pending = {'key': key, 'row': row}
            accepted = 0xF020 <= r[1] <= 0xF07E or r[1] in ALIASES or r[1] in (0x20, 0x8140)
            reason = None
            if r[1] in (0x2B, 0x2F, 0x5B, 0x5D) and r[14] == 0x08001E69:
                reason = 'Native ASCII plus/slash/brackets from the punctuation handler'
            if (r[1] in (0x874F, 0x8750) and self.observer.stack and
                    context[0:2] == b'\x08\x18' and context[2] == 6 and
                    context[4:6] == b'\x15\x08' and
                    len(self.observer.stack[-1]['glyph_positions']) == 1):
                reason = 'Original blank/equipped marker at the start of an inventory row'
            if self.final_queues and not self.observer.stack:
                queue = self.final_queues[-1]
                hero = bytes.fromhex(queue['player_hex'])
                n = len(queue['drawn_codes'])
                if (hero and len(hero) % 2 == 0 and bytes.fromhex(queue['raw_hex']).startswith(hero)
                        and n < len(hero)//2 and r[1] == int.from_bytes(hero[n*2:n*2+2], 'big')):
                    reason = 'Exact saved player-name prefix; Japanese name retained from this battery save'
                queue['drawn_codes'].append(r[1])
            if not accepted:
                if reason:
                    self.exceptions.append(row | {'reason': reason})
                else:
                    self.unclassified.append(row)
        elif a == 0x08001C14 and self.pending:
            # Native scrolling can move the cursor between draw entry and the
            # actual bitmap preparation. Keep both coordinates in the evidence.
            row = self.pending['row']
            x, y = m.u8[r[5]+2], m.u8[r[5]+3]
            glyph, _ = self.metrics.glyph_record(row['code'])
            width, rows = m.u8[r[5]+4]*8, m.u8[r[5]+5]
            row.update(drawn_x=x, drawn_row=y, advance=glyph['advance'],
                       window_width=width, window_rows=rows)
            if x+glyph['advance'] > width or y >= rows:
                self.layout_violations.append(dict(row))
        elif a == 0x08001C6E:
            self.pending = None

    def report(self):
        reads = [{k: v for k, v in row.items() if k not in ('tokens', 'entry_registers')}
                 | {'text': display_text(row['tokens'])} for row in self.observer.reads]
        return {'reads': reads, 'window_creates': self.observer.creates,
                'queues': self.queues, 'formats': self.formats, 'glyphs': self.glyphs,
                'final_queues': self.final_queues, 'contextual_exceptions': self.exceptions,
                'pickups': self.pickups, 'unclassified_glyphs': self.unclassified,
                'unreadable_streams': self.unreadable, 'layout_violations': self.layout_violations,
                'observed_addresses': list(self.ADDRESSES)}
