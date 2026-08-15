---
description: 開一個本機 server，讓複習頁上的畫記可以直接存檔
argument-hint: "[論文或筆記資料夾] [--port 8975]"
allowed-tools: Bash, Read, Glob, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入：
$ARGUMENTS

## 步驟

1. 找出 `notes/paper.yml` 所在的目錄。沒給路徑就從目前目錄往下找，多於一個時列出來讓
   他選——**一個 server 只服務一篇論文**。

2. 確認 `annotated/index.html` 存在；不在就先跑 `build_annotated.py` 與 `build_html.py`。

3. **在背景執行** `serve.py <work>`（Bash 的 `run_in_background`），不要佔住對話。
   使用者指定了 port 就帶 `--port`；沒指定就用預設 8975。同一篇已經在跑就不要重開，
   直接把網址給他。

4. 把網址告訴他，並說明這條網址底下才有「💾 存檔」——直接開 `index.html` 那顆按鈕
   不會出現。

5. 講清楚**畫記不會跨 `file://` 和 `http://`**：瀏覽器把兩者當成不同來源，各有各的
   儲存空間。他先前直接開檔案時畫、還沒落檔的畫記，要先在原本那個分頁按「複製畫記」
   帶出來，之後固定從這個網址讀。

6. 提醒結束方式（停掉那個背景工作），以及 server 只接受本機連線。

## 之後

使用者在頁面上按存檔、改註解、刪畫記，都由 server 自己寫檔並重建，**不需要你介入**。
他回報存檔失敗時才去看那個背景工作的輸出。

完成條件：使用者拿到網址，而且知道要從那條網址開頁面、怎麼停。
