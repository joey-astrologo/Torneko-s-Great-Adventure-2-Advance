"""Source/English and native evidence for the separate village-renaming prototype."""
import argparse
import html,json
from tools.rom import ROOT,digest,require
from tools.verify_mayor import OUT


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/mayor-validation'
    build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());rows={r['id']:r for r in build['mayor']['entries']};cards=[];images={};counts={}
    for filename,prefix in (('report.json',''),('editor.json','editor-'),('persistence.json',None)):
        report=json.loads((OUT/filename).read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale mayor evidence');counts[filename]=len(report['cases'])
        for case in report['cases']:
            pictures=[]
            for name,expected in case['images'].items():
                relative=name if prefix is None else prefix+case['case']+'/'+name
                require(digest((OUT/relative).read_bytes())==expected,'Mayor image changed');images[relative]=expected
                pictures.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
            row=rows.get(case.get('id'));text='' if row is None else '<pre>'+html.escape(row['japanese'])+'</pre><pre>'+html.escape(row['english'])+'</pre><p>'+html.escape(str(row['layout']))+'</p>'
            cards.append('<details><summary>'+html.escape(filename+': '+case['case'])+'</summary>'+text+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 village renaming</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}a{color:#bce}</style><h1>Torneko 2 village renaming</h1><p>Separate six-source prototype. Controlled service entry; native dialogue, keyboard, confirmation/cancellation and correction, followed by ordinary book saves and fresh cold reloads. Eight-cell legacy field rendering is stress-tested separately. Ordinary mayor unlocking remains unverified.</p>'''
    page=page.replace('Separate six-source prototype.', 'Six owned sources.').replace('Separate two-source prototype.', 'Two owned sources.').replace('Separate five-source prototype.', 'Five owned sources.') if cumulative else page
    (OUT/'index.html').write_text(page+''.join(cards)+'\n');(OUT/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'case_counts':counts,'images':images},indent=2)+'\n');print(OUT/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

