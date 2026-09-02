---
description: 盤點某篇論文還有哪裡沒懂，挑出該回頭複習的疑問
argument-hint: "[論文或筆記資料夾] [主題關鍵字]"
allowed-tools: Bash, Read, Edit, Glob, Grep, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

0. **Run `library.py`** and say its first line — what is due today across every
   paper. If anything is due, that is the queue: point him at the page
   (`…/annotated/index.html#review`, opened from 開啟書房.cmd) rather than
   working through it here. **Grades are recorded only on the page.** You never
   ask 「答得如何？」 in chat and never write `notes/reviews/`.

1. Find the directory holding `notes/paper.yml`; read `notes/QUESTIONS.md`.

2. **In paper order**, list the questions with status `open` and `half`, each
   with its section, as links he can click: `#card-0007` appended to the page
   path opens that card. If he gave a topic keyword, list only matching ones.

3. Go through them **the way the page does**, one at a time and in stages:
   the question only → his attempt, however short → the card's 一句話直覺 →
   the full 卡點 and 解答 only if he asks or was wrong. Never hand over the
   answer in the first message. What he says at the attempt step goes into the
   card verbatim as a `YYYY-MM-DD 猜：…` line under `## 自己的話`.

4. **A `half` card is closed, not answered.** Ask him to explain it in his own
   words; show the answer next to his explanation; ask whether they match. If he
   says yes: append his explanation as `YYYY-MM-DD 解釋：…` under `## 自己的話`,
   replace the `status:` line with `resolved` and the `updated:` line with today
   — **two line edits, nothing else in the file touched** — and rebuild. **Say
   out loud** that it is now in the schedule and will come back on its own. If
   he says no, append the line anyway and leave the status alone. At most five
   cards become `resolved` in one sitting.

5. Point out patterns worth noticing: one section concentrating several
   unresolved questions usually means that whole section needs rereading rather
   than patching question by question.

6. Give him the real path of the review page (see `annotated_root` in
   `notes/paper.yml`; by default beside the package, not inside it), and remind
   him the sidebar filters by status. If he is not already opening it from
   開啟書房.cmd, say once that grading and closing half cards need the server.

7. At the end, offer a local `git commit` of the notes repo if anything changed.
   Commit only if he says so; never push.

**Never modify or delete `notes/reviews/` in code.** That log is what he
accumulated by pressing buttons, and it is the only thing here that cannot be
rebuilt.
