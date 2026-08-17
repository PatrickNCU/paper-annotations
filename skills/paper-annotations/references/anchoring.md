# Anchors: always resolved against real content, never trusted from metadata

The core design decision of this tool. Read this page before changing
`resolve_anchor` in `pa/anchors.py`.

A card must know where in the source it belongs, and a conversion package usually
ships positioning data already (`chunk_id`, the equation index in `INDEX.md`,
numbered filenames). We deliberately **do not treat any of that as truth**: a
card only describes *what to look for*, and every build matches that against the
live source. Resolved → placed; unresolved → marked as unanchored. That is why
every card must store a quote even when it already has a structural reference
such as an equation number.

## Considered options

- **Trust `chunk_id` directly.** Least work, but assumes every paper was split by
  the same logic. He may bring an unsplit single-file Markdown, or use a tool
  that chunks completely differently; one reconversion invalidates every
  `chunk_id` at once, irrecoverably.
- **Quotes only, no structural reference.** General enough, but quotes for
  equations and figures are LaTeX or image syntax — fragile to match and
  unreadable. Ignoring a usable `\tag{7}` is waste.
- **Resolution ladder + redundant quote (adopted).** Structural reference →
  heading → quote, every rung verified against actual text.

## Consequences

- Each card stores ~100 extra characters of quote, and the quote may describe the
  same position the structural reference already does. The redundancy is
  deliberate.
- Reconversion or re-splitting is recoverable: `reanchor.py` searches the quote
  globally in the new structure. But **it only edits automatically on a unique
  whole-document hit** — papers repeat sentences constantly, and landing on a
  similar-but-wrong passage is worse than being visibly broken.
- The build never guesses a position. Unresolved is unresolved, and it is listed
  at the top of `QUESTIONS.md`. This system's failure mode is noisy, not silent.
- The capability probe in `notes/paper.yml` is therefore only a speedup and a
  hint. It can be hand-edited, it can be wrong, and correctness does not depend
  on it.

## Points use the quote, not the ladder

Points in `notes/points/` are **located by quote alone**; they do not climb
`ref → heading → quote`. The two describe different things: a card marks a
position in an argument and still holds if it falls back to the top of a section,
whereas a point paraphrases **one specific sentence**, and landing half a page
away means saying the wrong thing about the wrong text. A point's `heading` field
is purely an index label and takes no part in locating it.

Every other rule is identical: unresolved means not placed and reported, and
`reanchor.py` still only auto-fixes on a unique hit.

## Failure must be loud

Each of the following is reported, never silently skipped:

| Situation | Behaviour |
|---|---|
| Card has no YAML frontmatter | Say outright that this card is unused (otherwise notes he wrote simply vanish) |
| Two cards share an id | Name the file it collides with |
| Quote missing / appears several times | Report separately — the fixes are opposite |
| Quote not unique but anchored via ref/heading | 🟡 warning: fine now, unrecoverable the day he reconverts |
| heading matches several headings | Refuse to guess, fall back to the quote; better to report not-found than to anchor to the wrong place |
| A new file appeared in the source | Stop the build: a new file would not be covered by the notes |
| Notes created against `annotated/` | Refuse, and name the correct directory |
| Invalid `status` / `origin` | List the valid values |
| Card has no 問題 | Say so at build time, rather than letting him discover a blank card during review |
| Point's `kind` invalid or body empty | Drop it and list the valid values — a wrong claim carrying the paper's name is worse than none |
| Registry points at a missing folder | `library.py` lists it plainly: no automatic path fixing, no silent skipping |
