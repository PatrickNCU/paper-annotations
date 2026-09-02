# Section checkpoints

One question at the end of a section, answered before that section's points are
uncovered. **You write the questions; the page runs them and the server records
the answers.** Files live in `notes/checks/`.

The reader asked for "a question per section, kept asking until I get it, and a
running summary of what the paper has said so far". Three things were decided
differently, and they are settled — see [docs/adr/0005](../../../docs/adr/0005-a-twice-missed-checkpoint-creates-a-card.md)
and roadmap item 10. Do not reopen them:

- **No section summaries are written.** This tool does not summarise papers. The
  section's own points are the summary; the running digest is the points of the
  sections already passed, stacked up. A checkpoint's job is to make him say it
  before he reads it.
- **Two attempts, never three.** There is no model on the page, so only he can
  say whether he got it. A second miss files a suggested card and stops asking —
  "until you know it" is the review loop's job, and that loop already exists.
- **Skipping is allowed and visible.** The checkpoint sits in the text, not over
  it. Skipping opens the points and marks the section as skipped in the contents;
  he can answer it later.

## When to write them

At setup, or on the first real reading round — the same pass in which you gather
points. A checkpoint is written **from a point**, so it cannot be written before
that point exists.

**Fewer than 6 points in the paper: write none.** The build enforces this
(`checks.MIN_POINTS`) and will warn instead of placing them. A paper whose points
are thin produces questions about nothing, and one empty question is enough for
him to switch the feature off.

**At most one per section**, and only for sections that earned one: a section
whose point is a definition or a number does not need to be asked. Half the
sections having a checkpoint is a normal, good outcome.

## The file

`notes/checks/NNNN-a-short-slug.md`, four-digit id, unique across the paper.

```markdown
---
id: "0002"
section: S310-local-density-penalty-per-bin
target: P0003
created: 2026-09-02
---

## 問題
每個 bin 的懲罰係數跟壅塞量是什麼關係？為什麼要選這種關係而不是線性？

## 提示
塞住的 bin 和沒塞住的 bin，斥力差多少才夠？想想指數的形狀。
```

- `section` is the section file's stem, without `.md`. The checkpoint is placed
  at the end of that section.
- `target` is the point (`PNNNN`) the question was written from. The page shows
  that point as the answer, and a twice-missed checkpoint copies its anchor and
  tags onto the card it creates — so a wrong `target` produces a card anchored to
  the wrong sentence.
- `## 問題` is the question, asked once. `## 提示` is the **second** wording,
  shown only on the second attempt: not a smaller hint, a different angle in.
- `## 自己的話` is appended by the server, one line per attempt. Never write into
  it, never rewrite it — it is his own words (ADR 0004).

## Writing the question

The question is about the one thing in the section that has an opposite. If the
answer could be guessed from the section heading, it is not a question.

- **Ask for the mechanism, not the name.** 「為什麼要選這種關係而不是線性？」 beats
  「這一節提出什麼？」.
- **One question, answerable in a sentence or two.** He is reading, not sitting
  an exam; a question needing three parts is really three checkpoints, so pick one.
- **The point must actually answer it.** Read the target point back and check it
  does. The page shows nothing else as the answer.
- **The hint must not restate the question.** If the second attempt is the first
  one reworded, he misses twice for no reason and gets a card he did not need.

Language follows the skill's Language section: Traditional Chinese, each term in
the one form the field actually says it in.

## What the tool does with them

- `build_annotated.py` renders each checkpoint at the end of its section as
  readable Markdown, and reports how many were placed and how they stand.
- The page turns it into the question, hides that section's points until it is
  done with, marks the contents, and keeps a collapsed running summary of the
  points from earlier passed sections.
- `serve.py` appends each attempt to `notes/checks/answers/NNNN.md` and his
  sentence to the checkpoint's `## 自己的話`. State is replayed from that log,
  never stored.
- A second miss creates a `origin: suggested` card from a fixed template and
  rebuilds the paper. **That card's `## 解答` is only the point's sentence.** When
  you next open the paper, expand it into a real answer, or leave it for him.
