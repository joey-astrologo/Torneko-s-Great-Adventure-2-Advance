# Item text and budgets

The accepted build covers all **221 item definitions**. The original review
catalog contains 206 ordinary identified names; the additional 15 special/reserved
records are now covered too. Two equipment category descriptions and the invisible-
item fallback are separately accounted for. Current acceptance requires **2,006
item cases**, plus separate alias/custom-name/action families. See the
[coverage matrix](COVERAGE_AUDIT.md) and [receipt](english-services-validation.json);
a catalog entry alone does not establish every consumer.

Names retain the established **80px / 31-byte** base-name reserve, including the
encoded terminator. Complete inventory rows have 162 usable pixels and a
64-byte buffer. These limits account for quantities, equipment/curse markers,
charges, enhancements and prices; they do not authorize wider late-game menus.
The price background starts at relative x=121 even when its leading cells are
blank. Comparing names only against visible price digits would miss overlap.

Thirty-eight names need a separate compact display form in this reserve. The
full name remains in `translations/glossary.json` and each affected item entry's
`canonical_name`/`display_form_review` fields, together with both measurements.
Examples include `Liquid metal sword` -> `L. metal sword` and
`Hocus Pocus scroll` -> `H. Pocus scroll`. These are display abbreviations,
not claims of new official names. The selected T2 font is unchanged.

Descriptions preserve T2 effects, conditions and player substitutions. Info text
has a 216px authored line budget, a maximum of four description lines and a
256-byte combined formatter allowance checked natively. Player names reserve
**98px**, shared with the seven-character native name editor. The widest Japanese
name caught an incorrect 84px duplicate constant; Surefoot staff was rewrapped.

`tools.verify_items` requires nine row states per translated definition:
identified, equipped, cursed, unidentified, priced, maximum fields, priced with
maximum fields, and the last combination with equipment or curse markers.
It additionally checks four naturally carried items and all three name-width
cases for each description containing the player command. For this catalog that
is 2,006 cases, including the Ogre shield ability-present branch and the
Hocus Pocus scroll visibility branch. Price-background overlap, buffer guards, complete names/numbers,
native pixels, formatter ABI and parent-window restoration are checked.
Synthetic combinations are stress tests, not proof of natural item acquisition.
Warrior skills, inscriptions and pot contents have separate native verification
families in the cumulative receipt. Unvisited combinations and later-mode consumers
still need targeted investigation; these 2,006 cases alone do not cover them.

The additional 15 definition records are now included: bare hands (ID 0, with native
colour controls); 13 reserved/source-placeholder definitions (11, 85, 86, 139,
153, 168, 197–202, 211); and ID 214, whose ordinary display is native currency
despite its internal Japanese `Fire` label. Reserved wording does not prove
unreachability. Description slot 221 is an invisible-item fallback, not a 222nd
item definition; it is now explicitly included in the text inventory. Unidentified
aliases have a separate 154-label review and 166 native cases. Direct-name consumers
outside the audited paths remain open. English custom-name layouts pass 30 native
cases; see [the settled acceptance scope](TEXT_OPEN_QUESTIONS.md#custom-item-name-acceptance-scope).
Maximum Japanese custom-item-name width is not a regression requirement. The 98px
player-name reserve above applies to the separate seven-character player field.

The Info selector preserves two special native branches: Ogre shield uses only
the general shield description when item flag `0x20` is clear; Hocus Pocus scroll
selects description 221 when native visibility function `0801211C` returns false.
Its name then remains seven blank native glyphs. Controlled cases exercise both
branches without changing those gameplay rules.
