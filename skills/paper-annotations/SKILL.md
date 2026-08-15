---
name: paper-annotations
description: 讀論文時把使用者的疑問就地註記回原文，累積成可複習的筆記與單頁 HTML。使用時機：使用者問論文內容、要求記下疑問、要更新或複習既有的論文筆記、手上有 PDF 或 Markdown 論文要開始讀。
---

# 論文疑問註記

使用者讀論文時卡住的地方，做成**疑問卡**掛回原文對應位置，供日後複習。

原文唯讀。卡片是唯一真實來源，`annotated/` 與 `notes/QUESTIONS.md` 都可重新生成。

## 指令

`<scripts>` 代表本 skill 的 `scripts/` 目錄；`<paper>` 是論文 Markdown 套件的根目錄
（含 `sections/`、`INDEX.md` 的那一層，或單一 `.md` 所在目錄）。

```bash
python <scripts>/probe.py <paper> [--out <筆記路徑>] [--review <複習頁路徑>]
python <scripts>/build_annotated.py <work>             # 改卡片後：重建 Markdown 檢視與索引
python <scripts>/build_html.py <work>                  # 接著：重建複習用的 index.html
python <scripts>/reanchor.py <work>                    # 原文重新轉檔／切分後：把卡片接回去
python <scripts>/export_cards.py <work> [--format anki|csv|json] [--status resolved]
python <scripts>/import_marks.py <work> --from <檔>   # 複習頁「複製畫記」的輸出
python <scripts>/serve.py <work> [--port 8975]        # 複習頁的畫記可直接存檔
```

`export_cards.py` 是唯讀的，給想拿卡片去 Anki 排程或自己處理的人用；預設寫到
`notes/cards-export.txt`。這裡不做間隔複習演算法，只負責讓資料出得去。

**`<work>` 是 `notes/` 所在的目錄**，不一定是論文目錄。預設版面：

```
論文資料夾/
  論文.pdf
  論文_md/              ← 轉檔套件（原文唯讀）
    sections/ INDEX.md images/
    notes/              ← 疑問卡，唯一真實來源
  annotated/index.html  ← 複習頁，跟套件同一層
```

卡片留在套件裡（整包可攜），複習頁放在套件旁邊——套件裡有幾十個檔案，複習頁埋在
裡面就等於找不到。`probe.py` 只在論文套件看起來是轉檔產物時（目錄名以 `_md` 結尾，
或同層有 PDF）才往上放一層，否則仍放在 `<work>/annotated`。

`--out` 移動筆記，`--review` 只移動複習頁；兩者都會記進 `paper.yml`，之後的指令
不需要再帶旗標。給了 `--out` 就表示使用者自己決定了工作區位置，複習頁預設跟著筆記走。

不要為了搬動產物而去改路徑或搬檔案：所有相對連結（圖片、卡片回連、索引跳轉）都是
build 時依實際位置算出來的，手動搬移會全部斷掉。改位置就重跑一次 `probe.py`。

零依賴，只需要 Python 3.8+。所有檢查都在 Python 裡，不要改用 `grep`、`sed`——
使用者可能在只有 PowerShell 的 Windows 上。

## 何時動作

- 使用者問了關於論文內容的問題 → 回答，然後起草一張卡
- 使用者說「重建 / 更新筆記」→ build
- 使用者換了一版原文轉檔 → reanchor，再 build

## 閱讀回合的流程

1. **首次接觸一份論文**：跑 `probe.py`，把 Tier 告訴使用者。只有 PDF 時它會印出
   轉檔指引；Tier B/C 時說明升到 Tier A 能多拿到什麼、要花多少時間，讓他自己決定。
   細節見 [references/tiers.md](references/tiers.md)。
2. **回答問題**：遵守論文套件根目錄自己的 `AGENTS.md` 閱讀政策（通常是先讀
   `INDEX.md`、只讀 1–3 個 chunk）。
3. **起草卡片**：見下一節。
4. **回合結尾**：列出本回合新增的卡片標題，讓使用者當場否決。他不表態就是保留。
5. **執行 build**（先 `build_annotated.py` 再 `build_html.py`），把警告回報給使用者。

完成條件：本回合每個被回答的問題都有一張卡，且 build 回報「找不到位置」為 0、
沒有「🟡 引文提醒」（或已逐項向使用者說明原因）。

## 卡片格式

檔名 `notes/cards/NNNN-slug.md`，`NNNN` 是未使用過的流水號。**不要帶章節前綴**——
原文重新切分後前綴會變成誤導。

```yaml
---
id: "0007"
created: 2026-08-15
updated: 2026-08-15
status: open | half | resolved      # half = 半懂
origin: asked | suggested           # suggested = 你主動標的疑點，非使用者提問
tags: [density, poisson]
anchor:
  file: sections/S400-iv-a-density-function.md
  heading: ["IV. DENSITY FUNCTION ANALYSIS", "A. Density Function"]
  ref: eq:7                         # 選填：eq:N / fig:N / table:N
  quote:                            # 必填
    prefix: |-
      前文約 20 字
    exact: |-
      原文中獨一無二的一段字
    suffix: |-
      後文約 20 字
---

## 問題
## 卡點
## 解答
## 一句話直覺
```

`anchor` 只描述「要找什麼」，實際位置每次 build 都對原文重新解析，順序是
`ref` → `heading` → `quote` → 找不到位置。原理見
[references/anchoring.md](references/anchoring.md)。

## 卡片撰寫

**`## 問題` 是使用者複習時第一眼看到的東西**——複習頁上點了反白句子後，卡片最上面
就是它，疑問清單列的也是它。寫成看完就能開始嘗試回答的完整問題，不要寫成只有當下
才看得懂的簡稱。

**`## 卡點` 最重要**：寫下使用者當初缺哪個前提、誤解了什麼，不是重複問題。
沒有它，三個月後他會看不懂自己在問什麼。

**`## 一句話直覺`**：讓複習時不必重讀整段解答。

**引文會被標成高亮，而且是打開卡片的入口**：`quote.exact` 那句話在複習頁上會亮起來，
點它才叫得出卡片。所以引文要挑**真正讓使用者卡住的那一句**，不是隨便找一句夠獨特的
來當定位標記。找不到或找到多處時不標——跟錨點同一條規則，不猜；那張卡仍可從側邊的
疑問清單打開，只是正文裡沒有入口。

**引文唯一性**：`anchor.quote.exact` 必須在該檔案中只出現一次。build 每次都會檢查，
包括那些靠 `ref` 或 `heading` 已經掛好的卡。看到「🟡 引文提醒」就當場修掉，重新
build 到提醒消失為止——壞引文平常看不出來，會一路潛伏到使用者重新轉檔那天才爆炸。

**狀態**由使用者的反應決定：他說懂了 → `resolved`；還有疑慮 → `half`；沒解決 →
`open`。拿不準時用 `half`，那是最值得回頭看的一檔。

**`origin: suggested`** 留給你主動看出、使用者沒問但很可能踩到的坑。這種卡放行，
但要標清楚；複習介面可以一鍵把它們隱藏。

**卡片是筆記，不是論文**。解說中凡是論文沒明講、由你補上的推論，在卡片裡直說是
補充。使用者三個月後不會記得哪句是作者的、哪句是你的。

## 畫記（螢光筆）

複習頁上可以直接畫螢光筆並寫註解。**使用者跑 `serve.py` 時他自己按「存檔」就寫進
`notes/marks/` 並重建，不需要你介入**；他問怎麼免去複製貼上，就介紹這支。

沒有跑 server 時，畫記只活在瀏覽器裡。使用者按「複製畫記」把內容貼給你的時候，
**把整段存成檔案再交給 `import_marks.py`**，不要自己逐條轉寫：

```bash
python <scripts>/import_marks.py <work> --from <剛存下來的檔>
```

它會配流水號、寫成下面的格式、跳過已經存在的畫記（重跑安全），然後照常 build。
**畫記不需要你判斷或整理**：哪一段、什麼顏色、註解寫什麼，都是使用者已經決定好的。

匯入時的 🟡 提醒不必處理。含公式的畫記引文會是 KaTeX 的渲染字（例如 `x1,…,xn`），
在原始 Markdown 裡本來就找不到——頁面搜的是渲染後的文字，照樣定位得到。真正定位不到
的畫記，複習頁側欄會自己報數字。

檔案格式（`notes/marks/NNNN-slug.md`）：

```yaml
---
id: "0003"
created: 2026-08-16
color: yellow | green | blue | red
tags: [density]          # 選填
anchor:
  file: sections/S210-....md
  quote:
    prefix: |-
    exact: |-
    suffix: |-
---

註解內文，沒有就整段留空
```

定位得到的畫記會回到頁面上；使用者重新整理後，瀏覽器裡那份會自動消失，同一段不會被
畫兩次。build 也會再檢查一次引文並回報。

**畫記不是卡片**：沒有 status、不進疑問清單、不算進「疑問 N 則」。使用者只是把一段
標起來加一句話，就用畫記；他提出的是一個需要回答的問題，才建卡。

## 整理

使用者要一份「把疑問和原文合起來的整理」時，由你自己撰寫，不是跑腳本。三種模式
（回顧單／主題聚合／前提盤點）、出處規則與輸出位置見
[references/digests.md](references/digests.md)。整理是額外產物，不是真實來源。

## 邊界

- 原文只讀不寫。有話要說就寫成卡片。
- `annotated/`（含 `index.html`）與 `notes/QUESTIONS.md` 由 build 產生。要改內容
  改 `notes/cards/`、`notes/marks/` 後重建。
- 使用者的複習介面是 `annotated/index.html`；Markdown 版是給你和 git 用的。

## 沒有 Python 時

依同一套規則手工合併：從原文整份重建（不要增量插入舊的 `annotated/`），並在
`QUESTIONS.md` 標 `built_by: agent`。手工合併不保證冪等，這個標記是給使用者的
風險揭露。不要另寫一套實作。
