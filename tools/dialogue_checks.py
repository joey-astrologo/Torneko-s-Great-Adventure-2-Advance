"""Shared native checks for compiled English streams and their rendered glyphs."""

from tools.build_compact_font import FONT_OFFSET, HOOK_OFFSET, HOOK_BYTES
from tools.numeric_font import ALIASES, glyph as numeric_glyph, record_offset
from tools.compact_font import encode, load_font
from tools.dialogue_layout import PLAYER_WIDTH
from tools.name_entry import CHARACTERS, HERO, ID_FIRST, MAX_NAME, TABLE
from tools.review_fonts import extract
from tools.rom import load_base, require


def player_layout_cases():
    """Required English spelling and independently measured worst name glyphs."""
    font, original = load_font(), load_base()
    widest = max(CHARACTERS, key=lambda c: font['glyphs'][c]['advance'])
    codes = [int.from_bytes(original[TABLE + i * 2:TABLE + i * 2 + 2], 'big') for i in range(ID_FIRST)]
    widest_japanese = max(codes, key=lambda code: extract(original, code)['width'])
    require(PLAYER_WIDTH == MAX_NAME * extract(original, widest_japanese)['width'],
            'Compiled player reserve differs from widest original name glyph')
    return [('required-English', encode('Torneko')), ('widest-English', encode(widest * MAX_NAME)),
            ('widest-Japanese', widest_japanese.to_bytes(2, 'big') * MAX_NAME + b'\0')]


def rendered_codes(payload, player=None, foreground=None, saved=None):
    """Independent byte walk for the supported English stream/control subset."""
    output, cursor = [], 0
    while cursor < len(payload):
        code = payload[cursor]
        cursor += 1
        if code == 0:
            return output
        if code > 0x80 and not 0xA0 <= code <= 0xDF:
            require(cursor < len(payload), 'Truncated rendered glyph')
            glyph = code << 8 | payload[cursor]
            output.append(glyph if foreground is None else (glyph, foreground))
            cursor += 1
        elif code == 0x7E:
            require(player is not None, 'Nested or missing player substitution')
            output.extend(rendered_codes(player, foreground=foreground, saved=saved))
        elif code == 0x7F:
            require(player is not None and len(player) >= 3
                    and player[0] > 0x80 and not 0xA0 <= player[0] <= 0xDF
                    and player[1] != 0, 'Missing or invalid two-byte player initial')
            output.extend(rendered_codes(player[:2] + b'\0', foreground=foreground, saved=saved))
        elif 0x30 <= code <= 0x39 or code == 0x47:
            # The native formatter emits decimal ASCII; the reader maps these
            # to the original seven-pixel digit records, unlike authored F0xx.
            # The record gold suffix is native ASCII G, also remapped to
            # its original wide code (covered by the compact numeric alias).
            glyph = code + 0x821F
            output.append(glyph if foreground is None else (glyph, foreground))
        elif code == 0x20:
            output.append(code if foreground is None else (code, foreground))
        elif code in (1, 2, 9, 10, 13, 20, 28, 29):
            pass
        elif code in (4, 6):
            cursor += 1
        elif code == 3:
            # Status-kind skill names use operand3 in the original four-kind
            # palette map at ROM148364 (05 07 06 03).
            require(cursor < len(payload) and payload[cursor] in (2, 3, 4, 5, 6, 7), 'Unsupported rendered colour operand')
            if foreground is not None:
                saved, foreground = foreground, (payload[cursor] & 7) + 8
            cursor += 1
        elif code == 5:
            if foreground is not None:
                require(saved is not None, 'Missing saved foreground')
                foreground = saved
        elif code == 0x40:
            # w/W are the verified10/20-frame family-voice callback commands.
            require(payload[cursor:cursor + 2] in (b'A@', b'B@', b'C@', b'w@', b'W@'), 'Unexpected rendered command')
            cursor += 2
        elif 0x21 <= code <= 0x2F or code in (0x5B, 0x5D):
            output.append(code if foreground is None else (code, foreground))
        else:
            raise ValueError(f'Unsupported rendered code {code:02x}')
    raise ValueError('Unterminated rendered stream')


class TextChecks:
    ADDRESSES = (0x080021B4, 0x08001BC4, 0x08001C14, 0x08001C68, 0x080023A0, 0x08002284)

    def __init__(self, game, resources):
        self.game, self.resources = game, resources
        self.font = load_font()
        self.original = load_base()
        self.native_glyphs = {}
        self.active = None
        self.reads = []
        self.glyph_checks = 0
        self.glyph = None
        self.nested = 0

    def glyph_record(self, code):
        if code in (0x20, 0x8140):
            return {'advance': 6, 'rows': ['......'] * 14}, None
        if 0xF020 <= code <= 0xF07E:
            return self.font['glyphs'][chr(code & 255)], 0x08000000 + FONT_OFFSET + (code - 0xF020) * 32
        if code in ALIASES and self.game.core.memory.u32[0x08000000 + HOOK_OFFSET + HOOK_BYTES] == min(ALIASES):
            return numeric_glyph(self.font,code), 0x08000000+record_offset(code,HOOK_OFFSET+HOOK_BYTES)
        if code not in self.native_glyphs:
            raw = extract(self.original, code)
            self.native_glyphs[code] = ({'advance': raw['width'],
                                        'rows': [''.join('#' if b else '.' for b in line) for line in raw['pixels']]},
                                       0x08000000 + raw['rom_offset'])
        return self.native_glyphs[code]

    def callback(self, event):
        r, address = event['registers'], event['address']
        memory = self.game.core.memory
        active = self.active
        if address == 0x080021B4 and r[1] in self.resources:
            if (active is not None and not active['glyphs'] and not self.nested
                    and active.get('entry_registers') == tuple(r)):
                # A hardware breakpoint can be observed twice when an IRQ
                # returns to the same instruction before the reader executes.
                # A real recursive call changes SP/LR; never suppress that.
                row = self.resources[r[1]]
                payload = bytes.fromhex(row['encoded_hex'])
                require(bytes(memory[r[1]:r[1] + len(payload)]) == payload,
                        'Repeated reader entry source differs')
                require(bytes(memory[r[0]:r[0] + 24]).hex() == active['window_hex'],
                        'Repeated reader entry window differs')
                active['repeated_entry_observations'] = active.get('repeated_entry_observations', 0) + 1
                return
            require(active is None, 'Unexpected nested English stream')
            row = self.resources[r[1]]
            payload = bytes.fromhex(row['encoded_hex'])
            require(bytes(memory[r[1]:r[1] + len(payload)]) == payload, 'Native English source differs')
            self.active = {'id': row['id'], 'source': r[1], 'start_frame': event['frame'],
                           'window': r[0], 'window_hex': bytes(memory[r[0]:r[0] + 24]).hex(),
                           'entry_registers': tuple(r),
                           'glyphs': [], 'page_waits': 0, 'width': memory.u8[r[0] + 4] * 8,
                           'preserved': (r[4:12], r[13]),
                           'expected': rendered_codes(payload, bytes(memory[HERO:HERO + 16])),
                           'expected_colors': rendered_codes(payload, bytes(memory[HERO:HERO + 16]),
                                                             memory.u8[0x020000C2], memory.u8[0x020000C3]),
                           'foreground_counts': {},
                           'page_count': len(row['layout']['pages']), 'prepared': 0}
            require(memory.u8[r[0] + 6] == memory.u8[r[0] + 8] == 0, 'English fixed advance or spacing differs')
        elif active is not None:
            if address == 0x080021B4:
                require(r[1] == HERO and r[0] == active['window'], 'Unexpected nested English text source')
                self.nested += 1
            elif address == 0x08001BC4:
                require(r[0] == active['window'], 'Unexpected English window')
                glyph, _ = self.glyph_record(r[1])
                x, y = memory.u8[r[0] + 2], memory.u8[r[0] + 3]
                spacing = memory.u8[r[0] + 8]
                require(spacing in (0, 1), 'Unsupported native glyph spacing')
                draw_key = (r[0], r[1], r[13], r[14], x, y)
                if active['prepared'] == len(active['glyphs']) - 1:
                    require(active.get('draw_key') == draw_key,
                            'New glyph entry before previous glyph preparation')
                    active['repeated_draw_entry_observations'] = active.get('repeated_draw_entry_observations', 0) + 1
                    return
                active['draw_key'] = draw_key
                require(x + glyph['advance'] <= active['width'], 'English exceeds native window: '+repr((active['id'],hex(r[1]),x,glyph['advance'],active['width'],hex(r[0]))))
                require(y < memory.u8[r[0] + 5], 'English exceeds native text rows')
                active['glyphs'].append(r[1])
                self.glyph = r[1], x, glyph['advance'] - spacing
                if r[1] in (0x20, 0x8140):
                    # Native ASCII space advances without preparing a font bitmap.
                    require(active['prepared'] == len(active['glyphs']) - 1,
                            'Space encountered before previous glyph preparation')
                    active['prepared'] += 1
            elif address == 0x08001C14:
                glyph, expected_address = self.glyph_record(r[4])
                require(r[0] == expected_address, 'Native English glyph address differs')
                context = bytes(memory[r[5]:r[5] + 24])
                foreground = memory.u8[0x020000C2]
                # An IRQ can resume at the same pre-instruction breakpoint.
                # Validate every observation, but count one preparation per draw
                # entry; repeated samples must still match that same glyph.
                index = len(active['glyphs']) - 1
                require(active['prepared'] in (index, index + 1), 'Glyph preparation order differs: '+repr((active['id'],active['prepared'],index,hex(r[4]),active['glyphs'][-4:])))
                require(active['expected_colors'][index] == (r[4], foreground),
                        'Native glyph foreground differs from compiled colour controls: '
                        + repr((active['id'],active['expected_colors'][index],(r[4],foreground))))
                background = 4 if context[9] & 1 else 7
                pixels = bytes(foreground if bit == '#' else (7 if y < 2 else background)
                               for y, line in enumerate(glyph['rows']) for bit in line)
                pixels += bytes([background]) * glyph['advance']
                require(bytes(memory[0x02036430:0x02036430 + len(pixels)]) == pixels, 'Native English bitmap differs')
                if active['prepared'] == index:
                    active['foreground_counts'][foreground] = active['foreground_counts'].get(foreground, 0) + 1
                    active['prepared'] += 1
                    self.glyph_checks += 1
                else:
                    active['repeated_preparation_observations'] = active.get('repeated_preparation_observations', 0) + 1
            elif address == 0x08001C68:
                code, x, advance = self.glyph
                require(r[4] == code and r[0] & 255 == x + advance, 'Native English cursor advance differs: '+repr((active['id'],hex(code),x,advance,hex(r[4]),r[0]&255)))
            elif address == 0x080023A0:
                active['page_waits'] += 1
            elif address == 0x08002284:
                if self.nested:
                    self.nested -= 1
                    return
                require(active['glyphs'] == active.pop('expected'), 'Native glyph sequence differs from English')
                active.pop('expected_colors')
                require(active['prepared'] == len(active['glyphs']), 'Native glyphs were skipped')
                require(active['page_waits'] == active['page_count'] - 1, 'English page wait count differs: '+repr((active['id'],active['page_waits'],active['page_count'])))
                require(active.pop('preserved') == (r[4:12], r[13]), 'English reader changed preserved registers/SP')
                active['callee_saved_and_sp_preserved'] = True
                active['end_frame'] = event['frame']
                self.reads.append(active)
                self.active = None

    def completed(self, ident):
        return any(row['id'] == ident for row in self.reads)
