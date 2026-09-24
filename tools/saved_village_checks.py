"""Glyph/paging checks for a native1F saved-village substitution."""
from tools.dialogue_checks import TextChecks, rendered_codes
from tools.name_entry import HERO
from tools.rom import require


class SavedVillageChecks(TextChecks):
    def __init__(self,game,resources,source,name):
        super().__init__(game,resources);self.source=source;self.name=name
    def callback(self,e):
        a,r=e['address'],e['registers'];m=self.game.core.memory
        if a==0x080021B4 and r[1]==self.source:
            row=self.resources[r[1]];payload=bytes.fromhex(row['encoded_hex'])
            require(bytes(m[r[1]:r[1]+len(payload)])==payload,'Saved-village warning source differs')
            if self.active and self.active.get('entry_registers')==tuple(r) and not self.active['glyphs']:
                return
            require(self.active is None,'Overlapping saved-village warning')
            expanded=payload.replace(b'\x1f',self.name[:-1])
            self.active={'id':row['id'],'source':r[1],'start_frame':e['frame'],'window':r[0],
                'window_hex':bytes(m[r[0]:r[0]+24]).hex(),'entry_registers':tuple(r),'glyphs':[],
                'page_waits':0,'width':m.u8[r[0]+4]*8,'preserved':(r[4:12],r[13]),
                'expected':rendered_codes(expanded,bytes(m[HERO:HERO+16])),
                'expected_colors':rendered_codes(expanded,bytes(m[HERO:HERO+16]),m.u8[0x020000C2],m.u8[0x020000C3]),
                'foreground_counts':{},'page_count':len(row['layout']['pages']),'prepared':0}
            require(m.u8[r[0]+6]==m.u8[r[0]+8]==0,'Saved-village warning spacing differs')
            return
        if a==0x080021B4 and self.active and r[1]==0x0200CEE8:
            require(r[0]==self.active['window'] and bytes(m[r[1]:r[1]+len(self.name)])==self.name,
                    'Saved-village nested source differs')
            self.nested+=1;return
        super().callback(e)

