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


MARK_IDS = "<!--Q:{}-->"


def mark_quotes(lines, wanted):
    """Wrap every card's sentence in ==…==, however the sentences overlap.

    The card already knows which sentence tripped the reader up; marking it
    saves them re-reading the paragraph to find out where they were. Same
    refuse-to-guess rule as anchoring: unknown or ambiguous means no mark.

    wanted is [(card id, normalized quote)]. Every quote is located against the
    untouched lines first and only then written in, so one card's marks can no
    longer hide another's. Where quotes overlap the text is cut at every quote
    boundary and each piece is marked once, followed by the ids of every card
    covering it: ==exact routing tracks==<!--Q:0001 0007-->. The ids are what
    let the page open the right card -- the build knows which card drew which
    piece, so the page is told rather than left to guess from the words.

    ==…== rather than <mark>: the annotated Markdown stays portable (Obsidian
    and friends render it, and hide the comment) and minimd turns it into
    <mark data-ids> for the page.

    Returns (lines, why, near): why maps each card id that got no mark at all
    to the reason, so the build can say so instead of the mark silently not
    being there; near maps each of those whose quote was still found exactly
    once to the last line of the block holding it -- a formula can refuse a
    mark, but the page can still point at the paragraph it sits in.
    """
    haystack, spans = norm_map(lines)
    found, why, near = {}, {}, {}
    for cid, exact in wanted:
        if len(exact) < 12:
            why[cid] = "沒有引文，或引文太短"
            continue
        pos = haystack.find(exact)
        if pos < 0:
            why[cid] = "引文在這個檔案裡找不到"
            continue
        if haystack.find(exact, pos + 1) >= 0:
            why[cid] = "引文在這個檔案裡出現不只一次"
            continue
        end = pos + len(exact)
        home = next((idx for start, stop, idx in spans if stop > pos), None)
        got, reason = [], ""
        for start, stop, idx in spans:
            if stop <= pos or start >= end:
                continue
            fragment = haystack[max(start, pos) : min(stop, end)].strip()
            if len(fragment) < 4:
                continue
            # Match back into the raw line, tolerating the whitespace normalize() ate.
            pattern = r"\s+".join(re.escape(tok) for tok in fragment.split(" ") if tok)
            hits = list(re.finditer(pattern, lines[idx]))
            if len(hits) != 1:
                reason = reason or "引文在同一行裡出現不只一次"
                continue
            body = hits[0].group(0)
            # Never cut into math, code or a link target.
            if any(ch in body for ch in "$`"):
                reason = reason or "引文含公式或程式碼"
                continue
            if "](" in body or "==" in body:
                reason = reason or "引文跨過連結"
                continue
            got.append((idx, hits[0].start(), hits[0].end()))
        if not got:
            why[cid] = reason or "引文太短"
            if home is not None:
                near[cid] = _block_end(lines, home)
            continue
        for idx, a, b in got:
            found.setdefault(idx, []).append((a, b, str(cid)))

    out = list(lines)
    for idx, marks in found.items():
        out[idx] = _write_marks(out[idx], marks)
    return out, why, near


def _write_marks(line: str, marks) -> str:
    """Cut one line at every quote boundary and mark each covered piece once.

    ==…== cannot start or end on whitespace, so a piece's edge spaces are left
    outside it; the page puts them back inside when it joins the pieces up.
    """
    cuts = sorted({0, len(line)} | {a for a, _, _ in marks} | {b for _, b, _ in marks})
    out = []
    for a, b in zip(cuts, cuts[1:]):
        piece = line[a:b]
        ids = sorted({cid for start, stop, cid in marks if start <= a and stop >= b})
        core = piece.strip()
        if not ids or not core:
            out.append(piece)
            continue
        lead = piece[: len(piece) - len(piece.lstrip())]
        trail = piece[len(piece.rstrip()) :]
        out.append(f"{lead}=={core}=={MARK_IDS.format(' '.join(ids))}{trail}")
    return "".join(out)


def quote_offset(haystack: str, exact: str):
    """Where a quote starts in the normalized text, or None when not exactly once."""
    if len(exact) < 12:
        return None
    pos = haystack.find(exact)
    if pos < 0 or haystack.find(exact, pos + 1) >= 0:
        return None
    return pos


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
