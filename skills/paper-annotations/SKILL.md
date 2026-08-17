---
name: paper-annotations
description: 讀論文時把使用者的疑問就地註記回原文，累積成可複習的筆記與單頁 HTML。使用時機：使用者問論文內容、要求記下疑問、要更新或複習既有的論文筆記、手上有 PDF 或 Markdown 論文要開始讀。
---

# Paper annotations

Where the reader got stuck becomes a **question card**, anchored back onto the
spot that caused it, for later review.

Source text is read-only. Cards are the only source of truth; `annotated/` and
`notes/QUESTIONS.md` are regenerable.

## Language

Everything the user reads follows one convention — replies in conversation, card
bodies, point text, digests, category display names, anything you write for him:

**Traditional Chinese as the base, English as the technical anchor.**

- Write Traditional Chinese prose. Do not drift into English paragraphs.
- Carry the paper's own English term beside the Chinese the first time a term
  appears in that file: 「密度懲罰（density penalty）」. The paper he is reading is
  in English; a note he cannot map back onto its terminology is a note he cannot
  use.
- **An abbreviation always carries its full name on first use**:
  「HPWL（half-perimeter wirelength，半周長線長）」,
  「FFT（fast Fourier transform，快速傅立葉轉換）」. The bare abbreviation is fine
  after that.
- **"First use" is scoped per file, not per session.** A card is read on its own
  three months from now; a full name that only exists in some other card is a
  full name he does not have. Spell it out again in every card, point and digest
  that uses the abbreviation.
- Terms with no settled Chinese rendering stay in English — Nesterov's method,
  Lipschitz constant. Never invent a translation.

Exempt because they are keys rather than prose: `id`, filenames, topic slugs and
`tags`. Keep a tag as the paper's own short English term, which is what he would
search for, and spell the term out in the prose instead. A topic's **display
name** in `topics:` is prose and does follow the convention.

Chinese strings quoted in this file are literal — file headings, on-screen
buttons, filenames, build warnings. Reproduce them exactly; never translate them.

## Commands

`<scripts>` = this skill's `scripts/`. `<paper>` = root of the paper's Markdown
package (the level with `sections/` + `INDEX.md`, or the dir holding a single
`.md`). **`<work>` = the dir containing `notes/`**, not necessarily the paper dir.

```bash
python <scripts>/probe.py <paper> [--out <notes>] [--review <page>]
python <scripts>/build_annotated.py <work>       # after editing notes: Markdown view + index
python <scripts>/build_html.py <work>            # then: index.html, the page he reads
python <scripts>/library.py [<start>] [--json]   # all papers: cards, points, citations
python <scripts>/build_digest.py <work> [--only <prefix>]   # digest .md -> openable .html
python <scripts>/build_library.py [<start>]      # the shelf page library.html
python <scripts>/reanchor.py <work>              # source reconverted/re-split: reattach notes
python <scripts>/export_cards.py <work> [--format anki|csv|json] [--status resolved]
python <scripts>/import_marks.py <work> --from <file>   # output of the 「複製畫記」 button
python <scripts>/serve.py <work> [--port 8975]   # lets the page save highlights and grade
python <scripts>/serve.py --library [<start>]    # every paper at once; home is the shelf
python <scripts>/build_html.py <work> --embed-assets --to <file>   # one file to send
```

`export_cards.py` is read-only, for people who want their cards in Anki or their
own pipeline; defaults to `notes/cards-export.txt`. No scheduling logic there.

Default layout:

```
papers.yml              ← registry, at the git repo root
<paper folder>/
  paper.pdf
  paper_md/             ← conversion package (source, read-only)
    sections/ INDEX.md images/
    notes/              ← the only source of truth
      cards/ marks/ points/
      catalog.json references.json   ← generated, for cross-paper use
  annotated/index.html  ← review page, beside the package
```

Cards stay in the package so it travels as one unit; the page sits beside it,
because a page buried among dozens of files is a page nobody finds. `probe.py`
only lifts the page a level when the package looks like a conversion artifact
(dir ends in `_md`, or a PDF sits alongside); else `<work>/annotated`.

`--out` moves the notes, `--review` only the page; both are recorded in
`paper.yml`, so later commands need no flags. `--out` means he chose the
workspace, and the page then follows the notes.

Never move files or rewrite paths to relocate an artifact: every relative link
(images, backlinks, index jumps) is computed at build time from actual locations.
To change a location, re-run `probe.py`.

Zero dependencies, Python 3.8+. Do checks in Python, not `grep`/`sed` — he may be
on Windows with only PowerShell.

### The workspace itself

Four things the tool will not create but misbehaves without.
`/paper-annotations:setup` lists whichever are missing and asks — but only when
there is no `papers.yml` yet (step 0 of that command).

- **`.git`** — decides where `papers.yml` goes: repo root, else the dir the
  command ran from, provided the paper is under it. One run from an unrelated dir
  drops it inside the paper package, and that spot **cannot grow**: the next
  paper's upward search never passes a sibling's folder, so it starts a second
  registry and the shelf splits in two silently. `probe.py` warns on this.
- **`.gitattributes`** (`* text=auto eol=lf`) — CRLF rewriting changes the source
  fingerprint, and the build reports drift that never happened.
- **`.gitignore`** (at least `*.html`) — review and shelf pages are generated and
  large.
- **`AGENTS.md`** — without it a plain question about a paper does not route here.

All four are **ask, then do**. Never ask and hand the work back; he ran setup so
as not to deal with this.

Notes belong in a **private GitHub repo**: relative paths, plain text throughout,
so a clone works immediately. Local `git init` and commit once he agrees;
**pushing needs him to ask** — that sends material off his machine.

## When to act

- **Before touching any paper** → run `library.py`, to know what he has read
- He asks about a paper's content → answer, then draft a card
- "Rebuild / update the notes" → build
- He replaced the source with a new conversion → reanchor, then build

## A reading round

0. **Run `library.py`.** First thing every round, not just the first. A fresh
   session knows nothing of his reading history, and cross-paper connections are
   what he is here for.
1. **First contact**: `probe.py`, then tell him the Tier. PDF-only prints
   conversion instructions; at Tier B/C explain what Tier A buys and costs, let
   him decide ([references/tiers.md](references/tiers.md)). probe registers the
   paper and reports citations to/from his other papers — **say that unprompted**,
   it is the first thing he wants.
2. **One pass through**: structured scan for points (see Points).
3. **Answer**: follow the package's own `AGENTS.md` reading policy (usually
   `INDEX.md` first, 1–3 chunks). Record any point worth keeping while you are in
   that chunk.
4. **Draft the card.**
5. **End of round**: list new cards **and points** for on-the-spot veto. Silence
   means keep.
6. **Build** (`build_annotated.py`, then `build_html.py`), report warnings. If he
   is reading with no server, mention 開啟書房.cmd once — from there highlights
   save themselves.

Done when every question answered this round has a card, the build reports zero
「找不到位置」, and no 「🟡 引文提醒」 remains unexplained.

## Card format

`notes/cards/NNNN-slug.md`, `NNNN` an unused serial. **No section prefix** — it
becomes misleading once the source is re-split.

```yaml
---
id: "0007"
created: 2026-08-15
updated: 2026-08-15
status: open | half | resolved      # half = 半懂
origin: asked | suggested           # suggested = a doubt you raised, not his
tags: [density, poisson]
anchor:
  file: sections/S400-iv-a-density-function.md
  heading: ["IV. DENSITY FUNCTION ANALYSIS", "A. Density Function"]
  ref: eq:7                         # optional: eq:N / fig:N / table:N
  quote:                            # required
    prefix: |-
      ~20 chars before
    exact: |-
      text unique within the file
    suffix: |-
      ~20 chars after
---

## 問題
## 卡點
## 解答
## 一句話直覺
```

Those four headings are literal — write them exactly; build and page both look
for them.

`anchor` says only *what to look for*. Position is resolved against the live
source every build, in order `ref` → `heading` → `quote` → unresolved
([references/anchoring.md](references/anchoring.md)).

## Writing cards

Card bodies follow the Language section above — and the per-file scope matters
most here, because a card is exactly the thing he opens alone months later.

- **`## 問題`** is the first thing he sees when reviewing — top of the card, and
  the text in the question list. Write a full question answerable from cold, not
  shorthand that made sense at the time.
- **`## 卡點` matters most**: which premise he lacked, what he misunderstood — not
  a restatement of the question. Without it he cannot decode his own card in three
  months.
- **`## 一句話直覺`**: so review does not mean rereading the whole answer.

**The quote is the highlight and the way into the card.** `quote.exact` lights up
on the page; clicking it opens the card. So pick **the sentence that actually
stopped him**, not any unique string used as a position marker. Missing or
appearing twice → do not mark it; never guess. The card still opens from the
sidebar list, it just has no entry point in the body.

**Uniqueness**: `anchor.quote.exact` must occur exactly once in its file. The
build checks every card each time, including ones anchored by `ref`/`heading`.
Fix a 「🟡 引文提醒」 immediately and rebuild until it is gone — a bad quote is
invisible day to day and detonates the day he reconverts.

**Status** follows his reaction: understood → `resolved`; still uneasy → `half`;
unresolved → `open`. Unsure → `half`, the tier most worth revisiting.

**`origin: suggested`** is for pitfalls you spotted unasked. Allowed, but must be
marked; the interface can hide them in one click.

**A card is a note, not a paper.** Anything the paper does not state outright —
your inference — must say so inside the card. In three months he will not
remember which sentence was the author's.

## Highlights (marks)

**Normally you are not involved**: he runs `serve.py`, presses 「存檔」, and it
lands in `notes/marks/` and rebuilds. Editing a comment, recolouring, deleting all
work the same way. If he is still copy-pasting by hand, point him at
開啟書房.cmd. There is no slash command for the server: the launchers cover the
everyday case, and when he asks you to start one, run `serve.py` yourself in the
background.

Only **without a server** (usually someone sent him a review page) do highlights
stay in the browser. When he presses 「複製畫記」 and pastes the result, **save the
whole block to a file and hand it to `import_marks.py`** — do not transcribe
entries yourself:

```bash
python <scripts>/import_marks.py <work> --from <the file you just saved>
```

It assigns serials, writes the format below, skips ones already present (safe to
re-run), then builds. **Highlights need no judgement from you**: passage, colour
and comment are decisions he already made.

🟡 warnings on import need no action. A highlight over a formula carries KaTeX's
rendered text (e.g. `x1,…,xn`), absent from the raw Markdown; the page searches
rendered text and still finds it. Truly unlocatable ones are counted in the
sidebar.

`notes/marks/NNNN-slug.md`:

```yaml
---
id: "0003"
created: 2026-08-16
color: yellow | green | blue | red
tags: [density]          # optional
anchor:
  file: sections/S210-....md
  quote:
    prefix: |-
    exact: |-
    suffix: |-
---

comment body, or leave empty
```

Locatable highlights return to the page; after a reload the browser's copy
disappears, so nothing is highlighted twice. The build re-checks the quote.

**A highlight is not a card**: no status, not in the question list, not counted in
「疑問 N 則」. He marked a passage and added a sentence → highlight. He raised a
question needing an answer → card.

## Points

Cards come from his confusion, highlights from his hand; where neither happened
this system is blind. And **cross-paper relationships live exactly where he did
not get stuck** — whether two papers contradict is about their claims, not
anyone's doubts. Points are the paper's skeleton, written by you, to compare
against other papers ([docs/adr/0002](../../docs/adr/0002-points-are-a-third-note-type.md)).

`notes/points/NNNN-slug.md`:

```yaml
---
id: "0001"
created: 2026-08-17
kind: claim | method | assumption | definition | result | limitation
origin: agent | user            # agent = you read it out (default)
tags: [local-density, 兩篇對照]
anchor:
  file: sections/S130-....md
  heading: ["Contributions and Paper Organization"]   # optional, label only
  quote:                        # required, and the only locator
    prefix: |-
    exact: |-
    suffix: |-
---
One sentence. Just one.
```

**Points are located by quote alone** — no `ref → heading → quote` ladder. A card
marks a position in an argument, so a section heading is fine; a point paraphrases
**one specific sentence**, and landing half a page away says the wrong thing about
the wrong text. `heading` is an index label only.

### How to gather them

Both routes, neither optional.

**One pass through**: on first read scan abstract, intro, conclusion, section
headings, and any paragraph listing contributions. **Do not read the whole
paper** — the claims are already in those places, so cost is bounded. 5–12 per
journal paper; prefer few and accurate.

**As you go**: whenever you open a chunk to answer a question, record that chunk's
points. Zero extra reading; coverage grows with how deeply he reads.

### Guardrails

You generate points on your own initiative, so the risk is not being wrong — it is
**writing too many**. Once volume gets away, he turns the feature off rather than
correcting it.

- **List new points at the end of every round for veto**, same as cards.
- The opening pass has a ceiling. Nothing good there → take fewer, never pad.
- A point is **what the paper claims**, not your commentary. Inferences go in a
  card or a digest.
- One sentence each. Needing three means two points — or actually a card.

**A point is neither a card nor a highlight**: no status, not in the question
list, not counted in 「疑問 N 則」. Question needing an answer → card; he marked a
passage → highlight; **the paper asserted something** → point.

## Review scheduling

The 複習 panel in the page's sidebar is built-in spaced repetition; Anki not
required. **Grading needs `serve.py` running** — the log must reach a file, and
review history is the only data here that cannot be regenerated
([docs/adr/0003](../../docs/adr/0003-review-history-is-the-first-irreplaceable-data.md)).
Without a server the page still lists what is due, shows no grading buttons, and
says why.

Status decides what is scheduled. Do not intervene:

| Status | Scheduled? |
|---|---|
| `resolved` + `origin: asked` | Yes. He understood it; the job now is not forgetting |
| `half` | No, but permanently first in the queue. Half-understood is unfinished reading, not a memory problem |
| `open` | No. Already in the question list |
| `origin: suggested` | No. You raised it, he did not |

Logs in `notes/reviews/<card id>.md`, one line per grading. **The build never
writes that directory**; its only writer is the server's grading endpoint. The
schedule is not stored — it is replayed from the log, so changing the algorithm
later needs no migration.

A deleted card leaves its log behind and the build reports an orphan. **Never
clean those up automatically**; they are his data.

`export_cards.py --format csv` carries `reviews / interval / ease / lapses / due`,
so moving to Anki does not start from zero.

## Across papers

`library.py` is your only way to see past the current paper. It reads
`papers.yml` (registry, at the git repo root) and each paper's
`notes/catalog.json` (the build's index of cards and points), and prints every
paper's questions, points, and **who cites whom**.

Citations are mechanical: `probe.py` extracts the reference list into
`notes/references.json`, and matching happens **at read time**, so adding a paper
today updates the citation picture for one processed last month with no re-run. It
**involves no judgement**, so state it as fact — including which section the
citation is in and what the surrounding sentence says.

Judgement-bearing relationships (agreement, contradiction, one idea under two
names) are yours to write as a digest — the `connections` mode. Never write
judgement into `references.json` or `catalog.json`; both are generated.

### Typed links between cards and points

When a `connections` digest finds a relationship worth keeping, harden it into a
link. A digest is prose he must remember to go find; a link **appears next to the
sentence it is about**. Sequential, not alternatives.

Declared in a card's or point's frontmatter, one per line, **on one side only**:

```yaml
links:
  - contradicts eplace-ms#P0003
  - answers replace#Q0002
  - same-as #Q0004            # omitting the slug means this paper
```

Three types only: `answers`, `contradicts`, `same-as`. **Do not invent types** —
the build rejects them. The list is deliberately tiny: an open vocabulary grows
near-synonyms and then cannot be compared against anything, which was the only
reason links exist. Extend it when it genuinely runs out, not in advance.

Backlinks are **computed by the build**. Never write both sides; that drifts. The
target's one-line text is shown alongside, so a link tells you what the other side
says without going there.

Resolution follows ADR 0001: targets are matched against the current
`catalog.json`; unresolved is reported, never guessed. So **the target paper must
have been built**, and links pointing at a newly added paper connect on the next
build with no file edits.

### The shelf page

`build_library.py` produces `library.html` beside `papers.yml`: one card per
paper with question counts, point counts, and how many are due today.

**Citations sit on the cards, not in a footer.** The same edge appears at both
ends — citing side 「→ 引用了 X」, cited side 「← 被 X 引用」 — and clicking jumps
to the other card and flashes it, switching the filter back to 「全部」 first if
that card is hidden. "Who is this connected to" is a question about *this paper*,
so the answer belongs beside it.

**Open it with `serve.py --library`** — one server mounting every paper; click a
card and land in that paper's review page. `serve.py --library --launcher` puts a
開啟書房.cmd next to `papers.yml`; it takes no path argument, so it survives the
workspace being moved or cloned.

**Producing the shelf page and placing 開啟書房.cmd are one job, never split**:
`library.html` cannot be opened by double-click (paper links are server paths), so
a page without a launcher is a file that will not open and he has no way to know
what is missing. Step 8 of `:setup` writes both launchers.

Double-clicking `library.html` does open it, but the paper links are dead; the
page detects it is not on http and says so at the top, with the command to run.

### Categories

A row of chips above the shelf: 「全部」 lists every paper, any other chip lists
only its members. One list, each paper once, all of its categories shown on its
own card. **Every declared category is listed, including empty ones** (dashed,
count 0) — hiding empties makes a just-created category look like a failed one.

He can also **define his own** — 「已讀過」 and the like, about him rather than
about any paper's subject: 「＋ 新增分類」 on the shelf, or 「＋ 自訂新分類」 inside
a paper's 「＋ 加入分類」 picker, which defines and assigns in one step. His
categories always go to `topics`, never `topics_auto`.

「⚙ 管理分類」 grows a swatch (colour), `↺` (default) and `✕` (delete, **only when
no paper is in it**) beside each category. Colours live in `topic_colors:` in
`papers.yml` (slug → `#rrggbb`); a category without one looks exactly as before.
**Do not pick colours for him** — preference, not something derivable.

**The vocabulary is `topics:` in `papers.yml` (slug → display name); define
before use.** The build reports undefined ones and they get no chip. Not
fussiness: it stops `3D-IC` and `3d-ic` becoming two identical-looking categories.
Three lists per paper:

| Field | Meaning |
|---|---|
| `topics` | His own. Solid chips |
| `topics_auto` | **Yours**, equally in effect. Dashed chips |
| `topics_off` | He removed these. **Never suggest them again** |

#### When to propose

**Mainly during `/paper-annotations:setup`** — file a new paper as it arrives
rather than waiting for him to think of it. After that, propose for any
uncategorised paper you notice while running `library.py`.

#### How to propose

**A category must be coarser than a keyword.** `catalog.json`'s `keywords` are the
paper's own Index Terms: raw material, **not categories**. Measured on two papers
where one directly succeeds the other (ePlace-MS, RePlAce), their 13 index terms
intersect in **zero** entries — as categories every paper becomes its own bucket,
i.e. no categories at all. The job is collapsing "Analytic placement" and "Global
placement" into one `placement`.

- Write to `topics_auto`, never `topics` — that field is his
- 2–4 per paper. Categories exist to **separate**; tagging everything with
  everything separates nothing
- Add any new category to the `topics:` vocabulary at the same time, or the build
  reports it
- List new categories at end of round for veto, same as cards and points
- **Never re-propose anything in `topics_off`.** A rejected suggestion that keeps
  returning is worse than no suggestion

#### The build does not invent categories

The build only **reads and groups**: pure Python, no LLM, and it must be
idempotent. Deciding a category happens in conversation (you); applying one
happens in the build. Deliberate: recomputing categories per build would make the
same input produce different output, and the foundation of the design is gone.

When he presses 「＋ 加入分類」 or clicks a chip to remove it, the server writes
back to `papers.yml` — which **needs `serve.py --library` running**; without it the
buttons never appear. Adding writes `topics`; removing also records `topics_off`.
Colour and deletion use the same endpoint (`POST /_pa/topic`, action
`add`/`remove`/`define`/`color`/`undefine`), and every write rebuilds the shelf.

In multi-paper mode each paper mounts at `/p/<slug>/` and **serves only its own
directory**. Never give the server one root spanning all papers — scattered across
a disk that degrades to the whole drive. Likewise a write request carries a slug
and the server looks the path up in a table; never let a request string become a
path.

Single-paper mode (`serve.py <work>`) is unchanged; existing launchers still work.

## Digests

When he wants "the questions and the source pulled together", you write it — not a
script. The four modes (回顧單 / 主題聚合 / 前提盤點 / 接線), sourcing rules and
output location are in [references/digests.md](references/digests.md). A digest is
an extra artifact, never a source of truth.

**Always run `build_digest.py`** afterwards to render the `.md` into a same-named
`.html`, and **report the `.html` path** — that is what he opens. Digests usually
contain formulas; `$\lambda$` is unreadable in a text editor and you cannot assume
he has a Markdown editor. The `.md` stays the editable source: change it and
re-render.

## Boundaries

- Source text is read-only. Something to say → write a card.
- Generated: `annotated/` (incl. `index.html`), `notes/QUESTIONS.md`,
  `notes/catalog.json` by the build; `notes/references.json` and `papers.yml` by
  probe; `notes/digests/*.html` by build_digest. To change any of them, edit
  `notes/cards/`, `notes/marks/` or `notes/points/` and rebuild.
- **`notes/reviews/` is not generated and cannot be regenerated.** Only the
  server's grading endpoint writes it. Never modify or delete it in code.
- His review interface is `annotated/index.html`; the Markdown version is for you
  and for git.

## When Python is unavailable

Merge by hand under the same rules: rebuild from the source in full — never patch
the old `annotated/` incrementally — and mark `built_by: agent` in `QUESTIONS.md`.
A hand merge is not guaranteed idempotent; that marker is the risk disclosure. Do
not write a second implementation.
