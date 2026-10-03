"""Exceptions recognize user fields/icons without concealing authored Japanese."""
import unittest
from tools.compact_font import encode
from tools.screen_text_audit import copied_name_field, inventory_marker


class ScreenAuditExceptions(unittest.TestCase):
    def test_copied_name_bounds_and_surrounding_prose(self):
        field = 'あいう'.encode('cp932')
        prefix = encode('Village: ')[:-1]
        suffix = 'の村'.encode('cp932')+b'\0'
        row = copied_name_field(prefix+b'%s'+suffix, field, 8)
        self.assertEqual(row['glyph_start'], 9)
        self.assertEqual(row['codes'], [0x82A0, 0x82A2, 0x82A4])
        self.assertEqual(bytes.fromhex(row['raw_hex']), prefix+field+suffix)
        # The Japanese suffix is outside the three accepted field positions.
        self.assertEqual(len(row['codes']), 3)
        for invalid in (b'', field+b'x', field*6):
            self.assertIsNone(copied_name_field(prefix+b'%s'+suffix, invalid, 8))
        for template in (b'%s%s\0', b'%s %d\0', b'no field\0'):
            self.assertIsNone(copied_name_field(template, field, 8))

    def test_icon_contexts_and_rejections(self):
        context = bytes.fromhex('081806001508000600000000c2b800062c00000000000000')
        for code in (0x874F, 0x8750, 0x8751, 0x8752):
            for colour in (4, 5, 6, 7):
                raw = code.to_bytes(2, 'big')+bytes((3, colour))+encode('Herb')
                self.assertTrue(inventory_marker(code, context, raw, 1))
                self.assertTrue(inventory_marker(code, context, b'\1'+raw[:-1]+b'\2\0', 1))
                self.assertFalse(inventory_marker(code, context, raw, 2))
                self.assertFalse(inventory_marker(code, context, encode('Text')[:-1]+raw, 1))
                for pos,value in ((0,16),(1,40),(2,12),(4,28),(5,2)):
                    changed = bytearray(context);changed[pos]=value
                    self.assertFalse(inventory_marker(code, changed, raw, 1))
        self.assertFalse(inventory_marker(0x8753, context, bytes.fromhex('87530307')+b'\0', 1))
        self.assertFalse(inventory_marker(0x82A0, context, bytes.fromhex('82a00307')+b'\0', 1))
        self.assertFalse(inventory_marker(0x874F, context, bytes.fromhex('874f0300')+b'\0', 1))
        self.assertTrue(inventory_marker(0x874F, context, b'\x87\x4f'+encode('????'), 1))
        self.assertFalse(inventory_marker(0x874F, context, b'\x87\x4f'+'名前'.encode('cp932')+b'\0', 1))

class SparseMemory:
    def __init__(self):
        self.data = {}
        self.u8 = self
        self.u32 = self.Words(self)

    class Words:
        def __init__(self, memory): self.memory = memory
        def __getitem__(self, address):
            return int.from_bytes(self.memory[address:address+4], 'little')

    def __getitem__(self, key):
        if isinstance(key, slice):
            return bytes(self.data.get(i, 0) for i in range(key.start, key.stop))
        return self.data.get(key, 0)

    def put(self, address, data):
        self.data.update({address+i: value for i,value in enumerate(data)})


class ScreenAuditProducerTests(unittest.TestCase):
    def game(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.screen_text_audit import ScreenTextAudit
        memory = SparseMemory()
        game = SimpleNamespace(core=SimpleNamespace(memory=memory))
        with patch('tools.screen_text_audit.TextChecks'):
            audit = ScreenTextAudit(game)
        memory.put(0x02000000, bytes.fromhex('087800001c02')+bytes(18))
        return audit, memory

    def event(self, address, args=(), lr=0, sp=0x03007000):
        r = [0]*16
        r[:len(args)] = args
        r[13], r[14] = sp, lr
        return dict(address=address, registers=r, frame=1)

    def draw(self, audit, memory, pointer, codes):
        audit.callback(self.event(0x080021B4, (0x02000000,pointer)))
        for code in codes:
            audit.callback(self.event(0x08001BC4,(0x02000000,code),lr=0x080021AB))
            audit.callback(self.event(0x08001C6E))
        audit.callback(self.event(0x08002284))

    def mayor(self, caller=0x08020675, mutate=False, invalidate=False):
        audit, memory = self.game()
        sp, template = 0x03007000, 0x08800000
        field = 'あい'.encode('cp932')
        prefix = encode('Village: ')[:-1]
        suffix = '村'.encode('cp932')+b'\0'
        memory.put(template, prefix+b'%s'+suffix)
        memory.put(sp+0x100,field+b'\0')
        audit.callback(self.event(0x08000FB8,(sp,template,sp+0x100),lr=caller))
        if invalidate:
            audit.callback(self.event(0x08000FB8,(sp,template,sp+0x100),lr=0x0802063F))
        output = prefix+field+suffix
        if mutate: output=output[:-1]+'あ'.encode('cp932')+b'\0'
        memory.put(sp,output)
        codes = [0xF000+ord(c) for c in 'Village: ']+[0x82A0,0x82A2,0x91BA]
        if mutate: codes.append(0x82A0)
        self.draw(audit,memory,sp,codes)
        return audit

    def test_relocated_village_name_requires_hook_field_and_exact_output(self):
        from tools.name_entry import STORED
        for invalid in (None, 'caller', 'entry', 'field', 'output'):
            audit, memory = self.game()
            sp, helper, template, table = 0x03007000, 0x08851148, 0x08900000, 0x08810000
            field = 'あい'.encode('cp932')
            prefix, suffix = encode('In ')[:-1], '村'.encode('cp932')+b'\0'
            memory.put(0x08050BC4, bytes.fromhex('004b1847') if invalid!='entry' else bytes(4))
            memory.put(0x08050BC8, (helper+1).to_bytes(4,'little'))
            memory.put(0x08014970, table.to_bytes(4,'little'))
            memory.put(STORED, bytes([2,3]+[1]*6))
            memory.put(table+4, field)
            memory.put(template, prefix+b'%s'+suffix)
            memory.put(sp+448, (field if invalid!='field' else 'いう'.encode('cp932'))+b'\0')
            audit.callback(self.event(0x08000FB8,(sp,template,sp+448),lr=helper+(0x39 if invalid=='caller' else 0x37)))
            output=prefix+field+suffix
            if invalid=='output':output=output[:-1]+'あ'.encode('cp932')+b'\0'
            memory.put(sp,output)
            codes=[0xF000+ord(c) for c in 'In ']+[0x82A0,0x82A2,0x91BA]
            if invalid=='output':codes.append(0x82A0)
            self.draw(audit,memory,sp,codes)
            self.assertEqual([x['code'] for x in audit.exceptions], [] if invalid else [0x82A0,0x82A2])
            self.assertIn(0x91BA,[x['code'] for x in audit.unclassified])

    def test_mayor_accepts_only_name_not_authored_suffix(self):
        audit = self.mayor()
        self.assertEqual([x['code'] for x in audit.exceptions], [0x82A0,0x82A2])
        self.assertEqual([x['code'] for x in audit.unclassified], [0x91BA])

    def test_different_producer_cannot_reuse_name_exception(self):
        for args in (dict(caller=0x0802063F),dict(invalidate=True)):
            audit = self.mayor(**args)
            self.assertFalse(audit.exceptions)
            self.assertEqual(len(audit.unclassified),3)

    def test_changed_complete_output_invalidates_copied_field(self):
        audit = self.mayor(mutate=True)
        self.assertFalse(audit.exceptions)
        self.assertEqual(len(audit.unclassified),4)

    def test_equipped_spell_icon_does_not_hide_japanese_label(self):
        for colour,caller,accepted in ((7,0x08022643,True),(2,0x08022643,True),
                                       (6,0x08022643,False),(7,0x08022645,False)):
            audit,memory = self.game()
            source = 0x03006000
            memory.put(0x02000000,bytes.fromhex('081806001508')+bytes(18))
            memory.put(source,bytes((3,colour))+b'\x87\x50\x82\xa0\0')
            audit.callback(self.event(0x08002298,(0x02000000,source),lr=caller))
            self.draw(audit,memory,source,[0x8750,0x82A0])
            self.assertEqual([x['code'] for x in audit.exceptions], [0x8750] if accepted else [])
            self.assertEqual([x['code'] for x in audit.unclassified], [0x82A0] if accepted else [0x8750,0x82A0])

    def test_editor_header_requires_exact_indexed_input(self):
        from tools.name_entry import EDIT
        for changed in (False,True):
            audit,memory = self.game()
            sp,template,table = 0x03007000,0x08800000,0x08801000
            memory.put(0x08015634,table.to_bytes(4,'little'))
            memory.put(EDIT,b'\x05\x06')
            memory.put(table+10,b'\x82\xa0\x82\xa2')
            field = b'\x82\xa0\x82\xa2'
            memory.put(sp,field+b'\0')
            prefix = encode('Name: ')[:-1]
            memory.put(template,prefix+b'%s\x91\xba\0')
            event = self.event(0x08000FB8,(sp+0x14,template,sp),lr=0x08015569)
            event['registers'][8] = 2
            if changed: memory.put(EDIT,b'\x06\x05')
            audit.callback(event)
            memory.put(sp+0x14,prefix+field+b'\x91\xba\0')
            self.draw(audit,memory,sp+0x14,[0xF000+ord(c) for c in 'Name: ']+[0x82A0,0x82A2,0x91BA])
            self.assertEqual([x['code'] for x in audit.exceptions], [] if changed else [0x82A0,0x82A2])
            self.assertEqual([x['code'] for x in audit.unclassified], [0x82A0,0x82A2,0x91BA] if changed else [0x91BA])

    def test_password_exception_requires_native_generator_and_exact_output(self):
        for invalid in (None, 'caller', 'permutation', 'suffix', 'geometry'):
            audit, memory = self.game()
            sp, template = 0x03007000, 0x08800000
            memory.put(0x02000000, bytes.fromhex('383000001001')+bytes(18))
            memory.put(template, b'\x14'+b'%s'*9+b'\0')
            memory.put(0x08057A40, (0x08154494).to_bytes(4, 'little'))
            memory.put(0x08057A38, (0x02000100).to_bytes(4, 'little'))
            memory.put(0x02000100, (0x02000200).to_bytes(4, 'little'))
            memory.put(0x02000200, bytes(range(9)))
            fields = []
            for i in range(9):
                pointer = 0x08801000+4*i
                memory.put(0x08154494+4*i, pointer.to_bytes(4, 'little'))
                memory.put(pointer, bytes((0x82, 0xA0+2*i, 0)))
                fields.append(pointer)
            args = [fields[i] for i in (0,5,1,6,2,7,3,8,4)]
            if invalid == 'permutation': args[0], args[1] = args[1], args[0]
            for i, pointer in enumerate(args[2:]):
                memory.put(sp+4*i, pointer.to_bytes(4, 'little'))
            audit.callback(self.event(0x08000FB8, (sp+28, template, *args[:2]),
                                      lr=0x080579E5 if invalid == 'caller' else 0x080579E3))
            codes = [int.from_bytes(memory[p:p+2], 'big') for p in args]
            output = b'\x14'+b''.join(memory[p:p+2] for p in args)
            if invalid == 'suffix':
                output += b'\x91\xba'
                codes.append(0x91BA)
            if invalid == 'geometry': memory.put(0x02000000, b'\x30')
            memory.put(sp+28, output+b'\0')
            self.draw(audit, memory, sp+28, codes)
            self.assertEqual(len(audit.exceptions), 9 if invalid is None else 0)
            self.assertEqual(len(audit.unclassified), 0 if invalid is None else len(codes))


if __name__ == '__main__':
    unittest.main()
