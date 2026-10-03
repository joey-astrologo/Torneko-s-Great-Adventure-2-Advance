# Blank scrolls and English writing inputs

This guide explains how to use **Blank scrolls** in the English localization of
Torneko 2 Advance. It lists all **27 writable scroll effects and 56 accepted
English inputs** in the current translation catalog. Japanese input is not
required. Japanese names in research files identify original source text;
the localized inventory label is **Blank scroll**.

## How blank scrolls work

A Blank scroll takes on another scroll's effect when you write a recognized
name on it. The game's item description says to use the name of a scroll you
have **read before**. The writing handler checks the game's recorded scroll
history, so finding or identifying a scroll alone does not establish eligibility.

The separate **Blank list** reference menu contains the 27 candidate scrolls
and marks unavailable entries **Can't write**. Recognizing an input and having
permission to write that effect are separate checks. The list is a reference;
the inventory's **Write** action opens a keyboard.

Successful writing changes the item's identity to the selected scroll and
marks it as inscribed. Inventory labels preserve its origin with the format
**Blank: effect**, for example **Blank: Sheen**. Writing chooses the effect;
then use the resulting scroll as appropriate. Most effects use **Read**;
Sanctuary's description instead instructs you to place it at your feet.

Blank scrolls accept the fixed set below. They do not accept arbitrary item
names or spell names. **Spellbooks** have their own input list and check whether
you have ever learned the spell; that is a separate mechanic.

## Inventory menu actions

The verified menu for an identified, unwritten Blank scroll carried by the
merchant contains these actions, in order:

| Action | Purpose |
| --- | --- |
| Read | Attempt to read the scroll. To choose its effect, use Write first. |
| Throw | Throw the item. |
| Drop | Place the item on the ground. |
| Write | Open the inscription keyboard. |

See the [actual action-menu capture](../build/english/writing-editor-validation/scroll-long/action.png).
This records a controlled inventory setup followed by normal button input.
It is not an exhaustive action-menu audit for every vocation, ground-item
state, shop context or already-inscribed scroll.

## Entering an English name

1. Select **Blank scroll** in your inventory and choose **Write**.
2. Enter one of the exact inputs in the table below using the on-screen keyboard.
   The shorter effect name usually takes fewer button presses.
3. Press **Start** to select **Done**, then **A** to confirm.
4. Check the result message. On success, use the newly inscribed scroll's effect.

| Control | Keyboard behavior |
| --- | --- |
| Direction pad | Move the keyboard selection. |
| A | Choose the highlighted character or command. |
| Keyboard page label | Cycle keyboard pages, including uppercase and lowercase English. |
| Sp | Insert a space. |
| Next and Back | Move the position within the entered name. |
| B | Delete; from an empty editor, cancel. |
| Start, then A | Select Done, then confirm the input. |

The writing field permits **15 characters**, counting spaces and punctuation.
English letter case does not matter: `Sheen`, `sheen` and `SHEEN` select the same
effect. Spaces, hyphens and periods still matter. Do not add leading or trailing
spaces, omit the period from an abbreviated input, or assume an unlisted
abbreviation works. The matcher folds English letter case; it does not generally
normalize punctuation or spacing.

For example, `Great room` and `Great room scr.` both work. `Safe Passage`,
`Safe Pass.` and `Safe Pass. sc.` all select the same effect. These are explicit
accepted alternatives, not a rule that any shortened name will be understood.

## Every accepted English input

Each input between backticks is a complete accepted spelling. The first column
uses the displayed English item name, including its approved abbreviation.
Effect summaries come from the reviewed Torneko 2 item descriptions. Every
entry remains subject to the game's scroll-history requirement.

| Scroll | Accepted inputs | Effect |
| --- | --- | --- |
| Sheen scroll | `Sheen`; `Sheen scroll` | Removes curses from equipped items. |
| Peep scroll | `Peep`; `Peep scroll` | Identifies an item. |
| Bang scroll | `Bang`; `Bang scroll` | Creates an explosion that attacks monsters in the room. |
| Mouthseal scr. | `Mouthseal`; `Mouthseal scr.` | Seals your mouth for the rest of this floor. |
| Evac scroll | `Evac`; `Evac scroll` | Takes you out of the dungeon. |
| Trap scroll | `Trap`; `Trap scroll` | Adds traps to this floor. |
| Great room scr. | `Great room`; `Great room scr.` | Turns this floor into one large room. |
| Monster scroll | `Monster`; `Monster scroll` | Creates a Monster House. |
| Oomphle scroll | `Oomphle`; `Oomphle scroll` | Strengthens your equipped weapon and removes its curse. |
| Buff scroll | `Buff`; `Buff scroll` | Strengthens your equipped shield and removes its curse. |
| Plating scroll | `Plating`; `Plating scroll` | Protects your equipped weapon and shield from rust and removes their curses. |
| No-pickup scr. | `No-pickup`; `No-pickup scr.` | Stops you from picking up items for the rest of this floor. |
| Sanctuary scr. | `Sanctuary`; `Sanctuary scr.` | Place it at your feet to protect yourself from monsters' normal attacks. |
| See-all scroll | `See-all`; `See-all scroll` | Shows item locations on this floor's map. |
| Bread scroll | `Bread`; `Bread scroll` | Turns an item into Big bread. |
| Prayer scroll | `Prayer`; `Prayer scroll` | Adds uses to a staff or pot. |
| Glow scroll | `Glow`; `Glow scroll` | Reveals this floor's layout and the locations of items and monsters. |
| Binding scroll | `Binding`; `Binding scroll` | Paralyses adjacent monsters until you attack them. |
| Lyre of Ire sc. | `Lyre of Ire`; `Lyre of Ire sc.` | Calls monsters to surround you. |
| Foe sight scr. | `Foe sight`; `Foe sight scr.` | Reveals monster locations on this floor. |
| Safe Pass. sc. | `Safe Pass.`; `Safe Pass. sc.`; `Safe Passage` | Protects you from damaging terrain. |
| Gale scroll | `Gale`; `Gale scroll` | Makes the wind blow. |
| Foe bind scroll | `Foe bind`; `Foe bind scroll`; `Monster bind` | Briefly paralyses monsters in the room. Attacking them ends the effect. |
| Kasap scroll | `Kasap`; `Kasap scroll` | Lowers the defence of every monster on this floor. |
| Rooting scroll | `Rooting`; `Rooting scroll` | Roots monsters in the room to the spot. |
| Pulling scroll | `Pulling`; `Pulling scroll` | Gathers items lying on this floor around you. |
| Kazing scroll | `Kazing`; `Kazing scroll` | Revives monsters that have become graves. |

## Refusals and corrections

- **Cannot write that name on a Blank scroll.** The input did not match a
  supported name. Check the table, spelling, spaces and punctuation.
- **You cannot write a scroll you have not used yet.** The name was recognized,
  but the required scroll-history flag is missing. Check the Blank list.

The verified refusal branches leave the item's identity unchanged. They do
not turn it into the requested scroll. The native attempt flag is separate
from successful inscription, so an unchanged identity should not be described
as proof that every item-state bit stayed unchanged.

The 37 non-spell selectors used by internal rendering tests are **not** 37
player-enterable effects. Those tests include special or reserved states;
the actual writing lookup permits the **27 targets listed here**.

## Sources and verification scope

The full-English workflow is implemented in the cumulative build. Older notes
headed “prototype” describe its development history; integration is recorded
in [Text progress](TEXT_PROGRESS.md). The retained original input spellings
provide compatibility; they are not required to use this guide.

The input table is checked against
[the reviewed writing catalog](../translations/writing-input-review.json),
[the item descriptions](../translations/items-review.json), and the compiled
`writing_input.entries` in [the build manifest](../build/english/build.json).
The compiler and matcher are in [writing_input.py](../tools/writing_input.py).
English result messages are in
[the writing-message catalog](../translations/writing-review.json).

Existing native emulator reports cover:

- [584 lookup cases](../build/english/writing-lookup-validation/report.json),
  including English case variants, retained original inputs and rejected names
  across both scrolls and Spellbooks.
- [Nine editor cases](../build/english/writing-editor-validation/report.json),
  including actual Write selection and English typing of `Lyre of Ire`,
  `Safe Passage` and `Great room scr.` after controlled item/history setup.
- [102 writing-result cases](../build/english/writing-validation/report.json),
  covering scroll and Spellbook success/refusal branches and item mutations.
- [77 inscription-row cases](../build/english/scroll-item-validation/report.json)
  and [nine reference-list cases](../build/english/reference-lists-validation/report.json).

On 2026-10-03, the complete cumulative suite reran these checks on ROM SHA-256
`452394042d5be4c83adb79fa35eaba5ca261514533b2162604032b9561e44304`.
The reports, current compiled ROM and manifest now share that identity.
The additional unfiltered audit covers all nine editor cases on the same ROM.
See the [caller follow-up acceptance](../build/caller-audit-next/completion.json).

Natural acquisition, unlocking every effect through ordinary play, all menu
contexts, turn timing and every post-inscription use are outside those checks.
These family tests do not establish 100% whole-game localization coverage.
The implementation details are recorded in
[Memory map](MEMORY_MAP.md#native-scrollspell-writing-september-26),
[reference-list research](MEMORY_MAP.md#staged-reference-list-consumers), and
[English input research](MEMORY_MAP.md#english-inscription-input-prototype-not-yet-in-root-build).
