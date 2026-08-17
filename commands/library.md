---
description: 跨論文盤點：還有哪些疑問沒解決、哪幾篇互相引用、引用時原文怎麼說
argument-hint: "[起點資料夾]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

This command is **not about producing the shelf page** (that is steps 7–8 of
`:setup`) — it is about **reading**: going through the whole registry and telling
him what is in it. The shelf page gives counts; this gives what the page cannot:
each card's question in full, each point, and which section a citation appears in
together with the sentence around it.

User input:
$ARGUMENTS

## Steps

1. Run `library.py` (no start given → current directory). It searches upward for
   `papers.yml`.

2. If there is no registry, do not create one: it means `probe.py` has never been
   run on any paper. Tell him `/paper-annotations:setup` will create it.

3. **Report**, in order of importance:
   - Per-paper question counts, **open and half first** — that is where he is
     still stuck
   - Citations between papers. Mechanically determined fact, so state it
     directly, including which section it appears in and what that sentence says
   - Call out papers with zero points: no skeleton to compare against other
     papers, so a cross-paper digest will come out empty
   - **Uncategorised papers**: propose 2–4 categories into `topics_auto` in
     `papers.yml`, adding each new one to the `topics:` vocabulary at the same
     time, and list them for on-the-spot veto. Rules in the skill's Categories
     section — the point is that a category must be **coarser than a keyword**;
     keywords are only raw material

4. When a registered path no longer holds notes (folder moved), say plainly which
   paper and where it was registered, and that the fix is editing `work` in
   `papers.yml` or re-running `probe.py`. **Never fix it automatically.**

5. **If he wants a clickable page**: rebuild with `build_library.py` (the numbers
   change daily; the rebuild is cheap and idempotent), check 開啟書房.cmd exists
   beside `papers.yml` and only run `serve.py --library --launcher` if it does
   not — `:setup` usually placed it already, so do not treat this as something to
   redo every time. Then run `serve.py --library` in the background. Tell him it
   is **one server mounting every paper** (not one per paper), each serving only
   its own directory, and that existing single-paper launchers are unaffected.

6. When what he wants is the relationships rather than the list, follow up with
   `/paper-annotations:digest` in `connections` mode.

Done when he knows which papers he has read, which cite which, and what is still
unresolved.
