"""Bank numeric boundaries, with natural entry and explicitly controlled extremes."""
import json
import mgba.log
from tools.audit_menu_layouts import Observer
from tools.emulator import Session,Snapshot,Debugger
from tools.rom import ROOT,load_base,digest,require
from tools.review_fonts import extract

OUT=ROOT/'build/menu-resize/services'

def run():
    mgba.log.silence();rom=load_base();fixture=Snapshot.load(ROOT/'build/mansion/native/family-1-1/morning');rows=[];glyphs={}
    for name,amount in [('natural',None),('zero',0),('one',1),('maximum',99999999)]:
        with Session(rom,OUT/name) as game:
            game.restore(fixture);m=game.core.memory
            if amount is not None:
                actor=m.u32[0x02001624];m.u32[actor+0x60]=amount;m.u32[0x02002c1c]=amount
            observer=Observer(game);formats=[]
            def cb(e):
                observer.callback(e);a,r=e['address'],e['registers']
                if a==0x0801dff2:
                    dest=r[13]+4;data=bytes(m[dest:dest+384]);end=data.index(0)+1
                    require(end<=384,'Bank stream exceeds its existing stack region')
                    formats.append({'bytes':end,'capacity':384,'hex':data[:end].hex()})
            with Debugger(game,cb,max_events=20000) as debug:
                for a in observer.ADDRESSES+(0x0801dff2,):debug.breakpoint(a)
                game.press('UP',hold=8,wait=240);game.press('A',wait=240);game.press('A',wait=240);game.capture('menu')
                game.press('A',wait=240);game.capture('amount')
                game.press('B',wait=120)
            limits=[]
            for read in observer.reads:
                if read['window_width'] not in (176,112):continue
                edge=0
                for g in read['glyph_positions']:
                    if g['code'] not in glyphs:
                        v=extract(rom,g['code']);glyphs[g['code']]=max((x+1 for line in v['pixels'] for x,p in enumerate(line) if p),default=0)
                    edge=max(edge,g['x']+glyphs[g['code']])
                require(edge<=read['window_width'],'Bank native field exceeds window')
                limits.append({'window':read['window_width'],'ink_edge':edge,'text':read['text'],'raw_hex':read['raw_hex']})
            require(formats and any(x['window']==176 for x in limits),'Bank not reached')
            require(game.snapshot().battery==fixture.battery,'Bank probe wrote save')
            rows.append({'case':name,'controlled_balance':amount,'formats':formats,'limits':limits,'inputs':game.inputs,'battery_unchanged':True})
    report={'passed':True,'source_rom_sha256':digest(rom),'cases':rows,
            'bank_verb_budget':52,'bank_menu_width':176,'amount_entry_width':112,'amount_digits':8,
            'bank_balance_cap':99999999,'bank_stack_string_capacity':384,
            'scope':'Native original Japanese bank entry/cancel, plus controlled wallet/bank extremes in disposable RAM. No transaction committed; English bank/storage insertion is pending.'}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Bank budgets:',len(rows),'cases');return report
if __name__=='__main__':run()
