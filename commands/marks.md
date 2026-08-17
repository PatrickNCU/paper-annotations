---
description: 把複習頁「複製畫記」的內容存成 notes/marks/，然後重建
argument-hint: "[論文或筆記資料夾]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input (may itself be the pasted highlight block):
$ARGUMENTS

## Steps

1. Get the highlight block. If he ran the command with nothing attached, ask him
   to press 「複製畫記」 in the review page's sidebar and paste the result.

2. Find the directory holding `notes/paper.yml`.

3. Write the pasted block to a temp file **verbatim** and hand it to
   `import_marks.py --from`. **Never transcribe entries into YAML yourself** — a
   highlight is only "which passage, what colour, what comment", so nothing needs
   your judgement, and copying by hand produces exactly the kind of silent anchor
   error this system is least able to survive.

4. Run `build_annotated.py` and `build_html.py`.

5. Report how many were added and how many already existed. 🟡 warnings need no
   action (a highlight quoting a formula is not in the raw Markdown; the page
   searches rendered text and locates it anyway). 🔴 does need action.

6. If he keeps doing this by hand, tell him the round trip is avoidable: open the
   page from 開啟書房.cmd (or 開啟複習頁.cmd) and the 「存檔」 button writes
   highlights straight into `notes/marks/`.

Done when the highlights are in `notes/marks/`, the page has been rebuilt, and he
knows the launcher route exists.
