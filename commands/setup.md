---
description: 設定一篇新論文，開始累積疑問筆記
argument-hint: "<論文資料夾> [筆記要放哪]"
allowed-tools: Bash, Read, Glob, AskUserQuestion, Skill
---

Load the `paper-annotations` skill (`Skill` tool) first and follow its rules.
Speak to the user in Traditional Chinese.

User input:
$ARGUMENTS

## Steps

0. **Check the workspace.** Only when this folder has no `papers.yml` yet, i.e.
   the first paper he puts here. Skip the whole step once a registry exists; do
   not ask every time.

   Check the level holding the papers for these four, **list whichever are
   missing and ask** — they leave things in his folder, so ask first. **If he
   says yes, do it** (`git init` and writing files included); never ask and then
   hand the work back. He ran `:setup` precisely so as not to deal with this.

   | File | What goes wrong without it |
   |---|---|
   | `.git` | **The important one.** The registry prefers the git repo root; with no repo it falls back to the directory the command ran from. Those usually agree, but one run from another directory drops the registry inside the paper package, the second paper never finds it and starts its own, and the shelf splits in two |
   | `.gitattributes` | Suggest `* text=auto eol=lf`. If git rewrites the source's line endings to CRLF the fingerprint changes and the build reports source drift that never happened |
   | `.gitignore` | Suggest at least `*.html`. Review and shelf pages are generated and large; in version control every rebuild is a big fake diff |
   | `AGENTS.md` | One line: questions about papers go through the paper-annotations skill. Without it he has to type `/paper-annotations:…` every time, and simply asking a question does not reach this tool |

   Mention once the option of keeping the notes in a **private GitHub repo**: the
   registry stores relative paths and the notes, cards and review logs are all
   plain text, so a clone on another machine works immediately. Creating the repo
   and the first commit are local — do them if he agrees. **Pushing to a remote
   is a separate matter: do not push unless he asks explicitly**, and do not
   create a GitHub repo for him.

1. **Locate the paper.** No path given → look at what in the current directory
   resembles a paper folder and list the candidates; nothing found → just ask.

2. **Confirm where the notes go.** Default unless he says otherwise: cards inside
   the package (so it travels as one unit), review page **beside** it (same level
   as the PDF, no digging). **Say this explicitly**; never decide it silently. To
   change it he uses `probe.py --out <notes path>` or `--review <page path>`.

3. **Run `probe.py`** and translate the result into plain language:
   - **The first time you say "Tier", explain what it is**: a grade of how
     complete this paper's conversion is, A/B/C, which decides how precisely a
     question can be anchored. He is meeting this tool for the first time and
     「Tier A」 tells him nothing about good or bad. Same for 錨點 and 引文 —
     explain them in plain words.
   - What questions can be anchored to in this paper (equation numbers? figures
     and tables? only section headings?)
   - At Tier B/C, explain what reaching Tier A buys and what it costs, and let
     him decide
   - With only a PDF, `probe.py` prints full conversion instructions — relay
     them, and **be sure to include both the time cost and that model choice
     affects quality**. The rules-file path in those instructions is computed by
     probe.py from the actual location: copy it exactly, never guess a path.

4. **Say who cites whom.** `probe.py` registers the paper in `papers.yml` and
   works out which of the papers he has read cite it or are cited by it. If there
   are any, **say so unprompted** — it is the first thing he wants to know, and
   it is mechanical fact rather than inference. If there are none, no need to
   mention it.

5. **One pass through**, extracting this paper's points (claim / method /
   assumption / definition / result / limitation). Scan the abstract,
   introduction, conclusion, section headings and any paragraph marked as
   contributions — **do not read the whole paper**. Then list what you added so
   he can veto on the spot. Rules in the skill's Points section.

6. **Propose categories.** This is where categorisation belongs — a new paper
   gets filed as it arrives, rather than waiting for him to think of running
   library one day. From its Index Terms and the points you just extracted,
   propose 2–4 categories **coarser than keywords** into `topics_auto` in
   `papers.yml`, adding each new one to the `topics:` vocabulary at the same time.
   When other papers already exist, reuse their categories rather than inventing
   new ones per paper — categories exist to separate papers, and one bucket each
   separates nothing. Rules in the skill's Categories section. List them for
   on-the-spot veto, and tell him he can add and remove them on the shelf page
   himself, including his own categories like 「已讀過」.

7. **First build**: `build_annotated.py`, then `build_html.py`, then
   `build_library.py` to update the shelf page.

8. **Place both launchers.** Step 7 produced the shelf page, but `library.html`
   cannot be opened by double-clicking (paper links are server paths), so writing
   only the single-paper launcher leaves behind a file that will not open:

   - `serve.py --library --launcher` → **開啟書房.cmd** beside `papers.yml`.
     **This is his everyday entry point**: one server mounting every paper, click
     into any of them from the shelf.
   - `serve.py <work> --launcher` → **開啟複習頁.cmd** in the paper folder, this
     paper only. Mostly unused once he has several papers, but more direct when
     reading just one.

   For both, explain **why to open from them**: only a page served this way has
   「存檔」, so highlights reach the notes and reviews can be graded. Opening
   `index.html` directly still reads fine, but highlights stay in the browser.

   **Before finishing, verify both files actually exist** and give him the paths.
   An entry point he cannot see is a step that did not happen, and he has no way
   to know where to look.

9. **Tell him how to use it from here**: just ask questions about the paper;
   doubts accumulate into cards by themselves. No commands to remember.

Done when he knows which Tier he is on, where the notes will be produced, where
開啟書房.cmd and 開啟複習頁.cmd are and that they **really exist**, and that the
next step is simply to ask a question.
