"""Check numeric bitmap preparation, including fixed-cell bank amount entry."""
from tools.build_compact_font import HOOK_OFFSET, HOOK_BYTES
from tools.compact_font import load_font
from tools.numeric_font import ALIASES, glyph, record_offset
from tools.rom import require


class NumericChecks:
    ADDRESSES=(0x08001C14,)
    def __init__(self,game):
        self.game=game;self.font=load_font();self.samples=[]

    def callback(self,event):
        r=event['registers'];code=r[4]
        if event['address']!=0x08001C14 or code not in ALIASES:return
        m=self.game.core.memory;g=glyph(self.font,code)
        require(r[0]==0x08000000+record_offset(code,HOOK_OFFSET+HOOK_BYTES),'Numeric alias address differs')
        foreground=m.u8[0x020000c2];background=4 if m.u8[r[5]+9]&1 else 7
        pixels=bytes(foreground if p=='#' else (7 if y<2 else background)
                     for y,line in enumerate(g['rows']) for p in line)+bytes([background])*g['advance']
        require(bytes(m[0x02036430:0x02036430+len(pixels)])==pixels,'Compact number bitmap differs')
        self.samples.append({'code':code,'text':ALIASES[code],'advance':g['advance'],
                             'fixed_cell':m.u8[r[5]+6],'spacing':m.u8[r[5]+8],
                             'x':m.u8[r[5]+2],'window_width':m.u8[r[5]+4]*8})
