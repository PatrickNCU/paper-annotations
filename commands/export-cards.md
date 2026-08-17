---
description: 把疑問卡的資料匯出給別的程式用：Anki 匯入檔、CSV 或 JSON
argument-hint: "[論文或筆記資料夾] [anki|csv|json] [狀態]"
allowed-tools: Bash, Read, Glob, AskUserQuestion, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`.

2. **Decide which cards.** If he did not say, default to
   `--status resolved,half` and explain why: an `open` card has no answer yet, so
   as a Q&A card its back is blank. If he wants everything, do that.

3. Run `export_cards.py`; format defaults to `anki`.

4. **Report**: file path, how many cards, and how to import — Anki's
   「檔案 → 匯入」, with columns in the order Front / Back / Extra / Source /
   Tags, which have to be mapped to the note type's fields on first import.
   Formulas are already converted to the MathJax form Anki understands
   (`\(…\)`), so nothing more to do.

5. Remind him this is **read-only**: the cards themselves are untouched, and
   re-running overwrites the same export file.

Done when he has the file path and knows how to map the columns on import.
