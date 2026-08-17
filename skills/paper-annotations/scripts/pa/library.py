"""The library: which papers this reader has read, and how they connect.

Everything else in this tool works inside one paper. This module is the only
part that knows more than one exists. Without it a fresh session has no way to
learn that the reader has been here before -- which is why cross-paper work was
impossible, not merely unimplemented.

Three pieces, in order of how much they can be trusted:

  * ``papers.yml`` -- the registry. Lives at the git repository root so it
    travels with version control instead of sitting in a home directory a
    second machine never sees. Hand-editable; probe.py keeps it up to date.
  * ``notes/catalog.json`` -- one per paper, written by the build. Every card
    and point in a few hundred bytes, so a cross-paper reader can scan the
    whole library without opening dozens of markdown files.
  * ``notes/references.json`` -- one per paper, the reference list as printed.
    Matching it against the registry happens **at read time**, never at write
    time: adding a paper today should light up the citations in a paper
    processed last month, without re-running anything.

Citation edges are mechanical -- either two titles agree or they do not, and
nothing here guesses. Edges of judgement (this contradicts that) are the
agent's job and belong in a digest.

Usage:
    python library.py [<work>] [--json]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from . import cli, miniyaml, notes

cli.bootstrap()

REGISTRY_NAME = "papers.yml"
REGISTRY_SCHEMA = 1
CATALOG_NAME = "catalog.json"
REFS_NAME = "references.json"

# "Index Terms—Analytic placement, electrostatic analogy, …"
INDEX_TERMS = re.compile(r"^Index Terms\s*[—\-–:]\s*(.+)$", re.M)

# A topic's colour, if it has one. Six digits only: the shelf hands this
# straight to CSS, so anything it cannot parse would silently do nothing.
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# "[12] A. Author et al., “Title,” in Proc. …, 2015, pp. 1-6."
REF_LINE = re.compile(r"^\[(\d+)\]\s+(.+)$")
REF_TITLE = re.compile("[“\"]([^”\"]{8,})[”\"]")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------


def _ancestors(start: Path):
    start = start.resolve()
    yield start
    for parent in start.parents:
        yield parent


def find_registry(start: Path):
    """An existing papers.yml at or above `start`, or None."""
    for base in _ancestors(start):
        candidate = base / REGISTRY_NAME
        if candidate.is_file():
            return candidate
    return None


def _too_high(base: Path, home: Path) -> bool:
    """Somewhere no registry may be created: the home folder or a drive root.

    A papers.yml that far up would collect every paper on the machine plus
    whatever unrelated work happens to sit beneath it.
    """
    return base == home or base == base.parent


def registry_home(start: Path) -> Path:
    """Where papers.yml belongs when there is not one yet.

    The git repository root, by the reader's decision: the registry should be
    versioned alongside the notes rather than live in a home directory, so a
    clone on another machine arrives with the library intact.

    Failing that, the folder the command was run from -- which for every path
    the skill takes is the workspace holding the papers. The old fallback was
    the paper's own package, and that is worse than it sounds: the next paper
    probed does not walk through its sibling's folder, so it never finds that
    registry and quietly starts a second one. Two registries mean two shelves,
    no citations between them, and nothing on screen saying so. Guarded by
    containment, because a run from an unrelated directory should not drop a
    registry there.
    """
    found = find_registry(start)
    if found is not None:
        return found
    start = start.resolve()
    home = Path.home().resolve()
    for base in _ancestors(start):
        if _too_high(base, home):
            break
        if (base / ".git").exists():
            return base / REGISTRY_NAME
    here = Path.cwd().resolve()
    if not _too_high(here, home) and here in start.parents:
        return here / REGISTRY_NAME
    return start / REGISTRY_NAME


def load_registry(path):
    empty = {"schema": REGISTRY_SCHEMA, "papers": {}}
    if path is None or not Path(path).is_file():
        return empty
    try:
        data = miniyaml.load(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    if not isinstance(data, dict):
        return empty
    papers = data.get("papers")
    data["papers"] = papers if isinstance(papers, dict) else {}
    data.setdefault("schema", REGISTRY_SCHEMA)
    return data


DEFAULT_HEADER = (
    "# 論文登記簿：paper-annotations 靠它知道你讀過哪些論文。\n"
    "# probe.py 會自動登記；可以手改。路徑相對於這個檔案，所以整包 clone 到\n"
    "# 另一台機器仍然成立。\n"
    "#\n"
    "# topics 是分類的詞彙表，先定義才能使用（避免 3D-IC 和 3d-ic 變成兩個分類）。\n"
    "# topic_colors 是各分類的顏色（#rrggbb），沒寫的就用預設樣式。\n"
    "# 每篇論文底下：topics 是你自己定的、topics_auto 是 AI 建議的、\n"
    "# topics_off 是你移除過的（AI 不會再建議）。\n"
)


def _header(path: Path) -> str:
    """Whatever comment block the file already opens with.

    This file is meant to be edited by hand, and the server rewrites it every
    time a topic is added from the shelf. Stamping the canned header back over
    the top would quietly delete whatever the reader wrote to explain his own
    categories -- a comment is the one part of a config nobody expects a
    program to throw away.
    """
    if not path.is_file():
        return DEFAULT_HEADER
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            kept.append(line)
            continue
        break
    text = "\n".join(kept).rstrip("\n")
    return (text + "\n") if text.strip() else DEFAULT_HEADER


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = _header(path)
    path.write_text(
        header + miniyaml.dump(data) + "\n", encoding="utf-8", newline="\n"
    )


def paper_name(paper_root: Path) -> str:
    """The paper's name without the conversion package's suffix."""
    name = paper_root.name
    for suffix in ("_md", "-md"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)] or name
    return name


def _store_path(registry_path: Path, target: Path) -> str:
    """Relative to the registry when possible -- that is what makes it portable."""
    try:
        return target.resolve().relative_to(registry_path.parent.resolve()).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def _resolve_path(registry_path: Path, stored: str) -> Path:
    path = Path(stored)
    return path if path.is_absolute() else (registry_path.parent / path).resolve()


def paper_title(paper_root: Path):
    """(title, year) from manifest.json, falling back to the folder name."""
    manifest = paper_root / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            year = data.get("year")
            return (
                str(data.get("title") or paper_name(paper_root)),
                int(year) if isinstance(year, int) else None,
            )
        except (ValueError, OSError, TypeError):
            pass
    return paper_name(paper_root), None


def register(work_root: Path, paper_root: Path, config: dict):
    """Add or refresh this paper's entry. Returns (registry_path, slug)."""
    path = registry_home(work_root)
    data = load_registry(path)
    papers = data["papers"]
    stored = _store_path(path, work_root)

    # Match on the stored path, not the name: re-probing a paper must update
    # its entry rather than pile up a second one beside it.
    slug = ""
    for key, entry in papers.items():
        if isinstance(entry, dict) and str(entry.get("work") or "") == stored:
            slug = key
            break
    if not slug:
        base = re.sub(r"[^a-z0-9]+", "-", paper_name(paper_root).lower()).strip("-") or "paper"
        slug, n = base, 2
        while slug in papers:
            slug, n = f"{base}-{n}", n + 1

    title, year = paper_title(paper_root)
    previous = papers.get(slug) if isinstance(papers.get(slug), dict) else {}
    papers[slug] = {
        "work": stored,
        "title": title,
        "year": year,
        "tier": config.get("tier"),
        "added": previous.get("added") or date.today().isoformat(),
    }
    data["schema"] = REGISTRY_SCHEMA
    save_registry(path, data)
    return path, slug


def vocabulary(registry_path):
    """slug -> display name. The controlled list of topics.

    Define-before-use, deliberately: without it "3D-IC" and "3d-ic" become two
    categories that look identical on screen, and by the time anyone notices,
    half the papers are filed under each.
    """
    data = load_registry(registry_path)
    raw = data.get("topics")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v or k) for k, v in raw.items()}


def topic_slug(name: str) -> str:
    """A stable key for a display name.

    ASCII names get the usual lowercase-and-dash treatment; anything else --
    "已讀過" -- keeps its own characters, because transliterating it would give
    a key nobody could recognise in the file they are meant to hand-edit.
    """
    text = str(name or "").strip()
    ascii_form = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return ascii_form or re.sub(r"\s+", "-", text)


def define_topic(registry_path: Path, name: str, color: str = ""):
    """Add a category to the vocabulary. Returns (slug, message)."""
    text = str(name or "").strip()
    if not text:
        return "", "分類名稱不能空白"
    slug = topic_slug(text)
    if not slug:
        return "", "這個名稱轉不出可用的代號"
    tint = str(color or "").strip().lower()
    if tint and not COLOR.match(tint):
        return "", "顏色要寫成 #rrggbb"
    data = load_registry(registry_path)
    vocab = data.get("topics")
    if not isinstance(vocab, dict):
        vocab = {}
    already = slug in vocab
    vocab[slug] = vocab.get(slug, text)
    data["topics"] = vocab
    # Only when one was actually asked for: an existing category being defined
    # again must not silently lose the colour it already has.
    if tint:
        _paint(data, slug, tint)
    save_registry(registry_path, data)
    return slug, ("這個分類已經有了" if already else "")


def topic_colors(registry_path):
    """slug -> #rrggbb, for the categories that have been given one.

    A separate table rather than a field inside `topics`, so the vocabulary
    stays the one-line-per-category list it is meant to be read as, and a
    registry written before colours existed keeps loading unchanged.
    """
    data = load_registry(registry_path)
    raw = data.get("topic_colors")
    if not isinstance(raw, dict):
        return {}
    return {
        str(k): str(v).lower()
        for k, v in raw.items()
        if COLOR.match(str(v or ""))
    }


def _paint(data: dict, topic: str, color) -> bool:
    """Set or clear one topic's colour inside an already-loaded registry."""
    text = str(color or "").strip().lower()
    if text and not COLOR.match(text):
        return False
    table = data.get("topic_colors")
    if not isinstance(table, dict):
        table = {}
    if text:
        table[topic] = text
    else:
        table.pop(topic, None)
    if table:
        data["topic_colors"] = table
    else:
        data.pop("topic_colors", None)
    return True


def set_topic_color(registry_path: Path, topic: str, color):
    """Give a category its own colour, or ("") put it back to the default."""
    if topic not in vocabulary(registry_path):
        return False, f"分類 {topic} 還沒有定義"
    if str(color or "").strip() and not COLOR.match(str(color).strip().lower()):
        return False, "顏色要寫成 #rrggbb"
    data = load_registry(registry_path)
    _paint(data, topic, color)
    save_registry(registry_path, data)
    return True, ""


def undefine_topic(registry_path: Path, topic: str):
    """Delete a category outright. Returns (ok, message).

    Refused while any paper is still filed under it: emptying it first is one
    extra click, and it makes deletion incapable of losing anything. Also
    clears the topic out of every topics_off, because a name nobody has heard
    of should not go on suppressing a future suggestion of the same name.
    """
    data = load_registry(registry_path)
    vocab = data.get("topics")
    if not isinstance(vocab, dict) or topic not in vocab:
        return False, f"沒有這個分類：{topic}"
    users = [
        slug
        for slug, entry in (data.get("papers") or {}).items()
        if isinstance(entry, dict)
        and topic in (topics_of(entry)[0] + topics_of(entry)[1])
    ]
    if users:
        return False, f"還有 {len(users)} 篇論文在這個分類裡，先把它們移出去才能刪"
    vocab.pop(topic)
    data["topics"] = vocab
    _paint(data, topic, "")
    for entry in (data.get("papers") or {}).values():
        if not isinstance(entry, dict):
            continue
        left = [t for t in topics_of(entry)[2] if t != topic]
        if left:
            entry["topics_off"] = left
        else:
            entry.pop("topics_off", None)
    save_registry(registry_path, data)
    return True, ""


def set_topic(registry_path: Path, slug: str, topic: str, add: bool):
    """Add or remove one topic for one paper. Returns (ok, message).

    Removing takes it out of both lists and records it in topics_off, so a
    later session does not helpfully suggest it right back.
    """
    data = load_registry(registry_path)
    entry = (data.get("papers") or {}).get(slug)
    if not isinstance(entry, dict):
        return False, f"登記簿裡沒有 {slug}"
    if topic not in vocabulary(registry_path):
        return False, f"分類 {topic} 還沒有定義，請先加進 papers.yml 的 topics"

    mine, auto, off = topics_of(entry)
    if add:
        if topic in mine or topic in auto:
            return True, "已經在這個分類裡了"
        mine.append(topic)
        off = [t for t in off if t != topic]
    else:
        if topic not in mine and topic not in auto:
            return True, "本來就不在這個分類裡"
        mine = [t for t in mine if t != topic]
        auto = [t for t in auto if t != topic]
        if topic not in off:
            off.append(topic)

    for key, value in (("topics", mine), ("topics_auto", auto), ("topics_off", off)):
        if value:
            entry[key] = value
        else:
            entry.pop(key, None)
    save_registry(registry_path, data)
    return True, ""


def entries(registry_path):
    """Every registered paper, paths resolved, dead entries flagged not dropped."""
    if registry_path is None:
        return []
    out = []
    for slug, entry in (load_registry(registry_path).get("papers") or {}).items():
        if not isinstance(entry, dict):
            continue
        work = _resolve_path(registry_path, str(entry.get("work") or ""))
        mine, auto, off = topics_of(entry)
        out.append(
            {
                "slug": slug,
                "work": work,
                "title": str(entry.get("title") or slug),
                "year": entry.get("year"),
                "tier": entry.get("tier"),
                "added": entry.get("added"),
                "topics": mine,
                "topics_auto": auto,
                "topics_off": off,
                # A folder the reader moved is a fact worth saying out loud,
                # not a row to quietly omit.
                "alive": (work / "notes" / "paper.yml").is_file(),
            }
        )
    return out


# --------------------------------------------------------------------------
# per-paper catalog
# --------------------------------------------------------------------------


def _question_of(card) -> str:
    sections = notes.card_sections(card["body"])
    text = sections.get("問題") or sections.get("Question") or ""
    return " ".join(text.split()) or "(未填問題)"


def keywords(paper_root: Path, source_list):
    """The paper's own Index Terms, as printed.

    Raw material for proposing topics, never topics themselves. Two papers
    where one directly succeeds the other were observed to share not one index
    term, so keywords used as categories would give every paper its own bucket
    and say nothing. A useful topic is coarser than a keyword, and getting from
    one to the other is judgement -- which is why it happens in a reading
    session and not in here.
    """
    for rel in source_list:
        path = paper_root / rel
        if not path.is_file():
            continue
        found = INDEX_TERMS.search(path.read_text(encoding="utf-8"))
        if found:
            terms = [t.strip(" .;") for t in found.group(1).split(",")]
            return [t for t in terms if t]
    return []


def topics_of(entry):
    """(mine, agent-suggested, refused) for one registry entry.

    Three lists rather than one with a marker: miniyaml has no sequences of
    mappings, and a magic prefix inside the values would be unreadable in the
    file the reader is meant to be able to edit by hand. `off` exists so a
    topic he removed is not proposed again next session -- a suggestion that
    keeps coming back is worse than no suggestion.
    """
    def names(key):
        raw = entry.get(key)
        return [str(t).strip() for t in raw if str(t or "").strip()] if isinstance(raw, list) else []

    mine = names("topics")
    auto = [t for t in names("topics_auto") if t not in mine]
    return mine, auto, names("topics_off")


def _links_of(meta):
    """The note's declared links, verbatim. Validation belongs to the build."""
    raw = meta.get("links")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item or "").strip()]


def _where_of(meta) -> str:
    anchor = meta.get("anchor") or {}
    heading = anchor.get("heading") or []
    if isinstance(heading, list) and heading:
        return str(heading[-1])
    return Path(str(anchor.get("file") or "")).stem


def write_catalog(notes_dir: Path, paper_root: Path, config: dict, cards, points, review=None) -> Path:
    """A scannable index of one paper's notes, for cross-paper readers.

    Generated, never authoritative: notes/cards/ and notes/points/ remain the
    only sources of truth. It exists so that answering "what has he already
    wondered about?" costs one small file per paper instead of hundreds.
    """
    title, year = paper_title(paper_root)
    catalog = {
        "schema": 1,
        "paper": paper_name(paper_root),
        "title": title,
        "year": year,
        "tier": config.get("tier"),
        "generated": date.today().isoformat(),
        # A snapshot, deliberately: the authority on what is due is the replay
        # of notes/reviews/, and this is only here so the library page can show
        # counts without opening every paper's log.
        "review": review or {"due": 0, "half": 0, "tracked": 0},
        # The paper's own Index Terms: raw material for proposing topics, kept
        # here so a cross-paper reader has it without opening the abstract.
        "keywords": keywords(paper_root, [Path(p) for p in (config.get("sources") or [])]),
        "cards": [
            {
                "id": str(card["meta"].get("id")),
                "status": str(card["meta"].get("status", "open")),
                "origin": str(card["meta"].get("origin", "asked")),
                "tags": [str(t) for t in (card["meta"].get("tags") or [])],
                "question": _question_of(card),
                "where": _where_of(card["meta"]),
                # Kept raw: resolving them here would freeze an answer that
                # depends on which papers are registered right now.
                "links": _links_of(card["meta"]),
            }
            for card in cards
        ],
        "points": [
            {
                "id": str(point["meta"].get("id")),
                "kind": point["kind"],
                "origin": point["origin"],
                "tags": [str(t) for t in (point["meta"].get("tags") or [])],
                "text": point["text"],
                "where": _where_of(point["meta"]),
                "links": _links_of(point["meta"]),
            }
            for point in points
        ],
    }
    path = notes_dir / CATALOG_NAME
    path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def read_catalog(work_root: Path):
    return _read_json(work_root / "notes" / CATALOG_NAME)


# --------------------------------------------------------------------------
# references
# --------------------------------------------------------------------------


def _is_reference_file(rel: Path, text: str) -> bool:
    if "reference" in rel.name.lower():
        return True
    meta, body = notes.read_doc_text(text)
    types = meta.get("content_type") or []
    if isinstance(types, list) and any("reference" in str(t).lower() for t in types):
        return True
    return bool(re.search(r"^#{1,6}\s*references\b", body, re.I | re.M))


def extract_references(paper_root: Path, source_list):
    """The reference list exactly as printed -- no matching, no interpretation.

    Kept raw on purpose: the registry it would be matched against changes every
    time another paper is added, so a match recorded here would be stale the
    moment it was useful.
    """
    refs = []
    for rel in source_list:
        path = paper_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not _is_reference_file(rel, text):
            continue
        for line in text.splitlines():
            match = REF_LINE.match(line.strip())
            if not match:
                continue
            body = match.group(2).strip()
            found = REF_TITLE.search(body)
            years = YEAR.findall(body)
            refs.append(
                {
                    "n": int(match.group(1)),
                    "title": found.group(1).strip().rstrip(",.;") if found else "",
                    "year": int(years[-1]) if years else None,
                    "text": " ".join(body.split()),
                }
            )
    refs.sort(key=lambda r: r["n"])
    return refs


def write_references(notes_dir: Path, refs) -> Path:
    path = notes_dir / REFS_NAME
    path.write_text(
        json.dumps({"schema": 1, "references": refs}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_references(work_root: Path):
    data = _read_json(work_root / "notes" / REFS_NAME)
    if not isinstance(data, dict):
        return []
    refs = data.get("references")
    return refs if isinstance(refs, list) else []


def _norm_title(text) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def titles_match(a, b) -> bool:
    """Same paper, by title. Containment, never a fuzzy score.

    A citation keeps or drops a subtitle depending on the venue's house style,
    so exact equality alone misses real matches. Containment with a floor is
    the smallest relaxation that stays a fact: twenty-four characters of exact
    agreement between two paper titles is not a coincidence. Anything looser
    would start inventing edges, and a wrong edge is worse than a missing one.
    """
    first, second = _norm_title(a), _norm_title(b)
    if not first or not second:
        return False
    if first == second:
        return True
    short, long = sorted((first, second), key=len)
    return len(short) >= 24 and short in long


def citation_context(paper_root: Path, source_list, number: int, limit: int = 2):
    """Where in the body a reference number is actually used.

    The sentence around a citation usually describes the relationship better
    than anything inferred afterwards -- "we adopt the … of [29] but replace …"
    simply says it.
    """
    pattern = re.compile(r"\[%d\]" % number)
    hits = []
    for rel in source_list:
        path = paper_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _is_reference_file(rel, text):
            continue
        for line in text.splitlines():
            match = pattern.search(line)
            if not match:
                continue
            # A window around the citation, not the head of the paragraph: the
            # useful sentence is the one containing the bracket, and a long
            # paragraph would otherwise be truncated before reaching it.
            flat = " ".join(line.split())
            at = flat.find(match.group(0))
            start = max(0, at - 110)
            end = min(len(flat), at + 130)
            hits.append(
                {
                    "file": rel.as_posix(),
                    "text": ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else ""),
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def citation_edges(papers):
    """Which registered paper cites which, matched on title at read time.

    `papers` is the output of entries(); each gets "cites", a list of
    {slug, n, title} naming the other registered papers it references.
    """
    edges = []
    for paper in papers:
        if not paper["alive"]:
            continue
        refs = read_references(paper["work"])
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get("title"):
                continue
            for other in papers:
                if other["slug"] == paper["slug"]:
                    continue
                if titles_match(ref["title"], other["title"]):
                    edges.append(
                        {
                            "from": paper["slug"],
                            "to": other["slug"],
                            "n": ref.get("n"),
                            "title": ref.get("title"),
                        }
                    )
    return edges


# --------------------------------------------------------------------------
# the view an agent reads at the start of a session
# --------------------------------------------------------------------------


def survey(start: Path):
    registry = find_registry(start)
    papers = entries(registry)
    for paper in papers:
        paper["catalog"] = read_catalog(paper["work"]) if paper["alive"] else None
    return registry, papers, citation_edges(papers)


def _counts(catalog):
    tally = {"open": 0, "half": 0, "resolved": 0}
    for card in (catalog or {}).get("cards") or []:
        key = str(card.get("status") or "open")
        tally[key] = tally.get(key, 0) + 1
    return tally


def main(argv):
    args = cli.positionals(argv)
    start = Path(args[0] if args else ".").resolve()
    registry, papers, edges = survey(start)

    if "--json" in argv:
        print(
            json.dumps(
                {
                    "registry": str(registry) if registry else None,
                    "papers": [
                        {k: (str(v) if isinstance(v, Path) else v) for k, v in p.items()}
                        for p in papers
                    ],
                    "citations": edges,
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0

    if registry is None:
        print(f"還沒有論文登記簿。從 {start} 往上找不到 {REGISTRY_NAME}。")
        print(f"對任何一篇論文執行 probe.py 就會建立一份（預設放在 {registry_home(start)}）。")
        return 0

    print(f"論文庫  {registry}  共 {len(papers)} 篇")
    for paper in papers:
        if not paper["alive"]:
            print(f"\n⚠️  {paper['slug']} — 登記的位置找不到筆記：{paper['work']}")
            print("     資料夾可能搬走了。改 papers.yml 裡的 work，或重跑 probe.py。")
            continue
        catalog = paper["catalog"]
        head = f"\n{paper['slug']}  {paper['title']}"
        bits = [b for b in (f"Tier {paper['tier']}" if paper["tier"] else "",
                            str(paper["year"] or "")) if b]
        print(head)
        print(f"  {' · '.join(bits + [str(paper['work'])])}")
        if catalog is None:
            print("  （還沒有 catalog.json，跑一次 build_annotated.py 就會產生）")
            continue
        tally = _counts(catalog)
        cards = catalog.get("cards") or []
        points = catalog.get("points") or []
        print(
            f"  疑問 {len(cards)} 則（未解決 {tally.get('open', 0)} ·"
            f" 半懂 {tally.get('half', 0)} · 已解決 {tally.get('resolved', 0)}）"
            f" · 要點 {len(points)} 則"
        )
        review = catalog.get("review") or {}
        if review.get("tracked") or review.get("due"):
            print(
                f"  複習 排程 {review.get('tracked', 0)} 張，"
                f"上次建置時到期 {review.get('due', 0)} 張"
            )
        shown = [f"{t}" for t in paper["topics"]] + [f"{t}（建議）" for t in paper["topics_auto"]]
        print("  分類 " + ("、".join(shown) if shown else "未分類"))
        if catalog.get("keywords"):
            print("  關鍵字 " + "、".join(catalog["keywords"]))
        for card in cards:
            flag = " 💡" if card.get("origin") == "suggested" else ""
            tags = ", ".join(card.get("tags") or [])
            print(
                f"    Q{card.get('id')}{flag} [{card.get('status')}] {card.get('question')}"
                + (f"  ({tags})" if tags else "")
            )
        for point in points:
            label = notes.KIND_LABEL.get(point.get("kind"), point.get("kind"))
            print(f"    ·{label} {point.get('text')}")

    print("\n引用關係（由參考文獻標題比對，機械判定）")
    if not edges:
        print("  這些論文之間沒有互相引用，或參考文獻還沒抽出來。")
    for edge in edges:
        print(f"  {edge['from']} [{edge['n']}] → {edge['to']}")
        source = next((p for p in papers if p["slug"] == edge["from"]), None)
        if source is None:
            continue
        config_path = source["work"] / "notes" / "paper.yml"
        try:
            config = miniyaml.load(config_path.read_text(encoding="utf-8"))
            paper_root = (source["work"] / str(config.get("paper_root") or ".")).resolve()
            source_list = [Path(p) for p in (config.get("sources") or [])]
        except (OSError, ValueError):
            continue
        for hit in citation_context(paper_root, source_list, int(edge["n"])):
            print(f"      {hit['file']}")
            print(f"      「{hit['text']}」")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
