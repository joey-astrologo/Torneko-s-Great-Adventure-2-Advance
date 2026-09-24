"""Audition contexts backed by the cumulative synthesis/Remi native reports."""
import json
from tools.rom import ROOT,require


def append_contexts(config,build):
    for family,files in {'gaibara':['menus.json','selector.json'],
                         'remi':['menus.json','vocations.json','pickers.json','warp-menus.json']}.items():
        for filename in files:
            report=json.loads((ROOT/f'build/english/{family}-validation'/filename).read_text())
            require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Town service budget evidence stale')
    def add(ident,name,width,inset,rows,labels,capture,note):
        config['contexts'].append({'id':'town-services-current-'+ident,'name':name,'stage':'current',
            'window':width,'start':inset,'end':width,'rows':rows,'labels':labels,'alternatives':[],
            'capture':'build/english/'+capture,'reference':'docs/MEMORY_MAP.md','note':note})
    g={r['index']:r for r in build['gaibara']['entries']};r={r['index']:r for r in build['remi']['entries']}
    add('synthesis','Synthesis commands',72,12,3,g[112]['english'],'gaibara-validation/menu-cancel/root.png',
        'Original72px panel and two six-pixel structural cursor spaces.60px label budget. All choices, help and repeated reopening pass.')
    add('which','Shared item selection heading',40,0,1,[build['selection_prompt']['entries'][0]['english']],
        'gaibara-validation/selector-info-reopen/opened.png','Original40px heading atx8; inventory atx64 preserves8px outer-border gap. Three Info/cancel cycles restore both panels exactly.')
    add('remi-root','Remi services',112,12,5,[r[i]['english'] for i in (201,204,202,203,205)],
        'remi-validation/root-4-gate-1/root.png','Original112px panel,12px structural cursor reserve and100px labels. Ten profile/gate cases pass.')
    for vocation in range(3):
        add('vocation-'+str(vocation),'Change vocation: '+r[164+vocation]['english'],72,12,3,r[154+vocation]['english'],
            f'remi-validation/vocation-{vocation}-cancel/choices.png','Original72px panel and12px cursor reserve. Both offered vocations, both answers, Cancel and Leave pass; labels preserve choice order.')
    for index in (129,140,176):
        add('number-'+str(index),'Remi number selector: '+r[index]['english'],88,0,1,[r[index]['english'].replace('{number}','99')],
            f'remi-validation/remi.{index}-number-99-B/picker.png','Original88px panel. Only the three owned templates use proportional advance; unknown formats keep12px. Native aliases use the same compact digit glyphs as this font. Runtime compiler conservatively reserves14px for two digits and128bytes for output.')
    names={n['dungeon_id']:n['english'] for n in build['remi']['warp_names']['entries']}
    add('warp-first','Warp destinations: first page',128,6,5,[names[i] for i in (0,2,1,4,3)],
        'remi-validation/warp-pages-0-0/first-page.png','Original128px panel with native6px inset leaves122px. Native order, cursor, cancellation and exact pixel restoration after paging pass.')
    for vocation,ids in ((0,[5,6,8]),(1,[5,6,8,9]),(2,[5,6,8,10])):
        add('warp-second-'+str(vocation),'Warp destinations: '+r[164+vocation]['english'],128,6,4,[names[i] for i in ids],
            f'remi-validation/warp-pages-{vocation}-0/second-page-0.png','Original second-page geometry and native vocation filtering;18 repeated page restorations and all ten destination selections pass. Other dungeon/title/result consumers remain separate.')

    well=json.loads((ROOT/'build/english/well-picker-validation/report.json').read_text())
    require(well['passed'] and well['rom_sha256']==build['output_sha256'],'Well picker budget evidence stale')
    add('well-level','Well difficulty selector',88,0,1,['Level 10'],
        'well-picker-validation/progress-10-initial/initial.png',
        'Original88px number panel. Reuses the exact owned Remi proportional template; native progress caps, minimum/maximum, cancellation and return flags pass.')
