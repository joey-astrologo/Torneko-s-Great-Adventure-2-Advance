"""Hash-pinned writing lookup/editor and owned message evidence."""
import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
    specs={'writing-editor':('writing_input',9),'fused-loss':('fused_loss',39),'cannot-talk':('cannot_talk',12),'step-stairs':('step_stairs',6),'pot-view':('pot_view',11)}
    for family,(key,count) in specs.items():
        folder=source/(family+'-validation');path=folder/'report.json';report=json.loads(path.read_text());rows=report['cases']
        require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(rows)==count and len({r['case'] for r in rows})==count,'Incomplete/stale input-text evidence: '+family)
        require(all(r['visible_pixels_checked'] and r['inputs'] and r['images'] for r in rows),'Missing input-text pixels/input: '+family)
        if family=='writing-editor':
            require({r['case'] for r in rows}=={'spell-long','scroll-long','scroll-full','spell-case','spell-unknown','ordinary-name','scroll-display','spell-empty','wide-japanese'},'Writing editor case set differs')
            require(all(r['native_item_result_checked'] and len(r['editor_entry'])==len(r['editor_return'])==1 for r in rows),'Writing editor native result/ABI missing')
        elif family=='fused-loss':
            require({r['field'] for r in rows}=={f'native-{k}-{i}' for k in (0,1) for i in range(20 if k==0 else 16)}|{'stress-width','stress-bytes','stress-colour'},'Fused loss bit/field coverage differs')
            require(len(build[key]['entries'])==1 and len(build[key]['abilities'])==40 and all(r['caller_guard_abi_preserved'] and not r['visual_effect_skips'] for r in rows),'Fused loss ownership/effect scope differs')
        elif family=='cannot-talk':
            require({(r['branch'],r['field']) for r in rows}=={(b,f) for b in ('priest','companion') for f in ('required-English','widest-English','widest-Japanese','actor-width','actor-bytes','actor-colour')},'Talk branch/field coverage differs')
            require(all(r['caller_guard_abi_preserved'] and len(r['modals'])==len(r['modal_returns'])==len(r['formats'])==1 for r in rows),'Talk formatter/modal/ABI missing')
        elif family=='step-stairs':
            require({r['case'] for r in rows}=={k+'-'+c for k in ('step','stairs') for c in ('cancel','stay','act')},'Step/stairs selections incomplete')
            require(all(r['caller_guard_abi_preserved'] and len(r['reads'])==len(r['returns'])==3 and all(v['native_selection_checked'] for v in r['returns']) for r in rows),'Step/stairs reopening/result checks incomplete')
        elif family=='pot-view':
            require({r['case'] for r in rows}=={str(i)+'-'+str(n) for i,n in [(154,0),(154,3),(157,0),(157,3),(158,3),(159,3),(160,3),(161,3),(164,0),(164,3),(162,3)]},'Pot-view identities/capacities incomplete')
            require(all(r['caller_guard_abi_preserved'] and len(r['returns'])==3 for r in rows),'Pot-view repeated render/ABI missing')
            require({r['id'] for c in rows for r in c['reads']}=={r['id'] for r in build[key]['entries']},'Pot-view labels missing')
            require(all(len(r['copies'])==9 and all(c['guard_abi_preserved'] for c in r['copies']) for r in rows if r['item_id']==161),'Thief pot copied labels/guards missing')
        images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
        require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Stale input-text gallery: '+family)
        for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Changed input-text capture: '+p)
        for pattern in ('*.json','index.html','*/*.png','native/*.json'):
            for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
        counts[family]=count;receipt[family+'_scope']=report['scope']
    path=source/'writing-lookup-validation/report.json';report=json.loads(path.read_text());rows=report['cases']
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(rows)==584 and all(r['input_guard_preserved'] for r in rows),'Writing lookup evidence incomplete/stale')
    aliases=build['writing_input']['entries'];tables=build['writing_input']['tables']
    require(len(aliases)==106 and {(r['family'],r['english']) for r in aliases}<={(r['family'],r['text']) for r in rows},'English aliases missing from lookup checks')
    require({(t['family'],r['source']['japanese']) for t in tables for r in t['original_entries']}<={(r['family'],r['text']) for r in rows},'Original kana compatibility missing')
    receipt['artifacts'][str(path.relative_to(ROOT))]=digest(path.read_bytes());receipt['writing-lookup_scope']=report['scope'];counts['writing-lookup']=len(rows)
    receipt['additional_input_text_resources']=sum(build['reviewed_resource_counts'][key] for key in ('writing_input','fused_loss','cannot_talk','step_stairs','pot_view'))
