---
description: 盤點某篇論文還有哪裡沒懂，挑出該回頭複習的疑問
argument-hint: "[論文或筆記資料夾] [主題關鍵字]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`; read `notes/QUESTIONS.md`.

2. **In paper order**, list the questions with status `open` and `half`, each
   with its section. If he gave a topic keyword, list only matching ones.

3. For each, give **only the question and its 卡點** — never hand over the answer.
   The point of reviewing is that he tries first. Expand a card's answer when he
   says he cannot recall it or wants to check.

4. Point out patterns worth noticing: one section concentrating several
   unresolved questions usually means that whole section needs rereading rather
   than patching question by question.

5. Give him the real path of the review page (see `annotated_root` in
   `notes/paper.yml`; by default beside the package, not inside it), and remind
   him the sidebar filters by status.

6. **Introduce the sidebar's 複習 panel**: resolved cards enter spaced
   repetition, surface there when due, and are graded at the bottom of the card.
   **Grading needs `serve.py` running**, so tell him to open the page from
   開啟書房.cmd rather than by double-clicking `index.html`. Rules and limits in
   the skill's Review scheduling section.

Afterwards, if he confirms he now understands one, set that card's `status` to
`resolved`, update `updated`, and rebuild. **Say this out loud**: the moment it
becomes `resolved` it enters the schedule and will come back to him on its own —
otherwise he has no idea that changing a status does that.

**Never modify or delete `notes/reviews/` in code.** That log is what he
accumulated by pressing buttons, and it is the only thing here that cannot be
rebuilt.
