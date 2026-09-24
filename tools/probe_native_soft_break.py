"""Test native 0E conditional line breaks with compact English and exact boundaries."""
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.emulator import Session,Debugger
from tools.dialogue_checks import rendered_codes,player_layout_cases
from tools.verify_service_ui import cstring
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/native-soft-break'
CONTROL=b'\x0e\x0aI'

def exact_width(width):
    choices={0:''}
    for target in range(1,width+1):
        for c in 'Wti':
            advance=measure(c)
            if target-advance in choices:
                choices[target]=choices[target-advance]+c;break
    require(width in choices,'Unrepresentable specimen width');return encode(choices[width])[:-1]

def candidate():
    import tools.build_english as english
    prior=english.add_combat;rows=[]
    def add(build):
        combat=prior(build)
        cases=[(str(total),encode('W'*21)[:-1],126,exact_width(total-126),total-126)
               for total in (210,213,214,215,216,217,224,225)]
        japanese=player_layout_cases()[-1][1][:-1]
        cases.extend([('japanese-'+str(total),japanese,98,exact_width(total-98),total-98) for total in (215,216)])
        cases.append(('coloured',encode('W'*21)[:-1],126,b'\x03\x05'+exact_width(89)+b'\x05',89))
        for label,prefix,prefix_width,suffix,suffix_width in cases:
            payload=prefix+CONTROL+suffix+b'\0';offset=build.allocate('soft-break-'+label,payload,'soft-break-probe')
            rows.append({'id':label,'offset':offset,'encoded_hex':payload.hex(),'plain_hex':(prefix+suffix+b'\0').hex(),
                         'prefix_glyphs':len(rendered_codes(prefix+b'\0')),'prefix_width':prefix_width,'suffix_width':suffix_width,
                         'expected_one_line':prefix_width+suffix_width<=215})
        return combat
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['soft_break_probes']=rows;OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

class SoftBreakCheck(CombatCheck):
    def __init__(self,game,row,guard):
        super().__init__(game,bytes.fromhex(row['encoded_hex'])[:-1],0x08025863,256,guard)
        self.row=row;self.measurements=[]
    def callback(self,event):
        a,r=event['address'],event['registers'];m=self.game.core.memory;row=self.row
        if a==0x080158CE and self.queue_abi and self.queued is None:
            require(m.u32[r[13]+12]==self.queue_return,'Soft-break queue owner differs')
            raw=cstring(m,r[6]);require(raw==self.expected_payload,'Native soft-break stream changed')
            require(bytes(m[r[6]+256:r[6]+272])==self.guard,'Soft-break output guard differs')
            widths=[row['prefix_width']+row['suffix_width']] if row['expected_one_line'] else [row['prefix_width'],row['suffix_width']]
            self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':len(widths)==1,'bytes':len(raw)+1}
            self.expected=rendered_codes(bytes.fromhex(row['plain_hex']));self.window=0x02000000
        if a==0x080020F4 and self.queued and not self.complete:
            require(len(self.draws)==row['prefix_glyphs'],'Soft break moved relative to glyphs')
            require(r[0]==224 and r[1]==row['prefix_width']+row['suffix_width']+9,
                    'Native marker/residual-width arithmetic differs')
            self.measurements.append({'frame':event['frame'],'native_width':r[0],'measured_with_marker':r[1],
                                      'line_break':r[1]>r[0]})
        super().callback(event)

def run():
    import tools.verify_player_status_prototype as status
    mgba.log.silence();rom,build=candidate();prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    results=[]
    for row in build['soft_break_probes']:
        print('Native soft break',row['id'],flush=True)
        with Session(rom,OUT/row['id']) as game:
            game.restore(fixture);m=game.core.memory;address=0x0200DF28;old=bytes(m[address:address+120]);item=bytearray(old)
            struct.pack_into('<I',item,0,0xC8000000);item[8]=bytes(m[0x020013D0:0x020014D0]).index(176)
            item[4]=item[5]=1;item[24:]=bytes(96)
            for i,v in enumerate(item):m.u8[address+i]=v
            type_address=0x02003BAC+176*20;type_before=m.u32[type_address];m.u32[type_address]=type_before|0x40000000
            checks=[];overrides=[]
            def callback(event):
                a,r=event['address'],event['registers']
                if a==0x08000FB8 and r[14]==0x0802585B:
                    require(not checks and r[0]==r[13],'Unexpected soft-break formatter')
                    overrides.append({'pc':a,'register':'r1','before':r[1],'after':row['offset']+0x08000000})
                    game.core.cpu.gprs[1]=row['offset']+0x08000000
                    checks.append(SoftBreakCheck(game,row,bytes(m[r[0]+256:r[0]+272])))
                if checks and not (checks[0].complete and checks[0].returned):checks[0].callback(event)
            with Debugger(game,callback,max_events=50000) as debug:
                for a in (0x08000FB8,0x08025862,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x080020F4):debug.breakpoint(a)
                game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                actions=[]
                for i in range(7):
                    action=m.u16[0x0200CDD0+i*2]
                    if not action:break
                    actions.append(action)
                require(13 in actions,'Native Drink action absent')
                for _ in range(actions.index(13)):game.press('DOWN',wait=20)
                game.press('A',wait=0)
                for _ in range(180):
                    if checks and checks[0].complete and checks[0].returned:break
                    game.frames(1)
                game.capture('rendered')
            require(len(checks)==1 and checks[0].complete and checks[0].returned and checks[0].measurements,
                    'Native soft-break specimen did not finish')
            check=checks[0];after=check.draws[row['prefix_glyphs']]
            require(after['x']==(row['prefix_width'] if row['expected_one_line'] else 0),'Native soft-break cursor differs')
            require(all(g['x']+g['advance']<=216 for g in check.draws),'Native soft break exceeds safe text budget')
            require(game.snapshot().battery==fixture.battery,'Soft-break probe wrote battery')
            results.append({'case':row['id'],'queue':check.queued,'measurements':check.measurements,'glyphs':len(check.draws),
                            'first_suffix_cursor':{'x':after['x'],'y':after['y']},'controlled_format':overrides,
                            'controlled_item':{'address':address,'before':old.hex(),'after':item.hex()},
                            'controlled_type':{'address':type_address,'before':type_before,'after':type_before|0x40000000},'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Rendering research only. Appended specimens replace a native item-use formatter argument in a disposable session. Native 0E skips two operand bytes; its residual measure includes the hidden I marker, whose original fullwidth glyph is9px. It therefore joins totals<=215 in the224px window and wraps216+. Exact threshold, coloured text, Japanese glyphs, pixels, guards, ABI and battery pass. No production strings or consumer code are patched by this research.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Native soft break:',len(results),'cases passed')

if __name__=='__main__':run()
