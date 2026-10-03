"""Triage every observed producer context, including copied static notices.

A producer candidate is not proof of the complete buffer's contents. This
report preserves unknown formats and identifies Japanese format candidates for
code-path review, without equating intermediate Japanese bytes with a failure.
"""
from collections import Counter
import argparse
import json
from pathlib import Path

from tools.audit_source_readers import inserted_resources
from tools.rom import ROOT, digest, require
from tools.text_codec import readable, tokenize


def run(source=ROOT/'build/english', folder=ROOT/'build/localization-closure', trace_path=None):
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    trace_path = trace_path or folder/'source-readers-deep.json'
    trace = json.loads(trace_path.read_text())
    require(digest(rom) == build['output_sha256'] == trace['rom_sha256'], 'Producer audit ROM differs')
    storage_path = folder/'storage-readers.json'
    storage = json.loads(storage_path.read_text())
    require(storage['rom_sha256'] == digest(rom), 'Storage follow-up ROM differs')
    previously_unknown = {r['call'] for r in trace['argument_followup']
                          if r['classification']=='unresolved-data-flow'}
    storage_bindings = []
    for call in sorted(previously_unknown & {r['call'] for r in storage['routes']}):
        matches = [r for r in storage['routes'] if r['call']==call]
        if all(r.get('binding')=='bound-english-resource' for r in matches):
            storage_bindings.append(dict(call=call,routes=matches))
    english = {r['offset']+0x08000000:r for r in inserted_resources(build)}
    notices = {r['source']['offset']+0x08000000:r for r in build['combat']['queue_notices']['entries']}
    native_path = source/'queue-notice-validation/report.json'
    native = json.loads(native_path.read_text())
    require(native['passed'] and native['rom_sha256'] == digest(rom)
            and native['copied_strings_tested'], 'Copied-notice native evidence differs')
    require('notice_compare:' in build['combat']['helper_source'], 'Copied-notice adapter absent')
    native_cases = {r['case'] for r in native['cases']}
    contexts = {}
    for consumer in trace['argument_followup']:
        for producer in consumer['producer_candidates']:
            arguments = tuple(None if a is None else tuple(a) for a in producer['arguments'])
            key = producer['call'],producer['target'],arguments
            context = contexts.setdefault(key,dict(call=producer['call'],target=producer['target'],
                                                   arguments=arguments,consumers=[]))
            if consumer['call'] not in context['consumers']:
                context['consumers'].append(consumer['call'])
    for row in contexts.values():
        argument = row['arguments'][1]
        if row['target'] != 0x08000FB8:
            row['classification'] = 'other-helper'
        elif argument is None:
            row['classification'] = 'unknown-format'
        elif argument[1] in english:
            row.update(classification='reviewed-English-format',english=english[argument[1]]['english'])
        elif 0x08000000 <= argument[1] < 0x08000000+len(rom):
            tokens,end = tokenize(rom,argument[1]-0x08000000)
            text = readable(tokens)
            row.update(classification='other-ROM-format',text=text)
            if any('\u3040' <= c <= '\u9fff' for c in text):
                row['classification'] = 'Japanese-format-candidate'
                notice = notices.get(argument[1])
                if notice:
                    raw = rom[argument[1]-0x08000000:end]
                    require(raw.hex() == notice['source']['raw_hex'] and b'%' not in raw,
                            'Mapped notice is not an exact static format')
                    cases = [notice['id']+f'-copied-flag{flag}' for flag in (0,1)]
                    require(set(cases) <= native_cases, 'Mapped copied notice lacks native cases')
                    row.update(classification='copied-static-notice-mapped-at-queue',
                        notice_id=notice['id'],english=notice['english'],native_cases=cases,
                        source_hex=raw.hex(),queue_path_review='copied-producer-leads.txt')
        else:
            row['classification'] = 'RAM-format'
    rows = list(contexts.values())
    report = dict(rom_sha256=digest(rom),tool_sha256=digest(Path(__file__).read_bytes()),
        trace_sha256=digest(trace_path.read_bytes()),native_report_sha256=digest(native_path.read_bytes()),
        storage_report_sha256=digest(storage_path.read_bytes()),additional_storage_bindings=storage_bindings,
        counts=dict(Counter(r['classification'] for r in rows)),contexts=rows,scope=__doc__)
    (folder/'buffer-producers.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Producer contexts:',report['counts'])
    require(not any(r['classification']=='Japanese-format-candidate' for r in rows),
            'Unmapped Japanese producer candidates need caller/native investigation')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--folder',type=Path,default=ROOT/'build/localization-closure')
    parser.add_argument('--trace',type=Path)
    args=parser.parse_args();run(args.source,args.folder,args.trace)
