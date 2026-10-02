"""Execute original caller blocks in complete frames; audit every rendered glyph.

These are controlled rendering probes, not natural story/link progression.
Original source loads, formatting, callbacks, pages and modal choices execute.
Save deletion, item transfer and post-dialog progression are deliberately skipped.
"""
import argparse
import json
import re
import struct
from pathlib import Path

import mgba.log

from tools.audit_dungeon_screens import AuditedSession, save_json
from tools.emulator import Debugger, ffi
from tools.rom import ROOT, digest, require, default_rom
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_location_banner import fresh_fixture
from tools.dialogue_checks import TextChecks, rendered_codes, player_layout_cases
from tools.saved_village_checks import SavedVillageChecks
from tools.compact_font import encode
from tools.name_entry import HERO, indexed
from tools.inventory_action_text import CONTROL


def definitions():
    rows = []
    def add(name, frame, block, call, source, **kw):
        rows.append(dict(name=name, entry=frame[0], prologue=frame[1], epilogue=frame[2],
                         end=frame[3], return_register=frame[4], start=block[0], stop=block[1],
                         call=call, source=source, **kw))
    add('retry', (0x4BEC,0x4BF8,0x575E,0x576C,0), (0x564E,0x5670),0x566C,0x60A2C,choice=True,cancel_blocked=True)
    erase=(0x14780,0x1478C,0x14E4A,0x14E58,1)
    add('erase-confirm',erase,(0x14B5E,0x14B82),0x14B7E,0x5FFE8,choice=True,default_no=True,cancel_blocked=True)
    add('erase-complete',erase,(0x14B92,0x14BAA),0x14BA6,0x5FFD0,
        registers={4:3,5:512},literal_registers={7:0x14BAC,6:0x14BB4})
    add('bankers-safe',(0x1B2A8,0x1B2B4,0x1B532,0x1B540,0),(0x1B45E,0x1B488),0x1B484,0x61850)
    add('evil-floor',(0x1B548,0x1B54C,0x1B616,0x1B61C,0),(0x1B598,0x1B5BC),0x1B5B8,0x6B184,registers={3:0})
    melody=(0x1B6A0,0x1B6AC,0x1BA76,0x1BA84,0)
    add('melody',melody,(0x1B996,0x1B9BE),0x1B9BA,0x6B378)
    add('family-voices',melody,(0x1B9CC,0x1B9E8),0x1B9E4,0x6B24C,
        literal_registers={9:0x1BA90,6:0x1BA94,8:0x1BA98},registers={7:512})
    voice=(0x1C53C,0x1C548,0x1C680,0x1C68E,0)
    add('mysterious-voice',voice,(0x1C5B6,0x1C5E2),0x1C5DE,0x6AE80)
    for name,start,stop,call,source in [('child-of-man',0x1C5E2,0x1C5FE,0x1C5FA,0x6AE6C),
                                      ('inscription',0x1C610,0x1C62C,0x1C628,0x6B1D4)]:
        add(name,voice,(start,stop),call,source,literal_registers={9:0x1C668,6:0x1C66C,8:0x1C670},registers={5:512,4:0})
    add('stone-acquisition',voice,(0x1C636,0x1C644),0x1C640,0x6B1B4,
        literal_registers={9:0x1C668},actor_register=7,helper=True)
    add('shop-welcome',(0x27118,0x27122,0x2736C,0x27378,0),(0x272F0,0x27316),0x27312,0x63154,registers={7:0})
    add('locked-door',(0x4AB4C,0x4AB56,0x4B28C,0x4B298,0),(0x4ABD8,0x4ABEE),0x4ABEA,0x6C0A8,registers={4:0},layout_register=7)
    travel=(0x4B8AC,0x4B8B8,0x4BC2E,0x4BC3C,1)
    add('strong-monsters',travel,(0x4BA0C,0x4BA36),0x4BA32,0x14BCEC,registers={8:0},layout_register=9,choice=True)
    add('strong-overwrite',travel,(0x4BA3A,0x4BA52),0x4BA4E,0x14BD5D,registers={8:0,6:512},
        literal_registers={7:0x4BA68,5:0x4BA70,4:0x4BA6C},descriptor_register=4,choice=True)
    add('result-default',(0x1CA84,0x1CA90,0x1CF4C,0x1CF5A,0),(0x1CAF0,0x1CD04),0x1CD00,0x64278,
        window_jump=(0x1CAFE,0x1CCF4),registers={4:0x32})
    add('history-default',(0x56E04,0x56E10,0x5733C,0x5734A,0),(0x56EDC,0x570F4),0x570F0,0x64278,
        window_jump=(0x56EEA,0x570E4),registers={4:0x32})
    arrow=(0x2AB84,0x2AB90,0x2B108,0x2B116,0)
    add('silver-arrow-hit',arrow,(0x2AF2E,0x2AF60),0x2AF54,0x63B84,
        stack={0x18C:80,0x190:0},actor_register=6,fields=['item','actor'],capacity=256)
    add('arrow-landing',arrow,(0x2B0E2,0x2B108),0x2B0FC,0x63B38,
        stack={0x18C:78,0x190:0},fields=['item'],capacity=256)
    add('disarmed-landing',(0x2C9A0,0x2C9AC,0x2CD9A,0x2CDA8,0),(0x2CD5C,0x2CD8A),0x2CD7E,0x63B38,
        registers={4:1},stack={0x15C:0x0200DFA0},fields=['item'],capacity=256)
    add('link-success',(0x58110,0x5811C,0x5867A,0x58688,1),(0x5864E,0x58678),0x5866E,0x6ED58,
        registers={4:0x0201283C,10:0},fields=['item'],capacity=128)
    add('link-trading',(0x58110,0x5811C,0x5867A,0x58688,1),(0x58132,0x58138),0x58134,0x6ECF0)
    add('link-saving',(0x58110,0x5811C,0x5867A,0x58688,1),(0x5861A,0x58620),0x5861C,0x6ED24)
    add('identify-refusal-copy',(0x33B10,0x33B14,0x33BDA,0x33BE0,0),(0x33B8E,0x33BDA),0x33B9C,0x60600,
        fields=[],capacity=256,copy=True)
    smith=(0x1D110,0x1D122,0x1D530,0x1D542,0)
    for name,start,stop,call,index,count in [
        ('offer-two',0x1D15A,0x1D1AE,0x1D17C,61,2),
        ('offer-same',0x1D18C,0x1D1AE,0x1D1A2,62,1),
        ('accept-two',0x1D1D2,0x1D228,0x1D1F6,64,2),
        ('accept-same',0x1D204,0x1D228,0x1D21C,65,1),
        ('next-two',0x1D3B6,0x1D402,0x1D3D4,24,2),
        ('next-same',0x1D3E4,0x1D402,0x1D3F6,25,1)]:
        add('smith-'+name,smith,(start,stop),call,None,family='blacksmith',index=index,
            fields=['base-item']*count,capacity=512,bank=True,formatted_modal=True,
            registers={5:0x02002C14},recipe=True,choice=name.startswith('offer'))
    # The literal points to a definition's price (+0x0c), not its name (+0).
    # Keep this as a negative control for the raw-definition consumer audit.
    add('remi-safe-price',(0x1E75C,0x1E770,0x1F054,0x1F062,0),
        (0x1ECB4,0x1ECD2),0x1ECC6,None,family='remi',index=152,fields=['cost'],
        capacity=256,bank=True,formatted_modal=True,choice=True)
    return rows


def run(source, output, select=None, extended=False, allow_findings=False):
    mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Continuation ROM/ledger mismatch')
    fixture=fresh_fixture(rom,output/'fresh-fixture')
    from tools.bakery_playtest import service_ready
    saved_fixture=service_ready(rom,output/'bank-fixture') if not select or any(
        s['name'] in select and (s.get('bank') or s['name']=='strong-overwrite') for s in definitions()) else None
    protected={str(p):digest(p.read_bytes()) for p in (default_rom(),default_rom().with_suffix('.sav'))}
    results=[]
    variants=[]
    for spec in definitions():
        profiles=['native']
        if extended and spec.get('recipe'):profiles+=['widest-item','longest-item']
        elif extended and spec.get('fields') and not spec.get('bank'):profiles+=['maximum-width','maximum-bytes','coloured']
        if extended and spec['name']=='stone-acquisition':profiles+=['widest-English','widest-Japanese']
        if extended and spec['name']=='strong-overwrite':profiles+=['eight-English','eight-Japanese','empty','read-failure']
        variants.extend(spec|dict(profile=p) for p in profiles)
    for spec in variants:
      if select and spec['name'] not in select:continue
      for layout in ((0,2) if extended and ('layout_register' in spec or 'descriptor_register' in spec) else (0,)):
       for choice in (('yes','no','cancel') if extended and spec.get('choice') else ('yes',)):
        profile=spec['profile'];name=spec['name']+f'-{layout}-{choice}-{profile}'
        snap=saved_fixture if spec.get('bank') or spec['name']=='strong-overwrite' else fixture
        trigger=0x0801DFAC if snap is saved_fixture else 0x08015848
        with AuditedSession(rom,output/name) as g:
            g.restore(snap);m=g.core.memory;g.images=[]
            g.audit=audit=ScreenTextAudit(g)
            initial=[];returns=[];calls=[];overrides=[];waits=[];commands=[];error=None
            active=False;completed=False;format_pending=None;formats=[]
            restored=[];headers=[];produced=[];queue_checks=[];glyph_bitmaps=0;cancel_ignored=[]
            selected=next((r for r in build.get('remaining_callers',{}).get('entries',[]) if r['source']['offset']==spec['source']),None)
            if spec.get('family'):selected=next(r for r in build[spec['family']]['entries'] if r['index']==spec['index'])
            expected=selected['offset']+0x08000000 if selected else 0x08000000+spec['source']
            resources={expected:selected} if selected and not spec.get('fields') else {}
            table=build['name_entry']['glyph_table']-0x08000000
            japanese=next(i for i in range(1,185) if rom[table+i*2:table+i*2+2]==b'\x82\xb0')
            ids=(indexed('W'*8,maximum=8)[:8] if profile=='eight-English' else bytes([japanese])*8
                 if profile=='eight-Japanese' else b'\1'*8 if profile in ('empty','read-failure') else None)
            expected_name=(b''.join(rom[table+i*2:table+i*2+2] for i in ids.split(b'\1',1)[0])+b'\0') if ids else b'\0'
            panel=(SavedVillageChecks(g,resources,expected,expected_name) if selected and spec['name']=='strong-overwrite'
                   else TextChecks(g,resources))
            nameguard=bytes(m[0x0200CEFC:0x0200CF0C])
            def write(at,raw,why):
                overrides.append(dict(address=at,before=bytes(m[at:at+len(raw)]).hex(),after=raw.hex(),reason=why))
                for i,v in enumerate(raw):m.u8[at+i]=v
            def reg(e,i,v):
                overrides.append(dict(event=e,register=i,after=v,reason='Original basic-block live input'))
                g.core.cpu.gprs[i]=v if v<0x80000000 else v-0x100000000
            def jump(e,at,why):
                overrides.append(dict(event=e,pc_after=at+0x08000000,reason=why))
                require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Probe redirect failed')
            # Trigger Drink by ordinary buttons; a separate item supplies fields.
            for slot,ident in ([] if saved_fixture is snap else [(0,177),(1,30)]):
                item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1'
                item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident)
                write(0x0200DF28+120*slot,item,'Controlled known item in disposable inventory')
                at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000),'Known item flag; no inscription bit')
            if spec['name']=='link-success':
                # External item record uses the native reverse mapping (F6D8).
                external=bytearray(m[0x0200DFA0:0x0200DFA0+120]);external[8]=30
                write(0x0201283C,external,'Controlled received link record; transfer/save skipped')
            hero=m.u32[0x02001624]
            def cb(e):
                nonlocal active,completed,format_pending,expected_name,glyph_bitmaps
                a,r=e['address'],e['registers']
                if a==trigger and not initial:
                    initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                    if spec.get('bank'):reg(e,1,0)
                    jump(e,spec['entry'],'Controlled Drink/bank dispatch into complete original caller frame');return
                if active:audit.callback(e)
                if not initial or returns:return
                if a==spec['prologue']+0x08000000:
                    active=True
                    for i,v in spec.get('registers',{}).items():reg(e,i,v)
                    for i,at in spec.get('literal_registers',{}).items():reg(e,i,m.u32[at+0x08000000])
                    if 'layout_register' in spec:reg(e,spec['layout_register'],layout)
                    if 'descriptor_register' in spec:
                        i=spec['descriptor_register'];reg(e,i,m.u32[spec['literal_registers'][i]+0x08000000]+8*layout)
                    if 'actor_register' in spec:reg(e,spec['actor_register'],hero)
                    if spec['name']=='stone-acquisition' and profile!='native':
                        raw=dict(player_layout_cases())[profile];write(HERO,raw.ljust(16,b'\0'),'Player-name width boundary')
                    for off,v in spec.get('stack',{}).items():write(r[13]+off,struct.pack('<I',v),'Original local block input')
                    if spec.get('recipe'):
                        from tools.compact_font import measure
                        names=[x for x in build['items']['entries'] if x['id'].startswith('item.name.')]
                        ident=2 if profile=='native' else int(max(names,key=lambda x:
                            measure(x['english']) if profile=='widest-item' else len(encode(x['english'])))['id'].split('.')[-1])
                        pair=bytes([ident,3 if profile=='native' and len(spec['fields'])==2 else ident])
                        write(0x02002C14,pair,'Controlled recipe IDs; original name producer reads compiled item definitions')
                        reg(e,0,ident)
                    jump(e,spec['start'],'Execute original source loads/message block; preceding world/save effects excluded')
                if spec.get('window_jump') and a==spec['window_jump'][0]+0x08000000:
                    jump(e,spec['window_jump'][1],'Original window created; explicit defensive default selector 0x32')
                if a==spec['call']+0x08000000:
                    pointer=r[1] if spec.get('fields') or spec.get('window_jump') or spec.get('helper') or spec.get('copy') else r[0]
                    require(pointer==expected,'Caller source differs: '+repr((name,hex(pointer),hex(expected))))
                    calls.append(e|dict(source=pointer))
                    if spec.get('fields') or spec.get('copy'):
                        from tools.verify_service_ui import materialize
                        args=list(r[2:4])
                        if spec.get('fields') and profile!='native' and not spec.get('bank'):
                            for i,role in enumerate(spec['fields']):
                                field=(encode('W'*(31 if role=='actor' else 27)) if profile=='maximum-width' else
                                       encode('i'*31) if profile=='maximum-bytes' else
                                       b'\x03\x05'+encode('Torneko' if role=='actor' else 'Oaken club')[:-1]+b'\x05\0')
                                dest=(0x02008D08 if role=='actor' else r[13]+0x110
                                      if spec['name'] in ('silver-arrow-hit','arrow-landing') else args[i])
                                require(len(field)<=64 and (role=='actor' or r[13]<=dest<r[13]+0x1C4),'Field scratch outside original frame')
                                previous=bytes(m[dest:dest+len(field)]);restored.append((dest,field,previous))
                                write(dest,field,'Formatter-only boundary in existing actor scratch or owned caller local; restored at return')
                                args[i]=dest;reg(e,i+2,dest)
                        raw=bytes.fromhex(audit.stream(pointer,e)['raw_hex'])
                        expanded=materialize(raw,args,m);capacity=spec['capacity']
                        require(len(expanded)<=capacity,'Caller expansion exceeds native capacity')
                        format_pending=dict(output=r[0],expected=expanded.hex(),capacity=capacity,
                            guard=bytes(m[r[0]+capacity:r[0]+capacity+16]).hex(),registers=r)
                if format_pending and a==spec['call']+0x08000004:
                    f=format_pending;dest=f['output'];raw=bytes.fromhex(f['expected']);cap=f['capacity']
                    require(bytes(m[dest:dest+len(raw)])==raw and bytes(m[dest+cap:dest+cap+16]).hex()==f['guard']
                        and r[4:12]==f['registers'][4:12] and r[13]==f['registers'][13],'Caller formatter bytes/guard/ABI differs')
                    formats.append(f);format_pending=None
                    if selected and (spec['name']=='link-success' or spec.get('formatted_modal')):
                        panel.resources[dest]=selected|dict(encoded_hex=raw.hex())
                    for at,field,previous in restored:
                        require(bytes(m[at:at+len(field)])==field,'Formatter changed its field')
                        write(at,previous,'Restore controlled formatter field')
                    restored.clear()
                if selected and spec['name']=='strong-overwrite':
                    if a==0x0801FAC8:
                        before=bytes(m[r[13]+20:r[13]+28]);headers.append(e|dict(ids_hex=before.hex()))
                        if profile=='native':
                            native=before.split(b'\1',1)[0] if r[0]==0 else b''
                            expected_name=b''.join(rom[table+i*2:table+i*2+2] for i in native)+b'\0'
                        elif profile=='read-failure':reg(e,0,0xFFFFFFFF)
                        else:
                            require(r[0]==0,'Saved header unavailable for name profile')
                            write(r[13]+20,ids,'Decoded eight-cell saved-name boundary; no battery write')
                        panel.name=expected_name
                        if panel.active:
                            expanded=bytes.fromhex(selected['encoded_hex']).replace(b'\x1f',expected_name[:-1])
                            panel.active['expected']=rendered_codes(expanded,bytes(m[HERO:HERO+16]))
                            panel.active['expected_colors']=rendered_codes(expanded,bytes(m[HERO:HERO+16]),m.u8[0x020000C2],m.u8[0x020000C3])
                    if a==0x0801FB12:
                        require(bytes(m[0x0200CEE8:0x0200CEFC])==expected_name.ljust(20,b'\0') and bytes(m[0x0200CEFC:0x0200CF0C])==nameguard,'Saved name output/guard differs')
                        produced.append(e)
                if active and a in panel.ADDRESSES:panel.callback(e)
                if active and a==0x08001C14 and audit.pending:
                    glyph,at=audit.metrics.glyph_record(r[4]);context=bytes(m[r[5]:r[5]+24]);foreground=m.u8[0x020000C2]
                    require(r[0]==at,'Draw selected wrong glyph bitmap')
                    background=4 if context[9]&1 else 7
                    bitmap=bytes(foreground if bit=='#' else (7 if y<2 else background) for y,line in enumerate(glyph['rows']) for bit in line)
                    bitmap+=bytes([background])*glyph['advance']
                    require(bytes(m[0x02036430:0x02036430+len(bitmap)])==bitmap,'Native glyph pixels differ')
                    glyph_bitmaps+=1
                if a==0x080023A0:waits.append(e)
                if a==0x0801B674:commands.append(e|dict(command=bytes(m[r[0]:r[0]+3]).decode('ascii')))
                if spec.get('helper'):
                    if a==0x0801C962:
                        reg(e,4,0);jump(e,0x1C9FC,'Original relic helper frame/source; animation and item effects excluded')
                    if a==0x0801CA1E:jump(e,0x1CA34,'Return via complete original relic helper epilogue')
                if a==spec['stop']+0x08000000:
                    completed=True
                    if spec.get('choice'):require(r[0]==int(choice=='yes'),'Native choice result differs')
                    jump(e,spec['epilogue'],'Original message completed; post-message world/save effects excluded')
                if a==spec['end']+0x08000000:
                    old=initial[0]['registers']
                    require(r[4:12]==old[4:12] and r[13]==old[13] and r[spec['return_register']]==old[14]
                        and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Caller frame/guard/ABI differs')
                    returns.append(e)
            extra={trigger,0x080023A0,0x0801B674,0x0801FAC8,0x0801FB12}|{0x08000000+spec[k] for k in ('prologue','end','stop','call')}
            extra.add(spec['call']+0x08000004)
            if spec.get('window_jump'):extra.add(spec['window_jump'][0]+0x08000000)
            if spec.get('helper'):extra|={0x0801C962,0x0801CA1E}
            with Debugger(g,cb,max_events=250000) as d:
                for a in set(audit.ADDRESSES)|set(panel.ADDRESSES)|extra:d.breakpoint(a)
                try:
                    if trigger==0x08015848:
                        g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                        actions=[]
                        for i in range(7):
                            n=m.u16[0x0200CDD0+2*i]
                            if not n:break
                            actions.append(n)
                        require(13 in actions,'Drink trigger missing')
                        for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                    g.press('A',hold=1,wait=0);handled=set()
                    for tick in range(4000):
                        if returns:break
                        state=(len(waits),len(audit.observer.reads),bool(audit.observer.stack))
                        if calls and (waits or audit.observer.reads) and state not in handled and (not audit.observer.stack or len(waits)>len([s for s in handled if s[2]])):
                            g.frames(8);g.capture('page-'+str(len(handled)));handled.add(state)
                            if not audit.observer.stack and spec.get('choice'):
                                if choice=='no' and not spec.get('default_no'):g.press('RIGHT',hold=1,wait=15)
                                if choice=='yes' and spec.get('default_no'):g.press('LEFT',hold=1,wait=15)
                                if choice=='cancel' and spec.get('cancel_blocked'):
                                    g.press('B',hold=1,wait=30);require(not returns,'Confirmation unexpectedly accepts B')
                                    cancel_ignored.append(dict(frame=g.core.frame_counter,subsequent_answer='No'))
                                    if not spec.get('default_no'):g.press('RIGHT',hold=1,wait=15)
                                    g.press('A',hold=1,wait=0);continue
                            g.press('B' if not audit.observer.stack and choice=='cancel' else 'A',hold=1,wait=0)
                        else:g.frames(1)
                    require(len(initial)==len(returns)==len(calls)==1 and completed and not format_pending,
                            'Incomplete original block: '+repr((name,len(initial),len(calls),len(returns),len(audit.observer.reads),len(waits))))
                    g.frames(160)
                    if selected:
                        if spec.get('fields') and spec['name']!='link-success' and not spec.get('formatted_modal'):
                            expected_codes=rendered_codes(bytes.fromhex(formats[-1]['expected']).replace(CONTROL,b''),bytes(m[HERO:HERO+16]))
                            observed=[q for q in audit.final_queues if q['caller']==spec['stop']+0x08000001]
                            require(len(observed)==1 and observed[0]['drawn_codes']==expected_codes,'Queue glyph sequence differs')
                            queue_checks.append(dict(caller=observed[0]['caller'],glyphs=len(expected_codes),exact_sequence=True))
                        else:
                            require(len(panel.reads)==1 and not panel.active,'English reader check incomplete')
                        if spec['name']=='family-voices':
                            expected_commands=re.findall(b'@[wW]@',bytes.fromhex(selected['source']['raw_hex']))
                            require([c['command'].encode() for c in commands]==expected_commands,'Family callback sequence differs')
                except Exception as exc:error=str(exc)+((': '+str(exc.__cause__)) if exc.__cause__ else '')
            g.capture('result')
            result=dict(case=name,spec=spec,rom_sha256=digest(rom),fixture_state_sha256=digest(snap.state),
                route_error=error,inputs=g.inputs,overrides=overrides,calls=calls,returns=returns,formats_checked=formats,
                commands=commands,page_waits=waits,images=g.images,battery_unchanged=g.snapshot().battery==snap.battery,**audit.report())
            result.update(text_checks=panel.reads,queue_checks=queue_checks,glyph_bitmaps_checked=glyph_bitmaps,
                          name_headers=headers,name_outputs=produced,expected_saved_name_hex=expected_name.hex(),cancel_ignored=cancel_ignored)
            result['confirmed_japanese_output']=error is None and bool(audit.unclassified)
            result['english_output']=error is None and bool(audit.glyphs) and result['battery_unchanged'] and not (audit.unclassified or audit.unreadable or audit.layout_violations)
            save_json(g.output/'report.json',result);results.append(result)
            print(name,'JAPANESE' if result['confirmed_japanese_output'] else 'ENGLISH' if result['english_output'] else 'INCOMPLETE',error,flush=True)
    require(all(digest(Path(p).read_bytes())==h for p,h in protected.items()),'Source ROM/save changed')
    report=dict(rom_sha256=digest(rom),cases=results,source_hashes=protected,tool_sha256=digest(Path(__file__).read_bytes()),
        passed=all(r['english_output'] for r in results),scope=__doc__)
    save_json(output/'report.json',report)
    require(allow_findings or report['passed'],'Caller continuation has unresolved findings')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'build/english')
    p.add_argument('--output',type=Path,default=ROOT/'build/caller-continuation/native')
    p.add_argument('--case',action='append');p.add_argument('--extended',action='store_true')
    p.add_argument('--allow-findings',action='store_true');a=p.parse_args()
    run(a.source,a.output,a.case,a.extended,a.allow_findings)
