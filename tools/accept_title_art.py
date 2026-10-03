"""Bind native graphics evidence to six owned redirects and the prior release."""
import argparse
import json
from pathlib import Path
from tools.rom import ROOT,digest,load_base,require
from tools.extract_graphics_audition import save_json
from tools.title_art import OWNER,SOURCES,TABLE,APPROVAL,PACKED
from tools.verify_title_art import OUT,BASELINE,CASES


def run(source, insertion_delta=False):
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());original=load_base()
    previous=(BASELINE/'torneko-2-english.gba').read_bytes();old=json.loads((BASELINE/'build.json').read_text())
    require(digest(rom)==build['output_sha256'] and digest(previous)==old['output_sha256'],'ROM identity changed')
    art=build['title_art'];require(art['approval_sha256']==digest(APPROVAL.read_bytes()) and art['manifest_sha256']==digest((PACKED/'manifest.json').read_bytes()),'Graphics approval/packing changed')
    require(art['generator_sha256']==digest((ROOT/'tools/title_art.py').read_bytes()),'Insertion generator changed')
    patches=[p for p in build['patches'] if p['owner']==OWNER];allocations=[a for a in build['allocations'] if a['owner']==OWNER]
    require(len(patches)==len(allocations)==6 and {p['start'] for p in patches}=={TABLE+i*20 for i in SOURCES},'Unexpected patch ownership')
    # Current builds include later, separately owned text fixes. Reconstruct
    # the entire image from its ledger rather than treating every later change
    # as an unauthorized title edit. Strict insertion-only comparison remains
    # available for the original title milestone.
    from tools.rom_build import verify_ledger
    verify_ledger(original, rom, build)
    verify_ledger(original, previous, old)
    prior_allocations={a['id']:a for a in build['allocations']}
    require([(a['id'],a['owner']) for a in build['allocations'] if a['owner']!=OWNER]
            ==[(a['id'],a['owner']) for a in old['allocations']], 'Title baseline resource identities differ')
    first_title=min(a['start'] for a in allocations)
    require(all(prior_allocations.get(a['id'])==a for a in old['allocations'] if a['end_exclusive']<=first_title),
            'Pre-title allocation changed')
    for a in allocations:
        require(a['start']>=len(original) and digest(rom[a['start']:a['end_exclusive']])==a['sha256'],'Unowned/changed resource')
    for start in SOURCES.values():require(rom[start:start+38912]==original[start:start+38912],'Original artwork overwritten')
    require(rom[0x585304:0x58B269]==original[0x585304:0x58B269],'Original credits changed')
    require(build['reviewed_resource_counts']==old['reviewed_resource_counts']
            and build['arrival_cards']==old['arrival_cards'],'Text counts/arrival resources changed')
    if insertion_delta:
        require([a for a in build['allocations'] if a['owner']!=OWNER]==old['allocations'],'Existing allocations changed')
        require([p for p in build['patches'] if p['owner']!=OWNER]==old['patches'],'Existing patches changed')
        restored=bytearray(rom)
        for p in patches:restored[p['start']:p['end_exclusive']]=previous[p['start']:p['end_exclusive']]
        for a in allocations:restored[a['start']:a['end_exclusive']]=previous[a['start']:a['end_exclusive']]
        require(bytes(restored)==previous,'Unrelated ROM bytes changed')
        require(build['reviewed_resource_counts']==old['reviewed_resource_counts'],'Text resources changed')
    native=json.loads((OUT/'native-report.json').read_text())
    require(native['passed'] and native['rom_sha256']==digest(rom) and native['baseline_sha256']==digest(previous),'Native evidence stale')
    require(native['generator_sha256']==digest((ROOT/'tools/verify_title_art.py').read_bytes()),'Native verifier changed')
    require({r['index'] for r in native['cases']}=={i for i,_,_ in CASES} and native['palette_probes']['colors_checked']==640,'Native coverage incomplete')
    for item in native['cases']+ [{'index':'supplied','report':native['supplied_save_route']}]:
        report=item['report'];require(not report['controlled_overrides'],'Unexpected gameplay override')
        require(len(report['transition_frames'])==50 and any(f['native_title_pixels_checked'] for f in report['transition_frames']),'Title transition not checked')
        require(len(report['cases'])==6,'Missing opening/cancel/reopen state')
        for case in report['cases']:
            require(case['all_unedited_screen_pixels_and_ui_bytes_match_baseline'],'Unverified scene/UI preservation')
            require(digest((OUT/'native'/str(item['index'])/(case['phase']+'.png')).read_bytes())==case['png_sha256'],'Native screenshot changed')
    result={'passed':True,'rom_sha256':digest(rom),'baseline_sha256':digest(previous),'source_sha256':digest(original),
            'native_report_sha256':digest((OUT/'native-report.json').read_bytes()),'allocations':allocations,'patches':patches,
            'inserted_title_background_graphics':6,'total_inserted_graphics':build['total_reviewed_inserted_graphics'],
            'text_resource_count':build['total_reviewed_inserted_resources'],
            'pre_title_allocations_preserved':True,'text_resource_identities_and_counts_preserved':True,
            'complete_build_and_baseline_ledgers_verified':True,
            'strict_insertion_delta_checked':insertion_delta,
            'original_artwork_and_credits_preserved':True,'native_scene_cases':36,'native_colour_probes':640,
            'scope':'Approved title plus all five floating-logo backgrounds: six owned resources and six redirects. The native baseline is rebuilt without title resources; later allocations relocate in that comparison. Resource identities/counts and both full ledgers are checked; an exact title-only byte delta is asserted only with strict_insertion_delta_checked. Natural startup/menu/name/cancel/reopen and supplied-save route checked. Final palette conversion preserves the original footer, outside-corner pixels and UI palette. Full-game and later-logo discovery remain separate.'}
    save_json(OUT/'acceptance.json',result);print('Accepted six inserted graphics; resource identities and both build ledgers verified.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--insertion-delta',action='store_true');a=p.parse_args();run(a.source.resolve(),a.insertion_delta)
