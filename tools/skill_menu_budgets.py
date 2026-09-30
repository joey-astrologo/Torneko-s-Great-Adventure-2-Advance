"""Audition budgets pinned to native skill list, equipment and assignment checks."""
import json
from tools.compact_font import measure
from tools.rom import ROOT,digest,require


def append_contexts(config,build,source=ROOT/'build/english'):
    reports={}
    for family,count in (('skill-menu',4),('skill-equipment',7),('skill-set',1),('skill-action',3)):
        path=source/(family+'-validation')/'report.json';report=json.loads(path.read_text())
        require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==count,'Skill audition evidence incomplete: '+family)
        reports[family]=(path,report)
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('skill-current-')]
    def context(ident,name,window,start,end,rows,labels,family,note,capture=None):
        path,report=reports[family]
        row={'id':'skill-current-'+ident,'name':name,'stage':'current','window':window,'start':start,'end':end,'rows':rows,'labels':labels,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':note}
        if capture:row['capture']=str((path.parent/capture).relative_to(ROOT))
        config['contexts'].append(row)
    context('categories','Skill categories',48,6,48,2,['Weapon','Shield'],'skill-menu','Original48px selector. Six pixels reserved for cursor,42px text; two compact spaces retain the native inset.','weapon-learned/categories.png')
    context('actions','Skill actions',40,6,40,2,['Set','Info'],'skill-set','Original34px action region and8px border gap; actual native Set and cancellation are verified.','set-weapon/actions.png')
    context('retained-actions','Retained skill action labels',40,6,40,3,['Unset','Use','Info'],'skill-action','Original34px action budget. Retained Unset/Use variants are controlled render-only vector probes and are never executed; natural availability is not asserted.')
    definitions=build['skill_info']['definitions'];eligible=[r for r in definitions if r['menu_eligible']]
    for start in range(0,len(eligible),8):
        group=eligible[start:start+8]
        context('list-'+str(start//8+1),'Skill names '+str(start+1)+'-'+str(start+len(group)),168,20,162,len(group),[r['name'] for r in group],'skill-menu','Conservative142px name region after6px inset and14px native-marker reserve. All100 eligible names are verified in native selection;64-byte output. Learned/unlearned states and original pages remain separate in the report.')
    longest=sorted((r['name']+(' ('+str(r['hunger_cost'])+')' if r['hunger_cost'] else '') for r in eligible),key=measure,reverse=True)[:3]
    context('equipment','Equipment skill name/cost rows',168,12,160,3,longest,'skill-equipment','Three body rows,12px native inset and148px text. Parenthesized numbers are Hunger costs identified by the heading;256-byte formatting.','three-weapon/preview-0.png')
    context('equipment-heading','Equipment skill headings',168,6,162,1,['Skills (Hunger: 765)','No skills set'],'skill-equipment','The title has156px. Three original unsigned-byte costs bound the sum at765; actual native totals are checked separately.')
    context('confirmation','Skill Set confirmation',224,0,216,2,['Set Double-Edged Slash','on your equipped Whirlwind sword?'],'skill-set','Original256-byte output; explicit skill and equipped-item substitutions are retained. The gallery uses native Oaken club while this audition uses the longer Whirlwind sword.','set-weapon/confirmation.png')
