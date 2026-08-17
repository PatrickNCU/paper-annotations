# Digests

Cards plus source text, combined into something written for this particular
reader. **Written by the agent, not produced by a script.** Follows the skill's
Language section: Traditional Chinese, English term alongside on first use in
this file, abbreviations spelled out in full the first time — a digest is read on
its own, so it cannot rely on a full name given in some card.

## What not to make: a paper summary

SciSpace, Scholarcy and Elicit all summarise a paper well, and that is useful to
someone who has not read it. It is useless to someone who has read it and got
stuck: he does not want to know what the paper says, he wants to know **where he
personally did not get through**.

The cards are the only data this tool uniquely has. A digest must be built around
them, or the output is something any AI summariser would give — and give better.

## The four modes

If he did not name one, read the cards first and then recommend, **based on
whether there is a real thread between cards, not on how many there are**:

- Cards independent, scattered across sections → 回顧單
- Two or more cards actually asking the same unresolved thing → 主題聚合 (four
  cards can qualify; do not gate this on a count)
- The 卡點 fields repeatedly pointing at the same few concepts → 前提盤點
- **He has more than one paper** → 接線 (the first three are single-paper; this
  one spans papers)

If you cannot tell, use 回顧單: it holds for any set of cards.

### 1. 回顧單 `review-sheet`

In paper order, a table with one row per section: section, what it does (one
sentence, from the source), your questions here (**question only, no answer**),
status.

For use before rereading: five minutes of scanning shows which sections are still
unresolved. Include sections with no questions — a blank row is itself
information, meaning he did not get stuck there.

### 2. 主題聚合 `theme-map`

Merge questions that sit in different sections but are one misunderstanding. Per
group write:

- A theme name in the reader's words, not the paper's terminology
- Which cards are involved (markers like `[Q0004]`)
- **The shared 卡點**: the one thing underneath all of these questions
- A suggested rereading order, and why that order

The most valuable of the three, because it is the hardest thing for the reader to
do himself — at the time, each question looked like an isolated event. Also the
easiest to write as empty words: **if there is no real common thread, say so
rather than manufacturing a theme.**

### 3. 前提盤點 `prerequisites`

Work backwards from every 卡點 to the background he was missing. Per item:
concept, the cards it blocked, a one-sentence explanation, and where to get it
(which section of this paper, or noted as outside knowledge the paper assumes).

For use when one concept keeps reappearing across different 卡點 — that means the
thing to fix is the concept, not each question individually.

### 4. 接線 `connections`

**The only cross-paper mode.** Run it when he starts a new paper or finishes a
round, to connect this one back to what he has already read. Run `library.py`
first — without it you do not know what he has read.

Lead with the **citations**, because they are mechanical fact rather than your
inference: which of his papers this one cites, which section the citation is in,
and what that sentence says. The authors' own "we adopt the electrostatic model
of [29] but replace …" beats any after-the-fact reasoning.

Then the three judgement-bearing relationships, each pointing at a specific card,
point, or sentence in a named paper:

- **關聯**: which passage here corresponds to which card or point, in which paper
- **共識**: the two papers claim the same thing in different words. Often exactly
  why he got stuck twice — the same object under a new name reads as new again
- **矛盾**: the two disagree. The most valuable kind, usually meaning either a
  genuine dispute in the field or that he misread one of them. **Separate the
  two**: a real dispute is "the authors do not agree"; a misreading means naming
  which card of his rests on a wrong premise

All three may be empty. **If it does not connect, say it does not** — a
manufactured connection is worse than none, because he will read by a wrong map.

**Afterwards, harden what is worth keeping into links.** A digest is prose he has
to remember to come back to; a link appears next to the sentence it is about. The
three types `answers` / `contradicts` / `same-as` only cover part of what you
find — leave the rest in the digest rather than distorting a relationship to fit
a slot. Format is in the skill's "Typed links between cards and points".

Points (`notes/points/`) are this mode's main material. A paper with thin points
connects to nothing; add points first rather than forcing it with cards.

Output to `notes/digests/connections-<date>.md`, under the notes of the **newly
read** paper, with a `papers:` key in the frontmatter alongside `cards:` naming
every paper involved (by `papers.yml` slug).

## Shared rules

**Everything must have a source.** Borrowed from Elicit: every judgement must
point at a card, a section, or a sentence. If you cannot point, do not write it.

**Attribute clearly.** What the paper says, what the user said in his own card,
and the inference you are adding now must be distinguishable. Mark your additions
「（推論）」. In three months he will not remember which sentence was the author's.

**No answers unless the mode calls for them.** 回顧單 and 主題聚合 list questions
only — a digest is for reviewing, which only works if he thinks first. The answers
are in the cards, one expand away.

**Read-only.** Do not touch the source, the cards, or `annotated/`. A digest is an
extra artifact.

## Output

Write to `notes/digests/<mode>-<date>.md`, e.g.
`notes/digests/theme-map-2026-08-15.md`. Under `notes/` but **not** in
`notes/cards/`; the build does not touch it.

**Then run `build_digest.py <work>`**, which produces a same-named `.html`
alongside: same stylesheet, same offline KaTeX, formulas rendered. **Report the
`.html` path to the user** — digests usually contain formulas, `$\lambda$` is
unreadable in a text editor, and you cannot assume he has a Markdown editor.

The `.md` stays the editable source and the `.html` is derived; edit and re-run.
Embedded KaTeX makes each one about 650 KB, the price of "offline, opens with
nothing installed" — the same trade-off as the review page.

```yaml
---
kind: digest
mode: theme-map
generated: 2026-08-15
built_by: agent
cards: ["0001", "0003", "0004"]
papers: [replace, eplace-ms]     # connections only; papers.yml slugs
---
```

The first line of the body is this sentence, never omitted:

> 這份整理由 AI 依卡片與原文產生，不是論文內容。真實來源是 `notes/cards/` 與原文。

Re-running the same mode on the same day overwrites the previous one. To keep the
old version, rename it first — unlike `annotated/`, **a digest is not
idempotent**: the same cards run again will not produce identical text. Tell the
user this, or he will assume it can be regenerated at will and throw the old one
away.
