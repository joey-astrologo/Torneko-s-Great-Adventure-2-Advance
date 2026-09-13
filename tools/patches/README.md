# Tool build compatibility patches

`mgba-0.10.5-optional-ereader.patch` targets upstream commit
`26b7884bc25a5933960f3cdcd98bac1ae14d42e2` (release 0.10.5).

That release compiles its e-Reader image-scanning implementation only with FFmpeg,
but declares those functions unconditionally in headers consumed by CFFI. Building
the Python bindings with FFmpeg disabled then produces an extension that fails to
import because those optional symbols are absent.

The patch applies the same `USE_FFMPEG` condition to the scanning declarations.
It leaves the cartridge emulation declarations available. The build helper applies
it idempotently before compiling; no ROM changes are involved.

Lua is disabled separately in the Python library build because this release's
CMake discovery does not handle the installed Lua 5.5 package. Lua scripting is
available in the separately installed mGBA desktop application.

`gba-loader-remove-unused-jython-import.patch` targets loader commit
`9bfb2d1fe891aa78bab7093a328feb3a52318ab7`. It removes an unused import of
`org.python.bouncycastle.util.Arrays`, which is absent from current Ghidra's
build classpath. The loader does not use that class, so no replacement dependency
is needed. `tools/build_gba_loader.sh` applies the patch before building.
