---
description: 把疑問卡匯出成 Anki 匯入檔，或 CSV／JSON
argument-hint: "[論文或筆記資料夾] [anki|csv|json] [狀態]"
allowed-tools: Bash, Read, Glob, AskUserQuestion, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入：
$ARGUMENTS

## 步驟

1. 找出 `notes/paper.yml` 所在的目錄。

2. **決定要匯出哪些卡**。使用者沒說就預設 `--status resolved,half`，並說明理由：
   `open` 的卡還沒有解答，做成問答卡背面是空的。他想全部匯出就照做。

3. 執行 `export_cards.py`，格式預設 `anki`。

4. **回報**：檔案路徑、匯出幾張、以及匯入方式——Anki 的「檔案 → 匯入」，欄位依序是
   Front／Back／Extra／Source／Tags，第一次匯入時要把這五欄對到筆記類型的欄位。
   公式已經轉成 Anki 認得的 MathJax 寫法（`\(…\)`），不必再處理。

5. 提醒這是**唯讀**操作：卡片本身沒有被改動，重跑會覆蓋同一個匯出檔。

完成條件：使用者拿到檔案路徑，而且知道匯入時欄位怎麼對。
