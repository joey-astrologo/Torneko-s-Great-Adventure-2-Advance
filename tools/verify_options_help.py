"""Every Option/Controls mode, with fixed rows and native close/reopen behaviour."""
import argparse,json
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.verify_service_ui import UiChecks


def run(source=ROOT/'build/options-help-prototype'):
    out=source/'options-help-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale options-help ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    results=[]
    for mode in range(4):
        name=('merchant','warrior','mage','town')[mode];print('Options help:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;c=UiChecks(g,build['ui']);initial=[];returns=[];draws=[];images={};overrides=[];creations=[];pixels=0
            expected=[];table=0x6B736+16*mode
            by_pointer={p:r['id'] for r in build['ui']['entries'] for p in r['pointers']}
            for i in range(8):
                slot=int.from_bytes(rom[table+2*i:table+2*i+2],'little')*4
                if slot:expected.append(by_pointer[0x140D68+slot])
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x0801A794 and not initial:
                    require(r[1]==0,'Expected normal dungeon Option entry')
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    if mode<3:
                        address=m.u32[0x02001624]+0x90;overrides.append({'address':address,'before':m.u8[address],'after':mode});m.u8[address]=mode
                    else:
                        overrides.append({'event':e,'r1_after':1});g.core.cpu.gprs[1]=1
                if a==0x08001798:creations.append(e)
                if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                c.callback(e)
                if a==0x0801AAE8 and initial:
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Options caller ABI/guard differs');returns.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'No option/help glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Options final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=150000) as debug:
                for a in set(c.ADDRESSES+(0x0801A794,0x0801AAE8,0x08001798,0x08001750,0x08001888)):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('DOWN',wait=30);g.press('DOWN',wait=30);g.press('A',wait=120);capture('options')
                for repeat in range(2):
                    first=len(c.reads);g.press('A',wait=120);capture('help-'+str(repeat))
                    require([r['id'] for r in c.reads[first:]]==expected,'Options help mode/order differs')
                    require(creations[-1]['registers'][:4]==[1,3,28,8],'Help window geometry differs')
                    g.press('B',wait=120);capture('reopened-'+str(repeat))
                g.press('B',wait=120)
            require(len(initial)==len(returns)==1 and not c.active and not c.pending and g.snapshot().battery==fixture.battery,'Options close/reopen/save check incomplete')
            results.append({'case':name,'mode':mode,'expected_ids':expected,'reads':c.reads,'formats':c.formats,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'return':returns[0],'caller_guard_abi_preserved':True,'images':images})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Ordinary dungeon root navigation enters Option. Existing vocation byte or root town-mode argument is controlled only at entry. All four unchanged native help selectors display their original ordered rows in the224px/eight-row window. Full coloured final pixels, original36-byte option output guards, twice opening/cancelling/reopening, caller ABI and unchanged battery pass. Ordinary vocation unlocking and town entry are separately unverified.'},indent=2)+'\n');print('Options help:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/options-help-prototype');a=p.parse_args();run(a.source)
