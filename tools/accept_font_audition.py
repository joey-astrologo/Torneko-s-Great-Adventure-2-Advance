"""Pin the selected font, audition evidence and refreshed cumulative acceptance."""

import json

from tools.accept_mansion import run as cumulative_acceptance
from tools.compact_font import ASSET
from tools.rom import ROOT, digest, require


def run():
    root=ROOT/'build/font-audition'
    font=json.loads((root/'native/validation.json').read_text())
    require(font['passed'] and font['glyph_count']==95 and
            all(s['build']['font_asset_sha256']==digest(ASSET.read_bytes()) for s in font['samples']),
            'Native font acceptance is stale')
    audition=json.loads((root/'report.json').read_text())
    require(audition['passed'] and audition['selected_font']=='torneko3' and
            audition['config_sha256']==digest((ROOT/'config/font-audition.json').read_bytes()) and
            audition['native_menu_report_sha256']==digest((ROOT/'build/menu-layout-audit/native/report.json').read_bytes()),
            'Audition evidence is stale')
    browser=json.loads((root/'browser-checks.json').read_text())
    require(browser['passed'] and browser['contexts']==len(audition['contexts']) and
            browser['metric_comparisons']==len(audition['measurements']) and
            browser['page_sha256']==digest((root/'index.html').read_bytes()) and
            browser['checks_sha256']==digest((ROOT/'tools/check_font_audition.js').read_bytes()),'Browser checks are stale')
    path=ROOT/'docs/english-font-validation.json'
    result=cumulative_acceptance(receipt_path=path,check_directory='build/font-audition')
    result['selected_font']='Original Japanese Torneko 3 Latin font 0; unchanged advances/ink, two blank top rows'
    result['font_asset_sha256']=digest(ASSET.read_bytes())
    result['native_font_glyphs']=95
    result['audition_contexts']=len(audition['contexts'])
    result['audition_measurements']=len(audition['measurements'])
    result['menu_layout_signoff']=False
    result['remaining_selected_font_candidate_overflows']=[
        {k:r[k] for k in ('context','label','budget','advance','remaining')} for r in audition['measurements']
        if r['font']=='torneko3' and r['role']=='candidate' and not r['fits']]
    for relative in ['config/font-audition.json','build/font-audition/index.html',
                     'build/font-audition/report.json','build/font-audition/budgets.csv',
                     'build/font-audition/contexts.csv','build/font-audition/browser-checks.json',
                     'build/font-audition/audition-browser.png','build/font-audition/native/validation.json',
                     'build/font-audition/native/mixed-case/menu.png','build/menu-layout-audit/native/report.json',
                     'tools/verify_font_audition.m','tools/check_font_audition.js']:
        result['artifacts'][relative]=digest((ROOT/relative).read_bytes())
    result['scope']+=' Selected Torneko 3 font passes all 95 glyph checks. Audition measures known menus; remaining candidate overflows and unaudited menu families explicitly block full menu-layout sign-off. No new menu verbs or geometry changes are inserted.'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(path)
    return result


if __name__=='__main__':
    run()
