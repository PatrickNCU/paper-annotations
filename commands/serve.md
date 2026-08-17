---
description: 開一個本機 server，讓畫記可以存檔、複習可以評分
argument-hint: "[論文或筆記資料夾｜--library] [--port 8975]"
allowed-tools: Bash, Read, Glob, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入：
$ARGUMENTS

## 步驟

0. **他想一次開全部論文嗎？** 使用者說了「書房」「全部論文」「一次開」，或帶了
   `--library`，就走書房模式：跑 `build_library.py` 產生書房頁、
   `serve.py --library --launcher` 放啟動器（在 `papers.yml` 旁邊的 `開啟書房.cmd`），
   再背景執行 `serve.py --library`。首頁就是書房，點論文直接進去，**不需要另外開
   任何 server**——是一個 server 掛多篇，不是每篇一個。以下步驟改讀那一篇的路徑。

1. 單篇模式：找出 `notes/paper.yml` 所在的目錄。沒給路徑就從目前目錄往下找，
   多於一個時列出來讓他選。

2. 確認 `annotated/index.html` 存在；不在就先跑 `build_annotated.py` 與 `build_html.py`。

3. 跑一次 `serve.py <work> --launcher`，在論文資料夾裡放一個點兩下就能開的啟動器
   （Windows 是 `開啟複習頁.cmd`，其他系統是 `.command`）。它會覆寫舊的，重跑無妨。

4. **在背景執行** `serve.py <work>`（Bash 的 `run_in_background`），不要佔住對話。
   使用者指定了 port 就帶 `--port`；沒指定就用預設 8975。同一篇已經在跑就不要重開，
   直接把網址給他。

5. 把網址告訴他，並說明這條網址底下才有「💾 存檔」與**複習評分**——直接開
   `index.html` 那兩者都不會出現（複習紀錄寫不了檔，見 skill 的「複習排程」）。

6. 講清楚**畫記不會跨 `file://` 和 `http://`**：瀏覽器把兩者當成不同來源，各有各的
   儲存空間。他先前直接開檔案時畫、還沒落檔的畫記，要先在原本那個分頁按「複製畫記」
   帶出來，之後固定從這個網址讀。

7. 提醒結束方式（停掉那個背景工作），以及 server 只接受本機連線。

## 之後

使用者在頁面上按存檔、改註解、刪畫記，都由 server 自己寫檔並重建，**不需要你介入**。
他回報存檔失敗時才去看那個背景工作的輸出。

完成條件：使用者拿到網址與啟動器位置，而且知道要從那條網址開頁面、怎麼停。
