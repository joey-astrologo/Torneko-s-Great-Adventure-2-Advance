"""Reject conflicting glossary names and drift in the active identified items."""
import json
from tools.rom import ROOT,digest,require

def validate():
 glossary=ROOT/'translations/glossary.json';catalog=ROOT/'translations/items-review.json'
 terms=json.loads(glossary.read_text())['terms'];by_japanese={};by_item={}
 for term in terms:
  japanese=term['japanese'];japanese=japanese if isinstance(japanese,list) else [japanese]
  for source in japanese:
   prior=by_japanese.setdefault(source,term['english'])
   require(prior==term['english'],'Conflicting glossary names for '+source+': '+prior+' / '+term['english'])
  if 'item_id' in term:
   prior=by_item.setdefault(term['item_id'],term['english'])
   require(prior==term['english'],'Conflicting glossary item ID')
 additional=ROOT/'translations/special-items-review.json'
 rows=json.loads(catalog.read_text())['entries']+json.loads(additional.read_text())['entries']
 for row in rows:
  canonical=row.get('canonical_name',row['name'])
  expected=by_item.get(row['id'],by_japanese.get(row['name_source']['japanese']))
  require(expected is not None and expected==canonical,'Active item name differs from glossary: '+str(row['id']))
 spells=ROOT/'translations/spells-review.json';spell_rows=json.loads(spells.read_text())['entries']
 for row in spell_rows:
  require(by_japanese.get(row['name_source']['japanese'])==row['canonical_name'],'Spell identity differs from glossary: '+str(row['id']))
 report={'passed':True,'glossary_sha256':digest(glossary.read_bytes()),'item_catalog_sha256':digest(catalog.read_bytes()),'additional_item_catalog_sha256':digest(additional.read_bytes()),'spell_catalog_sha256':digest(spells.read_bytes()),'checked_spell_names':len(spell_rows),
         'unique_japanese_terms':len(by_japanese),'checked_item_names':len(rows),
         'scope':'Canonical spelling consistency and conflicting entries, not independent proof of official naming or prose fidelity. Different meanings sharing a Japanese spelling require an explicit identity-scoped policy before adding conflicting names.'}
 return report

def run():
 report=validate();out=ROOT/'build/text-inventory';out.mkdir(parents=True,exist_ok=True)
 (out/'terminology-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Terminology consistency:',report['checked_item_names'],'item names');return report

if __name__=='__main__':run()
