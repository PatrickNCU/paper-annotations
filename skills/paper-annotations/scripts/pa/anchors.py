"""Anchor resolution: match a card's anchor against the text as it is now.

Design rule (see ADR 0001): anchors are RESOLVED, never DECLARED. Nothing here
trusts metadata about where a card belongs -- every anchor is matched against
the source text as it exists right now, and a card that cannot be matched is
reported as unanchored rather than silently placed.
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def norm_map(lines):
    """Normalized haystack plus a lookup from char offset back to line index."""
    pieces, spans, cursor = [], [], 0
    for idx, line in enumerate(lines):
        norm = normalize(line)
        if not norm:
            continue
        if pieces:
            cursor += 1
        spans.append((cursor, cursor + len(norm), idx))
        pieces.append(norm)
        cursor += len(norm)
    return " ".join(pieces), spans


def _block_end(lines, start: int) -> int:
    """Index of the last line of the blank-line-delimited block containing start."""
    i = start
    while i + 1 < len(lines) and lines[i + 1].strip():
        i += 1
    return i


def _display_math_end(lines, start: int) -> int:
    i = start
    while i + 1 < len(lines):
        i += 1
        if lines[i].strip() == "$$":
            return i
    return _block_end(lines, start)


def _find_ref(lines, ref: str):
    kind, _, value = ref.partition(":")
    kind, value = kind.strip().lower(), value.strip()
    if not value:
        return None

    if kind in ("eq", "equation"):
        pattern = re.compile(r"\\tag\{\s*" + re.escape(value) + r"\s*\}")
        for i, line in enumerate(lines):
            if pattern.search(line):
                return _display_math_end(lines, i), "ref:equation-tag"
        return None

    if kind in ("fig", "figure"):
        num = value.zfill(2)
        pattern = re.compile(r"!\[[^\]]*\]\([^)]*figure-0*" + re.escape(num.lstrip("0") or "0") + r"\b[^)]*\)")
        for i, line in enumerate(lines):
            if pattern.search(line) or re.search(r"figure-" + re.escape(num) + r"\.", line):
                after = i
                nxt = i + 1
                while nxt < len(lines) and not lines[nxt].strip():
                    nxt += 1
                if nxt < len(lines) and re.match(r"^Fig(ure)?\.?\s", lines[nxt].strip()):
                    after = _block_end(lines, nxt)
                return after, "ref:figure"
        return None

    if kind in ("table", "tbl"):
        num = value.zfill(2)
        for i, line in enumerate(lines):
            if re.search(r"table-" + re.escape(num) + r"[.\b]", line):
                return _block_end(lines, i), "ref:table"
        return None

    return None


def _find_heading(lines, heading_path):
    if not heading_path:
        return None
    if isinstance(heading_path, str):
        heading_path = [heading_path]
    target = normalize(str(heading_path[-1])).lower()
    exact, loose = [], []
    for i, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        text = normalize(line.lstrip("#")).lower()
        if text == target:
            exact.append(i)
        elif len(target) > 6 and target in text:
            loose.append(i)
    if len(exact) == 1:
        return exact[0], "heading"
    if not exact and len(loose) == 1:
        return loose[0], "heading"
    # Several headings match: refuse to guess, same as an ambiguous quote.
    return None


def _find_quote(lines, quote):
    if not quote:
        return None
    exact = normalize(str(quote.get("exact") or "")) if isinstance(quote, dict) else normalize(str(quote))
    if len(exact) < 12:
        return None
    haystack, spans = norm_map(lines)
    pos = haystack.find(exact)
    if pos < 0:
        return None
    if haystack.find(exact, pos + 1) >= 0:
        return None  # ambiguous: refuse to guess
    for start, end, idx in spans:
        if start <= pos < end:
            return _block_end(lines, idx), "quote"
    return None


def highlight_quote(lines, exact: str):
    """Wrap the anchored sentence in ==…== on the lines it covers.

    The card already knows which sentence tripped the reader up; marking it
    saves them re-reading the paragraph to find out where they were. Same
    refuse-to-guess rule as anchoring: unknown or ambiguous means no mark.

    ==…== rather than <mark>: the annotated Markdown stays portable (Obsidian
    and friends render it) and minimd turns it into <mark> for the page.
    """
    if not exact:
        return lines
    haystack, spans = norm_map(lines)
    pos = haystack.find(exact)
    if pos < 0 or haystack.find(exact, pos + 1) >= 0:
        return lines
    end = pos + len(exact)

    out = list(lines)
    for start, stop, idx in spans:
        if stop <= pos or start >= end:
            continue
        fragment = haystack[max(start, pos) : min(stop, end)].strip()
        if len(fragment) < 4:
            continue
        # Match back into the raw line, tolerating the whitespace normalize() ate.
        pattern = r"\s+".join(re.escape(tok) for tok in fragment.split(" ") if tok)
        hits = list(re.finditer(pattern, out[idx]))
        if len(hits) != 1:
            continue
        head, body, tail = out[idx][: hits[0].start()], hits[0].group(0), out[idx][hits[0].end() :]
        # Never cut into math, code or a link target -- and never nest marks,
        # so a second card quoting the same line simply goes unmarked.
        if any(ch in body for ch in "$`") or "](" in body or "==" in out[idx]:
            continue
        out[idx] = f"{head}=={body}=={tail}"
    return out


def quote_text(quote) -> str:
    if isinstance(quote, dict):
        return normalize(str(quote.get("exact") or ""))
    return normalize(str(quote or ""))


def count_quote(lines, exact: str) -> int:
    """How many times a quote occurs in this file (whitespace-insensitive)."""
    if len(exact) < 12:
        return -1
    haystack, _ = norm_map(lines)
    count, pos = 0, 0
    pos = haystack.find(exact)
    while pos >= 0:
        count += 1
        pos = haystack.find(exact, pos + 1)
    return count


def diagnose(anchor: dict, lines) -> str:
    """Why an anchor failed, phrased so the fix is obvious.

    "找不到" and "出現多次" need opposite fixes -- reporting both as
    "unresolved" makes the warning useless at the moment it matters.
    """
    if not anchor:
        return "這張卡沒有寫要掛在哪裡"
    problems = []
    if anchor.get("ref"):
        problems.append(f"這個檔案裡找不到 {anchor['ref']}（公式或圖表編號對不上）")
    if anchor.get("heading"):
        problems.append("這個檔案裡找不到指定的小節標題")

    exact = quote_text(anchor.get("quote"))
    count = count_quote(lines, exact)
    if count < 0:
        problems.append("沒有指定要掛在哪一句原文旁（quote.exact 需 12 字以上）")
    else:
        if count == 0:
            problems.append("這個檔案裡找不到你指定的那句原文（換一句，或執行 reanchor.py）")
        elif count > 1:
            problems.append(f"你指定的那句原文在這個檔案裡出現 {count} 次，無法確定是哪一處（把句子引長一點）")
    return "；".join(problems) or "無法解析"


def resolve_anchor(anchor: dict, lines):
    """Return (insert_after_line_index, method) or (None, reason).

    Ladder: ref -> heading -> quote. Each rung is verified against the real
    text; a rung that does not match falls through to the next one.
    """
    if not anchor:
        return None, "這張卡沒有寫要掛在哪裡"
    for finder in (
        lambda: _find_ref(lines, str(anchor.get("ref"))) if anchor.get("ref") else None,
        lambda: _find_heading(lines, anchor.get("heading")),
        lambda: _find_quote(lines, anchor.get("quote")),
    ):
        hit = finder()
        if hit:
            return hit[0], hit[1]
    return None, diagnose(anchor, lines)
