"""Turn the review page's 「複製畫記」 text into notes/marks/ files.

The page cannot write to the notes folder -- it is a static file opened from
disk with nothing behind it -- so the reader copies their highlights out and
they arrive here as text. Parsing that text is the agent's job only in the
sense of running this; doing the transcription by hand invites exactly the
kind of quiet error the anchors cannot survive.

Usage:
    python import_marks.py <work> --from <檔案>
    python import_marks.py <work>            # 從 stdin 讀

Re-importing the same text writes nothing: a mark is identified by its file
plus its quote, so the run is safe to repeat.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import miniyaml
import paperkit

paperkit.bootstrap()

# "1. file: sections/S210-….md  color: yellow"
_HEAD = re.compile(r"^\s*\d+\.\s*file:\s*(\S+)\s+color:\s*([a-z]+)", re.I)
_FIELD = re.compile(r"^\s+(exact|prefix|suffix|note):\s?(.*)$")
# a wrapped note line: indented, and not itself a field
_CONT = re.compile(r"^\s{3,}(\S.*)$")


def parse(text: str):
    """Read the copied block into records, keeping wrapped note lines."""
    records, cur, field = [], None, None
    for line in text.splitlines():
        head = _HEAD.match(line)
        if head:
            cur = {"file": head.group(1), "color": head.group(2).lower(),
                   "exact": "", "prefix": "", "suffix": "", "note": ""}
            records.append(cur)
            field = None
            continue
        if cur is None:
            continue
        got = _FIELD.match(line)
        if got:
            field = got.group(1)
            cur[field] = got.group(2).strip()
            continue
        more = _CONT.match(line)
        if more and field == "note":
            cur["note"] = (cur["note"] + "\n" + more.group(1)).strip()
    return [r for r in records if r["exact"]]


def slug(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+|[一-鿿]", text)
    out = "-".join(words[:6]).lower()
    return out[:48].strip("-") or "mark"


def write_marks(paper_root: Path, notes: Path, records):
    """Write records into notes/marks/, skipping ones already there.

    Shared with serve.py, so the save button and the command line cannot drift
    apart. A mark is identified by its file plus its quote, which is what makes
    a repeat run write nothing.
    """
    marks_dir = notes / "marks"
    seen, used = set(), set()
    for mark in paperkit.load_marks(notes):
        anchor = mark["meta"].get("anchor") or {}
        quote = anchor.get("quote") or {}
        seen.add((str(anchor.get("file") or ""),
                  paperkit.normalize(str(quote.get("exact") or ""))))
        used.add(str(mark["meta"].get("id")))

    out = {"written": 0, "skipped": 0, "bad": [], "soft": [], "files": []}
    for rec in records:
        key = (rec["file"], paperkit.normalize(rec["exact"]))
        if key in seen:
            out["skipped"] += 1
            continue
        if rec["color"] not in paperkit.VALID_COLOR:
            rec["color"] = "yellow"
        # A missing file is a real error -- nothing can place that. A quote that
        # does not match the Markdown is not: it was made against the rendered
        # page, where a formula is glyphs that never appear in the source. The
        # page finds those perfectly well, because it searches the same rendered
        # text the mark was drawn on. Write it, say so, let the page place it.
        source = paper_root / rec["file"]
        if not source.is_file():
            out["bad"].append((rec["exact"][:40], f"原文裡沒有 {rec['file']}"))
            continue
        lines = source.read_text(encoding="utf-8").splitlines()
        hits = paperkit.count_quote(lines, paperkit.normalize(rec["exact"]))
        if hits == 0:
            out["soft"].append((rec["exact"][:40], "引文不在原始 Markdown 裡（含公式的畫記正常會這樣）"))
        elif hits > 1:
            out["soft"].append((rec["exact"][:40], f"引文出現 {hits} 次，頁面會用前後文挑一處"))

        num = 1
        while f"{num:04d}" in used:
            num += 1
        mid = f"{num:04d}"
        used.add(mid)

        meta = {
            "id": mid,
            "created": date.today().isoformat(),
            "color": rec["color"],
            "anchor": {
                "file": rec["file"],
                "quote": {k: rec[k] + "\n" for k in ("prefix", "exact", "suffix") if rec[k]},
            },
        }
        marks_dir.mkdir(parents=True, exist_ok=True)
        path = marks_dir / f"{mid}-{slug(rec['exact'])}.md"
        path.write_text(
            "---\n" + miniyaml.dump(meta) + "\n---\n\n"
            + (rec["note"] + "\n" if rec["note"] else ""),
            encoding="utf-8",
            newline="\n",
        )
        seen.add(key)
        out["written"] += 1
        out["files"].append(path.name)
    return out


def save_mark(mark, color: str, note: str) -> None:
    """Rewrite one mark in place, keeping its anchor exactly as it was.

    Only the two things the reader can change from the page -- colour and note.
    The quote is what makes the mark findable, so it is never touched here.
    """
    meta = dict(mark["meta"])
    if color in paperkit.VALID_COLOR:
        meta["color"] = color
    meta["updated"] = date.today().isoformat()
    mark["path"].write_text(
        "---\n" + miniyaml.dump(meta) + "\n---\n\n" + (note + "\n" if note else ""),
        encoding="utf-8",
        newline="\n",
    )


def main(argv) -> int:
    # --from takes a value: skip it, or "--from x.txt" alone reads x.txt as work
    args = []
    skip = False
    for arg in argv[1:]:
        if skip:
            skip = False
            continue
        if arg.startswith("--"):
            skip = arg == "--from"
            continue
        args.append(arg)
    work = Path(args[0] if args else ".").resolve()
    _, paper_root, notes, _ = paperkit.load_workspace(work)

    src = None
    for arg in argv[1:]:
        if arg.startswith("--from="):
            src = arg[len("--from="):]
    if src is None and "--from" in argv:
        idx = argv.index("--from")
        if idx + 1 < len(argv):
            src = argv[idx + 1]
    text = Path(src).read_text(encoding="utf-8") if src else sys.stdin.read()

    records = parse(text)
    if not records:
        print("讀不到任何畫記。請確認貼進來的是複習頁「複製畫記」的完整輸出。")
        return 1

    result = write_marks(paper_root, notes, records)
    for name in result["files"]:
        print(f"  + {name}")
    print(
        f"畫記匯入   新增 {result['written']} 條、已存在 {result['skipped']} 條、"
        f"無法匯入 {len(result['bad'])} 條"
    )
    for quote, why in result["bad"]:
        print(f"  🔴 「{quote}…」{why}")
    for quote, why in result["soft"]:
        print(f"  🟡 「{quote}…」{why}")
    if result["written"]:
        print("  接著跑 build_annotated.py 與 build_html.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
