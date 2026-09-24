"""Pin the restored T2 font, early-menu acceptance and cumulative English build."""
import json
from tools.accept_mansion import run as cumulative_acceptance
from tools.compact_font import ASSET,COMPACT_ASSET
from tools.rom import ROOT,require,digest,default_rom,load_base


def run():
    require(ASSET==COMPACT_ASSET,'T2 font is not the build default')
    ledger=json.loads((ROOT/'build/english/build.json').read_text());rom_hash=ledger['output_sha256']
    reports={}
    for name in ('menu','menu-edge','menu-action','menu-variant'):
        path=ROOT/f'build/english/{name}-validation/report.json';r=json.loads(path.read_text())
        require(r['passed'] and r['rom_sha256']==rom_hash,'Stale menu check: '+name);reports[name]=r
    require(len(reports['menu']['routes'])==7,'Natural menu routes missing')
    require(len(reports['menu']['border_checks'])==11 and
            all(c['gap_px']==8 for c in reports['menu']['border_checks']),'Separate window borders not verified')
    require(sum(len(r['parent_checks']) for r in reports['menu']['routes'])==9,'Parent restoration coverage changed')
    require(len(reports['menu-edge']['cases'])==12 and len(reports['menu-action']['cases'])==6,'Edge/action cases missing')
    variants=reports['menu-variant']['probes'];excluded=[r for r in variants if 'excluded' in r]
    require(len(variants)==286 and not excluded,'Controlled variant coverage changed')
    require(all(r['parent_preserved'] and r['stack_preserved'] and r['glyph_checks']>0 and r['max_item_ink_edge']<=168
                for r in variants if 'excluded' not in r),'Item variant did not pass')
    audition=json.loads((ROOT/'build/font-audition/report.json').read_text())
    require(audition['selected_font']=='compact' and audition['passed'] and
            audition['compiled_menu_report_sha256']==digest((ROOT/'build/english/menu-validation/report.json').read_bytes()) and
            audition['config_sha256']==digest((ROOT/'config/font-audition.json').read_bytes()),'Audition evidence stale')
    require(all(r['fits'] for r in audition['measurements'] if r['font']=='compact' and r['stage']=='current'),'Current label overflow')
    native_font=json.loads((ROOT/'build/font-audition/native/validation.json').read_text())
    require(native_font['passed'] and native_font['glyph_count']==95 and
            all(s['build']['font_asset_sha256']==digest(ASSET.read_bytes()) for s in native_font['samples']),'Native font evidence stale')
    browser=json.loads((ROOT/'build/font-audition/browser-checks.json').read_text())
    require(browser['passed'] and browser['contexts']==len(audition['contexts']) and
            browser['metric_comparisons']==len(audition['measurements']) and
            browser['page_sha256']==digest((ROOT/'build/font-audition/index.html').read_bytes()) and
            browser['checks_sha256']==digest((ROOT/'tools/check_font_audition.js').read_bytes()),'Browser checks stale')
    services=json.loads((ROOT/'build/menu-resize/services/report.json').read_text())
    require(services['passed'] and services['source_rom_sha256']==digest(load_base()),'Service audit stale')
    require(ledger['menus']['review_sha256']==digest((ROOT/'translations/menus-review.json').read_bytes()),'Menu translation review stale')
    path=ROOT/'docs/english-menu-validation.json'
    receipt=cumulative_acceptance(receipt_path=path,check_directory='build/services')
    receipt.update(selected_font='Torneko 2 compact English extension',font_asset_sha256=digest(ASSET.read_bytes()),
        native_font_glyphs=95,early_menu_layout_signoff=True,whole_game_menu_layout_signoff=False,
        reviewed_menu_resources=len(ledger['menus']['entries']),total_reviewed_inserted_resources=len(ledger['menus']['entries'])+receipt['inserted_reviewed_text_resources'],
        natural_menu_routes=7,natural_action_cases=6,controlled_edge_cases=12,
        controlled_item_attempts=len(variants),controlled_item_panels=len(variants)-len(excluded),controlled_item_exclusions=excluded,
        audition_contexts=len(audition['contexts']),audition_measurements=len(audition['measurements']),
        action_buffer_bytes=256,action_scratch_bytes=64,root_buffer_bytes=64,
        original_menu_geometry_restored=True,window_border_gap_px=8,native_border_checks=11,
        action_extra_stack_bytes=192,root_extra_stack_bytes=64,
        menu_glyph_checks=sum(r['glyph_checks'] for r in reports['menu']['routes']),
        controlled_item_glyph_checks=sum(r.get('glyph_checks',0) for r in variants))
    patterns=['config/font-audition.json','build/menu-resize/preview.json','build/menu-resize/index.html','build/menu-resize/menus.png','build/menu-resize/correction.png','build/menu-resize/previous-wide/*',
              'build/menu-resize/services/report.json','build/menu-resize/*.txt','build/menu-resize/initial-build.log',
              'build/font-audition/index.html','build/font-audition/report.json','build/font-audition/*.csv',
              'build/font-audition/browser-checks.json','build/font-audition/audition-browser.png',
              'build/font-audition/native/validation.json','build/font-audition/native/mixed-case/menu.png',
              'build/english/menu*-validation/report.json','build/english/menu*-validation/*/*.png',
              'tools/check_font_audition.js','tools/verify_font_audition.m']
    for pattern in patterns:
        for p in ROOT.glob(pattern):
            if p.is_file():receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    receipt['scope']='Current T2 compact font, 46 early-menu resources and original window geometry. Seven native menu routes, six ordinary-input action cases, twelve controlled edge cases and 286 controlled item/state cases across 221 bounded definitions. Service/item/typography acceptance is recorded separately. Whole-game layout coverage remains open.'

    require(digest(default_rom().with_suffix('.sav').read_bytes())=='71189f7fb6aed638640078fba3a35fda6c39c8962e74dcc75935aac948da9063','Supplied save changed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(path);return receipt
if __name__=='__main__':run()
