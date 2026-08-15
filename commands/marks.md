---
description: 把複習頁「複製畫記」的內容存成 notes/marks/，然後重建
argument-hint: "[論文或筆記資料夾]"
allowed-tools: Bash, Read, Write, Glob, Skill
---

先載入 `paper-annotations` skill（`Skill` 工具），照它的規則走。

使用者輸入（可能直接就是貼上來的畫記內容）：
$ARGUMENTS

## 步驟

1. 拿到畫記內容。使用者只打了指令沒附內容，就請他在複習頁側欄按「複製畫記」再貼上來。

2. 找出 `notes/paper.yml` 所在的目錄。

3. 把貼上來的整段**原封不動**寫成暫存檔，交給 `import_marks.py --from`。
   **不要自己逐條轉寫成 YAML**——畫記只是「哪段文字、什麼顏色、註解寫什麼」，沒有需要
   你判斷的地方，手抄只會製造錨點最禁不起的那種安靜錯誤。

4. 執行 `build_annotated.py` 與 `build_html.py`。

5. 回報新增幾條、已存在幾條。🟡 提醒不必處理（含公式的畫記引文本來就不在原始 Markdown
   裡，頁面搜的是渲染後的文字，照樣定位得到）；🔴 才要處理。

6. 如果使用者是重複在做這件事，告訴他 `/paper-annotations:serve` 可以讓頁面自己存檔，
   不必再經過複製貼上。

完成條件：畫記已經在 `notes/marks/`，複習頁重建過，而且使用者知道有 serve 這條路。
