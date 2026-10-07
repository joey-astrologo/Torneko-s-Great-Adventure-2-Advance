"""Data-flow evidence must retain alternate branches and unresolved RAM aliases."""
import struct
import unittest

from tools.audit_shared_source_dispositions import BASE, START, inspect


class TextDataflowTests(unittest.TestCase):
    def fixture(self):
        self.rom=bytearray(START+0xB00)
        self.function=dict(entry=BASE,nodes={},ops=[])
        self.node('constant:table:4',constant=BASE+START)
        self.node('constant:space:4',constant=0)
        return self.function

    def node(self, key, constant=None, address='unique:0'):
        self.function['nodes'][key]=dict(size=4,constant=constant,address=address,register='-')
        return key

    def op(self, kind, output, *inputs, address='unique:0', pc=BASE+32):
        self.node(output,address=address)
        self.function['ops'].append(dict(pc=pc,kind=kind,output=output,inputs=list(inputs)))
        return output

    def load(self, address):
        self.op('LOAD','loaded','constant:space:4',address)
        return inspect([self.function],self.rom)

    def test_branch_union_retains_untranslated_candidate(self):
        self.fixture()
        safe=self.node('constant:safe:4',constant=4)
        candidate=self.node('constant:candidate:4',constant=4*0x25D)
        selected=self.op('MULTIEQUAL','selected',safe,candidate)
        pointer=self.op('INT_ADD','pointer','constant:table:4',selected)
        self.assertEqual(self.load(pointer)[0]['addresses'],[BASE+START+4,BASE+START+4*0x25D])

    def test_unknown_index_stays_unresolved(self):
        self.fixture()
        unknown=self.node('input:register:index:4')
        pointer=self.op('INT_ADD','pointer','constant:table:4',unknown)
        result=self.load(pointer)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['addresses'],[])

    def test_rom_literal_survives_decompiler_call_alias_cycle(self):
        self.fixture()
        struct.pack_into('<I',self.rom,64,BASE+START)
        initial=self.node('input:08000040:4',address='08000040')
        loop=self.op('MULTIEQUAL','loop',initial,'after',address='08000040')
        self.op('INDIRECT','after',loop,'constant:space:4',address='08000040')
        self.assertEqual(self.load(loop)[0]['addresses'],[BASE+START])

    def test_mutable_ram_alias_is_not_treated_as_rom(self):
        self.fixture()
        value=self.op('INDIRECT','mutable','constant:table:4','constant:space:4',address='02000040')
        self.assertEqual(self.load(value)[0]['addresses'],[])


if __name__=='__main__':unittest.main()
