"""Independent native expectations for the compiled early menu streams."""
from tools.dialogue_checks import TextChecks
from tools.compact_font import load_font,COMPACT_ASSET,encode
from tools.menu_text import ACTIONS,ROOT_LABELS,ROOT_POINTERS
from tools.rom import load_base,require
from tools.text_codec import tokenize
import struct

class MenuChecks(TextChecks):
    ADDRESSES=TextChecks.ADDRESSES+(0x08000fb8,0x08019466,0x08019184,0x080194aa,0x08019a98,0x08019e36)
    def __init__(self,game,menus,font=None):
        super().__init__(game,{})
        self.font=font or load_font();self.menus=menus;self.formats=[];self.producer_stacks=[];self.pending=[]
        self.root_parts=[];self.action_expected=None;self.materialized=[]
        self.templates={0x8000000+e['offset']:e for e in menus['entries'] if e['id'].startswith('root.')}
    def callback(self,event):
        a,r=event['address'],event['registers'];m=self.game.core.memory
        if a in (0x08019184,0x08019a98):
            self.pending.append((a,r[13],r[4:12],bytes(m[r[13]:r[13]+32])))
            if a==0x08019a98:self.root_parts=[]
        if a in (0x080194aa,0x08019e36):
            start,sp,regs,guard=self.pending.pop()
            require(r[13]==sp and r[4:12]==regs and bytes(m[sp:sp+32])==guard,'Menu producer damaged stack or registers')
            self.producer_stacks.append({'entry':start,'sp':sp,'callee_saved_and_guard_preserved':True})
        if a==0x08000fb8 and r[1] in self.templates:
            row=self.templates[r[1]];template=bytes.fromhex(row['encoded_hex'])
            require(template.count(b'%c')==1 and r[2] in (2,7),'Root format/color changed')
            payload=template.replace(b'%c',bytes([r[2]]))
            self.root_parts.append(payload[:-1]);self.formats.append({'id':row['id'],'color':r[2],'bytes':len(payload)})
        if a==0x08019466:
            parts=[];ids=[]
            for i in range(7):
                value=m.u16[0x0200cdd0+i*2]
                if value==0:break
                ident=value&127;ids.append(value)
                require(ident<44,'Action ID outside label table')
                if ident in ACTIONS:payload=encode(ACTIONS[ident])[:-1]
                else:
                    pointer=struct.unpack_from('<I',self.original,0x141904+ident*4)[0]-0x8000000
                    _,end=tokenize(self.original,pointer);payload=self.original[pointer:end-1]
                parts.append((b'\x03\x02'+payload+b'\x05') if value&128 else payload)
            self.action_expected=b'\r'.join(parts)+b'\0'
            require(len(self.action_expected)<=256,'Materialized action stream exceeds buffer')
            self.materialized.append({'ids':ids,'bytes':len(self.action_expected),'expected_hex':self.action_expected.hex()})
        if a==0x080021B4:
            width=m.u8[r[0]+4]*8
            if width==40 and m.u8[r[0]]==192 and m.u8[r[0]+2]==4 and r[1]<0x08000000 and self.action_expected:
                payload=self.action_expected;ident='actions'
            elif width==40 and m.u8[r[0]]==8 and m.u8[r[0]+2]==6 and self.root_parts and r[1]<0x08000000:
                payload=b''.join(self.root_parts)+b'\x03\x07'+encode(ROOT_LABELS[0x19d98][0]);ident='root'
                require(len(payload)<=64,'Materialized root stream exceeds buffer')
            else:
                if self.active is None:return
                super().callback(event);return
            self.resources[r[1]]={'id':ident,'encoded_hex':payload.hex(),'layout':{'pages':[[ident]]}}
        # TextChecks handles original Japanese action fallback as well as F0xx.
        if a in TextChecks.ADDRESSES:super().callback(event)
