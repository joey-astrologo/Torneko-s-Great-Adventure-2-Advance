"""Native Remi format/output ownership and glyph checks."""
from tools.dialogue_checks import TextChecks
from tools.saved_village_checks import SavedVillageChecks
from tools.verify_service_ui import materialize
from tools.rom import require

RETURNS=(0x0801E97E,0x0801E9A8,0x0801EA06,0x0801EA4A,0x0801EB12,0x0801EBD4,
         0x0801EC3C,0x0801ECCA,0x0801ED76,0x0801EEB0,0x0801EF0A,0x0801EF6E,
         0x0801EFB6,0x0801EFD0,0x0801EFEC,0x0801F01C,0x080164E8)


class RemiChecks(SavedVillageChecks):
    ADDRESSES=TextChecks.ADDRESSES+(0x08000FB8,)+RETURNS
    def __init__(self,game,build,saved_village=None):
        self.rows={r['offset']+0x08000000:r for r in build['remi']['entries']}
        resources={p:r for p,r in self.rows.items() if r['layout']['direct_rom_stream']}
        resources.update({r['offset']+0x08000000:r for r in build['selection_prompt']['entries']})
        resources.update({r['offset']+0x08000000:r for r in build['remi']['warp_names']['entries']})
        choice=next(r for r in build['dialogue']['entries'] if r['id']=='rom.0006309c')
        resources[choice['rom_offset']+0x08000000]=choice
        super().__init__(game,resources,None,saved_village or b'\0');self.saved_village=saved_village;self.pending=None;self.formats=[]
    def callback(self,e):
        a,r=e['address'],e['registers'];m=self.game.core.memory
        if a==0x08000FB8 and r[1] in self.rows:
            row=self.rows[r[1]];require(row['layout']['kind']!='saved-village-format' or self.saved_village is not None,'Saved-village reader requires a verified expected name')
            capacity=row['layout']['capacity'];args=r[2:4]+[m.u32[r[13]+4*i] for i in range(4)]
            expected=materialize(bytes.fromhex(row['encoded_hex']),args,m)
            require(len(expected)<=row['layout']['maximum_formatted_bytes']<=capacity,'Remi output exceeds bound')
            require(r[0]==r[13]+(0 if capacity==128 else 0x14),'Remi output outside owned frame')
            require((r[14]&~1) in RETURNS,'Unknown Remi format consumer')
            self.pending=(r[14]&~1,r[0],expected,capacity,bytes(m[r[0]+capacity:r[0]+capacity+32]),r[4:12],r[13],row)
        if self.pending and a==self.pending[0]:
            _,dest,expected,capacity,guard,regs,sp,row=self.pending
            require(bytes(m[dest:dest+len(expected)])==expected,'Remi native format bytes differ')
            require(bytes(m[dest+capacity:dest+capacity+32])==guard and r[4:12]==regs and r[13]==sp,'Remi format guard/ABI differs')
            self.resources[dest]=row|{'encoded_hex':expected.hex()}
            self.source=dest if row['layout']['kind']=='saved-village-format' else None
            self.formats.append({'id':row['id'],'dest':dest,'capacity':capacity,'bytes':len(expected),'expected_hex':expected.hex(),'guard_preserved':True})
            self.pending=None
        if a in TextChecks.ADDRESSES:super().callback(e)
