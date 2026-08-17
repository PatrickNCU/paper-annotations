"""Cards and marks: frontmatter documents under notes/.

A card the user wrote must never disappear without a word -- every loader here
reports what it could not use instead of skipping it in silence.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import miniyaml
from .anchors import normalize

VALID_STATUS = ("open", "half", "resolved")
VALID_ORIGIN = ("asked", "suggested")
# Highlights the reader drew. Named rather than numbered: a file saying
# color: yellow survives being read by a human, "3" does not.
VALID_COLOR = ("yellow", "green", "blue", "red")
COLOR_SLOT = {"yellow": "1", "green": "2", "blue": "3", "red": "4"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def read_doc(path: Path):
    """Return (meta, body) for a markdown file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    return miniyaml.load(match.group(1)), text[match.end() :]


def write_doc(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---\n" + miniyaml.dump(meta) + "\n---\n" + body
    path.write_text(text, encoding="utf-8", newline="\n")


def load_cards(notes_dir: Path, problems=None):
    """Load every card, and report the ones that could not be used.

    A card the user wrote must never disappear without a word -- silently
    skipping an unreadable card looks exactly like the note was never saved.
    """
    cards = []
    cards_dir = notes_dir / "cards"
    if not cards_dir.is_dir():
        return cards

    def complain(path, message):
        if problems is not None:
            problems.append((path, message))

    for path in sorted(cards_dir.glob("*.md")):
        meta, body = read_doc(path)
        if not isinstance(meta, dict) or not meta:
            complain(path, "檔案開頭讀不到 --- YAML 區塊，這張卡沒有被使用")
            continue
        meta.setdefault("id", path.stem.split("-")[0])

        anchor = meta.get("anchor")
        if anchor is None:
            complain(path, "沒有 anchor 欄位，不知道要掛在哪裡")
        elif not isinstance(anchor, dict):
            complain(path, "anchor 欄位格式不對（應該是縮排的 file / heading / quote）")
            meta["anchor"] = {}
        elif anchor.get("file") is not None and not isinstance(anchor.get("file"), str):
            complain(path, "anchor.file 不是檔案路徑，YAML 可能寫壞了")
            anchor["file"] = ""

        status = str(meta.get("status", "open"))
        if status not in VALID_STATUS:
            complain(path, f"status 是「{status}」，只能是 {' / '.join(VALID_STATUS)}")
        origin = str(meta.get("origin", "asked"))
        if origin not in VALID_ORIGIN:
            complain(path, f"origin 是「{origin}」，只能是 {' / '.join(VALID_ORIGIN)}")

        if not card_sections(body).get("問題", "").strip():
            complain(path, "沒有寫「## 問題」，複習時只會看到一張沒有問題的卡")

        cards.append({"path": path, "meta": meta, "body": body})

    seen = {}
    for card in cards:
        cid = str(card["meta"].get("id"))
        if cid in seen:
            complain(
                card["path"],
                f"編號 {cid} 和 {seen[cid].name} 重複，索引會出現兩個同號的疑問",
            )
        else:
            seen[cid] = card["path"]
    return cards


def load_marks(notes_dir: Path, problems=None):
    """Load the highlights the reader drew, with whatever note each carries.

    A sidecar of its own rather than a kind of card: a note in the margin is
    not a question, and folding the two together would make "疑問 N 則" -- the
    number the whole review page is organised around -- stop meaning anything.
    Same refuse-to-lose rule as cards: an unusable file is reported, never
    skipped in silence.
    """
    marks = []
    marks_dir = notes_dir / "marks"
    if not marks_dir.is_dir():
        return marks

    def complain(path, message):
        if problems is not None:
            problems.append((path, message))

    for path in sorted(marks_dir.glob("*.md")):
        meta, body = read_doc(path)
        if not isinstance(meta, dict) or not meta:
            complain(path, "檔案開頭讀不到 --- YAML 區塊，這條畫記沒有被使用")
            continue
        meta.setdefault("id", path.stem.split("-")[0])

        anchor = meta.get("anchor")
        if not isinstance(anchor, dict):
            complain(path, "沒有 anchor 欄位，不知道要畫在哪一段")
            continue
        quote = anchor.get("quote")
        if not isinstance(quote, dict) or not str(quote.get("exact") or "").strip():
            complain(path, "anchor.quote.exact 是空的，沒有可以比對的原文")
            continue

        color = str(meta.get("color") or "yellow")
        if color not in VALID_COLOR:
            complain(path, f"color 是「{color}」，只能是 {' / '.join(VALID_COLOR)}")
            color = "yellow"

        marks.append({"path": path, "meta": meta, "color": color, "note": body.strip()})

    seen = {}
    for mark in marks:
        mid = str(mark["meta"].get("id"))
        if mid in seen:
            complain(mark["path"], f"編號 {mid} 和 {seen[mid].name} 重複")
        else:
            seen[mid] = mark["path"]
    return marks


def card_sections(body: str):
    """Split a card body on '## ' headings into {heading: text}."""
    sections, current, buf = {}, None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


# Re-exported so callers that read quotes off a card do not need a second
# import for the one normalize() they use alongside.
__all__ = [
    "VALID_STATUS", "VALID_ORIGIN", "VALID_COLOR", "COLOR_SLOT",
    "FRONTMATTER_RE", "read_doc", "write_doc", "load_cards", "load_marks",
    "card_sections", "normalize",
]
