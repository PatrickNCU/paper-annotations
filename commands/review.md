---
description: 盤點某篇論文還有哪裡沒懂，挑出該回頭複習的疑問
argument-hint: "[論文或筆記資料夾] [主題關鍵字]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入：
$ARGUMENTS

## 步驟

1. 找出 `notes/paper.yml` 所在的目錄，讀 `notes/QUESTIONS.md`。

2. **依論文順序**列出狀態為 `open`（未解決）與 `half`（半懂）的疑問，附上所在小節。
   使用者給了主題關鍵字就只列相關的。

3. 對每一則，只給**問題本身與當初的卡點**，不要直接給答案——複習的重點是他先自己
   想過。他說想不起來或想確認時，再展開該張卡的解答。

4. 順帶指出值得注意的模式，例如某一節集中了多則未解決的疑問，通常代表那整節需要
   重讀而不是逐題補洞。

5. 最後給他複習頁的路徑（`annotated/index.html`），並提醒側邊欄可以用狀態篩選。

回答完之後，若使用者確認某則已經懂了，把該卡的 `status` 改成 `resolved`、更新
`updated` 日期，然後重新建置。
