# PDF → Markdown 精確轉換規則

版本：v1.4

## 0. 使用方式

未來需要轉換時，請同時上傳：

1. 本規則文件。
2. 原始 PDF。
3. 若已經執行 Docling、Marker 或其他 parser，可一併上傳原始輸出 ZIP。

可直接使用以下指令：

> 請依照本文件處理上傳的 PDF。逐字保留原文，不得摘要、潤飾、改寫或改善文法。修復多欄閱讀順序、圖片與圖說對應、表格、公式、上下標、特殊符號及跨頁錯序。數學公式必須使用 VS Code Markdown Preview 可直接渲染的 `$...$` 與 `$$...$$`；Algorithm 縮排不得使用 `$\quad$` 或 `$\qquad$`；不得在 Abstract、Index Terms 等標籤前後加入會殘留顯示的 `**`。除完整的 `document.md` 外，必須依章節與語意將正文切分至 `sections/`，並產生 `INDEX.md`、`index.csv` 與 `AGENTS.md`，使 Agent 先讀索引、再只讀必要段落。交付套件的根目錄與 ZIP 必須命名為 `<短名>_md`（短名取原始 PDF 檔名第一個底線之前的片段，例如 `RePlAce_md`），不得使用 `output` 這類通用名稱，且解壓後最上層只有這一個資料夾。最終輸出不得包含 `raw/`。Parser 原始輸出只可作為轉換期間的暫存資料，完成核對後必須從交付套件中排除。回傳 ZIP 前須完成內容、切分、索引、重組與 ZIP 完整性驗證，且不得包含修復腳本、快取、工作目錄或其他暫存文件。

---

## 1. 任務目標

將 PDF 轉換成適合人類閱讀及供 Codex／程式分析的 Markdown 套件：

- 正文忠實。
- 閱讀順序正確。
- 圖片、表格、公式的位置與內容正確。
- 所有結果可追溯至原始 PDF。
- 移除無分析價值的版面雜訊。
- 最終套件不保留 parser 的原始輸出，以降低檔案體積、重複內容與 Codex context 干擾。
- 將完整正文切分為可選擇性讀取的語意段落，讓 Agent 一般只需讀取索引與 1～3 個相關子檔案。
- 提供人類可讀與機器可讀的段落索引，以及明確的 Agent 閱讀政策。
- 不因英文不自然而改寫原文。

---

## 2. 核心原則

### 2.1 原文逐字保留

正文不得摘要、簡化、重述、潤飾、改善文法、替換用字或合併句子。

例如原文：

```text
abbreviated as ms-cut as we subsequently refer to it
```

不得改成：

```text
abbreviated as ms-cuts
```

原文即使有不自然的文法，也應保留。

### 2.2 只修復轉換造成的錯誤

允許修復：

- 雙欄／多欄錯序。
- 跨頁句子錯序。
- 排版造成的斷字。
- parser 造成的亂碼。
- 公式與上下標遺失。
- 特殊符號解析錯誤。
- 圖片、圖說、表格位置錯誤。
- 頁首頁尾混入正文。
- 可由原始 PDF 明確確認的 OCR 錯字。

無法確定時不得猜測，應保留並標記 `review_required`。

### 2.3 不得把推論混入正文

新增說明、推論或修復備註只能放在：

- `README.md`
- `validation/issues.md`
- `validation/validation.json`

---

## 3. 保留與移除規則

### 3.1 必須保留

- 標題、作者、單位、E-mail。
- Abstract、Keywords。
- 所有章節、小節與正文。
- Lemma、Theorem、Proof、Definition。
- 所有 inline／display 公式與編號。
- 上標、下標與特殊符號。
- Figure、caption。
- Table、caption、單位、footnote。
- Algorithm／Pseudo-code。
- References。
- 有實質意義的 footnote。

### 3.2 從正文移除，但移至 metadata

- DOI、ISSN、arXiv 編號。
- 出版年份、期刊名稱、出版商。
- 網站、頁數、文件版本。

以上應寫入 `manifest.json`，不得反覆出現在正文。

### 3.3 預設移除

- 每頁重複的期刊名稱。
- 頁碼。
- 重複頁首頁尾。
- Publisher copyright footer。
- 重複 DOI／ISSN／網址。
- 期刊 Logo 與純裝飾圖片。
- 掃描邊框、空白頁。
- parser 造成的重複 caption。
- 因跨頁而重複的表頭。

### 3.4 不能無條件刪除

表格資料來源、Figure 授權註記、縮寫說明、學術 footnote、作者聲明等，若會影響理解、引用或數據解釋，必須保留。

---

## 4. 最終輸出結構

### 4.0 套件資料夾名稱

套件根目錄必須命名為 `<短名>_md`，ZIP 檔名為 `<短名>_md.zip`。

**短名的取法**：優先取原始 PDF 檔名中第一個底線之前的片段。

| PDF 檔名 | 短名 | 套件資料夾 |
|---|---|---|
| `ePlace-MS_Electrostatics-Based_Placement_for_Mixed-Size_Circuits.pdf` | `ePlace-MS` | `ePlace-MS_md/` |
| `RePlAce_Advancing_Solution_Quality_and_Routability_Validation.pdf` | `RePlAce` | `RePlAce_md/` |

若第一個片段不是有意義的名稱（例如 `1-s2.0-...`、`paper`、`2015`、`preprint`），改用
論文標題中的方法名稱或公認縮寫。短名只使用 `A-Z a-z 0-9 . -`，不使用空白、底線與中文。

**不得使用通用名稱**：`output/`、`result/`、`converted/`、`md/`、`markdown/` 一律禁止。

ZIP 解壓後最上層必須**只有這一個資料夾**——不要把檔案散在 ZIP 根目錄，也不要多包一層。

理由有兩個。其一，多篇論文的套件常常並存於同一個工作區，通用名稱會撞名，也看不出
內容是哪一篇。其二，下游工具靠 `_md` 結尾辨識「這是轉檔套件」而非一般資料夾——
例如 paper-annotations 用它決定複習頁該產生在哪一層。

### 4.1 目錄樹

```text
<短名>_md/
├── AGENTS.md
├── INDEX.md
├── index.csv
├── document.md
├── sections/
│   ├── S000-title-authors.md
│   ├── S010-abstract.md
│   ├── S100-introduction-01.md
│   └── ...
├── images/
│   ├── figure-01.png
│   └── ...
├── tables/
│   ├── table-01.png
│   ├── table-01.csv
│   └── ...
├── validation/
│   ├── validation.json
│   └── issues.md
├── manifest.json
└── README.md
```

### 4.2 完整文件與檢索文件的角色

- `document.md`：完整、忠實且具正確閱讀順序的權威正文，供人工通讀、全文查核與切分失敗時回退使用。
- `sections/*.md`：由 `document.md` 衍生的語意完整子檔案，供 Agent 選擇性讀取；不得摘要、改寫或省略正文。
- `INDEX.md`：Agent 與人類的第一閱讀入口，必須以表格統整所有子檔案、來源頁碼、主題、資產與預估 token。
- `index.csv`：與 `INDEX.md` 對應的機器可讀索引，供離線程式、搜尋腳本與 Agent 查詢。
- `AGENTS.md`：明確規定先讀索引、只讀最小必要段落、精確數值優先讀 CSV、不得預設掃描所有子檔案。
- `manifest.json`：記錄文件、切分、索引與資產的機器可讀 metadata。

`document.md` 與 `sections/` 必須同時保留：前者負責完整性，後者負責降低 Agent 的不必要 context 消耗。

### 4.3 最終套件禁止包含 `raw/`

- Docling、Marker、PyMuPDF、pdftotext 或其他 parser 的原始輸出可在轉換與驗證期間使用。
- 原始 parser 輸出不得放入最終交付 ZIP，也不得由 `document.md`、`INDEX.md` 或 `README.md` 連結。
- 若使用者上傳 parser 原始輸出 ZIP，只將其視為輸入資料；完成修復後不複製到輸出套件。
- 追溯資訊改由原始 PDF 名稱、檔案雜湊、parser 名稱／版本、來源頁碼、驗證報告及 `manifest.json` 保存。
- 回傳前必須確認 ZIP 中不存在名為 `raw` 的目錄或 parser dump 檔案。

此規則的目的，是避免重複文字、錯誤閱讀順序及未修復內容干擾 Codex，並減少 repository 體積與 context 消耗。

### 4.4 ZIP 不得包含暫存文件

不得包含：

- 修復用程式或腳本。
- `tmp/`、`temp/`、`work/`、`debug/`、`cache/`。
- `__pycache__/`、`.pytest_cache/`、`.ipynb_checkpoints/`。
- 測試圖片、debug screenshots。
- 臨時 PDF。
- 未使用的裁切圖。
- 重複輸出目錄。
- 非正式 log。

`validation/` 屬於正式輸出；`raw/` 不屬於正式輸出，必須排除。

---

## 5. Markdown 要求

### 5.1 閱讀順序

必須依語意順序重建，不可只沿用 PDF 物件順序。

需正確處理：

- 雙欄／三欄。
- 跨欄標題。
- 浮動 Figure／Table／Algorithm。
- 跨頁句子與跨頁表格。
- Figure／Table 的正確插入位置。

禁止：

- 圖片插在句子中間。
- 左右欄交錯。
- 頁首頁尾插入正文。
- Figure 編號錯序。
- caption 與錯誤圖片相鄰。

### 5.2 Heading

章節必須使用正確 Markdown heading：

```markdown
# 1 Introduction
## 1.1 Outline
### 3.2.1 Routing Model
```

不得將小節標題當成一般段落。

### 5.3 斷字

僅能合併由排版造成的行尾斷字，例如 `rout-` + `ing`。原文真正的連字號，例如 `two-terminal`，必須保留。


### 5.4 VS Code Markdown Preview 相容性

最終 `document.md` 必須可由 VS Code 內建 Markdown Preview 直接閱讀，不得依賴額外的 LaTeX、MathJax 或第三方 Markdown extension 才能正常顯示。

必須遵守：

- Inline math 使用 `$...$`。
- Display math 使用 `$$...$$`。
- 不得使用 `\(...\)` 或 `\[...\]` 作為最終公式分隔符。
- LaTeX 指令不得落在數學區塊之外，例如不得直接顯示 `\mathcal`、`\mathrm`、`\quad`、`\qquad`。
- `$` 分隔符必須成對，且不得跨越不相關段落、清單項目或表格儲存格。
- 最終結果應在 VS Code 設定 `Markdown › Math: Enabled` 開啟時正確渲染。

### 5.5 Markdown 標記不得外洩

Markdown 控制符號不得在預覽中以普通文字殘留，例如：

- `**`
- 單獨的 `$`
- 未閉合的反引號
- 未閉合的 HTML tag

`Abstract—`、`Index Terms—`、`Keywords—` 等標籤預設以普通文字保留：

```markdown
Abstract—Floorplanning determines ...

Index Terms—Floorplanning, Feedthrough, Components Placement
```

除非使用者另有要求，禁止輸出：

```markdown
**Abstract—**Floorplanning determines ...

**Index Terms—**Floorplanning, Feedthrough, Components Placement
```

此規則只限制 Markdown 標記，不得因此改寫、刪減或重排原文內容。


---

## 6. 圖片要求

每張 Figure 必須確認：

- 數量與原 PDF 一致。
- Figure 編號、caption、圖片內容一一對應。
- 無完全重複或語意重複。
- 無 Logo 被誤判為 Figure。
- 無 Algorithm 被誤判為 Figure。
- 子圖 `(a)`、`(b)` 完整。
- 座標軸、legend、箭頭、圖內文字未被裁掉。
- 不混入鄰近正文、頁首、頁尾或上一張 caption。

Caption 只可出現一次。預設將 caption 放在 Markdown，圖片本體不包含 caption。

命名：

```text
figure-01.png
figure-02.png
```

**必須使用行內語法插入圖片**，不得使用參考式（reference-style）：

```markdown
![Fig. 1](../images/figure-01.png)
```

不得輸出：

```markdown
![Figure 1][figure-01]

[figure-01]: ../images/figure-01.png
```

兩種都是合法 Markdown，但同一批論文混用兩種寫法，下游工具就得各支援一套；而且定義行
離圖片很遠，依章節切分時容易被拆到別的檔案，圖就此消失。

路徑一律相對於該檔案自己的位置：`sections/*.md` 用 `../images/…`，`document.md` 用
`images/…`。表格圖片同此規則。

---

## 7. 表格要求

每張 Table 原則上應輸出：

- PNG。
- CSV。
- 複雜表格建議再輸出 `cells.json` 或 HTML。

必須保留：

- 行列。
- 多層表頭與 merged cells。
- 單位。
- 上標、下標。
- footnote。
- 括號中的第二組數值。
- BC／WC 等雙值欄位。
- bold／最佳值的語意。

禁止：

- 猜數值或補值。
- 自行四捨五入。
- 改變有效位數。
- 漏掉負號、小數點或括號。
- 將 `0` 認成 `O`、`1` 認成 `l`。
- 合併錯列或填入空白 cell。

每張表至少核對：

- Table 編號與 caption。
- 行數、欄數、表頭。
- 每個數值及小數位數。
- 單位、上下標、footnote。
- 是否跨頁。
- 是否遺漏最後一列。
- PNG 與 CSV 是否為同一張表。

無法確認時不得輸出看似合理的結果，必須標記 `manual_review_required`。

---

## 8. 公式與上下標要求

所有公式必須轉成可渲染的 LaTeX，並使用 VS Code Markdown Preview 相容的分隔符。

Display math：

```markdown
$$
wt(e_{pq}) = \frac{\operatorname{length}(s_k)}{1-p_k}
\tag{1}
$$
```

Inline math：

```markdown
The normalized usage $p_k$ is constrained to 1.0.
```

禁止使用以下格式作為最終輸出：

```markdown
\(p_k\)

\[
PD(M_i)=\cdots
\]
```

必須正確保留：

- superscript／subscript。
- fraction、root、summation。
- set notation、union、intersection。
- quantifier、inequality。
- Greek symbols。
- complexity notation。
- Equation 編號。

典型修復：

| 錯誤 | 正確 |
|---|---|
| `O ( n 2 kt )` | `$O(n^2kt)$` |
| `G i r` | `$G_r^i$` |
| `G i c` | `$G_c^i$` |
| `p k` | `$p_k$` |
| `n i+1` | `$n_{i+1}$` |
| `t j = t k` | `$t_j \ne t_k$` |
| `10 6 µm` | `$10^6\,\mu\text{m}$` |

最終文件不得含：

```html
<!-- formula-not-decoded -->
```

亦不得出現：

- 未配對的 `$` 或 `$$`。
- `\mathcal`、`\mathrm`、`\frac`、`\sum`、`\arg\max` 等數學指令落在 `$...$`／`$$...$$` 外。
- 單純為了排版縮排而加入的 `$\quad$`、`$\qquad$`。
- 公式跨越不同清單項目，導致後續文字全部被當成數學區塊。

必須同時驗證語意，例如 `≠` 不得變成 `=`，分母不得移到分子，superscript／subscript 不得互換。

---

## 9. Algorithm 要求

Algorithm 優先轉成可搜尋的結構化 Markdown。若原版面對理解重要，可額外保留圖片。

### 9.1 內容與層級

必須保留：

- Algorithm 編號與標題。
- Require／Ensure。
- 原始行號。
- if／else／for／while／return／end if／end for／end while 的層級。
- 函式名稱、變數、上下標、集合及運算符號。

不得：

- 將 Algorithm 放到錯誤 Figure caption 下。
- 破壞 if／else／end if 層級。
- 讓 code block 與圖片在不合理位置重複。
- 改寫 pseudo-code 的操作順序或控制流程。

### 9.2 縮排

縮排不得使用數學公式命令充當空白。禁止：

```markdown
4. $\quad$Initialize $L_i$ ...
7. $\qquad N_i^c.\mathrm{value} \leftarrow \mathrm{Simulation}(N_i^c)$
```

建議使用一般 Markdown／HTML 縮排：

```markdown
4. Initialize $L_i$ with the root node $N_i^{\mathrm{root}}$
5. **while** $L_i \ne \varnothing$ **do**
6. &emsp;**for each** node $N_i^c \in L_i$ **do**
7. &emsp;&emsp;$N_i^c.\mathrm{value} \leftarrow \mathrm{Simulation}(N_i^c)$
8. &emsp;&emsp;**if** $N_i^c.\mathrm{value} == 1$ **then**
```

亦可使用巢狀清單或結構化 HTML，但必須同時滿足：

- VS Code 預覽中層級清楚。
- 原始行號不遺失。
- LaTeX 只包覆真正的數學內容。
- `\quad`、`\qquad` 不得殘留在數學區塊外。

### 9.3 Algorithm 驗證

每個 Algorithm 至少核對：

- 行數與原 PDF 一致。
- 行號未跳號、重複或錯置。
- 巢狀層級與原 PDF 一致。
- 所有數學片段均可渲染。
- 預覽中不得出現 `$\quad$`、`$\qquad$`、裸露 `\mathrm` 或裸露 `\mathcal`。

---

## 10. Metadata

`manifest.json` 建議包含：

```json
{
  "title": "",
  "authors": [],
  "source": "",
  "source_sha256": "",
  "doi": "",
  "arxiv": "",
  "year": null,
  "page_count": null,
  "main_document": "document.md",
  "authoritative_content": "document.md",
  "sections_path": "sections/",
  "index_file": "INDEX.md",
  "machine_index_file": "index.csv",
  "agent_policy_file": "AGENTS.md",
  "chunk_count": null,
  "chunking_policy": "semantic_heading_aware",
  "target_chunk_tokens": "600-1200",
  "hard_chunk_token_limit": 1500,
  "figure_count": null,
  "table_count": null,
  "algorithm_count": null,
  "equation_count": null,
  "parser_sources": [],
  "conversion_policy": "faithful",
  "raw_included": false,
  "raw_policy": "excluded_from_final_package",
  "unresolved_issues": []
}
```

---

## 11. 回傳前驗證

### 11.1 結構

- ZIP 可解壓縮且無 CRC error。
- 套件根目錄名為 `<短名>_md`（見 4.0），且是 ZIP 最上層唯一的資料夾。
- `AGENTS.md`、`INDEX.md`、`index.csv`、`document.md`、`sections/`、`images/`、`tables/`、`validation/`、`manifest.json`、`README.md` 均存在。
- `INDEX.md` 與 `index.csv` 列出的所有 chunk 檔案均存在，且 `sections/` 中沒有未被索引的正式 chunk。
- ZIP 中不存在 `raw/` 或 parser dump 目錄。
- 所有 Markdown、圖片、表格與相鄰 chunk 連結有效。
- 無零位元組資產。

### 11.2 圖片

- 數量、編號、caption、內容、順序正確。
- 無重複、錯圖、缺圖、錯裁切。
- 無 Logo 誤判。

### 11.3 表格

- 數量、編號、行列、數值、單位、上下標、footnote 正確。
- CSV 可解析。
- 無遺漏最後一列。
- PNG 與 CSV 對應。

### 11.4 Markdown

- Heading 正確。
- 多欄順序正確。
- 無句子被永久切斷。
- Figure／Table 未插入句子中央。
- References 完整。
- 無頁首頁尾混入正文。
- VS Code 內建 Markdown Preview 可正常顯示。
- `Abstract—`、`Index Terms—` 等標籤前後無殘留 `**`。
- Algorithm 縮排未使用 `$\quad$` 或 `$\qquad$`。

### 11.5 公式與內容

- 無 `formula-not-decoded`。
- LaTeX 可渲染。
- Inline／display 公式分別使用 `$...$` 與 `$$...$$`。
- 無 `\(...\)` 或 `\[...\]` 舊式分隔符。
- 無未配對的 `$`／`$$`。
- 無數學指令落在數學區塊外。
- 上下標及特殊符號完整。
- 所有章節、Lemma、Theorem、Proof、References 完整。
- 無長段正文消失。
- 無未說明的改寫。
- 無亂碼或 parser placeholder。

### 11.6 段落切分與索引

- 所有正文 block 均映射至一個且僅一個 primary chunk。
- 不得有正文遺漏、重複或跨 chunk 永久斷句。
- Formula 與緊接的變數定義不得分離。
- Algorithm 不得被任意拆開。
- Figure／Table caption 與其主要說明不得錯配。
- 所有 chunk 依索引順序重組並移除 YAML front matter、導航連結及檔案邊界空行後，必須與 `document.md` 的正規化正文一致。
- `INDEX.md` 與 `index.csv` 的 chunk ID、檔名、頁碼、類型、token 數及資產欄位必須一致。
- `AGENTS.md` 必須明確要求先讀 `INDEX.md`，且禁止預設掃描全部 `sections/`。
- 一般 chunk 目標為 600～1200 tokens；超過 1500 tokens 必須拆分，除非 Algorithm、公式定義、表格解釋或其他不可分割語意單位需要完整保留，並在驗證報告記錄原因。

### 11.7 暫存文件

最終 ZIP 中不得發現：

```text
tmp/
temp/
work/
debug/
cache/
__pycache__/
.ipynb_checkpoints/
*.pyc
repair.py
test_output/
raw/
```

---

## 12. 驗證報告

`validation/validation.json` 至少應包含：

```json
{
  "status": "pass",
  "zip_integrity": true,
  "raw_included": false,
  "raw_policy": "excluded_from_final_package",
  "chunk_count": 0,
  "indexed_chunks": 0,
  "missing_chunk_files": 0,
  "unindexed_chunk_files": 0,
  "duplicate_chunk_ids": 0,
  "missing_source_blocks": 0,
  "duplicate_source_blocks": 0,
  "sentence_split_errors": 0,
  "formula_definition_separations": 0,
  "algorithm_split_errors": 0,
  "reconstruction_match": true,
  "index_markdown_csv_consistent": true,
  "agent_policy_valid": true,
  "chunks_over_soft_limit": 0,
  "chunks_over_hard_limit": 0,
  "broken_links": 0,
  "missing_images": 0,
  "duplicate_images": 0,
  "figure_mapping_errors": 0,
  "table_errors": 0,
  "formula_placeholders": 0,
  "legacy_math_delimiters": 0,
  "unmatched_math_delimiters": 0,
  "math_commands_outside_math": 0,
  "algorithm_indent_math_tokens": 0,
  "literal_markdown_markers": 0,
  "vscode_preview_compatible": true,
  "reading_order_errors": 0,
  "temporary_files_found": 0,
  "unresolved_issues": []
}
```

仍有無法確認的項目時，狀態必須是：

```json
{
  "status": "review_required"
}
```

不得在仍有 unresolved issues 時宣稱 `pass`。

---

## 13. README

`README.md` 應說明：

- 原始 PDF 名稱。
- 使用的 parser。
- 修復範圍。
- 移除的版面元素。
- 保留的 metadata。
- Figure／Table／Formula 數量。
- unresolved issues。
- Parser 原始輸出未包含於最終套件。
- `document.md` 是否逐字保留。
- `sections/` 的 chunk 數量、目標 token 範圍與例外 chunk。
- `INDEX.md`、`index.csv` 與 `AGENTS.md` 的用途。
- 是否完成 coverage、重組一致性與索引一致性驗證。
- 建議 Agent 的閱讀順序，以及何時才應回退讀取完整 `document.md`。
- 使用的數學公式分隔符。
- 是否完成 VS Code Markdown Preview 相容性檢查。
- 是否移除 Algorithm 中以 `$\quad$`／`$\qquad$` 進行縮排的寫法。

不得宣稱完成未實際執行的檢查。

---

## 14. 預設模式

使用者未另行指定時，採用 **Faithful Conversion Mode**：

- 原文逐字保留。
- 不摘要、不改寫、不潤飾。
- 僅修復 parser 與版面錯誤。
- 移除無語意的頁首頁尾。
- metadata 另存。
- `raw/` 與 parser 原始輸出不納入最終套件。
- 同時輸出完整 `document.md` 與語意切分後的 `sections/`。
- 產生 `INDEX.md`、`index.csv` 與 `AGENTS.md`，並以索引優先、最小必要讀取為 Agent 預設流程。
- Figure、Table、Formula 逐一核對。
- 公式統一使用 `$...$`／`$$...$$`。
- Algorithm 縮排不用 LaTeX 空白命令。
- `Abstract—`、`Index Terms—` 不加入多餘 `**`。
- 以 VS Code 內建 Markdown Preview 進行最終顯示驗證。
- 無法確認時標記，不猜測。

---

## 15. 最終驗收條件

只有在以下條件成立時才能回傳：

- 原文未被改寫。
- 主要章節完整。
- Figure／Table／Algorithm 對應正確。
- 表格數值已核對。
- 公式與上下標已修復。
- 公式使用 `$...$`／`$$...$$`，且 VS Code 預覽可正確渲染。
- Algorithm 無 `$\quad$`／`$\qquad$` 縮排殘留。
- `Abstract—`、`Index Terms—` 等標籤無多餘 `**`。
- 多欄閱讀順序已修復。
- 頁首頁尾與 copyright 等雜訊已正確處理。
- 最終 ZIP 中不存在 `raw/` 或 parser 原始輸出。
- `sections/` 已依 heading 與語意完整切分，所有正文均恰好映射至一個 primary chunk。
- `INDEX.md` 與 `index.csv` 已完整統整所有子檔案，且彼此一致。
- `AGENTS.md` 已限制 Agent 先讀索引並只讀最小必要段落。
- 所有 chunk 重組後與 `document.md` 的正規化正文一致。
- 所有連結有效。
- 無暫存文件。
- ZIP 完整性測試通過。
- 驗證報告與實際結果一致。

> 結構可以修復，排版可以正規化，錯誤可以更正；但原文內容不得被重新創作。


---

## 16. Retrieval-Oriented Section Splitting

本章規定如何將完整 `document.md` 轉換為供 Agent 低 token、選擇性讀取的檢索套件。切分是忠實轉換的衍生步驟，不得改寫原文。

### 16.1 切分優先順序

依下列順序決定 chunk 邊界：

1. 先依文件結構切分：Title、Abstract、Index Terms、章、節、小節、Conclusion、References。
2. 小節過長時，再依語意轉換切分：方法步驟、公式定義、Algorithm、Figure／Table 討論、實驗設定、結果分析與原因討論。
3. 不得以 PDF 頁面或固定字數作為唯一切分依據。
4. 不得在句子中間、公式中間、Algorithm 控制流程中間或表格解釋中間切分。

### 16.2 Chunk 大小

- 一般 chunk 目標：600～1200 tokens。
- 一般 chunk 軟上限：1200 tokens。
- 一般 chunk 硬上限：1500 tokens。
- 一般 chunk 建議下限：250 tokens；過短且語意相關的相鄰段落應合併。
- Algorithm、完整公式定義、不可分割的證明、表格與其必要解釋可超過軟上限，但不得無理由超過硬上限。
- Token 應優先以離線 tokenizer 計算；無 tokenizer 時可使用近似值，但 `INDEX.md` 必須標記為 estimate。

切分目標不是檔案數量最大化，而是使一般單一問題只需讀取 `INDEX.md` 加 1～3 個 chunk。

### 16.3 不得拆開的原子內容

下列內容應保持在同一 primary chunk：

- Display／inline 公式及其緊接的 `where`、變數定義、單位與語意說明。
- Algorithm 的 Require、Ensure、主程序、Function、Return 與控制流程。
- Lemma／Theorem／Definition 與其直接相連的 Proof，除非 Proof 本身有明確的小節結構。
- Figure／Table caption 與其主要介紹或結果解讀段落。
- 跨頁但語意連續的同一句或同一段。

圖片與 CSV 資產可保存在獨立目錄，但對應 chunk 必須保留正確連結與 caption。

### 16.4 Chunk ID、檔名與 YAML front matter

每個 chunk 必須具有穩定且唯一的 ID。建議命名：

```text
S000-title-authors.md
S010-abstract.md
S100-introduction-01.md
S310-preliminaries-feedthrough.md
S460-algorithm-02.md
S700-references.md
```

ID 不應因輕微文字修復而變動。每個 chunk 必須包含精簡 YAML front matter：

```yaml
---
chunk_id: S310
title: Feedthrough
heading_path:
  - III. Preliminaries
  - B. Feedthrough
source_pages: [2, 3]
content_type: [definition]
approx_tokens: 940
figures: [figure-01]
tables: []
equations: [equation-01, equation-02]
previous_chunk: S300
next_chunk: S400
---
```

Front matter 只能放導航與來源 metadata，不得加入原文不存在的摘要或推論。

### 16.5 `INDEX.md`

`INDEX.md` 必須是 Agent 的第一閱讀入口，開頭需明確寫出：

1. 先讀此索引。
2. 根據問題選取最小必要 chunk 集合。
3. 只有精確數值需求才讀對應 CSV。
4. 只有圖形關係相關時才讀圖片。
5. 除非需要全文摘要、跨章一致性查核或 chunk 不完整，否則不得讀完整 `document.md`。
6. 不得預設掃描全部 `sections/`。

主索引表至少包含：

| 欄位 | 要求 |
|---|---|
| ID | 穩定且唯一的 chunk ID |
| Section | 人類可讀標題 |
| File | 相對檔案路徑 |
| Pages | 原 PDF 來源頁碼 |
| Type | `frontmatter`、`background`、`definition`、`method`、`algorithm`、`experiment`、`result`、`conclusion`、`reference` 等有限集合 |
| Approx. tokens | 預估讀取成本 |
| Key topics | 關鍵詞，不得寫成長摘要 |
| Related assets | Figure、Table、Equation、Algorithm 資產 |
| Dependencies | 可能需要先讀或相鄰閱讀的 chunk ID |

`INDEX.md` 另應包含 Figure Index、Table Index 與 Equation Index，使 Agent 可直接定位視覺資產與精確數據來源。

### 16.6 `index.csv`

`index.csv` 必須與 `INDEX.md` 一致，至少包含：

```csv
chunk_id,title,file,pages,type,approx_tokens,key_topics,figures,tables,equations,dependencies
```

多值欄位建議以分號分隔。CSV 必須可由標準 CSV parser 解析，不得以視覺對齊空格取代正確 quoting。

### 16.7 `AGENTS.md` 閱讀政策

`AGENTS.md` 必須明確規定：

```markdown
# Document Reading Policy

1. Read `INDEX.md` first.
2. Select the smallest relevant set of chunk IDs.
3. Read only those files under `sections/`.
4. Read `tables/*.csv` only when exact numerical values are required.
5. Read `images/*.png` only when visual structure is relevant.
6. Read adjacent chunks only when the selected chunk lacks necessary context.
7. Do not scan all files in `sections/` by default.
8. Do not read `document.md` unless a full-document task, cross-section verification, or chunk incompleteness requires it.
9. For full-document tasks, prefer `document.md` over sequentially reading all files in `sections/`.
```

來源優先順序：

- 正文：`sections/*.md` → `document.md` → 原始 PDF。
- 精確表格數值：`tables/*.csv` → `tables/*.png` → `document.md`。
- 圖形結構：`images/*.png` → 對應 chunk → 原始 PDF。

若套件放入既有 repository，應將此政策放在該文件目錄內可生效的位置，或合併至既有 `AGENTS.md`；不得無條件覆寫使用者原有規則。

### 16.8 Figure、Table、Equation 與 Algorithm 索引

- 每個 Figure 必須列出檔案、來源頁碼、primary chunk 與簡短描述。
- 每個 Table 必須列出 CSV、PNG、primary chunk 與內容類型。
- 每個 Equation 必須列出編號、primary chunk 與原文中的用途。
- 每個 Algorithm 必須列出編號、primary chunk 與相關 Figure／Equation。
- 描述只可作導航，不得加入研究推論或改寫論文主張。

### 16.9 Coverage 與重組驗證

切分完成後必須執行：

1. **Coverage validation**：`document.md` 的每個正文 block 恰好存在於一個 primary chunk。
2. **Duplicate validation**：不得因相鄰 context 而複製完整正文段落至多個 chunk；必要的導航文字不計入正文。
3. **Boundary validation**：無永久斷句、公式定義分離、Algorithm 拆斷或 caption 錯配。
4. **Reconstruction validation**：依 chunk 順序合併內容，移除 YAML front matter、導航連結與檔案邊界空行後，與 `document.md` 的正規化正文一致。
5. **Index validation**：`INDEX.md`、`index.csv`、front matter 與實際檔案名稱／資產連結一致。
6. **Token validation**：記錄超過 soft／hard limit 的 chunk 與合理例外原因。

正規化只允許忽略：front matter、chunk 專用 heading、previous／next 導航、檔案邊界空行。不得忽略正文內容差異。

### 16.10 Agent 查詢預期流程

對文件問題的預設流程應為：

```text
User question
→ read INDEX.md
→ select 1–3 relevant chunks
→ optionally read exact table CSV or relevant image
→ answer
→ read document.md only as fallback
```

若索引關鍵詞不足以定位問題，應先擴讀相鄰 chunk 或依 `index.csv` 搜尋，而不是立即全文載入全部文件。

---

## 17. 版本修訂紀錄

### v1.3

新增以下強制規則：

1. 完整 `document.md` 之外，必須產生語意切分後的 `sections/`。
2. 必須產生 `INDEX.md`、`index.csv` 與 `AGENTS.md`，並將 `INDEX.md` 設為 Agent 第一閱讀入口。
3. Chunk 必須依 heading 與語意邊界切分，不得只按頁面或固定字數切分。
4. 一般 chunk 目標為 600～1200 tokens，硬上限為 1500 tokens；不可分割內容可例外，但需記錄原因。
5. Formula 與定義、Algorithm、Figure／Table caption 與主要解釋不得任意分離。
6. 每個 chunk 必須具穩定 ID、來源頁碼、類型、token estimate、資產與相鄰 chunk metadata。
7. `INDEX.md` 必須以表格統整所有子檔案，並另列 Figure、Table、Equation 與 Algorithm 索引。
8. `AGENTS.md` 必須禁止 Agent 預設掃描全部 `sections/`，並規定精確數值優先讀 CSV。
9. 必須執行 coverage、duplicate、boundary、reconstruction、index consistency 與 token-size validation。
10. 一般單一問題的設計目標為只讀索引加 1～3 個相關 chunk。



### v1.2

新增以下強制規則：

1. 最終 ZIP 禁止包含 `raw/`。
2. Parser 原始輸出只可在轉換與驗證期間暫時使用，完成後不得複製到交付套件。
3. 若使用者上傳 Docling、Marker 或其他 parser 輸出，只將其視為輸入，不在結果中原樣保存。
4. 追溯資訊改由原始 PDF 雜湊、parser 名稱／版本、`manifest.json` 與驗證報告保存。
5. 回傳前必須驗證 `raw_directories_found == 0`，並確認 ZIP entry 中不存在 `raw/`。
6. 此變更以降低 Codex context 干擾、重複內容、repository 體積與錯誤來源衝突為目的。

### v1.1

新增以下強制規則：

1. 公式改用 VS Code Markdown Preview 相容的 `$...$` 與 `$$...$$`。
2. 禁止以 `\(...\)`、`\[...\]` 作為最終公式分隔符。
3. Algorithm 縮排禁止使用 `$\quad$`、`$\qquad$`，改用 Markdown 巢狀結構或 `&emsp;`。
4. `Abstract—`、`Index Terms—`、`Keywords—` 預設不加入 `**`。
5. 回傳前增加 VS Code Preview、未配對公式分隔符、數學指令外洩及 Markdown 標記外洩檢查。
