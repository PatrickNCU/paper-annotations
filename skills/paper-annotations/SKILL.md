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
python <scripts>/library.py [<起點>] [--json]          # 讀過哪些論文、疑問與要點、互相引用
python <scripts>/build_digest.py <work> [--only <前綴>] # 把整理的 .md 渲染成可直接開的 .html
python <scripts>/build_library.py [<起點>]             # 產生書房頁 library.html
python <scripts>/reanchor.py <work>                    # 原文重新轉檔／切分後：把卡片接回去
python <scripts>/export_cards.py <work> [--format anki|csv|json] [--status resolved]
python <scripts>/import_marks.py <work> --from <檔>   # 複習頁「複製畫記」的輸出
python <scripts>/serve.py <work> [--port 8975]        # 複習頁的畫記可直接存檔
python <scripts>/serve.py --library [<起點>]          # 一次服務所有論文，首頁是書房
python <scripts>/build_html.py <work> --embed-assets --to <檔>   # 寄給別人的單檔
```

`export_cards.py` 是唯讀的，給想拿卡片去 Anki 排程或自己處理的人用；預設寫到
`notes/cards-export.txt`。這裡不做間隔複習演算法，只負責讓資料出得去。

**`<work>` 是 `notes/` 所在的目錄**，不一定是論文目錄。預設版面：

```
papers.yml              ← 論文登記簿，放 git repo 根目錄
論文資料夾/
  論文.pdf
  論文_md/              ← 轉檔套件（原文唯讀）
    sections/ INDEX.md images/
    notes/              ← 唯一真實來源
      cards/ marks/ points/
      catalog.json references.json   ← 產生物，給跨論文用
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

### 工作區本身

放論文的那一層有四樣**工具不會自己建、但少了會出事**的東西。`/paper-annotations:setup`
在還沒有 `papers.yml` 時會列出缺的哪幾樣問使用者，規則見那支指令的第 0 步。

- **`.git`** — 決定 `papers.yml` 落在哪。有 repo 就放 repo 根目錄；沒有就退而放
  **執行指令的那一層**，前提是論文在它底下。兩條路通常給出同一個答案，但從別的目錄
  跑一次工具就會落到論文套件裡去，而那個位置**長不大**：下一篇論文往上找的路徑不會
  經過同輩的資料夾，於是自己再開一份登記簿，書房裂成兩半而畫面上什麼都不會說。
  probe.py 偵測到這件事會警告。
- **`.gitattributes`（`* text=auto eol=lf`）** — git 把原文行尾換成 CRLF 的話指紋
  就變了，build 會報出根本沒發生的原文漂移。
- **`.gitignore`（至少 `*.html`）** — 複習頁與書房頁都是產生物，且很大。
- **`AGENTS.md`** — 沒有它，使用者直接問論文問題不會自動走到這套工具。

這四樣都是**問過就做完**的事，不要問完又叫使用者自己去跑——他叫你 setup 就是不想自己
處理這些。

筆記適合放進**私有 GitHub repo**：登記簿存相對路徑，卡片、要點、複習紀錄全是純文字，
clone 到另一台機器直接可用。本機的 `git init` 與 commit 他同意就做；**push 到遠端要他
明確開口**，那是把東西送出這台機器。

## 何時動作

- **接觸任何一篇論文之前** → 先跑 `library.py`，知道他讀過什麼（見下節）
- 使用者問了關於論文內容的問題 → 回答，然後起草一張卡
- 使用者說「重建 / 更新筆記」→ build
- 使用者換了一版原文轉檔 → reanchor，再 build

## 閱讀回合的流程

0. **先看他讀過什麼**：跑 `library.py`。這是每個回合的第一件事，不是只有第一次。
   新 session 的你對這個人的閱讀史一無所知，而跨論文的關聯正是他要的東西——
   `library.py` 印出每篇的疑問、要點與互相引用，一次就補齊。
1. **首次接觸一份論文**：跑 `probe.py`，把 Tier 告訴使用者。只有 PDF 時它會印出
   轉檔指引；Tier B/C 時說明升到 Tier A 能多拿到什麼、要花多少時間，讓他自己決定。
   細節見 [references/tiers.md](references/tiers.md)。probe 會登記這篇論文，並報出
   它和他讀過的哪幾篇互相引用——**引用關係要主動講**，那是他最想知道的第一件事。
2. **開卷一次**：新論文第一次讀，做一趟結構化掃描抽出要點。見「要點」那節。
3. **回答問題**：遵守論文套件根目錄自己的 `AGENTS.md` 閱讀政策（通常是先讀
   `INDEX.md`、只讀 1–3 個 chunk）。讀到的 chunk 裡若有值得留的要點，**順手記下來**。
4. **起草卡片**：見下一節。
5. **回合結尾**：列出本回合新增的卡片標題**與要點**，讓使用者當場否決。他不表態就是保留。
6. **執行 build**（先 `build_annotated.py` 再 `build_html.py`），把警告回報給使用者。
   他正在讀而且還沒開 server，順帶提一次 `/paper-annotations:serve`：畫記可以直接存檔，
   不必再經過複製貼上。

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

**畫記正常不需要你介入**：使用者跑 `serve.py`，在頁面上按「存檔」就寫進 `notes/marks/`
並重建；改註解、換顏色、刪畫記也一樣。這是預設路徑——他還在手動複製貼上，就介紹
`/paper-annotations:serve`。

只有**沒跑 server**時（多半是別人寄了一個複習頁 HTML 給他）畫記才留在瀏覽器裡。他按
「複製畫記」把內容貼給你的時候，**把整段存成檔案再交給 `import_marks.py`**，不要自己
逐條轉寫：

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

## 要點

卡片來自使用者的困惑，畫記來自他的手；兩者都沒發生的地方，這套系統就是瞎的。而**跨論文
的關係恰恰長在他沒卡住的地方**——兩篇論文會不會矛盾，矛盾的是主張，不是誰的疑問。要點就是
補這個洞：論文的骨架，由你寫，用來和其他論文對照。設計理由見
[docs/adr/0002](../../docs/adr/0002-points-are-a-third-note-type.md)。

檔案 `notes/points/NNNN-slug.md`：

```yaml
---
id: "0001"
created: 2026-08-17
kind: claim | method | assumption | definition | result | limitation
origin: agent | user            # agent = 你讀出來的（預設）
tags: [local-density, 兩篇對照]
anchor:
  file: sections/S130-....md
  heading: ["Contributions and Paper Organization"]   # 選填，只當標籤
  quote:                        # 必填，而且是唯一的定位方式
    prefix: |-
    exact: |-
    suffix: |-
---
一句話，就一句。
```

**要點只靠引文定位**，不走卡片的 `ref → heading → quote` 階梯。卡片講的是論證裡的一個
位置，掛在小節開頭沒問題；要點轉述的是**特定那一句**，掛到半頁之外就會變成對錯誤的文字
說錯誤的話。`heading` 純粹是索引上的標籤。

### 怎麼取得

兩條並用，缺一不可：

**開卷一次**：新論文第一次讀時，掃摘要、引言、結論、各節標題，以及明確標了貢獻的段落。
**不要讀全文**——論文的主張本來就寫在這幾個地方，成本有界。一篇期刊論文抽 5～12 則就夠，
寧可少而準。

**順手記**：之後每次為了回答問題讀某個 chunk，同時記下那個 chunk 裡值得留的要點。零額外
閱讀成本，覆蓋率跟著他讀的深度長。

### 護欄

要點是你主動產生的，所以最大的風險不是寫錯，是**寫太多**。量一失控，使用者會關掉整個功能
而不是修它。

- **每回合結尾列出新增的要點讓他當場否決**，跟卡片一樣。他不表態就是保留。
- 開卷那趟有上限。抽不到好的就少抽，不要湊數。
- 要點是**論文說的**，不是你的評論。你的推論寫進卡片或整理，不要混進要點。
- 一則一句話。需要三句才講得完的，多半是兩則，或者其實是一張卡。

**要點不是卡片也不是畫記**：沒有 status、不進疑問清單、不算進「疑問 N 則」。使用者提出
需要回答的問題 → 卡片；他自己標起一段 → 畫記；**論文自己主張了什麼 → 要點**。

## 複習排程

複習頁側欄的「複習」是內建的間隔重複，不需要 Anki。**評分必須有 `serve.py` 在跑**——
複習紀錄要寫成檔案，而複習歷史是這套系統裡唯一無法重生的資料，設計理由見
[docs/adr/0003](../../docs/adr/0003-review-history-is-the-first-irreplaceable-data.md)。
沒跑 server 時頁面照樣列出待複習的卡，但不給評分按鈕，也會說明原因。

哪些卡進排程，由狀態決定，你不需要也不應該手動干預：

| 狀態 | 進排程嗎 |
|---|---|
| `resolved` ＋ `origin: asked` | 進。他懂了，接下來是別忘掉 |
| `half` | 不排程，但永遠排在佇列最前面。半懂不是記憶問題，是還沒讀完 |
| `open` | 不進。它本來就在疑問清單裡 |
| `origin: suggested` | 不進。那是你標的，不是他問的 |

紀錄放在 `notes/reviews/<卡片編號>.md`，一行一次評分。**build 絕對不寫這個目錄**，
唯一的寫入者是 server 的評分端點。排程狀態不儲存，每次由紀錄重放算出來——所以日後換
演算法不需要任何遷移。

卡片被刪除後紀錄會留著，build 回報成孤兒。**不要自動清掉**，那是使用者的資料。

`export_cards.py --format csv` 會帶上 `reviews / interval / ease / lapses / due`，
想搬去 Anki 的人不必從零開始。

## 跨論文

`library.py` 是你看見「不只這一篇」的唯一途徑。它讀 `papers.yml`（登記簿，在 git repo
根目錄）與每篇的 `notes/catalog.json`（build 產生的卡片與要點目錄），印出全部論文的疑問、
要點，以及**互相引用的關係**。

引用關係是機械判定的：`probe.py` 把參考文獻抽進 `notes/references.json`，比對在讀取時
才做，所以今天新增一篇論文，上個月處理的那篇的引用關係會自動跟著更新。它**不需要判斷**，
所以可以直接當事實講給使用者聽——包括引用出現在哪一節、當下那句話怎麼說的。

有判斷成分的關係（共識、矛盾、同一概念的不同講法）由你寫成整理，見下一節的 `connections`
模式。不要把判斷寫進 `references.json` 或 `catalog.json`，那兩個是產生物。

### 卡片與要點之間的連結

`connections` 整理找出的關係，值得留下的就固化成連結。整理是散文，得靠使用者想起來去翻；
連結會**自己出現在它所談的那一句旁邊**，兩者是前後關係，不是二選一。

宣告在卡片或要點的 frontmatter，一行一條，**只寫一邊**：

```yaml
links:
  - contradicts eplace-ms#P0003
  - answers replace#Q0002
  - same-as #Q0004            # 省略代號就是本篇
```

型別只有三種：`answers`（這則回答了目標）、`contradicts`（兩邊說法牴觸）、`same-as`
（同一件事的不同講法）。**不要自己發明型別**，build 會擋下來。清單刻意很短——開放的
詞彙會長出一堆近義詞，然後就不能拿來比對了，而那是連結存在的唯一理由。真的不夠用時
再來加，不要預先擴充。

反向連結**由 build 算出來**，不要在兩邊各寫一條——那會漂移。目標的一句話也會一起顯示，
所以看到連結就知道對方說了什麼，不必跳過去。

解析遵循 ADR 0001：目標是拿當下的 `catalog.json` 比對的，解不到就回報、不猜。因此
**目標論文必須先 build 過**（沒有 catalog 就沒有可比對的東西），而新增一篇論文之後，
指向它的連結會在下次 build 時自動接上，不需要改任何檔案。

### 書房頁

`build_library.py` 產生 `library.html`（放在 `papers.yml` 旁邊）：每篇論文一張卡，帶疑問
統計、要點數、今天要複習幾張。

**互相引用列在卡片上，不是頁尾**：同一條邊在兩端都出現一次（引用方看到「→ 引用了 X」、
被引用方看到「← 被 X 引用」），按下去會跳到對方那張卡並讓它閃一下；對方被目前的篩選藏起來
時會先切回「全部」。「這篇跟誰有關係」是關於這篇論文的問題，答案就該放在這篇論文旁邊。

**用 `serve.py --library` 開**——一個 server 掛所有論文，點卡片直接進那篇的複習頁，
不需要另外開任何東西。`serve.py --library --launcher` 會在 `papers.yml` 旁邊放一個
`開啟書房.cmd`，點兩下就起來；它不帶路徑參數，所以整個工作區搬家或 clone 到別台機器
都還能用。

直接雙擊 `library.html` 也開得起來，但論文連結是 server 路徑、點不動——頁面偵測到不是
http 就會在最上面明講並附上指令，不必等使用者踩到。

### 分類

書房頁上方一排分類標籤：**全部**列出所有論文，點某個分類就只列出屬於它的。清單只有一份，
一篇論文只出現一次，它的所有分類顯示在自己的卡片上。**已定義的分類一律列出來，包含底下
一篇論文都沒有的**（虛線、數字 0）——把空分類藏起來的話，剛建好一個分類跟建立失敗看起來
一模一樣。

使用者也可以**自訂分類**（像「已讀過」這種和論文主題無關、屬於他自己的分類）：書房頁上
「＋ 新增分類」，或在某篇論文的「＋ 加入分類」裡選「＋ 自訂新分類」，後者會建立並直接掛上。
自訂的分類一律進 `topics`（他的），不是 `topics_auto`。

書房頁的「⚙ 管理分類」會在每個分類旁邊長出色票（換顏色）、`↺`（回到預設）和 `✕`
（刪掉分類，**只有底下沒有論文的刪得掉**）。顏色存在 `papers.yml` 的 `topic_colors:`
（slug → `#rrggbb`），沒設定的分類外觀完全不變。**不要主動幫使用者配色**，那是他的偏好，
不是可以推導的事實。

**詞彙表在 `papers.yml` 的 `topics:`（slug → 顯示名稱），先定義才能使用。** 沒定義的分類
build 會回報，篩選列上也不會有它——那不是龜毛，是避免 `3D-IC` 和 `3d-ic` 變成兩個看起來
一樣的分類。每篇論文底下三個清單：

| 欄位 | 意思 |
|---|---|
| `topics` | 使用者自己定的。頁面上是實線標籤 |
| `topics_auto` | **你**建議的，一樣生效。頁面上是虛線標籤 |
| `topics_off` | 使用者移除過的。**不要再建議這些** |

#### 什麼時候提議分類

**主要時機是 `/paper-annotations:setup`**——新論文第一次進來就分好，不要等使用者哪天
想到才補。之後跑 `library.py` 看到沒分類的論文時再補提。

#### 你要怎麼提議分類

**分類必須比關鍵字粗。** `catalog.json` 的 `keywords` 是論文自己的 Index Terms，那是
**原料，不是分類**——實測兩篇直接相承的論文（ePlace-MS 與 RePlAce）13 個關鍵字交集為零，
拿來當分類的話每篇各自成一類，等於沒分類。要做的是把 "Analytic placement" 和
"Global placement" 收斂成同一個 `placement`。

- 寫進 `topics_auto`，不要寫進 `topics`——那是使用者的欄位
- 一篇 2～4 個就夠。分類是拿來把論文**分開**的，每篇都掛滿等於沒分
- 新分類要同時加進 `topics:` 詞彙表，否則 build 會回報
- 回合結尾列出新增的分類讓使用者當場否決，跟卡片與要點一樣
- **`topics_off` 裡的絕對不要再提**。一個被拒絕還一直回來的建議比沒有建議更煩

#### 分類不是由 build 想出來的

build 只負責**讀取與分組**，它是純 Python、裡面沒有 LLM，而且必須冪等。「想出分類」發生
在對話裡（你做），「套用分類」發生在 build。這個分工是刻意的：分類若每次 build 重算，
同樣的輸入就會產生不同的輸出，整套設計的地基就沒了。

使用者在書房頁上按「＋ 加入分類」或點標籤移除時，由 server 寫回 `papers.yml`——**需要
`serve.py --library` 在跑**，沒有就不顯示按鈕。加入寫進 `topics`，移除同時記進
`topics_off`。改顏色、刪分類走同一個端點（`POST /_pa/topic`，action 為
`add`／`remove`／`define`／`color`／`undefine`），寫完都會重建書房頁。

多論文模式下每篇掛在 `/p/<代號>/` 底下，**各自只開放自己的資料夾**。不要試圖給 server 一個
橫跨所有論文的根目錄——論文散在硬碟各處時那會退化成整顆磁碟。同理，寫入請求帶的是論文代號，
由 server 端查表得到路徑；任何情況下都不要讓請求裡的字串變成路徑。

單篇模式（`serve.py <work>`）完全沒變，既有的啟動器照舊可用。

## 整理

使用者要一份「把疑問和原文合起來的整理」時，由你自己撰寫，不是跑腳本。四種模式
（回顧單／主題聚合／前提盤點／接線）、出處規則與輸出位置見
[references/digests.md](references/digests.md)。整理是額外產物，不是真實來源。

**寫完一定要跑 `build_digest.py`**，把 `.md` 渲染成同名的 `.html`，並且**回報 `.html`
的路徑**——那才是使用者要開的檔案。整理裡多半有公式，`$\lambda$` 在文字編輯器裡讀不了，
而且不能假設使用者裝了 Markdown 編輯器。`.md` 仍然是可編輯的來源，改完重跑即可。

## 邊界

- 原文只讀不寫。有話要說就寫成卡片。
- `annotated/`（含 `index.html`）、`notes/QUESTIONS.md`、`notes/catalog.json` 由 build
  產生；`notes/references.json` 與 `papers.yml` 由 probe 產生；`notes/digests/*.html`
  由 build_digest 產生。要改內容改 `notes/cards/`、`notes/marks/`、`notes/points/` 後重建。
- **`notes/reviews/` 不是產生物，也不可重生。** 只有 server 的評分端點寫它。任何情況下
  都不要用程式碼去改或刪它。
- 使用者的複習介面是 `annotated/index.html`；Markdown 版是給你和 git 用的。

## 沒有 Python 時

依同一套規則手工合併：從原文整份重建（不要增量插入舊的 `annotated/`），並在
`QUESTIONS.md` 標 `built_by: agent`。手工合併不保證冪等，這個標記是給使用者的
風險揭露。不要另寫一套實作。
