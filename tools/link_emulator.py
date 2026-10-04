"""Two disposable Session cores using the pinned native mGBA link driver."""
import ctypes as C
import json
import shlex
import subprocess
import time

from tools.emulator import ffi, version
from tools.rom import ROOT, digest, require


def compile_bridge(output):
    require(version() == '0.10.5', 'Reinspect link scheduling for another mGBA')
    output.mkdir(parents=True, exist_ok=True)
    native = ROOT / '.tools/build/mgba'
    flags = (native / 'CMakeFiles/mgba.dir/flags.make').read_text()
    defines = next(line.split('=', 1)[1] for line in flags.splitlines()
                   if line.startswith('C_DEFINES ='))
    source = ROOT / 'tools/link_bridge.c'
    library = output / 'link_bridge.dylib'
    command = ['cc', '-dynamiclib', '-O2', '-DNDEBUG', *shlex.split(defines),
               '-I'+str(ROOT / '.tools/src/mgba/include'), '-I'+str(native / 'include'),
               str(source), '-L'+str(native), '-lmgba', '-Wl,-rpath,'+str(native),
               '-o', str(library)]
    subprocess.run(command, check=True, capture_output=True)
    evidence = dict(emulator=version(), compiler_command=command,
        bridge_source_sha256=digest(source.read_bytes()),
        bridge_binary_sha256=digest(library.read_bytes()),
        emulator_binary_sha256=digest((native / 'libmgba.0.10.5.dylib').read_bytes()),
        native_sources={str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in (
            ROOT / '.tools/src/mgba/src/gba/sio/lockstep.c',
            ROOT / '.tools/src/mgba/src/platform/qt/MultiplayerController.cpp',
            ROOT / '.tools/src/mgba/src/arm/arm.c',
            ROOT / '.tools/src/mgba/src/debugger/debugger.c')},
        scope='Cooperative host scheduling of the original native SIO lockstep driver. '
              'No ROM, native emulator library, protocol, serial register or IRQ patches.')
    (output / 'bridge.json').write_text(json.dumps(evidence, indent=2)+'\n')
    return library, evidence


class LinkPair:
    """Attach after restoring snapshots; detach before destroying either core.

    Both Sessions must have a Debugger. Never restore snapshots while attached:
    raw mGBA states do not serialize the shared host-side link driver.
    """
    def __init__(self, games, library):
        require(len(games) == 2 and all(g.debugger is not None for g in games),
                'Link pair needs two live debugged Sessions')
        self.games = games
        self.inputs = []
        self.api = b = C.CDLL(str(library))
        b.pair_gba_size.restype = C.c_size_t
        require(b.pair_gba_size() == ffi.sizeof('struct GBA'), 'Native/CFFI GBA layout differs')
        b.pair_create.argtypes = [C.c_void_p, C.c_void_p]
        b.pair_create.restype = C.c_void_p
        b.pair_pump.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
        b.pair_count.argtypes = [C.c_void_p, C.c_int]
        b.pair_count.restype = C.c_uint64
        b.pair_awake.argtypes = [C.c_void_p, C.c_int]
        b.pair_words.argtypes = [C.c_void_p, C.POINTER(C.c_uint16)]
        b.pair_destroy.argtypes = [C.c_void_p]
        self.debuggers = [int(ffi.cast('uintptr_t', g.debugger.native)) for g in games]
        self.native = b.pair_create(*[int(ffi.cast('uintptr_t', ffi.addressof(g.core._native, 'sio')))
                                     for g in games])
        require(self.native, 'Could not create native link pair')

    def frames(self, count):
        require(isinstance(count, int) and count >= 0, 'Invalid linked frame count')
        before = [g.core.frame_counter for g in self.games]
        targets = [f+count for f in before]
        deadline = time.monotonic()+60
        while any(g.core.frame_counter < target for g, target in zip(self.games, targets)):
            self.api.pair_pump(self.native, *self.debuggers)
            for game in self.games:
                game.debugger.check_errors()
            require(any(self.api.pair_awake(self.native, i) for i in range(2)), 'Native link deadlocked')
            require(time.monotonic() < deadline, 'Native link frame budget exceeded')
        self.inputs.append(dict(frames=count, before=before,
                                after=[g.core.frame_counter for g in self.games]))

    def press(self, key, wait=120, hold=2):
        require(hold > 0 and wait >= 0, 'Invalid linked input schedule')
        before = [g.core.frame_counter for g in self.games]
        codes = [getattr(g.core, 'KEY_'+key.upper()) for g in self.games]
        for game, code in zip(self.games, codes):
            game.core.set_keys(code)
        try:
            self.frames(hold)
        finally:
            for game, code in zip(self.games, codes):
                game.core.clear_keys(code)
        self.frames(wait)
        self.inputs.append(dict(key=key, peers=[0,1], hold=hold, released=wait,
                                before=before, after=[g.core.frame_counter for g in self.games]))

    def report(self):
        counts = [self.api.pair_count(self.native, i) for i in range(3)]
        words = (C.c_uint16*(2*min(counts[1], 16384)))()
        self.api.pair_words(self.native, words)
        raw = bytes(words)
        return dict(started=counts[0], master_finished=counts[1], slave_finished=counts[2],
                    wire_words=[list(pair) for pair in zip(words[::2], words[1::2])],
                    wire_sha256=digest(raw), wire_capture_complete=counts[1] <= 16384,
                    inputs=self.inputs)

    def close(self):
        if self.native:
            self.api.pair_destroy(self.native)
            self.native = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
