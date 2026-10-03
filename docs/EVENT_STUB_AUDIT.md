# Single-character event source audit — 2026-10-02

The Japanese ROM contains 36 event records consisting of one character and a
terminator. These are source anomalies, not full Japanese sentences awaiting
translation. On 2026-10-02 the user approved contextual repairs for the two
referenced records. Both are now inserted and verified. Their provenance remains
explicitly editorial reconstruction, not recovered Japanese dialogue.

`tools.research_event_script_refs`, `tools.research_npc_script_refs` and
`tools.research_npc_control_flow` account for the extracted script references.
The ordinary event scan covers 133 roots in seven banks. Conservative NPC branch
traversal follows both outcomes of flag/choice branches and stops at END.

| Classification | Records | Evidence and limit |
| --- | ---: | --- |
| Referenced by NPC branch traversal | 2 | Native selectors and full follow-on handlers exercised below; ordinary map access is not established. |
| Present after an unconditional END in a linear scan | 3 | `event-bank-2.382a`, `.382d`, `.3830`; the bank-2 script at decoded `0x5AB` reaches END at `0x5AE` first. These bytes are not an executable fallthrough. |
| No reference in these extracted script roots | 31 | Remain source records with unproven reachability. This is not a claim that all possible readers are known or that the records are unused. |

The malformed bank-2 selector at decoded `0x5E2` is outside the declared script
region ending at `0x5E0`; another root at `0x5DF` runs out of operands. These are
original-data anomalies. No range is treated as free space or translated by
guessing a missing script. Direct event getters and tutorial bank/map pairs are
separate from NPC script traversal; see `MEMORY_MAP.md`.

## Confirmed follow-on behavior

The initial [`tools.research_event_stubs`](../tools/research_event_stubs.py) report
contains six controlled cases on the preceding 3,811-resource build. The native bank loader and NPC selector
choose the original script; the original flag, dialogue, choice and actor
handlers execute its original operands. A host driver dispatches these handlers
and skips WAIT before END. It records every override, input, source, branch,
image hash and handler return guard. This is controlled handler evidence, not
an ordinary walk to either NPC. Inventory and battery-save bytes are preserved.

- **Saruyama:** bank 3, map 11, NPC selectors 1 and 2. The source
  `event-bank-3.3ec2` is only `サ`. Both selectors open the same Yes/No prompt.
  Yes reaches the existing English Synthesis-pot tutorial (`.3ef9`); No reaches
  “Saruyama: I-I see. My apologies.” (`.3ec5`). Both then terminate after WAIT.
  There is no concatenated text or hidden continuation supplying the question.
- **Bratty boy:** bank 4, map 5, selector 1. With flag `0x82` clear, `.0c68`
  displays his complete, already translated speech about his busy father, then
  sets the flag. With that flag set, `.0d25` displays only `な` and ends. No
  subsequent handler supplies missing words.

The isolated characters match the first character of each Japanese speaker
label. That supports an unfinished-source inference; it does not recover an
intended sentence. The other 34 records cannot responsibly be assigned invented
dialogue on this evidence.

Native report: [six follow-on cases](../build/localization-closure/event-stubs/report.json).
Static report: [all 36 source IDs](../build/event-script-audit/npc-control-flow.json).

## Approved repairs — inserted and verified

The agreed translation source is the pinned Japanese ROM. Its two records do
not contain enough text for a sentence translation. The user approved these
exact editorial repairs on 2026-10-02 (“Yes fix them please my friend”):

1. The Saruyama stub now reads **“Saruyama: Shall I explain how to use a
   Synthesis pot?”** This is reconstructed from the verified Yes/No outcomes.
2. The boy's repeat stub now reads **“Bratty boy: My dad's so busy, he doesn't
   even have time for a bath!”** This reuses the first paragraph of his already
   translated initial speech and introduces no new story information.

Both replacements compile to one two-line page in the selected font without adding
event controls. Saruyama's lines measure 192/74px; the boy's measure 212/131px,
within the existing 216px authored budget. The encoded streams are 106 and
134 bytes. [Layout-only evidence](../build/localization-closure/event-stubs/proposed-layouts.json)
records their exact wording and wrapping. Approval, source bytes/hashes and the
reason for each reconstruction are stored in
[`event-prose-review.json`](../translations/event-prose-review.json), carried
into the build ledger and source inventory.

The existing `RomBuild` event-bank allocator binds bank 3 group 23/index 0 and
bank 4 group 6/index 1 to the new streams. Scripts, native choice/flag handlers,
window geometry and decoded bank sizes are unchanged. No RAM/save storage is added.

[`tools.verify_event_repairs`](../tools/verify_event_repairs.py), also run by
`build.sh`, passes eight controlled cases: both Saruyama selectors with Yes,
RIGHT+A for No, and B cancellation; and the boy with the repeat flag clear/set.
Yes still opens the full English tutorial; No/B still opens the apology. The
first boy conversation still sets flag `82`, and the repeat preserves it.
Full text reads, every glyph/bitmap, two-row bounds, exact visible repair pixels,
handler register/stack guards and unchanged inventory/battery pass. The host
still drives original opcode handlers and skips WAIT; ordinary map access is
not established by these checks.

- [Eight native cases](../build/event-stub-repair/candidate/event-repairs-validation/report.json)
- [Saruyama capture](../build/event-stub-repair/candidate/event-repairs-validation/bank-3-map-11-npc-1-flag-None-A/page-0.png)
- [Boy repeat capture](../build/event-stub-repair/candidate/event-repairs-validation/bank-4-map-5-npc-1-flag-1-A/page-0.png)
- [All seven native bank loads and 1,046 getters](../build/event-stub-repair/candidate/event-bindings-validation/report.json)
- [Release and verification receipt](../build/event-stub-repair/receipt.json)

The other 34 records retain their original bytes and unresolved classification.
No missing dialogue is invented for them, and this repair does not establish
whole-game coverage.
