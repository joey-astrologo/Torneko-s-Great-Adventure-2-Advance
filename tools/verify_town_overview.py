"""Native town overview setup, computed labels, navigation and repeated redraws."""
import argparse
import json
from pathlib import Path
import struct

import mgba.log

from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.emulator import Session, Debugger
from tools.rom import ROOT, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit


def run(source):
    mgba.log.silence()
    original=load_base();rom=(source/'torneko-2-english.gba').read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'], 'Overview ROM differs')
    out=source/'town-overview-validation';fixture=service_ready(rom,out/'fixture')
    rows={r['index']:r for r in build['town_overview']['entries']}
    resources={r['offset']+0x08000000:r|dict(layout=dict(pages=[[r['english']]])) for r in rows.values()}
    word=lambda at:struct.unpack_from('<I',original,at)[0]
    selector,refresh=word(0x51FB4),word(0x51F40)
    cases=[];images={};restorations=[]
    for index,row in rows.items():
        print('Town overview:',index,row['english'],flush=True)
        with Session(rom,out/str(index)) as g:
            g.restore(fixture);m=g.core.memory
            audit=ScreenTextAudit(g);checks=TextChecks(g,resources)
            controls=[];activation=[];entries=[];returns=[];closes=[];selections=[];navigation=[]
            activated=False;selected=False;pending=None;current_draws=[];draws=[]
            pending_button=None;restore_button=None
            inventory=bytes(m[0x0200DF28:0x0200E888])
            def write(at,raw,reason):
                controls.append(dict(address=at,before=bytes(m[at:at+len(raw)]).hex(),after=raw.hex(),reason=reason))
                for i,v in enumerate(raw):m.u8[at+i]=v
            def callback(e):
                nonlocal activated,selected,pending,pending_button,restore_button
                a,r=e['address'],e['registers']
                audit.callback(e);checks.callback(e)
                if a==0x0804E7C0 and not activated:
                    write(0x0201020C,struct.pack('<I',(m.u32[0x0201020C]&~0x07800000)|0x00800000),
                          'Select original overview activation state; mode2 is native fixture state')
                    require(m.u8[0x02010210]==2,'Original overview activation mode differs');activated=True
                if a in (0x08051B98,0x08051C70) and a not in [x['address'] for x in activation]:activation.append(e)
                if a==0x08051E4C:
                    require(pending is None,'Overview callback reentered')
                    pending=e|dict(guard=bytes(m[r[13]:r[13]+32]).hex());entries.append(pending)
                    if not selected:
                        write(selector,bytes([index]),'Controlled existing overview selection')
                        write(refresh,struct.pack('<I',1),'Request native label redraw');selected=True
                    if pending_button is not None:
                        restore_button=bytes(m[0x0200884C:0x0200884E])
                        write(0x0200884C,struct.pack('<H',pending_button),
                              'Controlled key state for this complete overview callback only; isolate unrelated town movement')
                        pending_button=None
                if a==0x0805202C and pending:
                    old=pending['registers']
                    require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14]
                            and bytes(m[r[13]:r[13]+32]).hex()==pending['guard'], 'Overview callback ABI/guard differs')
                    returns.append(e);pending=None
                    if restore_button is not None:
                        write(0x0200884C,restore_button,'Restore key state at overview callback return')
                        restore_button=None
                if a==0x08001888 and selected:closes.append(e)
                if a==0x08051F86:
                    require(m.u8[selector] in rows and r[1]==rows[m.u8[selector]]['offset']+0x08000000,
                            'Overview computed source differs')
                    w=rows[m.u8[selector]]['window']
                    require(bytes(m[r[0]:r[0]+2])==bytes([w[0]*8,w[1]*8])
                            and bytes(m[r[0]+4:r[0]+6])==bytes(w[2:]),'Overview actual geometry differs')
                    current_draws.clear()
                if a==0x08001BC4 and checks.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not current_draws or current_draws[-1]['key']!=key:
                        current_draws.append(dict(key=key,code=r[1],x=m.u8[w+2],y=m.u8[w+3],
                          origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
                if a==0x08051F32:
                    actual=m.u32[word(0x51EF8)];expected=struct.unpack_from('<h',original,word(0x51EFC)-0x08000000+2*m.u8[selector])[0]&0xffffffff
                    require(actual==expected,'Overview destination selection differs');selections.append(dict(actual=actual,expected=expected))
            def capture(label):
                require(checks.active is None and current_draws,'Overview draw incomplete')
                pic=g.capture(label);width=rows[m.u8[selector]]['text_width'];w=rows[m.u8[selector]]['window'];x=(w[2]*8-width)//2
                require(current_draws[0]['x']==x,'Overview native centring differs')
                pixels=0
                for d in current_draws:
                    glyph,_=checks.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])]
                    rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for i,bit in enumerate(line):
                            require((pic.getpixel((d['origin'][0]+d['x']+i,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),
                                    'Overview visible glyph pixels differ');pixels+=1
                draws.append(dict(label=label,selector=m.u8[selector],pixels=pixels))
                return pic
            with Debugger(g,callback,max_events=500000) as d:
                for a in set(audit.ADDRESSES+checks.ADDRESSES+(0x0804E7C0,0x08051B98,0x08051C70,
                    0x08051E4C,0x0805202C,0x08001888,0x08051F86,0x08051F32)):d.breakpoint(a)
                g.frames(180);first=capture('opened');images[index]=first
                box=(row['window'][0]*8,row['window'][1]*8,(row['window'][0]+row['window'][2])*8,row['window'][1]*8+16)
                for cycle in range(2):
                    write(refresh,struct.pack('<I',1),'Repeat native window destruction/recreation')
                    g.frames(30);reopened=capture('reopened-'+str(cycle))
                    require(first.crop(box).tobytes()==reopened.crop(box).tobytes(),'Overview label changed after reopening')
                # Scope input to this callback: the controlled map activation
                # has not suspended the fixture's separate town movement task.
                for key,column,mask in [('DOWN',0,0x80),('RIGHT',1,0x10),('UP',2,0x40),('LEFT',3,0x20)]:
                    write(selector,bytes([index]),'Reset selection for independent direction check')
                    write(refresh,struct.pack('<I',1),'Redraw direction starting point')
                    g.frames(30)
                    before=m.u8[selector];target=original[word(0x51EE8)-0x08000000+4*before+column]
                    if target>=12:
                        navigation.append(dict(key=key,target=target,scope='Separate travel-exit handler, outside nine label selectors'))
                        continue
                    pending_button=mask;g.frames(30)
                    require(pending_button is None and restore_button is None,'Overview controlled key was not consumed/restored')
                    if 0<target<12:require(m.u8[selector]==target,'Native overview navigation differs')
                    pic=capture('navigation-'+key)
                    navigation.append(dict(key=key,target=target,observed=m.u8[selector],passed=True))
                    restorations.append((index,m.u8[selector],key,pic))
                # Restore only the selector, then the original A branch computes
                # and returns the destination. Stop before following town travel.
                write(selector,bytes([index]),'Restore selection for native A destination check')
                write(refresh,struct.pack('<I',1),'Redraw restored selection')
                g.frames(30);capture('restored')
                pending_button=1
                for _ in range(30):
                    if selections:break
                    g.frames(1)
                require(selections and len(activation)==2 and len(closes)>=3 and len(returns)>=3,
                        'Overview setup/reopen/selection route incomplete')
                require(pending is None and pending_button is None and restore_button is None,
                        'Overview callback/key restoration incomplete')
            r=audit.report()
            require(not r['unclassified_glyphs'] and not r['unreadable_streams'] and not r['layout_violations'],
                    'Overview screen has unclassified text/layout findings')
            require(bytes(m[0x0200DF28:0x0200E888])==inventory and g.snapshot().battery==fixture.battery,
                    'Overview altered inventory/battery')
            cases.append(dict(index=index,english=row['english'],inputs=g.inputs,controls=controls,
                setup=activation,callback_returns=len(returns),callback_abi_preserved=True,navigation=navigation,
                window_closures=len(closes),native_selection=selections,draws=draws,checks=checks.reads,
                audit=r,images={p.name:digest(p.read_bytes()) for p in g.output.glob('*.png')}))
    # Compare vacated label rectangles with independent native captures of the
    # new selection, including the old border and any newly exposed width.
    restored=[]
    for before,after,key,pic in restorations:
        if before==after:continue
        old,new=rows[before]['window'],rows[after]['window']
        bounds=lambda w:(w[0]*8-2,w[1]*8-2,(w[0]+w[2])*8+2,w[1]*8+18)
        x0,y0,x1,y1=bounds(old);a,b,c,d=bounds(new);pixels=0
        for y in range(y0,min(y1,160)):
            for x in range(x0,min(x1,240)):
                if a<=x<c and b<=y<d:continue
                require(pic.getpixel((x,y))==images[after].getpixel((x,y)),
                        'Overview vacated panel/background differs: '+repr((before,after,key,x,y)))
                pixels+=1
        restored.append(dict(before=before,after=after,key=key,background_pixels=pixels))
    report=dict(passed=True,rom_sha256=digest(rom),cases=cases,
        background_restoration=restored,
        tool_sha256=digest(Path(__file__).read_bytes()),audit_tool_sha256=digest((ROOT/'tools/screen_text_audit.py').read_bytes()),
        scope='Controlled existing activation/selection/refresh RAM and key masks scoped to the complete overview callback; original key bytes restored at return. No PC/register/source substitutions. Nine labels, all in-table direction inputs, native A destination IDs, exact centre/pixels, repeated native window destruction/recreation, vacated background comparison, callback guards/ABI, unchanged inventory/save. Directions to separate travel-exit selectors are enumerated but not executed. Four standalone windows widen toward the screen interior, retaining8px screen margins. This isolates the fixture\'s still-active separate town movement task. Natural story activation and subsequent travel remain separate.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Town overview:',len(cases),'passed',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english')
    run(p.parse_args().source)
