"""Font audition regions for audited reference menus, shop and save panels."""
import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
    reports={}
    for family,count in (('reference-lists',9),('town-root',4),('save-preview',56),('dungeon-shop',16),('save-notices',2)):
        path=source/(family+'-validation')/'report.json';report=json.loads(path.read_text())
        require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==count,'Additional text audition evidence stale: '+family)
        reports[family]=(path,report)
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('saved-text-current-')]
    def context(ident,name,window,start,end,rows,labels,family,note,capture=None):
        path,report=reports[family]
        row={'id':'saved-text-current-'+ident,'name':name,'stage':'current','window':window,'start':start,'end':end,'rows':rows,'labels':labels,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':note}
        if capture:row['capture']=str((path.parent/capture).relative_to(ROOT))
        config['contexts'].append(row)
    context('reference-root','Reference categories',64,6,64,3,['Blank list','Skill list','Spell list'],'reference-lists','Original64px window,6px cursor reserve and58px labels. Native masks1/3/7, cancellation and reopening are verified.','categories-7/categories.png')
    context('reference-locked','Reference locked rows',168,6,168,2,["Can't write.",'Not learned'],'reference-lists','Original162px row region and64-byte row buffer. Actual locked A refusal and all pages are checked.','scroll-locked/page-0.png')
    rom=(source/'torneko-2-english.gba').read_bytes();scroll_ids=set(rom[0x148343:0x14835E])
    groups={'scroll':[r['english'] for r in build['items']['entries'] if r['id'].startswith('item.name.') and int(r['id'].split('.')[-1]) in scroll_ids],
            'skill':[r['name'] for r in build['skill_info']['definitions'] if r['menu_eligible']],
            'spell':[r['name'] for r in build['spell_info']['definitions'] if r['menu_eligible']]}
    for kind,labels in groups.items():
        for start in range(0,len(labels),8):
            group=labels[start:start+8]
            context(f'reference-{kind}-{start//8+1}',f'Reference {kind} names {start+1}-{start+len(group)}',168,6,168,len(group),group,'reference-lists','Original162px name region and64-byte row output, page indicator remains separate with8px outer-border gap.','%s-known/page-%d.png'%(kind,start//8))
    context('town-root','Town commands',40,6,40,2,['Items','Option'],'town-root','34px after6px cursor reserve. Root closes before child. Native empty/populated inventory, Option, cancellation and twice reopening verified.','option/reopened-1.png')
    context('save-village','Save preview village field',224,112,216,1,[' Village  Run 32767'],'save-preview','112px reserved for all eight widest stored Japanese village glyphs. Original256-byte output; ordinary editor limits remain separate.','town-0-wide-Japanese/preview.png')
    context('save-stats','Save preview maximum stats',224,0,216,1,['Lv32767  HP 32767/32767'],'save-preview','Positive signed16-bit maximum level/currentHP/maxHP; native formatter argument order and following name field are verified.')
    locations=[r['english'] for r in build['save_preview']['entries'] if r.get('table_offset') in range(0x5D0,0x604,4)]
    for start in range(0,len(locations),3):
        group=locations[start:start+3]
        context('save-dungeons-'+str(start//3),'Save preview dungeon fields',224,20,216,len(group),[x+' 32767F  Run 32767' for x in group],'save-preview','20px reserve for existing castle graphic;196px text. Complete dungeon names, maximum floor/attempt retained. Original artwork and geometry unchanged.')
    context('save-home','Save preview home field',224,98,216,1,["Inside 's home"],'save-preview','98px reserved for native seven-character player substitution in Inside {player}\'s home. Name is never shortened; native English and Japanese cases pass.')
    for row in build['dungeon_shop']['entries']:
        lines=row['english'].replace('{amount}','2147483647').split('\n')
        context(row['id'],'Dungeon shop: '+row['id'],224,0,216,len(lines),lines,'dungeon-shop','Original256-byte output, numeric colour and two-row confirmation with original Yes/No. Amount is a rendering bound; transaction outcomes are separate.')
    for row in build['save_notices']['entries']:
        lines=row['english'].split('\n')
        for start in range(0,len(lines),2):
            group=lines[start:start+2]
            context(row['id']+'-'+str(start//2),'Save notice page',224,0,216,len(group),group,'save-notices','Original28-tile two-row modal; native wait advances improper-suspension warning to its second page.')
