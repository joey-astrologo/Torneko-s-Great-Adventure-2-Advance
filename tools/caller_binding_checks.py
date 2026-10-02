"""Exact native binding and buffer checks shared by caller regression probes."""
from tools.rom import require
from tools.verify_service_ui import materialize
from tools.compact_font import encode


class CallerBindingChecks:
    def __init__(self, game, build, field_profile=None):
        self.game = game
        family = build.get('caller_repairs', {})
        self.bindings = {b['call']: b for b in family.get('bindings', [])}
        self.rows = {r['source']['offset']: r for r in family.get('entries', [])}
        self.pending, self.observed, self.formats = {}, [], []
        self.profile, self.overrides, self.restore_fields = field_profile, [], []
        self.wrapper_row = None
        self.addresses = {b['consumer'] for b in self.bindings.values()} | {
            b['call']+4 for b in self.bindings.values() if b['consumer'] in (0x08000FB8, 0x0805CF54)}
        self.addresses |= {0x08000FB8, 0x08015860}

    def callback(self, event):
        a, r, m = event['address'], event['registers'], self.game.core.memory
        if a in self.pending:
            dest, expected, guard, regs, sp, record, capacity = self.pending.pop(a)
            require(bytes(m[dest:dest+len(expected)]) == expected, 'Repaired formatter output differs')
            require(bytes(m[dest+capacity:dest+capacity+16]) == guard and r[4:12] == regs and r[13] == sp,
                    'Repaired formatter exceeded buffer or changed ABI')
            self.formats.append(record | {'output_hex': expected.hex(), 'output_bytes': len(expected),
                                          'capacity': capacity, 'guard_and_abi_preserved': True})
            for pointer, raw, previous in self.restore_fields:
                require(bytes(m[pointer:pointer+len(raw)]) == raw, 'Formatter modified a substitution field')
                for i, value in enumerate(previous):
                    m.u8[pointer+i] = value
            self.restore_fields.clear()
        call = (r[14] & ~1)-4
        binding = self.bindings.get(call)
        wrapper = a == 0x08000FB8 and call == 0x0801585C and self.wrapper_row is not None
        if not wrapper and (not binding or a != binding['consumer']):
            return
        pointer = r[1] if a in (0x08000FB8, 0x08002298, 0x0805CF54) else r[0]
        row = self.wrapper_row if wrapper else self.rows[binding['source_offset']]
        require(pointer == row['offset']+0x08000000, 'Repaired caller selected the wrong text')
        if wrapper:
            self.wrapper_row = None
        record = {'call': call, 'consumer': a, 'source': pointer, 'frame': event['frame'], 'id': row['id']}
        self.observed.append(record)
        if a == 0x08015848 and row['fields']:
            self.wrapper_row = row
        if a in (0x08000FB8, 0x0805CF54):
            require(not self.pending, 'Overlapping repaired formatter checks')
            args = r[2:4]+[m.u32[r[13]+4*i] for i in range(8)]
            if self.profile and a == 0x08000FB8:
                require(not self.restore_fields, 'Previous formatter fields unrestored')
                for i, role in enumerate(row['fields']):
                    before = args[i]
                    if role == 'amount':
                        # These quantities are nonnegative gameplay values.
                        # Exercise zero and the signed-positive decimal limit.
                        after = 0 if self.profile == 'coloured' else 0x7FFFFFFF
                    else:
                        raw = (encode('W'*(31 if role == 'actor' else 27)) if self.profile == 'maximum-width'
                               else encode('i'*31) if self.profile == 'maximum-bytes'
                               else b'\x03\x05'+encode('Torneko' if role == 'actor' else 'Oaken club')[:-1]+b'\x05\0')
                        # Reuse the established 64-byte actor-name scratch, or
                        # this caller's native item-name field beyond its output.
                        after = 0x02008D08 if role == 'actor' else before
                        require(role == 'actor' or r[0]+256 <= after < r[13]+0x1000,
                                'Item substitution is not in the caller name scratch')
                        require(len(raw) <= 64, 'Controlled field exceeds native capacity')
                        previous = bytes(m[after:after+len(raw)])
                        self.restore_fields.append((after, raw, previous))
                        for n, value in enumerate(raw):
                            m.u8[after+n] = value
                        self.overrides.append({'address': after, 'before_hex': previous.hex(), 'after_hex': raw.hex(),
                                               'restore_at_formatter_return': True})
                    require(i < 2, 'Unverified stack field substitution')
                    args[i] = after
                    self.game.core.cpu.gprs[i+2] = after if after < 0x80000000 else after-0x100000000
                    self.overrides.append({'call': call, 'register': i+2, 'before': before, 'after': after,
                                           'reason': 'Formatter-only field boundary; native source/reader unchanged'})
            expected = materialize(bytes.fromhex(row['encoded_hex']), args, m)
            capacity = 9 if a == 0x0805CF54 else 256
            require(len(expected) <= row['maximum_bytes'] <= 256, 'Repaired formatter expansion exceeds capacity')
            self.pending[call+4] = (r[0], expected, bytes(m[r[0]+capacity:r[0]+capacity+16]), r[4:12], r[13], record, capacity)

    def report(self):
        return {'binding_checks': self.observed, 'format_checks': self.formats,
                'binding_checks_complete': not self.pending and not self.restore_fields and self.wrapper_row is None,
                'field_profile': self.profile, 'field_overrides': self.overrides}
