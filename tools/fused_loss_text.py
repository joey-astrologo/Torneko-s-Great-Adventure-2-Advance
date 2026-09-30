"""Owned synthesized-ability loss message and exact bit-indexed name table."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_items import source
from tools.inventory_action_text import CONTROL
CATALOG=ROOT/'translations/fused-loss-review.json'

def add_fused_loss(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original),'Fused ability base differs')
 require(len(c['abilities'])==40 and {(r['kind'],r['bit']) for r in c['abilities']}=={(k,i) for k in (0,1) for i in range(20)},'Fused ability table incomplete')
 table=bytearray(build.original[0x144848:0x1448E8]);abilities=[]
 for row in c['abilities']:
  slot=row['kind']*80+row['bit']*4;src=source(build.original,struct.unpack_from('<I',table,slot)[0]);require(row['source']==src and row['status']=='reviewed','Fused ability source/review differs')
  payload=encode(row['english']);at=build.allocate(row['id'],payload,'fused-loss');struct.pack_into('<I',table,slot,at+0x08000000);abilities.append(row|{'offset':at,'encoded_hex':payload.hex(),'width':measure(row['english'])})
 ability_at=build.allocate('fused-ability-names',bytes(table),'fused-loss')
 require(len(c['entries'])==1,'Fused loss format count differs');row=c['entries'][0];text=row['english'];src=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x3AC)
 require(row['status']=='reviewed' and row['source']==src and row['table_offset']==0x3AC and re.findall(r'\{([^}]+)\}',text)==['item','fit','ability'],'Fused loss fields/source differ')
 payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p in ('{item}','{ability}') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
 maximum=len(payload)+63-2+max(len(bytes.fromhex(r['encoded_hex']))-1 for r in abilities)-2
 widths=[measure(re.sub(r'\{[^}]+\}','',part))+162*part.count('{item}')+max(r['width'] for r in abilities)*part.count('{ability}') for part in text.split('{fit}')]
 require(maximum<=256 and max(widths)<=216,'Fused loss formatter/window exceeded')
 at=build.allocate(row['id'],payload,'fused-loss');messages=bytearray(build.original[START:END]);struct.pack_into('<I',messages,0x3AC,at+0x08000000)
 msg_at=build.allocate('fused-loss-messages',bytes(messages),'fused-loss')
 for site,old,new in ((0x112C0,START,msg_at),(0x112C4,0x144848,ability_at)):
  build.patch('fused-loss-reader-'+hex(site),site,struct.pack('<I',old+0x08000000),struct.pack('<I',new+0x08000000),'fused-loss')
 return {'entries':[row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256}],'abilities':abilities,'table_offset':msg_at,'ability_table_offset':ability_at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
