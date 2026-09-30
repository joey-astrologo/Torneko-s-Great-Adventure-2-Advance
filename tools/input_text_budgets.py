"""Audition regions for English writing and remaining small prompts."""
import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
    reports={}
    for family,count in (('writing-editor',9),('cannot-talk',12),('fused-loss',39),('step-stairs',6),('pot-view',11)):
        path=source/(family+'-validation')/'report.json';report=json.loads(path.read_text())
        require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==count,'Input text budget evidence stale: '+family)
        reports[family]=(path,report)
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('input-text-current-')]
    def add(ident,title,window,start,end,labels,family,note,capture=None):
        path,report=reports[family]
        row={'id':'input-text-current-'+ident,'name':title,'stage':'current','window':window,'start':start,'end':end,'rows':len(labels),'labels':labels,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':note}
        if capture:row['capture']=str((path.parent/capture).relative_to(ROOT))
        config['contexts'].append(row)
    labels=[r['english'] for r in build['writing_input']['entries']]
    for i in range(0,len(labels),8):
        add('aliases-'+str(i//8),'Writable English names',224,0,216,labels[i:i+8],'writing-editor','Each label is a separate one-row input candidate, up to15characters. Full native keyboard/lookup and longest English/Japanese rows are checked. Case folding changes lookup only; font spacing is unchanged.')
    add('ordinary-name','Ordinary item name',120,0,112,['W'*8],'writing-editor','Original8-character custom-name editor. Item-row category/count/price layout remains separate.')
    add('input-limit','Writing input maximum',224,0,216,['W'*15],'writing-editor','Special scroll/spellbook editor only; ordinary names and stored saves keep their original limits.')
    add('talk','Unable to talk',224,0,216,['W'*31,"can't talk."],'cannot-talk','Two native refusal blocks, original two-row modal; maximum186px actor substitution and256-byte formatter output.')
    add('step','Trap step first column',112,6,52,['Step'],'step-stairs','Original two-column prompt:6px cursor reserve, second column starts52px. Native choices and repeated cancellation pass.','step-act/opened-2.png')
    add('stay','Trap step second column',112,52,112,['Stay'],'step-stairs','Original second-column position and width; no geometry change.')
    add('stairs','Two-choice stairs',96,6,96,['Descend','Stay'],'step-stairs','Original96px window,90px after cursor. Native B/Stay/Descend results and repeated reopening pass.','stairs-act/opened-2.png')
    for i in range(0,40,8):
        labels=['lost its fused ['+r['english']+']!' for r in build['fused_loss']['abilities'][i:i+8]]
        add('fused-'+str(i//8),'Fused ability removal predicates',224,0,216,labels,'fused-loss','Each predicate follows the complete item field. Conditional break keeps the whole message on one line only when the native measured join fits; otherwise two lines. Original64-byte item scratch/256-byte output preserved.')
    add('pot-labels','Pot view labels',168,6,168,['Something','- Nothing inside -'],'pot-view','Original168px pot window;6px cursor inset for concealed slots. Empty label retains the native inert07/08 controls, which do not center the GBA text. Eleven native states and repeated reopening pass.','161-3/view-2.png')
