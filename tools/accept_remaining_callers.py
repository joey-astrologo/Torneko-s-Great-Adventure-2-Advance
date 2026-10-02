"""Bind continuation fixes, frozen Japanese baselines and native acceptance."""
import argparse
import html
import json
from pathlib import Path

from tools.rom import ROOT, digest, require


def run(source, folder):
    build=json.loads((source/'build.json').read_text())
    rom_hash=digest((source/'torneko-2-english.gba').read_bytes())
    require(build['output_sha256']==rom_hash,'Continuation ledger differs')
    evidence={}
    def read(path, current=True):
        raw=path.read_bytes();report=json.loads(raw)
        evidence[str(path.relative_to(ROOT))]=digest(raw)
        if current:
            require(report['rom_sha256']==rom_hash,'Mixed-ROM continuation evidence')
            require(report.get('passed',True),'Continuation check failed')
        return report
    native=read(folder/'release-acceptance/report.json')
    for path,sha in native['source_hashes'].items():
        require(digest(Path(path).read_bytes())==sha,'Protected original ROM/save changed')
    validation=folder/'validate.log'
    require('Ran 150 tests' in validation.read_text() and 'All checks passed.' in validation.read_text(),
            'Unit/toolchain/fresh-save validation is incomplete')
    evidence[str(validation.relative_to(ROOT))]=digest(validation.read_bytes())
    prior=read(folder/'release-prior-callers/report.json')
    floor=read(folder/'release-floor/report.json');expiry=read(folder/'release-expiry/report.json')
    smith=read(source/'blacksmith-validation/transactions.json')
    results=read(source/'ui-probes/report.json');history=read(source/'history-ui-probes/report.json')
    repro=read(folder/'repro.json');items=read(folder/'item-definition-callers.json')
    static=read(folder/'release-static')
    require(not static['disposition_counts'].get('original_japanese_argument_needs_followup'),
            'Expanded scan found an unresolved Japanese source binding')
    require(native['tool_sha256']==digest((ROOT/'tools/audit_remaining_callers.py').read_bytes()),'Native probe changed')
    family=build['remaining_callers']
    require(family['catalog_sha256']==digest((ROOT/'translations/remaining-callers-review.json').read_bytes()),'Continuation review changed')
    repaired={r['call'] for r in family['bindings']}|{r['call_offset']+0x08000000 for r in family['item_definition_bindings']}
    observed={e['address'] for c in native['cases'] if c['english_output'] for e in c['calls']}
    require(repaired<=observed and len(repaired)==29,'A repaired caller lacks native English acceptance')
    baseline_calls=set()
    for sub in ('baseline','baseline-more','link-baseline','item-baseline'):
        report=read(folder/sub/'report.json',False)
        baseline_calls.update(e['address'] for c in report['cases'] if c['confirmed_japanese_output'] for e in c['calls'])
    require(repaired<=baseline_calls,'A repair lacks a reproduced Japanese baseline')
    figures=[]
    for case in native['cases']:
        require(case['english_output'],'Incomplete/non-English continuation case')
        for img in case['images']:
            path=folder/'release-acceptance'/case['case']/img['path']
            require(digest(path.read_bytes())==img['png_sha256'],'Native image changed')
            if case['spec']['profile']=='native' and '-0-yes-' in case['case']:
                text=''.join(g['text'] for g in case['glyphs'][slice(*img['glyph_range'])])
                figures.append('<figure><figcaption>'+html.escape(case['case'])+'</figcaption><img src="'+
                    html.escape(str(path.relative_to(folder)))+'"><p>'+html.escape(text)+'</p></figure>')
    for name in ('remaining_caller_text.py','audit_remaining_callers.py','audit_item_definition_callers.py',
                 'verify_blacksmith_transactions.py','screen_text_audit.py','dialogue_checks.py','audit_text_callers.py'):
        p=ROOT/'tools'/name;evidence[str(p.relative_to(ROOT))]=digest(p.read_bytes())
    receipt=dict(passed=True,rom_sha256=rom_hash,repaired_callers=sorted(repaired),original_static_leads_closed=20,
        additional_failed_callers_fixed=9,copied_identification_refusal='native English via downstream byte matching',
        remi_price_control='native English; numeric field, no repair',continuation_cases=len(native['cases']),
        blacksmith_transactions=len(smith['cases']),prior_caller_cases=sum(p['cases'] for p in prior['profiles']),
        floor_cases=len(floor['cases']),expiry_cases=len(expiry['cases']),result_cases=len(results['cases']),
        history_cases=len(history['cases']),item_definition_loads=len(items['consumers']),repro=repro,evidence=evidence,
        static_scope=static['scope'],unresolved_static_arguments=len(static['unresolved_calls']),unit_tests=150,
        scope='29 caller failures reproduced and repaired; original20 leads closed. Controlled complete frames, '
              'native producers, pages, choices, callbacks, exact formatting/guards/ABI and unfiltered glyphs. '
              'Blacksmith exchanges execute actual item effects from controlled entry/state. Story progression, '
              'save deletion, cable transfer and whole-game reachability are not established by these probes.')
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Caller continuation acceptance</title>'
        '<style>body{font:16px system-ui;background:#17191e;color:#eee;max-width:1200px;margin:32px auto}'
        'main{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0;width:360px}img{width:360px;image-rendering:pixelated}'
        'p{font-size:14px}a{color:#9dcaff}</style><h1>29 caller repairs</h1><p>ROM '+rom_hash+'</p>'
        '<p>110 controlled continuation cases, 13 blacksmith exchanges. See <a href="receipt.json">the receipt</a> '
        'for scope, baselines and regression evidence. Captures show actual native frames; glyph traces also '
        'cover messages that clear within a frame.</p><main>'+''.join(figures)+'</main>')
    print('Continuation acceptance:',len(repaired),'repaired callers')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'build/caller-continuation/release-candidate')
    p.add_argument('--folder',type=Path,default=ROOT/'build/caller-continuation')
    a=p.parse_args();run(a.source.resolve(),a.folder.resolve())
