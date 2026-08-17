# Input tiers and conversion

`probe.py` scans the paper package and decides which anchoring methods it
actually supports, recording the result in `notes/paper.yml`. That result is only
a hint about which rung to try first, never a guarantee — the build still
re-verifies against actual content.

| Tier | Condition | What a question can anchor to |
|---|---|---|
| A | Full conversion package with `sections/` and `INDEX.md` | Equation `\tag{n}`, figures, tables, section headings, a named sentence |
| B | Ordinary Markdown with section headings (one file or many) | Section headings, a named sentence |
| C | Plain text with no section headings | A named sentence only |

B and C work fine; they are just more fragile — a revised source is more likely to
lose its positions.

## When he only has a PDF

`probe.py` prints the full instructions; relay them. In short:

1. Open the ChatGPT web app and upload [pdf2md_rules.md](pdf2md_rules.md) and the
   PDF
2. Paste the prompt from §0 「使用方式」 of the rules file
3. Unzip the returned archive into the paper folder and re-run `probe.py`

`pdf2md_rules.md` **stays in Chinese by the user's decision**, unlike every other
document here. It is never loaded into this agent's context — probe.py only
prints its path — so translating it would save nothing, and its §0 prompt is text
the user copies into ChatGPT himself. Do not "helpfully" convert it.

**Always state the cost up front** so he does not expect one click:

- Conversion takes real time; an IEEE journal paper usually needs several rounds
- Model and reasoning effort visibly change the result; GPT-5.6 Sol with high
  reasoning tested best
- His own pdf2md tool is fine too: any Markdown with section headings works
  (Tier B)

Why AI conversion rather than a program parser: a parser cannot make the
judgement calls — aggressively dropping headers and footers, deciding an image is
just the journal's logo. That judgement is the input shape this tool assumes.

## When the source is replaced

`probe.py` records a fingerprint per body file. If a later build finds content
changed, a file gone, or a new file present, it **stops** and explains why: the
source may have been reconverted or re-split, and the notes risk pointing at the
wrong places. Changes to `document.md`, `INDEX.md` and `manifest.json` only warn
softly — they do not affect note positions, but usually mean the package is
internally inconsistent.

Recovery is `reanchor.py`: it searches each card's quote globally in the new
structure and **only edits automatically on a unique whole-document hit**.
Multiple hits and zero hits both go into the report for a human to settle —
papers repeat sentences constantly, and landing on a similar-but-wrong passage is
worse than being visibly broken.
