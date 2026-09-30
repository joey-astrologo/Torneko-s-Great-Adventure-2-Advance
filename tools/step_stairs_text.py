"""Private trap-step and two-choice stairs text; original geometry and commands."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_items import source
CATALOG=ROOT/'translations/step-stairs-review.json'
def add_step_stairs(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==2,'Step/stairs review cohort differs');rows=[]
 for row in c['entries']:
  if row['id']=='step-stairs.step':
   src=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x18);require(row['english']=='Step / Stay','Step labels differ');raw=encode('Step')[:-1]+b'\x04\x38'+encode('Stay');widths=[measure('Step'),measure('Stay')];require(widths[0]<=46 and widths[1]<=60,'Step columns overflow')
  else:
   src=source(build.original,0x0806B590);require(row['id']=='step-stairs.stairs' and row['english']=='Descend\nStay','Stairs labels differ');raw=encode(row['english']);widths=[measure(x) for x in row['english'].split('\n')];require(max(widths)<=90,'Stairs width overflow')
  require(row['source']==src and row['status']=='reviewed','Step/stairs source review differs');at=build.allocate(row['id'],raw,'step-stairs');rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'line_widths':widths,'layout':{'pages':[[row['id']]]}})
 table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x18,rows[0]['offset']+0x08000000);at=build.allocate('step-choice-private-table',bytes(table),'step-stairs')
 build.patch('step-choice-reader',0x1786C,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'step-stairs')
 build.patch('two-choice-stairs-reader',0x178F8,struct.pack('<I',0x0806B590),struct.pack('<I',rows[1]['offset']+0x08000000),'step-stairs')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
