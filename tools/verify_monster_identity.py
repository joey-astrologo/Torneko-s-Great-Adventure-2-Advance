"""Full original already-known monster handler: exact format, no display."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.compact_font import encode
from tools.verify_result_ui import native_format
from tools import verify_player_status_prototype as status

def run(source):
 rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Monster identity ROM differs');row=b['monster_identity']['entries'][0];out=source/'monster-identity-validation';mgba.log.silence();prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,b)
 finally:status.OUT=prior
 cases=[]
 # Every native definition at the ordinary level, maximum signed16-bit level on the
 # widest name, and synthetic64-byte-field boundaries used by other consumers.
 widest=max(b['monsters']['entries'],key=lambda r:r['width_px'])['id']
 cohort=[(i,1,'native') for i in range(141)]+[(widest,32767,'native')]+[(1,1,k) for k in ('maximum-width','maximum-bytes','coloured')]
 for species,level,kind in cohort:
  name=f'{species}-{level}-{kind}';print('Monster identity:',name,flush=True)
  with Session(rom,out/name) as g:
   g.restore(fixture);m=g.core.memory;cpu=g.core.cpu;overrides=[];formats=[];finished=[];pending={};queue=[]
   def write(a,data,reason):
    require(0x02000000<=a and a+len(data)<=0x04000000,'Probe outside existing RAM');overrides.append(dict(address=a,before=bytes(m[a:a+len(data)]).hex(),after=data.hex(),reason=reason))
    for i,v in enumerate(data):m.u8[a+i]=v
   actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203FF00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
   write(actor+8,struct.pack('<I',0x80000000),'Controlled active monster');write(actor+0x91,bytes([species]),'Controlled native species');write(actor+0x88,struct.pack('<h',level),'Controlled native signed16-bit level');write(actor+0x95,bytes(12),'No status name aliases');write(actor+0xA7,b'\0','No species91 name disguise');flag=m.u32[m.u32[0x08029EFC]+0x30]+28*species+0x13;write(flag,b'\0','Original already-known species branch')
   baseline=dict(actor=bytes(m[actor:actor+0x100]),inventory=bytes(m[0x0200DF28:0x0200E888]),hero=bytes(m[m.u32[0x02001624]:m.u32[0x02001624]+0x100]))
   regs=[int(cpu.gprs[i])&0xffffffff for i in range(16)];guard=bytes(m[regs[13]:regs[13]+32]);cpu.gprs[0]=actor;cpu.gprs[14]=0x08000355
   for reg,v in ((b'cpsr',int(cpu.cpsr.packed)|0x20),(b'pc',0x08029EB8)):require(g.core._core.writeRegister(g.core._core,reg,ffi.new('uint32_t*',v)),'Identity controlled entry failed')
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x08000FB8 and r[14]==0x08029EF9:
     require(not formats and r[1]==row['offset']+0x08000000 and r[0]==r[13],'Identity source/output differs')
     arg=r[2]
     if kind=='native':
      entry=b['monsters']['entries'][species];expected=native_format(bytes.fromhex(b['monsters']['level_format']['encoded_hex']),[entry['offset']+0x08000000,level],m) if level>1 else bytes.fromhex(entry['encoded_hex']);require(bytes(m[arg:arg+len(expected)])==expected,'Native species/level name differs')
     if kind!='native':
      raw=encode('W'*31 if kind=='maximum-width' else 'i'*31 if kind=='maximum-bytes' else 'Slime')
      if kind=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
      require(len(raw)<=64,'Identity field overflow');arg=0x02008D08;write(arg,raw.ljust(64,b'\0'),'Owned native actor-name scratch boundary');cpu.gprs[2]=arg;overrides.append(dict(event=e,register=2,after=arg))
     data=native_format(bytes.fromhex(row['encoded_hex']),[arg],m);require(len(data)<=row['maximum_bytes']<=256,'Identity output overflow');write(r[0],b'\xa5'*256,'Canary inside owned original output buffer');pending.update(event=e,data=data,guard=bytes(m[r[0]+256:r[0]+272]),field_address=arg,field=bytes(m[arg:arg+64]))
    if a==0x08029EF8:
     old=pending['event']['registers'];at=old[0];data=pending['data'];require(bytes(m[at:at+len(data)])==data and bytes(m[at+len(data):at+256])==b'\xa5'*(256-len(data)) and bytes(m[at+256:at+272])==pending['guard'],'Identity exact output/canary differs');require(r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[pending['field_address']:pending['field_address']+64])==pending['field'],'Identity format ABI/field differs');formats.append(dict(event=pending['event'],formatted_hex=data.hex(),bytes=len(data),name_hex=pending['field'].hex(),guard_abi_preserved=True))
    if a in (0x0801588C,0x08015A34,0x08001BC4):queue.append(e)
    if a==0x08000354:finished.append(e)
   with Debugger(g,callback,max_events=10000) as d:
    for a in (0x08000FB8,0x08029EF8,0x0801588C,0x08015A34,0x08001BC4,0x08000354):d.breakpoint(a)
    d.run_until(lambda _:bool(finished),max_steps=1000000)
   r=finished[0]['registers'];require(len(formats)==1 and not queue and r[4:12]==regs[4:12] and r[13]==regs[13] and bytes(m[regs[13]:regs[13]+32])==guard,'Identity owner ABI or no-display behavior differs');require(m.u8[flag]==0 and bytes(m[actor:actor+0x100])==baseline['actor'] and bytes(m[0x0200DF28:0x0200E888])==baseline['inventory'] and bytes(m[m.u32[0x02001624]:m.u32[0x02001624]+0x100])==baseline['hero'] and g.snapshot().battery==fixture.battery,'Identity branch changed actor/items/player/save')
   cases.append(dict(case=name,species=species,level=level,kind=kind,inputs=g.inputs,overrides=overrides,controlled_call=dict(address=0x08029EB8,arguments=[actor],return_trap=0x08000354),formats=formats,no_display_calls=True,owner_abi_guard_preserved=True,gameplay_save_preserved=True))
 report=dict(passed=True,rom_sha256=digest(rom),cases=cases,scope='Controlled complete original already-known monster handler, all141 species at level1, widest name at signed16-bit level32767, three native64-byte name-field boundary/colour cases. Exact format bytes, untouched buffer tail/guards/ABI, no queue/modal/glyph calls, unchanged actor/player/items/battery. This branch originally discards its formatted stack buffer: no new on-screen message or display behavior is claimed. Natural encounter routing remains separate.');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Monster identity:',len(cases),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
