# paper-annotations

讀論文時把疑問就地註記回原文，累積成可複習的筆記與單頁 HTML。

- 論文原文唯讀，疑問卡是唯一真實來源，註記檢視可隨時重新生成
- 疑問掛在公式編號、圖、表、小節或指定的一句原文上；每次建置都對實際內容重新解析
- 產出單頁 HTML：側邊目錄、疑問清單、狀態篩選、全文搜尋、明暗主題，公式離線渲染
- 卡住的那句原文會標成高亮，卡片被篩掉時高亮跟著收起來
- 可以把累積的疑問整理成回顧單、主題聚合或前提盤點；卡片也能匯出到 Anki
- 零依賴，只需要 Python 3.8+

## 跟其他工具的差別

| 類別 | 代表 | 它記什麼 |
|---|---|---|
| PDF 標註／文獻管理 | [Zotero](https://www.zotero.org)、[Obsidian Annotator](https://github.com/elias-sundqvist/obsidian-annotator)、[PDF++](https://github.com/RyotaUshio/obsidian-pdf-plus) | 螢光筆與註解——「這段很重要」 |
| Web 標註 | [Hypothes.is](https://web.hypothes.is) | 引文定位的公開標註層 |
| AI 讀論文 | [SciSpace Copilot](https://scispace.com)、ChatPDF、Explainpaper | 對話與摘要，存在側邊筆記本 |
| 間隔複習 | [RemNote](https://www.remnote.com)、[SuperMemo](https://help.supermemo.org/wiki/Incremental_reading) | 抽出原文做成卡片，有排程演算法 |
| Agent plugin | [research-papers-plugin](https://github.com/ctoth/research-papers-plugin)、[phd-skills](https://github.com/fcakyon/phd-skills) | 把論文加工成結構化摘要與 claims |

這套工具記的是**你的問題**。點開才有答案——複習時你得先自己答一次。上面每一類都不記
這個：它們記重點、記答案、記摘要，就是不記讀的人哪裡不懂。

三個實際差異：

- **問問題本身就是記錄動作。** 不必停下來切到標註軟體再手動建卡。incremental
  reading 這類方法通常死在這道摩擦上。
- **錨點是每次建置重新解析出來的，不是宣告的。** 先試公式編號這種重新轉檔後仍然
  存在的標籤，再試小節標題，最後才用引文；比對到多個位置就拒絕猜並報錯。
  Hypothes.is 的[研究](https://www.arxiv.org/abs/1512.06195)量測過純引文定位的下場：
  27% 的標註已經失去依附，另外 61% 只要內容一改就會失去。
- **卡片就是你當初卡住的那一句。** 引文會在複習頁上標成高亮，不必重讀整段才想起
  自己在問什麼。
- **產物是純檔案，而且出得去。** 卡片是 Markdown，可以進 git；複習頁是一個離線
  HTML，沒有帳號、沒有訂閱、沒有廠商。這裡不做間隔複習演算法，但
  `export_cards.py` 可以把卡片倒成 Anki 匯入檔（公式自動轉成 Anki 的 MathJax
  寫法）、CSV 或 JSON，排程交給專門做這件事的工具。

**不適合的情況**：想直接標 PDF 不想轉檔（用 Zotero；開源轉檔工具不少很吃硬體，
沒有 GPU 加速時可能比用 LLM 轉還慢）、要間隔複習排程（用 Anki，卡片可直接匯出過去，
這裡本身只有狀態篩選）、要標圖上的區域、要多人共享標註層（用 Hypothes.is）、
要管理整個文獻庫（用 Zotero）。

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

## 先把 PDF 轉成 Markdown

這套工具吃的是 Markdown，不是 PDF。repo 裡附了一份轉檔規則文件：
**[skills/paper-annotations/references/pdf2md_rules.md](skills/paper-annotations/references/pdf2md_rules.md)**（v1.3，923 行）。
它是寫給 LLM 看的規格書，管到逐字保留、多欄閱讀順序、圖說對應、表格、公式、
Algorithm 縮排，以及把正文切分成 `sections/` 並產生索引。

用法是開 **ChatGPT 網頁版**，同時上傳這兩個檔案：

1. `pdf2md_rules.md`
2. 你的論文 PDF

然後貼上規則文件 §0 裡的那段指令（開頭是「請依照本文件處理上傳的 PDF」），
把回傳的 ZIP 解壓到論文資料夾即可。

為什麼是 ChatGPT 網頁版而不是現成的 pdf2md 工具：聊天額度限制幾乎可忽略，AI 轉檔
可以做更積極的篩選（頁碼、頁首頁尾這類版面雜訊會被丟掉，不會混進正文），而且不少
開源轉檔工具相當吃硬體——沒有 GPU 加速時，實測轉一篇論文比丟給 LLM 還久。

兩個要有心理準備的地方：

- **很花時間。** 一篇 IEEE 期刊論文通常要多次來回。
- **模型與推理強度顯著影響結果。** 實測 GPT-5.6 Sol＋高推理較佳。

想用自己的工具轉也可以，只要 Markdown 有章節標題就能用——只是疑問沒辦法精準掛在
公式或圖表上，論文改版時比較容易對不上位置。轉完跑 `/paper-annotations:setup`，
它會告訴你這份轉檔支援到什麼程度。

## 產物放在哪

```
論文資料夾/
  論文.pdf
  論文_md/              ← 轉檔套件（原文唯讀）
    sections/ INDEX.md images/
    notes/              ← 你的疑問卡，唯一真實來源
  annotated/index.html  ← 複習頁，跟套件同一層
```

疑問卡跟原文放在一起，整包搬走還是完整的；複習頁放在套件外面，不用在幾十個檔案裡
翻。想換位置在 setup 時說一聲就好（`--out` 移動筆記、`--review` 移動複習頁），
路徑會記進 `notes/paper.yml`，之後都不必再帶。

## 複習頁

`annotated/index.html`，一個檔案、離線可開、公式照樣渲染（KaTeX 內嵌）。

- **頁面就是一篇論文。** 卡片不佔版面，正文只多了幾處反白——**點反白的句子**才叫出
  當初的問題，蓋在畫面中間，關掉就繼續讀。疑問再多，論文也不會被撐開
- **先看問題再看答案**：叫出來時最上面是你當初的提問，底下才是卡點、解答、直覺
- **側邊欄滑出式**：滑鼠移到左上角的按鈕就滑出來，蓋在論文上方——**論文一格都不會位移**。
  裡面是論文目錄與按論文順序排的疑問清單，點清單一樣叫出卡片（沒有反白可點的卡片就
  靠這裡進入）。要它留著就按「釘住」，觸控裝置也是點一下釘住
- **右邊有提問草稿區**：讀完整段再一次把問題寫下來，不必讀到一半打斷去問。打開時
  論文會讓開，不會被蓋住；寫完按「複製」貼回對話。內容存在瀏覽器本機，重開還在。
  它只是草稿——不會送出，也不會自己變成卡片
- **篩選**：依狀態（未解決／半懂／已解決）、隱藏 AI 主動標的卡、全文搜尋。
  選「不顯示疑問」連反白都熄掉，剩一份乾淨的論文
- **明暗主題**，跟隨系統或手動切換
- 要寄給別人就加 `--embed-assets`，圖片一併內嵌成單一檔案

## 整理

`/paper-annotations:digest` 讀卡片和原文，寫一份給你自己的整理。**不做論文摘要**——
那是 SciSpace、Scholarcy 那類工具的活，而且對讀完並卡過的人沒用。

| 模式 | 產出 | 什麼時候用 |
|---|---|---|
| `review-sheet` 回顧單 | 按論文順序，一節一行：這節在做什麼、你的疑問、狀態 | 重讀之前，五分鐘掃出還有哪幾節沒通 |
| `theme-map` 主題聚合 | 把散在不同節、其實同一件事沒通的疑問併組，附重讀順序 | 疑問彼此有牽連時；這是自己最難做的一種 |
| `prerequisites` 前提盤點 | 從卡點反推缺的背景知識，指出去哪補 | 同一個概念反覆出現在不同卡點時 |

回顧單和主題聚合**只列問題不給答案**，答案在卡片裡展開就有。整理寫到
`notes/digests/`，是額外產物，不影響建置。

**整理不是冪等的**：`annotated/` 可以隨時重生，整理不行——同樣的卡片再跑一次不會得到
一樣的文字。想留舊版就先改檔名。

## 匯出

`/paper-annotations:export`，或直接跑：

```bash
python export_cards.py <論文路徑> --format anki --status resolved,half
```

`## 問題` → Front，`## 解答` → Back，卡點、直覺與原文引文進 Extra；`$…$` 會轉成 Anki
的 MathJax 寫法（`\(…\)`），匯進去就會渲染。也支援 `--format csv` 與 `json`。

預設不匯出 `open` 的卡——還沒有解答的問題，做成問答卡背面是空的。匯出是唯讀的，
卡片本身不會被改動。

## 指令

| 指令 | 用途 |
|---|---|
| `/paper-annotations:setup <論文資料夾>` | 設定新論文，判定支援程度，首次建置 |
| `/paper-annotations:build [路徑]` | 重新產生註記檢視與複習頁，回報所有警告 |
| `/paper-annotations:review [路徑]` | 盤點還有哪裡沒懂 |
| `/paper-annotations:digest [路徑] [模式]` | 把疑問與原文合成一份整理：回顧單、主題聚合、或前提盤點 |
| `/paper-annotations:export [路徑] [格式]` | 匯出卡片：Anki 匯入檔、CSV 或 JSON |

平常**不需要指令**：直接問論文問題，疑問會自動累積成卡片。

## 授權

MIT。內含 [KaTeX](https://katex.org) v0.18.4（MIT），見 `skills/paper-annotations/scripts/vendor/katex/LICENSE`。
