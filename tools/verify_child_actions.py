"""Contained-item action producer: checked frame, native selection and labels."""
import argparse,json,struct,tempfile
from contextlib import contextmanager
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.emulator import Session,Snapshot,Debugger
from tools.menu_checks import MenuChecks
from tools.audit_menu_layouts import Observer,parent_image
import tools.menu_text as menus

OUT=ROOT/'build/child-actions-prototype'
CATALOG=ROOT/'translations/additional-actions-review.json'

from tools.verify_additional_actions import reviewed_actions
from tools.child_action_text import add_child_actions

class ChildChecks(MenuChecks):
    ADDRESSES=MenuChecks.ADDRESSES+(0x080194C0,0x080196F4,0x080196B2)
    def callback(self,event):
        a,r=event['address'],event['registers'];m=self.game.core.memory
        if a==0x080194C0:
            self.pending.append((a,r[13],r[4:12],bytes(m[r[13]:r[13]+32])))
        if a==0x080196F4:
            start,sp,regs,guard=self.pending.pop()
            require(start==0x080194C0 and r[13]==sp and r[4:12]==regs and bytes(m[sp:sp+32])==guard,'Child producer damaged ABI/guard')
            self.producer_stacks.append({'entry':start,'sp':sp,'callee_saved_and_guard_preserved':True})
        if a==0x080196B2:event=dict(event,address=0x08019466)
        super().callback(event)

def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/child-action-validation'
    from tools.build_english import build_rom
    mgba.log.silence();OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    with reviewed_actions() as catalog:
        if cumulative:
            rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes();build=json.loads((ROOT/'build/english/build.json').read_text())
            require(digest(rom)==build['output_sha256'],'Child action ROM differs')
        else:
            import tools.build_english as english
            prior=english.add_combat;child=None
            def add(build):
                nonlocal child
                result=prior(build);child=add_child_actions(build);return result
            try:english.add_combat=add;rom,build=build_rom(include_story=False,include_extra_consumers=False)
            finally:english.add_combat=prior
            build['child_actions']=child
        (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
        (OUT/'combined-review.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
        import tools.verify_player_status_prototype as status
        prior=status.OUT
        try:status.OUT=OUT;fixture=status.ready(rom,build)
        finally:status.OUT=prior
        original=load_base();require(rom[0x141904:0x1419B4]==original[0x141904:0x1419B4],'Shared action table changed')
        ids=sorted(menus.ACTIONS);require(len(ids)==39,'Nonempty action set differs')
        for disabled in (False,True):
            for start in range(0,len(ids),7):
                group=ids[start:start+7];values=[i+(128 if disabled else 0) for i in group]
                name=f'group-{start//7+1}-'+('disabled' if disabled else 'enabled')
                with Session(rom,OUT/name) as game:
                    print('Action labels:',name,flush=True);game.restore(fixture);m=game.core.memory
                    checks=ChildChecks(game,build['menus']);observer=Observer(game);overrides=[]
                    def callback(event):
                        if event['address']==0x0801962C:
                            before=bytes(m[0x0200CDD0:0x0200CDDE]);after=struct.pack('<7H',*(values+[0]*(7-len(values))))
                            for i,b in enumerate(after):m.u8[0x0200CDD0+i]=b
                            overrides.append({'address':0x0200CDD0,'before':before.hex(),'after':after.hex(),'frame':event['frame']})
                        observer.callback(event);checks.callback(event)
                    with Debugger(game,callback,max_events=90000) as debug:
                        for a in set(checks.ADDRESSES+observer.ADDRESSES+(0x0801962C,)):debug.breakpoint(a)
                        slot=0x0200DF28;before=bytes(m[slot:slot+120]);mapping=bytes(m[0x020013D0:0x020014D0])
                        pot=bytearray(120);struct.pack_into('<I',pot,0,0xC8000000);pot[4]=7;pot[5]=1;pot[8]=mapping.index(154)
                        struct.pack_into('<I',pot,24,0xC8000000);pot[28]=pot[29]=1;pot[32]=mapping.index(1)
                        for i,b in enumerate(pot):m.u8[slot+i]=b
                        overrides.append({'address':slot,'before':before.hex(),'after':pot.hex()})
                        for ident in (1,154):
                            address=0x02003BAC+20*ident;before_type=m.u32[address];m.u32[address]=before_type|0x40000000
                            overrides.append({'address':address,'before':before_type,'after':m.u32[address]})
                        game.press('B',hold=8,wait=120);game.press('A',wait=120);game.press('A',wait=120)
                        actions=checks.materialized[-1]['ids'];require(42 in actions,'View action missing')
                        for _ in range(actions.index(42)):game.press('DOWN',wait=20)
                        game.press('A',wait=120);parent=parent_image(game)
                        inventory=bytes(m[0x0200DF28:0x0200DF28+20*120])
                        for cycle in range(3):
                            game.press('A',wait=120);game.capture(f'open-{cycle}')
                            require(checks.materialized[-1]['ids']==values,'Action IDs changed')
                            for _ in group:game.press('DOWN',wait=20)
                            if disabled:
                                game.press('A',wait=60)
                                require(m.u32[0x0200CD20]!=0,'Disabled action unexpectedly closed menu')
                            game.press('B',wait=120)
                            require(parent_image(game)==parent,'Action cancellation changed parent pixels')
                        game.capture('restored')
                        require(bytes(m[0x0200DF28:0x0200DF28+20*120])==inventory,'Label selection changed inventory')
                    require(len(overrides)==6 and len(checks.materialized)==4 and not checks.active,'Action checks incomplete')
                    reads=[r for r in observer.reads if r['raw_hex']==checks.materialized[-1]['expected_hex']]
                    require(len(reads)==3 and all(r['initial_x']==4 and r['screen_x']==192 and r['window_width']==40 for r in reads),f'Action geometry changed: {[(r["initial_x"],r["rows"],r["source"]) for r in reads]}')
                    require(game.snapshot().battery==fixture.battery,'Action label probe wrote battery')
                    results.append({'case':name,'ids':values,'controlled_overrides':overrides,'materialized':checks.materialized,
                                    'reads':reads,'glyph_checks':checks.glyph_checks,'producer_checks':checks.producer_stacks,
                                    'parent':parent,'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'catalog_sha256':digest(CATALOG.read_bytes()),
            'scope':'Contained-item producer: all39 owned action IDs1..43 (excluding empty/null slots; separate discard ID44 is outside this private copy), enabled and disabled in controlled groups of at most seven. Three open/cancel cycles, cursor inputs, native glyph pixels, original geometry, parent restoration, buffers/registers and unchanged inventory/battery. Synthetic action availability; enabled actions are not executed. Original shared table and other consumers remain Japanese.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Contained action labels:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
