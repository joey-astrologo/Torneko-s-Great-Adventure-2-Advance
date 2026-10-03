"""Observe every text consumer/glyph while running an existing native verifier.

Adds observation breakpoints in this process only. The original verifier sees
only its own registered events, preserving run_until predicates and event caps.
Original callback controls run first; the observer records resulting registers.
This adds unfiltered display evidence, not natural-route reachability.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys
import traceback

from tools import emulator
from tools import rom as rom_module
from tools.audit_text_callers import CONSUMERS
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit, display_text
from tools.text_codec import tokenize


def run(module, arguments, source, output):
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'], 'Native caller audit ROM differs')
    output.mkdir(parents=True,exist_ok=True)
    tool_hashes = {p:digest((ROOT/'tools'/p).read_bytes()) for p in
                   ('audit_native_callers.py','emulator.py','screen_text_audit.py','audit_menu_layouts.py')}
    verifier_hash = digest((ROOT/Path(*module.split('.'))).with_suffix('.py').read_bytes())
    original_init = emulator.Debugger.__init__
    original_entered = emulator.Debugger._entered
    original_breakpoint = emulator.Debugger.breakpoint
    original_close = emulator.Debugger.close
    cases = []

    def init(self, session, callback=None, max_events=10000):
        self.audit_enabled = session.rom_sha256 == digest(rom)
        self.audit_points = set()
        self.audit_recorded = False
        self.audit_calls = {}
        if self.audit_enabled:
            self.text_audit = ScreenTextAudit(session)
        original_init(self,session,callback,max_events)
        if self.audit_enabled:
            for address in set(ScreenTextAudit.ADDRESSES)|set(CONSUMERS):
                original_breakpoint(self,address)

    def breakpoint(self,address):
        self.audit_points.add(address)
        return original_breakpoint(self,address)

    def entered(self,native,reason,info):
        if not self.audit_enabled or info==emulator.ffi.NULL:
            return original_entered(self,native,reason,info)
        if reason not in (emulator.lib.DEBUGGER_ENTER_BREAKPOINT,emulator.lib.DEBUGGER_ENTER_WATCHPOINT):
            return original_entered(self,native,reason,info)
        # Watchpoints are always owned by the underlying verifier.
        owned = reason==emulator.lib.DEBUGGER_ENTER_WATCHPOINT or int(info.address) in self.audit_points
        if owned:
            original_entered(self,native,reason,info)
        try:
            if reason!=emulator.lib.DEBUGGER_ENTER_BREAKPOINT:
                return
            cpu = emulator.ffi.cast('struct ARMCore*',self.session.core._core.cpu)
            event = dict(kind='breakpoint',address=int(info.address),frame=self.session.core.frame_counter,
                         registers=[int(r)&0xffffffff for r in cpu.gprs],thumb=bool(cpu.cpsr.packed&0x20))
            self.text_audit.callback(event)
            if event['address'] in CONSUMERS:
                r = event['registers'];pointer = r[CONSUMERS[event['address']][1]]
                raw = bytes(self.session.core.memory[pointer:pointer+2048])
                try:
                    tokens,end = tokenize(raw)
                    stream = dict(raw_hex=raw[:end].hex(),text=display_text(tokens,formatting=event['address']==0x08000FB8))
                except ValueError as error:
                    stream = dict(error=str(error),sample_hex=raw[:128].hex())
                key = (event['address'],r[14],pointer,stream.get('raw_hex'))
                if key not in self.audit_calls:
                    self.audit_calls[key] = dict(consumer=event['address'],call=(r[14]&~1)-4,
                        source=pointer,arguments=r[:4],first_frame=event['frame'],observations=0,**stream)
                self.audit_calls[key]['observations'] += 1
        except Exception as error:
            if not self.errors:
                self.errors.append(error)
        finally:
            native.state = emulator.lib.DEBUGGER_RUNNING

    def close(self):
        if self.audit_enabled and not self.audit_recorded:
            self.audit_recorded = True
            audit = self.text_audit.report()
            ident = len(cases)
            row = dict(index=ident,session_output=str(self.session.output),inputs=self.session.inputs,
                calls=list(self.audit_calls.values()),audit=audit,
                observer_errors=[repr(e) for e in self.errors],
                reader_active_at_probe_end=bool(self.text_audit.observer.stack))
            row['passed'] = not any((audit['unclassified_glyphs'],audit['unreadable_streams'],
                                     audit['layout_violations'],row['observer_errors']))
            name = f'case-{ident:04d}.json'
            (output/name).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
            cases.append(dict(index=ident,report=name,passed=row['passed'],calls=len(row['calls']),
                glyphs=len(audit['glyphs']),reads=len(audit['reads']),
                findings={k:len(audit[k]) for k in ('unclassified_glyphs','unreadable_streams','layout_violations')},
                reader_active_at_probe_end=row['reader_active_at_probe_end']))
        original_close(self)

    error = None
    previous_argv = sys.argv
    real_root = rom_module.ROOT
    class AuditRoot(type(real_root)):
        """Redirect generated cumulative outputs, retaining source/tool paths."""
        def __truediv__(self, key):
            path = super().__truediv__(key)
            prefix = real_root/'build/english'
            if path.is_relative_to(prefix):
                return source.resolve()/path.relative_to(prefix)
            return path
    try:
        emulator.Debugger.__init__ = init
        emulator.Debugger._entered = entered
        emulator.Debugger.breakpoint = breakpoint
        emulator.Debugger.close = close
        rom_module.ROOT = AuditRoot(real_root)
        sys.argv = [module]+arguments
        runpy.run_module(module,run_name='__main__')
    except Exception as exc:
        error = str(exc)+(': '+repr(exc.__cause__) if exc.__cause__ else '')
        (output/'error.txt').write_text(traceback.format_exc())
    finally:
        emulator.Debugger.__init__ = original_init
        emulator.Debugger._entered = original_entered
        emulator.Debugger.breakpoint = original_breakpoint
        emulator.Debugger.close = original_close
        sys.argv = previous_argv
        rom_module.ROOT = real_root
    report = dict(rom_sha256=digest(rom),module=module,arguments=arguments,error=error,cases=cases,
        passed=bool(cases) and error is None and all(c['passed'] for c in cases),
        tools=tool_hashes, verifier_sha256=verifier_hash,
        tools_unchanged=all(digest((ROOT/'tools'/p).read_bytes())==h for p,h in tool_hashes.items()),
        scope=__doc__)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Unfiltered caller audit:',module,len(cases),'sessions; passed:',report['passed'],error,flush=True)
    require(report['passed'], 'Native caller audit has findings: '+str(output/'report.json'))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('module')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args = parser.parse_args()
    run(args.module,args.arguments,args.source,args.output)
