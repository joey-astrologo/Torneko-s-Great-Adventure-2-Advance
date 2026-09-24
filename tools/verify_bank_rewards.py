"""Native bank gift branches with explicit disposable balance/inventory setups."""
import argparse,json,struct
from collections import Counter
import mgba.log
from tools.rom import ROOT,load_base,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.build_english import build_rom
from tools.verify_bank import BankChecks,open_bank,balance
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.compact_font import encode
from tools.verify_storage import SAVE
from tools.town_playtest import position

OUT=ROOT/'build/english/bank-rewards-validation'
CLAIMED=0x02002c16
INVENTORY=0x0200df28

def carried(m):
 return [m.u8[0x020013d0+m.u8[INVENTORY+i*120+8]] for i in range(20) if m.u32[INVENTORY+i*120]&0x80000000]

def ready(rom):
 path=OUT/'native/ready'
 if path.with_suffix('.json').exists():
  snap=Snapshot.load(path)
  if snap.rom_sha256==digest(rom):return snap
 with Session(rom,OUT/'native',initial_save=SAVE.read_bytes()) as g:
  g.frames(600);g.press('START',wait=180);g.press('A',wait=300)
  require(position(g)==(288,224),'Storage quest save did not resume at book')
  for key,hold in [('RIGHT',16),('DOWN',32),('LEFT',32),('DOWN',32),('LEFT',32),('DOWN',3),('DOWN',16),('RIGHT',64),('DOWN',16),('RIGHT',16),('UP',3)]:g.press(key,hold=hold,wait=120)
  snap=g.snapshot();snap.save(path);g.capture('ready')
  (OUT/'native/provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'source_save_sha256':digest(SAVE.read_bytes()),'inputs':g.inputs,'controlled_overrides':[]},indent=2)+'\n')
  return snap

def run(only=None):
 mgba.log.silence();rom,build=build_rom();original=load_base()
 fixture=ready(rom)
 thresholds=struct.unpack_from('<10I',original,0x148284)
 counts=original[0x1482b0:0x1482ba];gifts=original[0x1482bb:0x1482bb+30]
 require(list(counts)==[0,1,1,1,1,1,1,3,1,1],'Native gift counts changed')
 names={int(r['id'].split('.')[-1]):r['english'] for r in build['items']['entries'] if r['id'].startswith('item.name.')}
 cases=[('no-reward',0,False,None)]+[(f'tier-{i}'+('-full' if full else ''),i,full,None) for i in range(1,10) for full in (False,True)]
 cases.extend((f'tier-7-{label}',7,False,name) for label,name in player_layout_cases()[1:])
 if only:cases=[r for r in cases if r[0] in only]
 rows=[]
 for name,tier,full,player in cases:
  with Session(rom,OUT/name) as g:
   print('Bank reward',name,flush=True);g.restore(fixture);m=g.core.memory
   m.u32[0x02002c1c]=thresholds[tier];m.u8[CLAIMED]=max(tier-1,0)
   if full:
    template=bytes(m[INVENTORY:INVENTORY+120]);require(template[3]&0x80,'Need a native carried item for capacity probe')
    for slot in range(20):
     for j,v in enumerate(template):m.u8[INVENTORY+slot*120+j]=v
   if player:
    for j,v in enumerate(player.ljust(16,b'\0')):m.u8[HERO+j]=v
   before=carried(m);gold=balance(g);c=BankChecks(g,build);entries=[];returned=[]
   def cb(e):
    c.callback(e)
    if e['address']==0x0801dfac:
     entries.append({'original_arguments':e['registers'][:3],'controlled_reward_enable_argument':1})
     g.core.cpu.gprs[2]=1
    if e['address']==0x0801e37a:returned.append(e['frame'])
   with Debugger(g,cb,max_events=100000) as debug:
    for a in set(c.ADDRESSES+(0x0801dfac,0x0801e37a)):debug.breakpoint(a)
    g.press('A',wait=150);g.press('A',wait=150)
    require(c.completed('bank.81'),'Bank menu missing');g.press('B',wait=120)
    for step in range(30):
     g.capture(f'page-{step:02}')
     if returned:break
     g.press('A',wait=120)
    require(returned and not c.active and not c.pending,'Bank rewards did not finish')
   require(entries,'Native bank entry missing')
   require(c.completed('bank.93'),'Reward explanation missing')
   require(balance(g)==gold,'Reward display changed gold')
   after=carried(m);expected=list(gifts[tier*3:tier*3+counts[tier]]) if tier else []
   if tier:
    require(c.completed('bank.87'),'Reward threshold missing')
    if full:
     require(c.completed('bank.89') and c.completed('bank.90'),'Full-inventory reward refusal/count missing')
     require(after==before and m.u8[CLAIMED]==tier-1,'Declined reward changed items or claim counter')
    else:
     require(c.completed('bank.91'),'Received-gift text missing')
     require(Counter(after)==Counter(before)+Counter(expected) and m.u8[CLAIMED]==tier,'Native gift item IDs/count or claim counter differs')
     received=[f for f in c.formats if f['id']=='bank.91'];payload=bytes.fromhex(received[-1]['expected_hex'])
     for ident,count in Counter(expected).items():
      require(payload.count(encode(names[ident])[:-1])==count,'Gift name text differs from the native item IDs/count')
   else:require(after==before and m.u8[CLAIMED]==0,'No-reward branch changed inventory/counter')
   if tier<9 or full:require(c.completed('bank.92'),'Next reward threshold missing')
   require(g.snapshot().battery==fixture.battery,'Reward probe wrote the source save')
   rows.append({'case':name,'tier':tier,'full_inventory':full,'controlled_name_hex':player.hex() if player else None,
                'controlled_balance':thresholds[tier],'claimed_before':max(tier-1,0),'claimed_after':m.u8[CLAIMED],
                'items_before':before,'items_after':after,'expected_gift_ids':expected,'native_bank_arguments':entries,
                'reads':c.reads,'formats':c.formats,'glyph_checks':c.glyph_checks,'inputs':g.inputs})
 report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Native bank menu exit and reward delivery/refusal, with controlled bank balance, claim counter, reward-enable argument at native bank entry, optional full inventory and two maximum-width player names. The early checkpoint ordinarily disables rewards. Native gift items/counter, next threshold, gold, format guards, pixels and save immutability checked. This is not ordinary unlocking or earning of rewards.'}
 (OUT/('probe-report.json' if only else 'report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Bank reward cases:',len(rows));return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',action='append');run(p.parse_args().case)
