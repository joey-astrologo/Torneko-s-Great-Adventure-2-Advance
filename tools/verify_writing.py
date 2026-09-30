"""Native writing success/refusal and all valid name-table selector bounds."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'scroll-success':(0x26A30,0x26AB4,0x26B03,0x26B84,0,0x444),
 'spell-success':(0x26A30,0x26B4A,0x26B73,0x26B84,0,0x858),
 'scroll-name':(0x26A30,0,0x26B03,0x26B84,None,0x440),
 'spell-name':(0x26A30,0,0x26B03,0x26B84,None,0x854),
 'scroll-unused':(0x26A30,0,0x26B03,0x26B84,0,0x6E8),
 'spell-never':(0x26A30,0,0x26B73,0x26B84,0,0x85C),
}
class Writing:
    breakpoints=(0x08026A3A,0x0805CF54,0x08026AD8,0x08026B6A)
    allow_scrolled=False
    scope='Native writing routine26A30 with the original selected-item getter and existing command/inventory records. All37 category0 non-spell targets and61 spell targets, including controlled special/reserved IDs, render their exact reviewed ROM name. Four invalid-name/history refusals run natively. Source copies,256-byte output, complete glyph/pixel fit, item identity/inscription/amount changes or refusal preservation, full caller ABI and battery are checked. These are controlled selectors/history states; normal text-entry matching and eligibility remain separate.'
    def case_fields(self,owner):
        return tuple(f'native-{i}' for i in (range(116,153) if owner=='scroll-success' else range(61))) if owner.endswith('success') else ('native',)
    def setup(self,owner,g,hero,actor,write,overrides):
        self.owner=owner;self.copy=None;m=g.core.memory;self.item=0x0200DF28;self.command=self.item+120;spell=owner.startswith('spell');self.original_id=151 if spell else 124
        self.selected=int(self.field.split('-')[1]) if owner.endswith('success') else 1 if spell else 116
        item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(self.original_id);write(self.item,item)
        command=bytearray(120);command[6]=0 if owner.endswith('name') else self.selected+(10 if spell else 0);write(self.command,command)
        if spell:write(0x02004DBD+self.selected,bytes([int(owner=='spell-success')]))
        else:
            at=0x02003BAC+20*self.selected;write(at,struct.pack('<I',(m.u32[at]|0x400000) if owner=='scroll-success' else m.u32[at]&~0x400000))
        return(self.command,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):
        a,r=e['address'],e['registers'];m=g.core.memory
        if a==0x08026A3A:require(r[0]==self.item,'Native writing selected item differs')
        if a==0x0805CF54 and r[14] in (0x08026AD9,0x08026B6B):
            require(r[1]==self.row['offset']+0x08000000 and r[0]==r[13],'Writing refusal copy source/frame differs');self.copy=(r,bytes(m[r[0]+256:r[0]+272]))
        if a in (0x08026AD8,0x08026B6A) and self.copy:
            old,guard=self.copy;require(r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[old[0]+256:old[0]+272])==guard,'Writing native copy guard/ABI differs');self.copy=None
    def return_register(self,owner):return 0
    def returned(self,owner,g,hero,actor):
        m=g.core.memory;ident=m.u8[0x020013D0+m.u8[self.item+8]];flags=m.u32[self.item]
        require(flags&0x1000000 and not self.copy,'Writing attempt flag/copy differs')
        if owner=='scroll-success':require(ident==self.selected and flags&0x400000,'Native scroll inscription identity differs')
        elif owner=='spell-success':require(ident==153 and flags&0x400000 and m.u8[self.item+4]==self.selected,'Native spell inscription identity/ID differs')
        else:require(ident==self.original_id and not flags&0x400000,'Rejected inscription changed item identity')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='writing',folder='writing-validation',hooks=Writing())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/writing-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
