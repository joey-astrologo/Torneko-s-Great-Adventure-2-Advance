# Link error callers and recovery

October 7, 2026. This is a text and protocol-path audit, not a graphics audit.
The current English ROM is `588dc92ce09104cb80d18fb4929e6e713f86836e65d8c12b135dfb4f4269b7ad`.
The refreshed [October 7 release checkpoint](../build/releases/2026-10-07-text-audit.zip)
contains the unchanged accepted patch. The root outputs are
`build/torneko-2-english.gba` and `.bps`.

## Finding

All five error messages work through their native selectors and complete error
handler. A separate original-game recovery defect is reproduced in both the
Japanese and English ROMs: hardware-error and extra-system exits after the
intermediate save discard the offered item. The item remains absent after a
battery-only cold load. The ordinary timeout path restores it correctly.

The hardware fault latch and third participant sample are deliberately injected;
these observations do not establish a failure rate with physical cables. The
original code has the same missing restoration branches. The user explicitly
chose to preserve original gameplay behavior. This finding is closed as
documented original behavior; no gameplay repair has been inserted or is planned.

## Callers and conditions

The green-book script calls owner `08057C54` from `0804A18A`; after its native
picker and confirmations it calls protocol `08058110` at `08057D42`.
Protocol failure returns `-1`, exits the owner and returns to town. Error handler
`08057C1C` stops serial operation, constructs the selected English message,
displays it, sorts storage at `08057C3C`, and returns `-1`.

| Index | English message | Actual selecting condition |
|---|---|---|
| 0 | No response from the other player. | Protocol timeout after connection, or timeout during reconnect after the intermediate save; `080585EC`. Saved transactions first restore storage and save it again at `080585C2..080585EC`. |
| 1 | Hardware error. | Native status bit `1000`, constructed from serial-driver fault byte `02012859`; `080581B8` leads to `08058600`. |
| 2 | Connect only two systems. | Native status bit `2000`, constructed when the SIOCNT participant ID exceeds 1; `080581C4` leads to `08058608`. |
| 3 | No other player found. | The 500-iteration initial connection deadline expires before a save; `08058268..08058282`. |
| 4 | Data was not received correctly. | Received record count in `r9` differs from the peer's advertised count after the transfer handshake; `080585A6..080585B0`. |

Every error also displays “Check the link cable.” The existing bounded formatter
checks remain relevant for the 128-byte buffer and maximum message width.
This audit additionally exercises the real selection, storage cleanup, native
owner return and cold-load state. It does not redirect execution into an error
label, substitute the error index or skip cleanup.

The switch at `0805821E` has five targets at ROM `[00058254,00058268)`:
`08058268`, `080582E4`, `0805834C`, `080584D4`, `08058518`.
Each target was explicitly disassembled; the initial Ghidra decompilation did
not follow that computed switch automatically. Its first incomplete pseudocode
is not evidence that those blocks are unreachable.

## Native cases

Entry uses ordinary green-book inputs and the two native bread/staff saves from
`tools.verify_link_entry`. No story, map, item, menu or entry-register overrides
are used. Each run uses disposable cartridges and saves.

| Scenario | Observed errors | Inventory/save result |
|---|---|---|
| No cable | 3 | Unchanged, including cold load |
| Hardware fault before transfer (injected latch) | 1 | Unchanged, including cold load |
| Third system before transfer (injected SIOCNT sample) | 2 | Unchanged, including cold load |
| Received-count mismatch on one peer (injected count) | 4 on that peer; 0 on the other | Both restored; the other peer executes the rollback save |
| Delayed confirmation on one peer | 3 on both | Unchanged, including cold load |
| One peer declines the connection prompt | 3 on waiting peer; no error on declining peer | Unchanged, including cold load |
| Disconnect during protocol phases 1, 2 or 3 | 0 on both, each phase separately | Unchanged, including cold load |
| Disconnect during phase 4, after intermediate save | 0 on both | Both restored and saved; cold loads retain exact original item properties |
| Cancel picker, item confirmation or connection confirmation | No protocol error; three separate cases | Unchanged, native town return |
| Hardware fault after intermediate save (injected latch) | 1 on both | Offered item lost on both; also reproduced in original ROM and cold loads |
| Third-system indication after intermediate save (injected sample) | 2 on both | Offered item lost on both; also reproduced in original ROM and cold loads |

Disconnects detach the pinned mGBA native link driver; both cores then continue
normally. Asymmetric inputs retain their actual per-peer frame schedules.
Fault injection is recorded with the triggering instruction, registers and
before/after value. These cases do not simulate arbitrary electrical noise,
all possible timing offsets, power loss during writes, or a physical third GBA.

## Evidence and reproduction

```sh
bash tools/ghidra.sh functions build/link-errors/functions.txt 0x08057C1C 0x08057C54 0x08058110
bash tools/ghidra.sh functions build/link-errors/switches.txt 0x08058268 0x080582E4 0x0805834C 0x080584D4 0x08058518 0x08058610 0x0805869C 0x080587C8 0x08058764
bash tools/ghidra.sh functions build/link-errors/save-driver.txt 0x08058098 0x08058598 0x08058934 0x080588C0 0x08057BB0
.venv/bin/python -m tools.verify_link_errors --output build/link-errors/verified
.venv/bin/python -m tools.verify_link_errors --original-baseline --cases hardware-after-save third-system-after-save --output build/link-errors/original
```

[English report](../build/link-errors/verified/report.json) ·
[Original-ROM comparison](../build/link-errors/original/report.json) ·
[Disassembled owner](../build/link-errors/functions.txt) ·
[Explicit switch targets](../build/link-errors/switches.txt) ·
[Save/restore code](../build/link-errors/save-driver.txt).

The verifier asserts exact error identities, complete cleanup and owner ABI,
English glyph/layout output, expected inventory contents and battery-only
reloads. Its report separates text checks from `inventory_preserved`; reproduced
item-loss cases are documented original behavior, not successful recovery or
pending repair work. `--original-baseline` explicitly omits English-only display
acceptance. The optional `--expect-recovery` diagnostic would reject the original
lost-item behavior; it is not a release requirement. The default verifier checks
the preserved original outcomes.
