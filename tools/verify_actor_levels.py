"""Native name getter at level extremes, with its existing 64-byte scratch guard."""
import argparse,json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.combat_fixtures import create
from tools.compact_font import encode
from tools.verify_service_ui import cstring

def run(cumulative=False):
 mgba.log.silence();root=ROOT/('build/english/combat-validation' if cumulative else 'build/combat-prototype');base=root.parent if cumulative else root
 rom=(base/('torneko-2-english.gba' if cumulative else 'game.gba')).read_bytes();build=json.loads((base/'build.json').read_text());create(rom,build,root);fixture=Snapshot.load(root/'native/actor-getter');results=[];names={r['id']:r for r in build['monsters']['entries']}
 for ident in (21,96,99,128):
  for level in (1,2,32767):
   with Session(rom,root/'levels'/f'{ident}-{level}') as g:
    g.restore(fixture);m=g.core.memory;r=g.core.cpu.gprs;actor=int(r[0]);m.u8[actor+0x91]=ident;m.u16[actor+0x88]=level
    before=[int(r[i])&0xffffffff for i in range(4,12)];sp=int(r[13]);ret=int(r[14])&~1;guard=bytes(m[0x02008d48:0x02008d68]);observed=[]
    expected=encode(names[ident]['english']) if level==1 else encode(names[ident]['english']+' Lv')[:-1]+str(level).encode()+b'\0'
    def cb(e):
     regs=e['registers'];actual=cstring(m,regs[0])+b'\0'
     require(actual==expected,'Actor level/name differs from native record')
     require(regs[4:12]==before and regs[13]==sp,'Actor getter changed registers/SP')
     require(bytes(m[0x02008d48:0x02008d68])==guard and len(actual)<=64,'Actor level scratch guard changed')
     observed.append({'pointer':regs[0],'encoded_hex':actual.hex(),'bytes':len(actual)})
    with Debugger(g,cb,max_events=1000) as d:
     d.breakpoint(ret);d.run_until(lambda _:bool(observed))
    results.append({'id':ident,'level':level,'getter':observed[0],'controlled_actor_fields':['type byte +0x91','level halfword +0x88'],'stack_and_scratch_guard_preserved':True})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native getter arguments on a naturally reached visible enemy. Four names at levels 1, 2 and maximum positive signed16. Existing 64-byte name scratch only; no new RAM.'}
 (root/'actor-levels.json').write_text(json.dumps(report,indent=2)+'\n');print('Actor level cases:',len(results));return report
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
