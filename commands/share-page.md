---
description: 把複習頁打包成單一 HTML 檔寄給別人（圖片全部內嵌，對方不必裝任何東西）
argument-hint: "[論文或筆記資料夾]"
allowed-tools: Bash, Read, Glob, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

1. Find the directory holding `notes/paper.yml`. No path given → search downward
   from the current directory; more than one → list them and let him pick.

2. Run `build_annotated.py` and `build_html.py` first (no flags), so the content
   is current.

3. Produce the shareable file:

   ```bash
   python <scripts>/build_html.py <work> --embed-assets --to "<paper folder>/<paper>-複習頁.html"
   ```

   `--to` **is not optional**. Without it this overwrites `annotated/index.html`
   in place, replacing the page he reads with the embedded version; the next
   ordinary build swaps it back, and the whole thing was for nothing. Use the
   level holding the PDF as `<paper folder>`, so the file sits with the paper and
   is findable when he wants to send it.

4. **Report**: full path, size, and how many images were embedded. If the build
   printed 「🔴 有 N 張圖片找不到檔案」, relay it — the recipient will see broken
   images.

5. Over 20 MB, warn him: most mail attachment limits are 20–25 MB, so beyond that
   use a cloud drive link.

## Teach him to do it himself

**Write this out in full; do not just say "run that command".** He should be able
to regenerate it later without opening a conversation.

- Give a **copy-pasteable** complete command with every path filled in as a real
  absolute path — no `<work>`-style placeholders.
- Say **where to run it**: on Windows, type `cmd` in File Explorer's address bar
  and press Enter to get a terminal in that folder, or `cd` there from a terminal.
  Also say that since the paths in the command are absolute, the working
  directory does not actually matter — otherwise he will think a wrong location
  means it cannot run.
- Note that **regenerating is just re-running the same line**, which overwrites
  the old shareable file.

## What the recipient gets

Tell him this too, so he knows what to say to the other person:

- Double-click opens it in a browser, nothing to install, phones and tablets
  included
- Paper, cards, filtering, search, light/dark theme and formulas all work
- They can highlight and comment themselves, stored in their own browser; to send
  feedback back they press 「複製畫記」 in the sidebar and return the content, and
  you take it in with `/paper-annotations:marks`
- 「💾 存檔」 will not appear — that needs a server, and they have no notes folder
  to write to

Done when he has the path and size, a line he can paste directly, and knows where
to run it and what the recipient will see.
