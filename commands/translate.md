---
description: 把論文某幾節翻成中文，放進複習頁右邊的譯文欄
argument-hint: "[論文或筆記資料夾] [章節，例如 S130 S200]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its
**Translations** section. Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`, and the sections he named. If he
   named none, run `translate.py <work>` and ask which sections — do not
   translate a whole paper unasked.
2. `translate.py <work> --todo <sections>`, read the files under `# 先讀：`,
   write the translations into a copy of that output, `--put` it.
3. Fix and re-put any 🔴 block, then run `build_html.py <work>`.
4. Report how many blocks went in, any 🟡 worth a look, and that the page's
   bottom-right 「譯文」 button (對照 / 只看譯文) shows them.

Done when every block he asked for is filed or explained, and the page is rebuilt.
