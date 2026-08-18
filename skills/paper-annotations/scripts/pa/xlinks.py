"""Typed links between notes, across papers.

A digest is where a connection is discovered; a link is where it is kept. The
difference that matters is not the format -- it is that a digest has to be
remembered and reopened, while a link comes back to you at the sentence it is
about. Prose carries the reasoning, structure carries the reach; neither one
replaces the other.

Declared once, on whichever note has something to say:

    links:
      - contradicts eplace-ms#P0003
      - answers #Q0004

and rendered at both ends. Storing it twice would let the two halves drift.

One string per link rather than a type/to mapping, because miniyaml does not
do sequences of mappings and this is not worth widening it for: "<type>
<target>" is shorter to write, and a reader who has never seen the format can
still tell what it says.

Resolution follows ADR 0001: a target either resolves against the catalog that
is actually on disk or it is reported unresolved. Nothing here guesses which
note was meant -- a link to the wrong claim is worse than a missing one,
because it will be believed.

The type list is short on purpose. An open vocabulary drifts into a hundred
near-synonyms and stops being comparable, which is the only thing links are
for. Widen it when a digest keeps needing a word that is not here, not before.
"""

from __future__ import annotations

import re

from . import library

# forward label (on the note that declares it), reverse label (on the target)
LINK_TYPES = {
    "answers": ("回答了", "答案在"),
    "contradicts": ("牴觸", "牴觸"),
    "same-as": ("同一件事", "同一件事"),
    # a successor paper improving its predecessor is the single most common
    # relationship between two papers on a shelf, and calling it contradicts
    # reads three months later as a dispute that never happened.
    "refines": ("改進了", "被…改進"),
}

# "eplace-ms#P0003", "#Q0001" (this paper), case-insensitive on the kind
REF = re.compile(r"^\s*([A-Za-z0-9][\w.-]*)?\s*#\s*([QqPp])\s*(\d+)\s*$")
# one link per line: "<type> <target>"
LINE = re.compile(r"^\s*([A-Za-z][\w-]*)\s+(\S+)\s*$")


def parse_ref(text, this_slug: str):
    """"<slug>#Q0001" -> {"slug","kind","id"}. None when it is not a reference."""
    match = REF.match(str(text or ""))
    if not match:
        return None
    return {
        "slug": (match.group(1) or this_slug).lower(),
        "kind": match.group(2).upper(),
        "id": match.group(3).zfill(4),
    }


def ref_text(ref) -> str:
    return f"{ref['slug']}#{ref['kind']}{ref['id']}"


def index(registry_path):
    """slug -> catalog, for every registered paper whose notes are still there.

    Catalogs are what links resolve against, which means a paper that has never
    been built cannot be linked to yet. That is the right failure: the catalog
    is the record of what notes exist, and without it any target would be a
    guess.
    """
    out = {}
    for paper in library.entries(registry_path):
        if not paper["alive"]:
            continue
        catalog = library.read_catalog(paper["work"])
        if catalog is not None:
            out[paper["slug"]] = catalog
    return out


def find(idx, ref):
    """The note a reference names, or None. Never a near miss."""
    catalog = idx.get(ref["slug"])
    if not catalog:
        return None
    bucket = "cards" if ref["kind"] == "Q" else "points"
    for note in catalog.get(bucket) or []:
        if str(note.get("id") or "").zfill(4) == ref["id"]:
            return note
    return None


def summarise(note, kind: str) -> str:
    """One line describing the target, so a link says something on its own."""
    if not note:
        return ""
    text = str(note.get("question") if kind == "Q" else note.get("text") or "")
    return " ".join(text.split())


def declared(meta, this_slug: str, problems=None, where=""):
    """Validate and parse one note's `links:` block.

    Returns the usable ones. Anything malformed is reported rather than
    dropped -- a link the reader wrote and never sees again is the same
    failure as a card that vanishes.
    """
    raw = meta.get("links")
    if raw is None:
        return []
    if not isinstance(raw, list):
        if problems is not None:
            problems.append((where, "links 不是清單（應該是 - type: … / to: … 的列表）"))
        return []

    out = []
    for item in raw:
        line = LINE.match(str(item or ""))
        if line is None:
            if problems is not None:
                problems.append(
                    (where, f"連結「{item}」格式不對，應該是「型別 目標」，例如 "
                            "contradicts eplace-ms#P0003")
                )
            continue
        kind = line.group(1).lower()
        if kind not in LINK_TYPES:
            if problems is not None:
                problems.append(
                    (where, f"連結型別「{kind}」不認得，只能是 " + " / ".join(LINK_TYPES))
                )
            continue
        ref = parse_ref(line.group(2), this_slug)
        if ref is None:
            if problems is not None:
                problems.append(
                    (where, f"連結目標「{line.group(2)}」格式不對，"
                            "應該像 eplace-ms#P0003 或 #Q0001")
                )
            continue
        out.append({"type": kind, "ref": ref})
    return out


def resolve(links, idx, this_slug: str):
    """Split declared links into ones that hit a real note and ones that do not."""
    good, missing = [], []
    for link in links:
        ref = link["ref"]
        note = find(idx, ref)
        if note is None:
            why = (
                f"登記簿裡沒有 {ref['slug']} 這篇論文"
                if ref["slug"] not in idx
                else f"{ref['slug']} 裡找不到 {ref['kind']}{ref['id']}"
            )
            missing.append({**link, "why": why})
            continue
        good.append({**link, "note": note, "summary": summarise(note, ref["kind"])})
    return good, missing


def incoming(idx, this_slug: str):
    """Backlinks: who points here, derived rather than stored.

    A link lives in exactly one file. The other end is computed at build time,
    so the two can never disagree -- which is the whole reason not to write it
    down twice.
    """
    back = {}
    for slug, catalog in idx.items():
        for bucket, kind in (("cards", "Q"), ("points", "P")):
            for note in catalog.get(bucket) or []:
                for link in declared({"links": note.get("links") or []}, slug):
                    ref = link["ref"]
                    if ref["slug"] != this_slug:
                        continue
                    key = f"{ref['kind']}{ref['id']}"
                    back.setdefault(key, []).append(
                        {
                            "type": link["type"],
                            "from": {"slug": slug, "kind": kind,
                                     "id": str(note.get("id") or "").zfill(4)},
                            "summary": summarise(note, kind),
                        }
                    )
    return back
