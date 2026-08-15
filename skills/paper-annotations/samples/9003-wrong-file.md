---
id: "9003"
created: 2026-08-15
status: open
origin: asked
tags:
  - 測試
anchor:
  file: sections/S999-this-file-does-not-exist.md
  quote:
    exact: |-
      這張卡的檔案路徑故意指向不存在的檔案
---

## 問題

測試用：anchor.file 指向不存在的檔案時，系統會怎麼講？

## 卡點

測試卡，看完可以直接刪。這種情況通常代表原文被重新切分了，該跑 reanchor.py。
