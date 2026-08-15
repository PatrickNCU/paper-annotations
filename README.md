# paper-annotations

讀論文時把疑問就地註記回原文，累積成可複習的筆記與單頁 HTML。

- 論文原文唯讀，疑問卡是唯一真實來源，註記檢視可隨時重新生成
- 疑問掛在公式編號、圖、表、小節或指定的一句原文上；每次建置都對實際內容重新解析
- 產出單頁 HTML：側邊目錄、疑問清單、狀態篩選、全文搜尋、明暗主題，公式離線渲染
- 零依賴，只需要 Python 3.8+

## 安裝

需要 Claude Code CLI（`/plugin` 是互動面板，桌面版叫不出來）。在 CLI 裡跑：

```
/plugin marketplace add PatrickNCU/paper-annotations
/plugin install paper-annotations@patrickncu
```

安裝範圍選 **user scope**，這樣在任何資料夾都能用。零依賴，只要有 Python 3.8+。

## 開發

安裝會把 plugin 複製到 `~/.claude/plugins/cache/`，那才是 Claude Code 實際載入的副本。
要改功能請改這個 repo，push 之後在面板上 **Update marketplace** 再重裝；直接改 cache
會在下次更新時被覆蓋。

本機開發可以直接把 clone 下來的資料夾當 marketplace：
`/plugin marketplace add <你的 clone 路徑>`

## 指令

| 指令 | 用途 |
|---|---|
| `/paper-annotations:setup <論文資料夾>` | 設定新論文，判定支援程度，首次建置 |
| `/paper-annotations:build [路徑]` | 重新產生註記檢視與複習頁，回報所有警告 |
| `/paper-annotations:review [路徑]` | 盤點還有哪裡沒懂 |

平常**不需要指令**：直接問論文問題，疑問會自動累積成卡片。

## 授權

MIT。內含 [KaTeX](https://katex.org) v0.18.4（MIT），見 `skills/paper-annotations/scripts/vendor/katex/LICENSE`。
