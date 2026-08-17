---
description: 把疑問卡和原文合成一份整理，產出公式可讀的網頁
argument-hint: "[論文或筆記資料夾] [review-sheet|theme-map|prerequisites|connections]"
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, Skill, Write
---

Load the `paper-annotations` skill (`Skill` tool), then read
`references/digests.md` and write by its rules. The digest itself is written in
Traditional Chinese — the user reads it.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`; read `notes/QUESTIONS.md`,
   `notes/cards/` and `notes/points/`.

2. **Pick the mode.** If he named one, use it. Otherwise recommend one from what
   the cards actually look like, say why, and let him change it. The four modes
   and when each fits are in `references/digests.md`.

3. **`connections` runs `library.py` first**; the other three do not need it.
   Without it you do not know which papers he has read, and have no citations.

4. **Read the source text.** A digest cannot be built from cards alone — a card
   carries one quoted sentence, not enough to judge whether two questions are the
   same misunderstanding. Follow the package's own `AGENTS.md` reading policy.

5. **Write it.** Output location, frontmatter and the opening disclaimer all
   follow `references/digests.md`. Where you have nothing, say so; never pad.

6. **Run `build_digest.py`** to produce the same-named `.html`. Not skippable.

7. **Report**: the **`.html` path** (the file he opens, formulas already
   rendered), which mode you used, which cards it covers, and that **a digest is
   not idempotent** — re-running the same day overwrites it, and will not produce
   the same text. The `.md` is the editable source; edit it and re-run
   `build_digest.py`.

Done when every judgement in the digest can point at a specific card or section,
and he knows this file is an AI artifact whose sources of truth remain the cards
and the paper.
