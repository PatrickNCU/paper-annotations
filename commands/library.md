---
description: 你讀過哪些論文、疑問與要點、彼此怎麼引用
argument-hint: "[起點資料夾]"
allowed-tools: Bash, Read, Glob, Grep, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入：
$ARGUMENTS

## 步驟

1. 執行 `library.py`（沒給起點就用目前目錄）。它會往上找 `papers.yml`。

2. 還沒有登記簿時，不要自己造一份：那代表還沒對任何論文跑過 `probe.py`。
   告訴使用者跑 `/paper-annotations:setup` 就會建立。

3. **回報**，順序照重要性：
   - 每篇論文的疑問統計，**未解決與半懂的優先列出來**——那是他還沒通的地方
   - 論文之間的引用關係。這是機械判定的事實，可以直接講，包括引用出現在哪一節、
     當下那句話怎麼說的
   - 要點數為 0 的論文要指出來：那篇沒有骨架可以拿去和別篇對照，
     跨論文的整理會做不出東西

4. 登記的位置找不到筆記時（資料夾被搬走），照實說是哪一篇、原本登記在哪，
   並說明修法是改 `papers.yml` 的 `work` 或重跑 `probe.py`。**不要自動改。**

5. **想要一頁能點的**：跑 `build_library.py` 產生書房頁，再跑
   `serve.py --library --launcher` 放一個 `開啟書房.cmd`，最後背景執行
   `serve.py --library`。告訴他這是**一個 server 掛所有論文**（不是每篇一個），
   每篇只開放自己的資料夾，而既有的單篇啟動器完全不受影響。

6. 使用者想看的是關聯而不只是清單時，接著跑 `/paper-annotations:digest` 的
   `connections` 模式。

完成條件：使用者知道自己讀過哪幾篇、哪幾篇互相引用、還有哪些疑問沒解決。
