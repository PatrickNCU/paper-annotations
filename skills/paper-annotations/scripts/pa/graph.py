"""The note link graph: nodes, typed edges, and the numbers worth printing.

Assembled from what already exists -- each paper's ``notes/catalog.json`` for
the notes and their declared links, ``notes/references.json`` for the citations.
No new note format, and nothing here is written to disk: this is a view.

Three things decided here rather than in the pages that draw it, because both
pages have to agree on them:

  * **A cell's number is breadth, not a count of lines.** Four links between
    two papers can be four separate relationships, or one relationship written
    down four times because a single note fans out. Counting lines cannot tell
    those apart and reads the second as four times more related than it is.
    Breadth is how many *distinct* notes on each side actually take part, taking
    the narrower side -- so the fan-out case is 1, which is what it is. The raw
    count is kept beside it, never instead of it.
  * **Nothing is normalised.** Dividing by note counts produces a decimal nobody
    can explain, and an unexplainable number on screen is worse than an honest
    integer. The diagonal carries each paper's own note count instead, so "this
    row is big because I wrote a lot about it" stays visible.
  * **A contradiction is flagged separately.** One 牴觸 is worth more than four
    改進了, and by any count it sinks to the bottom of the table.

Layout is never computed here and never anywhere else either: the pages draw
tables and columns, so the same data draws the same picture every time.
"""

from __future__ import annotations

from pathlib import Path

from . import library, miniyaml, xlinks

# How many neighbours one note's view draws per direction before it stops and
# says so. Past this the picture is a hairball whatever the layout.
EGO_LIMIT = 10


def _short(catalog, slug: str) -> str:
    return str((catalog or {}).get("paper") or slug)


def _label(note, kind: str) -> str:
    text = str(note.get("question") if kind == "Q" else note.get("text") or "")
    return " ".join(text.split())


def collect(registry_path):
    """Everything the three views need, in one JSON-ready dictionary.

    Ordered throughout -- papers by year then slug, notes and edges by id -- so
    that two builds of the same notes produce the same file, byte for byte.
    """
    entries = [p for p in library.entries(registry_path)]
    catalogs = xlinks.index(registry_path)
    alive = [p for p in entries if p["alive"] and p["slug"] in catalogs]

    papers, notes = [], {}
    for entry in sorted(alive, key=lambda p: (p.get("year") or 9999, p["slug"])):
        slug = entry["slug"]
        catalog = catalogs[slug]
        cards = catalog.get("cards") or []
        points = catalog.get("points") or []
        papers.append({
            "slug": slug,
            "short": _short(catalog, slug),
            "title": str(catalog.get("title") or entry.get("title") or slug),
            "year": catalog.get("year") or entry.get("year"),
            "cards": len(cards),
            "points": len(points),
            "notes": len(cards) + len(points),
            "topics": sorted(set(entry["topics"]) | set(entry["topics_auto"])),
        })
        for bucket, kind in (("cards", "Q"), ("points", "P")):
            for note in catalog.get(bucket) or []:
                key = f"{slug}#{kind}{str(note.get('id') or '').zfill(4)}"
                notes[key] = {
                    "slug": slug,
                    "kind": kind,
                    "id": str(note.get("id") or "").zfill(4),
                    "text": _label(note, kind),
                    "where": str(note.get("where") or ""),
                    "tags": [str(t) for t in (note.get("tags") or [])],
                    # cards carry a status, points carry what kind of claim it is
                    "status": str(note.get("status") or "") if kind == "Q" else "",
                    "pkind": str(note.get("kind") or "") if kind == "P" else "",
                }

    edges = []
    for key in sorted(notes):
        slug = notes[key]["slug"]
        catalog = catalogs[slug]
        bucket = "cards" if notes[key]["kind"] == "Q" else "points"
        raw = next(
            (n for n in catalog.get(bucket) or []
             if str(n.get("id") or "").zfill(4) == notes[key]["id"]),
            None,
        )
        for link in xlinks.declared({"links": (raw or {}).get("links") or []}, slug):
            target = f"{link['ref']['slug']}#{link['ref']['kind']}{link['ref']['id']}"
            # ADR 0001: a target that is not on disk is not drawn. A line to a
            # note nobody can open is a line that will be believed anyway.
            if target in notes:
                edges.append({"type": link["type"], "from": key, "to": target})

    return {
        "papers": papers,
        "notes": notes,
        "edges": edges,
        "cites": _citations(entries),
        "pairs": pairs(papers, notes, edges),
        "types": {k: list(v) for k, v in xlinks.LINK_TYPES.items()},
    }


def _citations(entries):
    """Who cites whom, with the sentence around the citation where we can get it.

    Mechanical: either two titles agree or they do not. This is the background
    the drawn links sit on -- "you have read both of these and one cites the
    other, but you never connected them" is the actionable gap.
    """
    out = {}
    for edge in library.citation_edges(entries):
        source = next((p for p in entries if p["slug"] == edge["from"]), None)
        key = f"{edge['from']}>{edge['to']}"
        row = out.setdefault(key, {"from": edge["from"], "to": edge["to"], "sites": []})
        if source is None or len(row["sites"]) >= 2:
            continue
        try:
            config = miniyaml.load(
                (source["work"] / "notes" / "paper.yml").read_text(encoding="utf-8")
            )
            paper_root = (source["work"] / str(config.get("paper_root") or ".")).resolve()
            source_list = [Path(p) for p in (config.get("sources") or [])]
        except (OSError, ValueError):
            continue
        for hit in library.citation_context(paper_root, source_list, int(edge["n"] or 0)):
            row["sites"].append({"n": edge["n"], **hit})
    return [out[k] for k in sorted(out)]


def pairs(papers, notes, edges):
    """Per ordered pair of papers: breadth, the raw count, and what inflated it.

    Everything a cell and the page behind it needs is worked out once, here,
    so the matrix and the pair view can never disagree about the same number.
    """
    known = {p["slug"] for p in papers}
    out = {}
    for edge in edges:
        a, b = notes[edge["from"]]["slug"], notes[edge["to"]]["slug"]
        if a not in known or b not in known:
            continue
        row = out.setdefault(f"{a}>{b}", {
            "from": a, "to": b, "links": 0,
            "src": [], "dst": [], "types": [], "secs": [], "secd": [],
        })
        row["links"] += 1
        for field, value in (
            ("src", edge["from"]), ("dst", edge["to"]),
            ("types", edge["type"]),
            ("secs", notes[edge["from"]]["where"]), ("secd", notes[edge["to"]]["where"]),
        ):
            if value not in row[field]:
                row[field].append(value)

    for row in out.values():
        fan = {}
        row["breadth"] = min(len(row["src"]), len(row["dst"]))
        row["contra"] = "contradicts" in row["types"]
        for edge in edges:
            if notes[edge["from"]]["slug"] == row["from"] and notes[edge["to"]]["slug"] == row["to"]:
                fan[edge["from"]] = fan.get(edge["from"], 0) + 1
        row["fan"] = max(fan.values()) if fan else 0
        # the note responsible for the widest fan, so the warning can name it
        row["fanof"] = max(sorted(fan), key=lambda k: fan[k]) if fan else ""
        row["src"] = sorted(row["src"])
        row["dst"] = sorted(row["dst"])
        row["types"] = sorted(row["types"])
        row["secs"] = sorted(row["secs"])
        row["secd"] = sorted(row["secd"])
    return out


def ego_slice(data, slug: str):
    """Trim the shelf's graph to what one paper's review page can ever draw.

    A review page only ever shows the neighbourhood of a note it already holds,
    so shipping every other paper's notes with it would be dead weight that
    grows with the shelf -- which is exactly the failure the three layers exist
    to avoid.
    """
    keep = {k for k, n in data["notes"].items() if n["slug"] == slug}
    edges = [e for e in data["edges"] if e["from"] in keep or e["to"] in keep]
    for edge in edges:
        keep.add(edge["from"])
        keep.add(edge["to"])
    slugs = {data["notes"][k]["slug"] for k in keep}
    return {
        "self": slug,
        "papers": [p for p in data["papers"] if p["slug"] in slugs],
        "notes": {k: data["notes"][k] for k in sorted(keep)},
        "edges": edges,
        "types": data["types"],
        "limit": EGO_LIMIT,
    }
