---
description: 把疑問卡和原文合成一份可以直接讀的整理
argument-hint: "[論文或筆記資料夾] [review-sheet|theme-map|prerequisites]"
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, Skill, Write
---

先載入 `paper-annotations` skill（`Skill` 工具），再讀
`references/digests.md`，照它的規則寫。

使用者輸入：
$ARGUMENTS

## 步驟

1. 找出 `notes/paper.yml` 所在的目錄，讀 `notes/QUESTIONS.md` 與 `notes/cards/`。

2. **決定模式**。使用者指定了就照做；沒指定就依卡片的實際樣子推薦一種，說明理由，
   讓他改。三種模式與各自適用的情況見 `references/digests.md`。

3. **讀原文**。整理要靠原文，不能只靠卡片——卡片裡的引文只有一句，不足以判斷兩個
   疑問是不是同一件事沒通。遵守論文套件自己的 `AGENTS.md` 閱讀政策。

4. **寫**。輸出位置、frontmatter 與開頭的免責句都照 `references/digests.md`。
   寫不出來的部分就說沒有，不要為了填滿版面硬湊。

5. **回報**：檔案路徑、用了哪個模式、涵蓋哪幾張卡，以及**這份整理不是冪等的**——
   同一天重跑會覆蓋，重跑也不會得到一樣的文字。

完成條件：整理裡的每一條判斷都指得出是哪張卡或哪一節，而且使用者知道這份檔案是
AI 產物、真實來源仍是卡片與原文。
