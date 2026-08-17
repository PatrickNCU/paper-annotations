---
description: 重新產生註記檢視與複習頁，並回報所有警告
argument-hint: "[論文或筆記資料夾]"
allowed-tools: Bash, Read, Glob, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`. No path given → search downward
   from the current directory; more than one → list them and let him pick.

2. Run `build_annotated.py`, then `build_html.py`.

3. **Relay every warning**; never just say it built:
   - 「找不到位置」 cards do not appear on the review page — explain each one's
     cause and fix
   - 「🟡 引文提醒」 is harmless today but unrecoverable once the source is
     reconverted; fix it now
   - 「卡片本身有問題」 means that card is unused: the file still holds the
     content but nothing displays it
   - If the build stopped because the source changed, explain the possible
     consequences first, then follow its instructions

4. Report the review page path and current question counts (open / half /
   resolved).

Done when warnings are zero, or every one has been explained and he has decided
what to do about it.
