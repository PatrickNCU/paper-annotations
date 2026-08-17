"""paper-annotations 的核心套件。

scripts/ 底下的同名 .py 只是命令列薄殼；所有邏輯都在這個套件裡：

  cli        入口共用：直譯器版本檢查、argv 解析
  miniyaml   零依賴的 YAML 子集（卡片 frontmatter 與 paper.yml）
  minimd     轉檔論文專用的 Markdown 渲染器
  notes      疑問卡與畫記的讀寫（frontmatter 文件）
  sources    論文原文的探索、排序與指紋
  anchors    錨點解析：ref → heading → quote 的階梯與診斷
  links      連結改寫（reference-style 正規化、相對路徑重定）
  workspace  notes/paper.yml 的載入與預設輸出位置

  probe      偵測論文套件能力，寫 paper.yml
  annotate   重建 annotated/ 與 notes/QUESTIONS.md
  page       組出單頁複習 HTML（樣式與腳本在 assets/）
  marks      畫記的匯入與存檔
  export     疑問卡匯出（anki / csv / json）
  reanchor   原文重轉檔後把卡片接回去
  server     本機 server，讓複習頁的畫記直接落檔
"""
