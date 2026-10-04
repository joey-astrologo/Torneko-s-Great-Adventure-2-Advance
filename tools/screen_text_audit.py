"""Observe every shared text read and glyph, without a resource-pointer filter.

This is a bounded screen audit, not a claim that all graphical text uses these
functions. Unknown glyphs are retained as failures, including unregistered reads.
"""

import re
from hashlib import sha256

from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks
from tools.name_entry import EDIT, HERO, STORED
from tools.compact_font import encode
from tools.numeric_font import ALIASES
from tools.text_codec import readable, tokenize

KEYBOARD_PAGES = {
    0x080600F8: 'defe7e9f7c8863580e49e479a8c88113153d40b841697987dc1e3be1f0fadb85',
    0x080646BC: '109547ab62a40a3e96a6dccd9829aae5f8b732c2923d0d8e1eb243f50342e0cd',
    0x080645C4: '67222e64d41940664f060daf97e3a7e20987b80d7b613b270e5e6616735b3a2f',
}


def copied_name_field(template, field, cells):
    """Describe only the bounded name span, never exempt its surrounding prose."""
    parts = template.split(b'%s')
    if (len(parts) != 2 or b'%' in b''.join(parts) or not field or
            len(field) > cells*2 or len(field) % 2):
        return None
    codes = [int.from_bytes(field[i:i+2], 'big') for i in range(0, len(field), 2)]
    tokens, _ = tokenize(parts[0]+b'\0')
    start = sum(len(t['text']) if t['kind']=='text' else t['kind']=='glyph' for t in tokens)
    return dict(raw_hex=(parts[0]+field+parts[1]).hex(), glyph_start=start, codes=codes)


def inventory_marker(code, context, raw, glyph_count):
    if code not in (0x874F, 0x8750, 0x8751, 0x8752):
        return False
    body = raw[1:-2]+b'\0' if raw.startswith(b'\x01') and raw.endswith(b'\x02\0') else raw
    marker = code.to_bytes(2, 'big')+b'\x03'
    return (context[:2] in (b'\x08\x18', b'\x40\x18') and context[2] == 6 and
            context[4] == 21 and context[5] in (1, 4, 8) and glyph_count == 1 and
            (body.startswith(marker) and body[len(marker):len(marker)+1] in (b'\x04', b'\x05', b'\x06', b'\x07') or
             code == 0x874F and body == b'\x87\x4f'+encode('????')))


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
        self.preview_name_fields = {}
        self.formatted_player_fields = {}
        self.formatted_village_fields = {}
        self.editor_fields = {}
        self.protocol_fields = {}

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
        if a == 0x08002298:
            self.editor_fields.pop(r[1], None)
            # Optional symbol/kana pages are deliberately retained. Restrict the
            # exemption to the native keyboard draw, exact page and geometry.
            if r[14] in (0x080155F1, 0x0801842F) and r[1] in (0x080600F8, 0x080646BC, 0x080645C4):
                raw = self.stream(r[1], event).get('raw_hex')
                context = bytes(m[r[0]:r[0]+6])
                if (raw and sha256(bytes.fromhex(raw)).hexdigest() == KEYBOARD_PAGES[r[1]] and
                        context[:2] == b'\x08\x28' and context[4:6] == b'\x1c\x07'):
                    self.editor_fields[r[1]] = dict(raw_hex=raw, reason='Retained optional symbol/kana keyboard page at its native editor caller')
            if r[14] == 0x080183CB and r[1] == r[13] and m.u32[r[13]+32] in (8, 15):
                limit = m.u32[r[13]+32]
                ids = bytes(m[EDIT:EDIT+limit+1])
                table = m.u32[0x08018474]
                expected = b''.join(encode('_')[:-1] if i == 1 else bytes(m[table+2*i:table+2*i+2])
                                    for i in ids[:-1])+b'\0'
                if ids[-1] == 0 and bytes(m[r[1]:r[1]+len(expected)]) == expected:
                    self.editor_fields[r[1]] = dict(raw_hex=expected.hex(), reason='Exact indexed user input in the native item writing/name editor')
        if a in (0x0801588C, 0x08000FB8):
            pointer = r[0] if a == 0x0801588C else r[1]
            row = {'frame': event['frame'], 'source': pointer, 'caller': r[14],
                   'phase': self.phase, **self.stream(pointer, event)}
            (self.queues if a == 0x0801588C else self.formats).append(row)
            if a == 0x08000FB8:
                self.formatted_player_fields.pop(r[0], None)
                self.formatted_village_fields.pop(r[0], None)
                self.protocol_fields.pop(r[0], None)
            if (a == 0x08000FB8 and r[14] == 0x080579E3 and r[0] == r[13]+28 and
                    row.get('raw_hex') == (b'\x14'+b'%s'*9+b'\0').hex() and
                    m.u32[0x08057A40] == 0x08154494):
                # The retained promotion password is generated protocol data.
                # Verify its native permutation and complete nine-kana output;
                # this cannot exempt the heading or surrounding notice.
                indices = m.u32[m.u32[0x08057A38]]
                args = r[2:4]+[m.u32[r[13]+4*i] for i in range(7)]
                expected = [m.u32[0x08154494+4*m.u8[indices+i]] for i in (0,5,1,6,2,7,3,8,4)]
                fields = [bytes(m[p:p+3]) for p in args]
                if args == expected and all(len(f)==3 and f[2]==0 and f[0]>=0x80 for f in fields):
                    self.protocol_fields[r[0]] = (b'\x14'+b''.join(f[:2] for f in fields)+b'\0').hex()
            if (a == 0x08000FB8 and r[14] == 0x08015569 and
                    r[0] == r[13]+0x14 and r[2] == r[13] and 1 <= r[8] <= 8):
                # Native village/player editor: decode the actual indexed input,
                # then recognize only that field within the complete header.
                table = m.u32[0x08015634]
                decoded = b''.join(bytes(m[table+2*i:table+2*i+2])
                                   for i in bytes(m[EDIT:EDIT+r[8]]))
                if bytes(m[r[2]:r[2]+len(decoded)+1]) == decoded+b'\0':
                    bounded = copied_name_field(bytes.fromhex(row['raw_hex']), decoded, 8)
                    if bounded:
                        self.formatted_village_fields[r[0]] = bounded | dict(
                            reason='Exact indexed user input in the native village/player name editor header')
            helper = m.u32[0x08050BC8] & ~1
            if (a == 0x08000FB8 and bytes(m[0x08050BC4:0x08050BC8]) == bytes.fromhex('004b1847')
                    and 0x08800000 <= helper < 0x0A000000 and r[14] == helper+0x37
                    and r[0] == r[13] and r[2] == r[13]+448):
                # Relocated village prose uses native indexed saved-name data.
                # Check the actual generated field; surrounding text is audited.
                table = m.u32[0x08014970]
                indices = bytes(m[STORED:STORED+8]).split(b'\x01')[0]
                decoded = b''.join(bytes(m[table+2*i:table+2*i+2]) for i in indices)
                if decoded and bytes(m[r[2]:r[2]+len(decoded)+1]) == decoded+b'\0':
                    bounded = copied_name_field(bytes.fromhex(row['raw_hex']), decoded, 8)
                    if bounded:
                        self.formatted_village_fields[r[0]] = bounded | dict(
                            reason='Exact indexed saved village name in the owned village prose helper')
            village_producer = (r[14] == 0x08020675 and r[2] == r[13]+0x100 or
                                r[14] == 0x0801FB3D and r[2] == 0x0200CEE8)
            if a == 0x08000FB8 and village_producer and r[0] == r[13]:
                # Mayor confirmation copies the native eight-cell input field.
                # Match this producer, its bounded field and the complete output;
                # Japanese surrounding that field is still a finding.
                template = bytes.fromhex(row['raw_hex'])
                field = bytes(m[r[2]:r[2]+20]).split(b'\0')[0]
                bounded = copied_name_field(template, field, 8)
                if bounded:
                    self.formatted_village_fields[r[0]] = bounded | dict(
                        reason='Exact bounded village-name field copied by the native mayor/book confirmation formatter')
            if (a == 0x08000FB8 and r[14] in (0x080149B3, 0x08014A13, 0x08014A77)
                    and r[0] == r[13]+0x14 and r[2] == r[13]+0x114):
                # This native preview copies the saved village name into its
                # output instead of invoking the nested name reader. Match the
                # exact indexed name and native decoded field, never a sentence.
                table = m.u32[0x08014970]
                decoded = b''.join(bytes(m[table+i*2:table+i*2+2])
                                   for i in bytes(m[STORED:STORED+8]) if i != 1)
                if decoded and bytes(m[r[2]:r[2]+len(decoded)+1]) == decoded+b'\0':
                    self.preview_name_fields[r[0]] = decoded
            player_producers = {
                # Return address: (output stack offset, string count, name index).
                0x0802BE19: (4, 3, 1),    # Gold theft.
                0x0802FA8B: (0x54, 3, 1), # Staff-charge drain.
                0x08031883: (0, 2, 1),    # Player pulled by a monster.
                0x08033B6D: (0x80, 1, 0), # Whole-inventory identification.
            }
            producer = player_producers.get(r[14])
            if a == 0x08000FB8 and producer and r[0] == r[13]+producer[0]:
                # These disassembled producers copy the saved name into a
                # specific field. Match the arguments and complete output;
                # only the name's glyph positions receive an exception.
                template = bytes.fromhex(row['raw_hex'])
                parts = template.split(b'%s')
                hero = bytes(m[HERO:HERO+16]).split(b'\0')[0]
                _, count, name_index = producer
                args = (r[2], r[3], m.u32[r[13]])[:count]
                strings = [bytes(m[p:p+256]).split(b'\0')[0] for p in args]
                if (hero and len(hero) % 2 == 0 and len(parts) == count+1
                        and args[name_index] == HERO and strings[name_index] == hero
                        and b'%' not in b''.join(parts)):
                    prefix = b''.join(parts[i]+strings[i] for i in range(name_index))+parts[name_index]
                    tokens, _ = tokenize(prefix+b'\0')
                    glyph_start = sum(len(t['text']) if t['kind'] == 'text' else t['kind'] == 'glyph' for t in tokens)
                    expected = b''.join(parts[i]+strings[i] for i in range(count))+parts[-1]
                    self.formatted_player_fields[r[0]] = dict(raw_hex=expected.hex(),
                        player_hex=hero.hex(), glyph_start=glyph_start, producer=r[14]-1,
                        reason='Exact saved player-name field from a verified native message formatter')
            if a == 0x08000FB8 and r[14] == 0x08015861:
                # The common player wrapper supplies one saved-name field.
                # Verify the field bytes and entire expected output, then exempt
                # only that field's glyphs; surrounding Japanese remains visible.
                template = bytes.fromhex(row['raw_hex'])
                parts = template.split(b'%s')
                hero = bytes(m[HERO:HERO+16]).split(b'\0')[0]
                field = bytes(m[r[2]:r[2]+16]).split(b'\0')[0]
                if hero and field == hero and len(parts) == 2 and b'%' not in b''.join(parts):
                    tokens, _ = tokenize(parts[0]+b'\0')
                    start = sum(len(t['text']) if t['kind']=='text' else t['kind']=='glyph' for t in tokens)
                    self.formatted_player_fields[r[0]] = dict(
                        raw_hex=(parts[0]+hero+parts[1]).hex(), player_hex=hero.hex(),
                        glyph_start=start, producer=r[14]-1,
                        reason='Exact saved player-name field from the native player-message wrapper')
        if a == 0x080158CE:
            # Observe the payload AFTER the localization hook redirects static
            # Japanese pointers and joins combat fragments. Entry arguments alone
            # are not evidence of what the player actually sees.
            raw = self.stream(r[6], event)
            hero = bytes(m[HERO:HERO+16]).split(b'\0')[0]
            field = self.formatted_player_fields.pop(r[6], None)
            if field and (field['raw_hex'] != raw.get('raw_hex') or field['player_hex'] != hero.hex()):
                field = None
            self.final_queues.append({'frame': event['frame'], 'source': r[6],
                'caller': m.u32[r[13]+12], 'phase': self.phase, **raw,
                'player_hex': hero.hex(), 'verified_player_field':field, 'drawn_codes': []})
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
            if self.observer.stack and r[14] == 0x08002169:
                reader = self.observer.stack[-1]
                raw = bytes.fromhex(reader['raw_hex'])
                offset = r[4]-reader['source']
                if (0 <= offset < len(raw) and raw[offset] == 0x7F and
                        r[1] == int.from_bytes(bytes(m[HERO:HERO+2]), 'big')):
                    reason = 'Exact first saved-player glyph selected by the native name-initial control'
            if r[1] in (0x2B, 0x2F, 0x5B, 0x5D) and r[14] == 0x08001E69:
                reason = 'Native ASCII plus/slash/brackets from the punctuation handler'
            if self.observer.stack and self.observer.stack[-1]['source'] in (HERO,0x0200CEE8):
                reader=self.observer.stack[-1]
                n=len(reader['glyph_positions'])-1
                raw=bytes.fromhex(reader['raw_hex'])
                # Only the exact native nested player/saved-village name read;
                # a Japanese sentence elsewhere in this window is not exempt.
                if n>=0 and n*2+2<len(raw) and int.from_bytes(raw[n*2:n*2+2],'big')==r[1]:
                    reason='Exact native player or saved-village name substitution'
            if self.observer.stack:
                reader = self.observer.stack[-1]
                raw = bytes.fromhex(reader['raw_hex'])
                outer = self.observer.callers[-1] if self.observer.callers else {}
                if (r[1] == 0x8750 and len(reader['glyph_positions']) == 1 and
                        outer.get('return') == 0x08022643 and outer.get('source') == reader['source'] and
                        outer.get('window') == reader['window'] and raw[:4] in (b'\x03\x07\x87\x50',b'\x03\x02\x87\x50') and
                        context[:3] == b'\x08\x18\x06' and context[4:6] == b'\x15\x08'):
                    reason = 'Original equipped icon at the native spell-list row caller'
                if (r[1] in (0x874F,0x8750) and len(reader['glyph_positions']) == 1 and
                        outer.get('return') == 0x08021E7B and outer.get('source') == reader['source'] and
                        outer.get('window') == reader['window'] and
                        raw[:3] == r[1].to_bytes(2,'big')+b'\x03' and raw[3:4] in (b'\x02',b'\x03',b'\x07') and
                        context[:3] == b'\x08\x18\x06' and context[4] == 21 and 1 <= context[5] <= 8):
                    reason = 'Original blank/equipped icon at the native skill-list row caller'
                editor = self.editor_fields.get(reader['source'])
                if editor and editor['raw_hex'] == reader['raw_hex']:
                    reason = editor['reason']
                if (self.protocol_fields.get(reader['source']) == reader['raw_hex'] and
                        context[:2] == b'\x38\x30' and context[4:6] == b'\x10\x01'):
                    reason = 'Exact nine-kana native promotion password; retained protocol data'
                village = self.formatted_village_fields.get(reader['source'])
                position = len(reader['glyph_positions'])-1-village['glyph_start'] if village else -1
                if (village and village['raw_hex']==reader['raw_hex'] and
                        0<=position<len(village['codes']) and village['codes'][position]==r[1]):
                    reason = village['reason']
                name = self.preview_name_fields.get(reader['source'])
                n = len(reader['glyph_positions'])-1
                if (name and raw.startswith(name) and 0 <= n < len(name)//2
                        and r[1] == int.from_bytes(name[n*2:n*2+2], 'big')
                        and context[:2] == b'\x08\x68' and context[4:6] == b'\x1c\x03'):
                    reason = 'Exact indexed saved-village name copied by the native save-preview formatter'
                for label, row_index in (('Weapon: ',4), ('Shield: ',5), ('Ring: ',6)):
                    prefix = encode(label)[:-1]
                    if (r[1] in (0x874F,0x8750) and n == len(label)
                            and raw.startswith(prefix+r[1].to_bytes(2,'big')+b'\x03\x07')
                            and context[:2] == b'\x08\x18' and context[4:6] == b'\x1c\x08'
                            and context[3] == row_index):
                        reason = 'Original equipped marker in the native results equipment field'
            if self.observer.stack and inventory_marker(r[1], context,
                    bytes.fromhex(self.observer.stack[-1]['raw_hex']),
                    len(self.observer.stack[-1]['glyph_positions'])):
                reason = 'Original blank/equipped/curse marker at the start of an inventory, target-selector, pot-content or ground-item row'
            if self.final_queues and not self.observer.stack:
                queue = self.final_queues[-1]
                hero = bytes.fromhex(queue['player_hex'])
                n = len(queue['drawn_codes'])
                if (hero and len(hero) % 2 == 0 and bytes.fromhex(queue['raw_hex']).startswith(hero)
                        and n < len(hero)//2 and r[1] == int.from_bytes(hero[n*2:n*2+2], 'big')):
                    reason = 'Exact saved player-name prefix; Japanese name retained from this battery save'
                field = queue.get('verified_player_field')
                offset = n-field['glyph_start'] if field else -1
                if field and 0 <= offset < len(hero)//2 and r[1] == int.from_bytes(hero[offset*2:offset*2+2],'big'):
                    reason = field.get('reason', 'Exact saved player-name field from the verified native gold-theft formatter')
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
