"""HTML-level passes over the assembled review page.

Each pass takes the rendered body and returns it transformed: algorithm boxes,
figure/table ids, clickable cross-references, mark-to-card joins, image
embedding. They run on the whole page at once because a section often points
at a figure that lives in another section.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from . import anchors, notes

# An algorithm is a title paragraph followed by its numbered steps. Both
# conversions agree on that shape; only the title's emphasis differs.
# The title is short and its steps follow immediately (an "Input:/Output:"
# paragraph may sit between). Both bounds matter: prose that merely opens with
# "Algorithm 1 describes the procedure..." must not match, because a rejected
# match still consumes its span and would hide the next real listing.
_ALGO = re.compile(
    r"(<p>\s*(?:<strong>)?\s*Algorithm\s+(\d+)\b.{0,200}?</p>)"
    r"((?:\s*<p>.{0,400}?</p>){0,2}\s*<ol>.*?</ol>)",
    re.S | re.I,
)
_HEADING_TAG = re.compile(r"<h[1-6]\b", re.I)


def wrap_algorithms(body_html: str):
    """Box each listing. Anything that does not clearly end in its own list is
    left alone -- swallowing the following paragraphs would be worse than a
    plain-looking algorithm."""
    found = {}

    def wrap(match):
        title, number, rest = match.group(1), match.group(2), match.group(3)
        # a heading in between means the list belongs to something else
        if _HEADING_TAG.search(rest) or re.search(r"Algorithm\s+\d", rest, re.I):
            return match.group(0)
        if len(rest) > 12000:
            return match.group(0)
        anchor = f"alg-{number}"
        found[("algorithm", number)] = anchor
        inner = re.sub(r"^<p>\s*|\s*</p>$", "", title)
        inner = re.sub(r"^<strong>\s*|\s*</strong>$", "", inner.strip())
        return f'<div class="algo" id="{anchor}"><div class="algo-t">{inner}</div>{rest}</div>'

    return _ALGO.sub(wrap, body_html), found


# --------------------------------------------------------------------------
# cross-references ("see Fig. 4", "Table V")
# --------------------------------------------------------------------------

_ASSET_IMG = re.compile(
    r'<img\s+([^>]*?)src="([^"]*?(figure|table)-0*(\d+)\.[A-Za-z]+)"([^>]*?)>', re.I
)
_ALT = re.compile(r'alt="([^"]*)"', re.I)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
# "Fig. 4", "Figure 4", "FIG. 4", "Table V", "TABLE 8" -- the label varies from
# paper to paper, the shape does not.
_XREF = re.compile(r"\b(Figs?\.|Figures?|FIGs?\.|Tables?|TABLES?|Algorithms?|ALGORITHMS?)\s*(\d+|[IVXLCDM]+)\b")
# Inside these, a link would either fight the element's own click or jump the
# page out from under an open card.
_CITED = re.compile(r"\[\s*\d+\s*,\s*$")
_SKIP_OPEN = re.compile(r"<(details|a|mark|h[1-6])\b", re.I)
_SKIP_CLOSE = re.compile(r"</(details|a|mark|h[1-6])\s*>", re.I)


def roman_to_int(text: str):
    total, prev = 0, 0
    for char in reversed(text.upper()):
        value = _ROMAN.get(char)
        if value is None:
            return None
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total or None


def label_ids(body_html: str):
    """Give every figure/table image an id, and map what the text may call it.

    The number comes from the asset filename, which both conversions agree on;
    the alt text supplies the paper's own label (Roman or Arabic) when it has
    one, so "Table V" and "Table 5" both resolve without assuming they match.
    """
    targets = {}

    def stamp(match):
        head, src, kind, number, tail = match.groups()
        kind = kind.lower()
        num = int(number)
        anchor = f"{'fig' if kind == 'figure' else 'tab'}-{num}"
        targets[(kind, str(num))] = anchor
        alt = _ALT.search(head + tail)
        if alt:
            token = alt.group(1).split()[-1].strip(".:") if alt.group(1).split() else ""
            if token:
                targets[(kind, token.upper())] = anchor
                as_roman = roman_to_int(token)
                if as_roman:
                    targets[(kind, str(as_roman))] = anchor
        if re.search(r'\bid="', head + tail):
            return match.group(0)
        return f'<img {head}id="{anchor}" src="{src}"{tail}>'

    return _ASSET_IMG.sub(stamp, body_html), targets


def linkify_xrefs(body_html: str, targets):
    """Turn mentions into links, but only where the target actually exists."""
    linked, unresolved = 0, {}

    def repl(match):
        nonlocal linked
        word, number = match.group(1), match.group(2)
        # "[13, Table V]" is a table inside reference 13, not one of ours.
        if _CITED.search(match.string[: match.start()]):
            return match.group(0)
        first = word[0].lower()
        kind = "figure" if first == "f" else ("algorithm" if first == "a" else "table")
        key = (kind, number.upper() if not number.isdigit() else number)
        anchor = targets.get(key)
        if anchor is None and not number.isdigit():
            as_roman = roman_to_int(number)
            anchor = targets.get((kind, str(as_roman))) if as_roman else None
        if anchor is None:
            unresolved[f"{word} {number}"] = unresolved.get(f"{word} {number}", 0) + 1
            return match.group(0)
        linked += 1
        return f'<a class="xref" href="#{anchor}">{match.group(0)}</a>'

    out, depth = [], 0
    for segment in re.split(r"(<[^>]+>)", body_html):
        if segment.startswith("<"):
            if _SKIP_OPEN.match(segment) and not segment.startswith("</"):
                depth += 1
            elif _SKIP_CLOSE.match(segment):
                depth = max(0, depth - 1)
            out.append(segment)
        elif depth:
            out.append(segment)
        else:
            out.append(_XREF.sub(repl, segment))
    return "".join(out), linked, unresolved


_CARD_OPEN = re.compile(r"<details([^>]*class=\"qcard\"[^>]*)>\s*<summary>(.*?)</summary>", re.S)
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')
_MARK_RE = re.compile(r"<mark>(.*?)</mark>", re.S)


def tag_marks(body_html: str, cards) -> str:
    """Attach each highlight to the card that put it there.

    The mark is written as plain ==…== in the Markdown so that view stays
    portable; the id is joined back on here, by quote, so a filtered-out card
    takes its highlight with it. An ambiguous match gets no id and simply stays
    lit -- the harmless failure of the two.
    """
    quotes = []
    for card in cards:
        anchor = card["meta"].get("anchor") or {}
        quote = anchors.quote_text(anchor.get("quote"))
        if quote:
            quotes.append(
                (quote, str(card["meta"].get("id")), str(card["meta"].get("origin") or "asked"))
            )

    def sub(match):
        inner = anchors.normalize(re.sub(r"<[^>]+>", "", match.group(1)))
        if not inner:
            return match.group(0)
        hits = [(cid, origin) for quote, cid, origin in quotes if inner in quote or quote in inner]
        if len(hits) != 1:
            return match.group(0)
        return f'<mark data-id="{hits[0][0]}" data-origin="{hits[0][1]}">{match.group(1)}</mark>'

    return _MARK_RE.sub(sub, body_html)


def collect_marks(notes_dir, paper_root):
    """Read notes/marks/, check each quote against the paper, hand back JSON.

    Checked here against the original sections rather than against annotated/,
    because the annotated copy already has ==…== wrapped round the sentences
    the cards point at -- matching there would fail for reasons that have
    nothing to do with the mark.

    Placement itself is left to the page: it resolves marks with the same
    quote-plus-neighbours search it uses for the ones drawn in the browser, so
    there is one locator, not two that can disagree.

    Which is also why a quote that does not match here is a warning and not a
    veto. A mark is made against the rendered text, and a rendered formula is
    glyphs that never appear in the Markdown at all -- checking those against
    the source and then dropping them threw away marks the page could place
    perfectly well. The page reports what it could not find; this reports what
    looks wrong. Neither gets to delete the reader's highlight.
    """
    problems = []
    marks = notes.load_marks(notes_dir, problems)
    bad = [(path.name, message) for path, message in problems]
    soft, data, cache = [], [], {}

    for mark in marks:
        anchor = mark["meta"].get("anchor") or {}
        rel = str(anchor.get("file") or "").strip()
        quote = anchor.get("quote") or {}
        exact = anchors.normalize(str(quote.get("exact") or ""))
        name = mark["path"].name

        src = (paper_root / rel) if rel else None
        if not src or not src.is_file():
            bad.append((name, f"anchor.file 是「{rel or '空白'}」，原文裡沒有這個檔案"))
            continue
        if rel not in cache:
            cache[rel] = src.read_text(encoding="utf-8").splitlines()
        hits = anchors.count_quote(cache[rel], exact)
        # -1 means the quote is too short to count on its own; the page still
        # places it, using the neighbouring text to choose between occurrences
        if hits == 0:
            soft.append((name, "引文在原始 Markdown 裡找不到（含公式的畫記正常會這樣）"))
        elif hits > 1:
            soft.append((name, f"引文在原文裡出現 {hits} 次，頁面會用前後文挑一處"))

        data.append(
            {
                "id": str(mark["meta"].get("id")),
                "s": Path(rel).stem,
                "f": rel,
                "e": exact,
                "p": anchors.normalize(str(quote.get("prefix") or "")),
                "x": anchors.normalize(str(quote.get("suffix") or "")),
                "c": notes.COLOR_SLOT.get(mark["color"], "1"),
                "n": mark["note"],
            }
        )

    return marks, data, bad, soft


def collect_questions(body_html: str):
    """Every question in the order it appears in the paper.

    Taken from the assembled page rather than from the card files, so the list
    order is the anchor order -- the same order the reader meets them.
    """
    found = []
    for match in _CARD_OPEN.finditer(body_html):
        attrs = dict(_ATTR.findall(match.group(1)))
        summary = match.group(2)
        label = re.search(r"</b>\s*·\s*(.*?)\s*<sub>", summary, re.S)
        text = re.sub(r"<[^>]+>", "", label.group(1) if label else summary).strip()
        found.append(
            {
                "id": attrs.get("data-id", "?"),
                "status": attrs.get("data-status", "open"),
                "origin": attrs.get("data-origin", "asked"),
                "text": text,
            }
        )
    return found


def slugify(text: str, used: dict) -> str:
    base = re.sub(r"[^\w一-鿿]+", "-", text.strip().lower()).strip("-") or "sec"
    n = used.get(base, 0)
    used[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def embed_images(html_text: str, base_dir: Path):
    """Inline every local image as a data: URI so one file travels alone.

    Returns (html, embedded, missing). The counts are the point: a file that
    quietly kept half of its images as relative paths still looks right here,
    and arrives at the other end full of holes.
    """
    done, missing = [], []

    def sub(match):
        src = match.group(1)
        # skip the script's own string concatenations, not just real URLs
        if src.startswith(("data:", "http:", "https:")) or "'" in src:
            return match.group(0)
        path = (base_dir / src).resolve()
        if not path.is_file():
            missing.append(src)
            return match.group(0)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        done.append(src)
        return f'src="data:{mime};base64,{data}"'

    # (?<![-\w]) so this is src=, not the tail of data-src= -- the sections
    # carry one of those, and matching it reported every chunk as a lost image
    return re.sub(r'(?<![-\w])src="([^"]+)"', sub, html_text), len(done), missing
