"""A translation beside the paper, one paragraph against one paragraph.

The unit is a block of the source section -- a paragraph, a whole list, a
blockquote -- exactly as minimd renders it, so a block of translation can sit
in the same row as the block it translates and the two columns scroll as one.
Headings, display formulas, tables and figures are not translated; they span
or stay on the paper's side.

Each block is named by a fingerprint of its own text, not by its position:

    <!-- p:3f9a1c2b4d -->
    在這篇論文中，我們……

so inserting a paragraph upstream does not shift every name below it. When the
source text of a block changes, its fingerprint changes and the old
translation no longer matches anything -- it is then shown as 待更新 in the
same place, found by its neighbours (``align``). That is the only thing that
makes a translation stale: a change to the paper. A change to the glossary does
not; re-translating after one is the reader's call (docs/adr/0008).

Translations are written by an agent, never by the tool. ``--todo`` lists what
is missing in the form ``--put`` accepts back; ``--put`` checks each block and
files it under notes/translations/<section>.md, one file per section, which is
also the file a highlight on the translation is anchored to.

Usage:
    python translate.py <work>                     # 每一節翻了多少
    python translate.py <work> --todo [S130 S200]  # 列出還沒翻、待更新的段落
    python translate.py <work> --put <檔案>        # 收下譯文（也可從 stdin）
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from collections import Counter
from pathlib import Path

from . import atomic, cli, library, links, minimd, miniyaml, notes, workspace

DIRNAME = "translations"
# A section's translation is its own highlight zone. The page names it by the
# section's id plus this, so a mark drawn on it never resolves against the
# English beside it.
LAYER = "~tr"

_MARKER = re.compile(r"^<!--\s*p:([0-9a-f]{6,20})\s*-->\s*$")
# What --todo prints around a block for the agent's benefit; --put drops it.
_ASIDE = re.compile(r"<!--\s*(?:原文|舊譯文)[\s\S]*?-->")
_BARE_IMAGE = re.compile(r"^!\[[^\]]*\]\([^)]*\)$")
# --todo's file headings ("## sections/S130-….md") end a block too
_FILE_HEAD = re.compile(r"^##\s+\S+\.md\s*$")

HEADER = (
    "<!-- paper-annotations 譯文。原文：{source}\n"
    "     每段前面的 p: 是原文那一段的指紋，原文改了這段就會標成待更新。\n"
    "     要改譯文直接改這裡的字；指紋那一行不要動。 -->\n"
)


# ---- blocks -------------------------------------------------------------

def canonical(raw: str) -> str:
    """The block's text with everything the build adds or moves taken out.

    The page renders annotated/, where a card's sentence is wrapped in
    ==…==<!--Q:id--> and every link is rebased; the source has neither. Both
    must come out the same here or the page could never find its translation.
    """
    text = re.sub(r"<!--Q:[^>]*-->", "", raw).replace("==", "")
    text = re.sub(r"(!?\[[^\]]*\])\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def key(raw: str) -> str:
    return hashlib.sha1(canonical(raw).encode("utf-8")).hexdigest()[:10]


def translatable(raw: str) -> bool:
    return bool(canonical(raw)) and not _BARE_IMAGE.match(raw.strip())


def blocks(text: str):
    """[(key, raw)] for one section's Markdown, in reading order."""
    text = notes.FRONTMATTER_RE.sub("", text, count=1)
    text = "\n".join(links.normalize_ref_links(text.splitlines()))
    found = []

    def hook(raw, out):
        if translatable(raw):
            found.append((key(raw), raw.strip()))
        return out

    minimd.render(text, block_hook=hook)
    return found


def source_blocks(paper_root: Path, rel) -> list:
    src = paper_root / rel
    if not src.is_file():
        return []
    text = src.read_text(encoding="utf-8")
    # A reference list is names and venues: nothing to translate, and counting
    # its fifty entries would make every paper look a third untranslated.
    head = notes.FRONTMATTER_RE.match(text)
    if head:
        kinds = (miniyaml.load(head.group(1)) or {}).get("content_type") or []
        if "reference" in (kinds if isinstance(kinds, list) else [kinds]):
            return []
    return blocks(text)


# ---- files --------------------------------------------------------------

def tr_path(notes_dir: Path, rel) -> Path:
    return notes_dir / DIRNAME / (Path(rel).stem + ".md")


def mark_file(paper_root: Path, notes_dir: Path, rel) -> str:
    """The translation file as a mark names it: relative to the paper, like
    sections/… is, so notes/marks/ treats both the same way."""
    return Path(os.path.relpath(tr_path(notes_dir, rel), paper_root)).as_posix()


def is_tr_file(rel: str) -> bool:
    return Path(rel).parent.name == DIRNAME


def parse(text: str):
    """[(key, body)] in file order. Anything before the first marker is the
    header; a body runs until the next marker."""
    entries, cur, buf = [], None, []

    def flush():
        if cur is not None:
            body = _ASIDE.sub("", "\n".join(buf)).strip()
            if body:
                entries.append((cur, body))

    for line in text.splitlines():
        match = _MARKER.match(line.strip())
        if match:
            flush()
            cur, buf = match.group(1), []
        elif _FILE_HEAD.match(line.strip()):
            flush()
            cur, buf = None, []
        elif cur is not None:
            buf.append(line)
    flush()
    return entries


def read_entries(notes_dir: Path, rel):
    path = tr_path(notes_dir, rel)
    if not path.is_file():
        return []
    return parse(path.read_text(encoding="utf-8"))


def write_entries(notes_dir: Path, rel, entries) -> Path:
    path = tr_path(notes_dir, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"\n<!-- p:{k} -->\n{t.strip()}\n" for k, t in entries)
    # swapped in whole: a write that fails halfway must not leave the reader's
    # translation truncated
    atomic.write_text(path, HEADER.format(source=Path(rel).as_posix()) + body)
    return path


# ---- alignment ----------------------------------------------------------

def align(src_keys, entries):
    """What each source block has: ("ok", text), ("stale", text, old key) or
    None -- plus the entries that belong nowhere.

    A stale translation is one whose fingerprint matches no block any more.
    It is put back where it was by its neighbours: between two blocks that do
    still match, if as many blocks lost their translation as there are
    unmatched entries, they pair up in order. Anything less certain stays an
    orphan, reported and kept, rather than shown beside the wrong paragraph.
    """
    have, at = {}, {}
    for j, (k, text) in enumerate(entries):
        if k not in have:
            have[k], at[k] = text, j
    wanted = set(src_keys)
    result = [("ok", have[k]) if k in have else None for k in src_keys]

    anchors_ = [(-1, -1)]
    last = -1
    for i, k in enumerate(src_keys):
        if k in at and at[k] > last:
            anchors_.append((i, at[k]))
            last = at[k]
    anchors_.append((len(src_keys), len(entries)))

    paired = set()
    for (i0, j0), (i1, j1) in zip(anchors_, anchors_[1:]):
        gap_src = [i for i in range(i0 + 1, i1) if result[i] is None]
        gap_tr = [j for j in range(j0 + 1, j1) if entries[j][0] not in wanted]
        if gap_src and len(gap_src) == len(gap_tr):
            for i, j in zip(gap_src, gap_tr):
                result[i] = ("stale", entries[j][1], entries[j][0])
                paired.add(j)
    orphans = [entries[j] for j in range(len(entries))
               if entries[j][0] not in wanted and j not in paired]
    return result, orphans


def section(paper_root: Path, notes_dir: Path, rel) -> dict:
    src = source_blocks(paper_root, rel)
    entries = read_entries(notes_dir, rel)
    state, orphans = align([k for k, _ in src], entries)
    return {"rel": Path(rel).as_posix(), "blocks": src, "state": state,
            "orphans": orphans, "entries": entries}


def survey(work: Path):
    config, paper_root, notes_dir, _ = workspace.load_workspace(work)
    return paper_root, notes_dir, [
        section(paper_root, notes_dir, rel) for rel in (config.get("sources") or [])
    ]


def counts(sec: dict) -> dict:
    out = Counter(s[0] if s else "none" for s in sec["state"])
    return {"total": len(sec["state"]), "ok": out["ok"], "stale": out["stale"],
            "none": out["none"], "orphans": len(sec["orphans"])}


# ---- the page -----------------------------------------------------------

class PageLayer:
    """Translation cells for build_html, one paper at a time.

    The renderer leaves a numbered marker just inside each block's closing
    tag; ``place`` swaps every marker for the closing tag plus that block's
    cell once the page's own transforms are done. Inside the tag, so the
    algorithm and figure patterns -- which expect a block to be followed
    directly by the next one -- still see what they always saw.
    """

    def __init__(self, work: Path):
        self.paper_root, self.notes_dir, sections = survey(work)
        self.by_rel = {s["rel"]: s for s in sections}
        self.cells = []
        self.total = Counter()
        for sec in sections:
            self.total.update(counts(sec))
        # No translation anywhere: the page is exactly the page it was.
        self.active = any(s["entries"] for s in sections)

    def file_for(self, rel) -> str:
        return mark_file(self.paper_root, self.notes_dir, rel)

    def hook(self, rel):
        sec = self.by_rel.get(Path(rel).as_posix())
        if not self.active or not sec or not sec["blocks"]:
            return None
        by_key = {}
        for (k, _), state in zip(sec["blocks"], sec["state"]):
            by_key.setdefault(k, state)
        empty = not sec["entries"]
        first = [True]

        def tag(raw, out):
            k = key(raw)
            if k not in by_key or not translatable(raw):
                return out
            state = by_key[k]
            if state is None:
                # a section with nothing translated says so once, not per block
                cls = " none" + ((" first" if first[0] else " quiet") if empty else "")
                cell = f'<div class="trc{cls}" data-p="{k}"></div>'
                first[0] = False
            else:
                inner, _ = minimd.render(state[1])
                # the paper's footnote link already owns that id
                inner = re.sub(r' id="fnref-[^"]*"', "", inner)
                tagline = ""
                if state[0] == "stale":
                    tagline = ('<div class="trtag" title="原文這一段改過，譯文還是舊的">'
                               "待更新</div>")
                cls = " stale" if state[0] == "stale" else ""
                cell = f'<div class="trc{cls}" data-p="{k}">{tagline}{inner}</div>'
            self.cells.append(cell)
            cut = out.rfind("</")
            return f"{out[:cut]}<!--tr:{len(self.cells) - 1}-->{out[cut:]}"

        return tag

    def place(self, page: str) -> str:
        return re.sub(
            r"<!--tr:(\d+)-->(</[a-z0-9]+>)",
            lambda m: m.group(2) + "\n" + self.cells[int(m.group(1))],
            page,
        )

    def summary(self) -> str:
        t = self.total
        if not t["total"]:
            return ""
        msg = f"已翻 {t['ok']} / {t['total']} 段"
        if t["stale"]:
            msg += f"，待更新 {t['stale']} 段"
        return msg


# ---- checks -------------------------------------------------------------

_MATH = re.compile(r"\$\$[\s\S]+?\$\$|(?<!\$)\$[^$\n]+?\$(?!\$)")
_CITE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
_NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def _bag(pattern, text):
    return Counter(re.sub(r"\s+", "", m) for m in pattern.findall(text))


def check(raw: str, text: str):
    """(errors, warnings) for one translated block.

    Formulas and citation numbers must come through untouched -- a formula is
    the paper's claim, and the page renders both sides with the same KaTeX, so
    a dropped $ shows up as broken math. Plain numbers only warn: 「兩個」 for
    "two" is fine, and so, sometimes, is a reworded figure.
    """
    errors, warnings = [], []
    lost = _bag(_MATH, raw) - _bag(_MATH, text)
    extra = _bag(_MATH, text) - _bag(_MATH, raw)
    if lost or extra:
        errors.append("公式和原文不一致：" + "、".join(list(lost or extra)[:3]))
    if _bag(_CITE, raw) != _bag(_CITE, text):
        errors.append("引用編號和原文不一致")
    plain = lambda s: _MATH.sub("", s)
    missing = _bag(_NUM, plain(raw)) - _bag(_NUM, plain(text))
    if missing:
        warnings.append("原文的數字沒出現在譯文裡：" + "、".join(list(missing)[:4]))
    if re.search(r"<[a-zA-Z/][^>]*>", _MATH.sub("", text)):
        errors.append("譯文裡有 HTML 標籤")
    return errors, warnings


# ---- glossary and preferences -------------------------------------------
#
# Two files, at two levels: TERMS.md and LANGUAGES.md beside papers.yml are the
# shelf's, shared by every paper; the same names in a paper's own folder override
# them, a term at a time. They are read by the agent that translates, never
# applied by the tool -- and changing them does not make a translation stale
# (docs/adr/0008). The page edits them through the server, which is why every
# write carries the revision it was made against.

DEFAULT = Path(__file__).resolve().parent / "LANGUAGES.default.md"
SCOPES = ("shelf", "paper")
SCOPE_LABEL = {"shelf": "書房共用", "paper": "這篇論文"}
TERMS_HEAD = ("# 術語表\n\n翻譯時照這張表決定每個術語怎麼寫。"
              "論文資料夾裡的同名檔案逐條覆寫書房的。\n\n")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def folders(work: Path) -> dict:
    """{scope: folder}. The paper's is the folder its page sits in, beside the
    PDF; the shelf's is the one holding papers.yml, when there is one and it is
    not the same folder."""
    _, _, _, annotated = workspace.load_workspace(work)
    out = {"paper": annotated.parent}
    registry = library.find_registry(work)
    if registry is not None and registry.parent.resolve() != annotated.parent.resolve():
        out["shelf"] = registry.parent
    return out


def revision(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12] if path.is_file() else ""


def parse_terms(text: str):
    """(rows, intro). Rows from the first pipe table: 原文, 譯法, 備註.

    Whatever is not the table -- a heading, a paragraph he wrote -- is kept as
    the intro and written back untouched.
    """
    rows, intro, seen_table = [], [], False
    for line in text.splitlines():
        if _TABLE_ROW.match(line):
            seen_table = True
            if _TABLE_SEP.match(line):
                continue
            cells = [c.strip().replace("\\|", "|")
                     for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            cells += [""] * (3 - len(cells))
            if cells[0] in ("原文", "術語", "term", "Term"):
                continue
            if cells[0]:
                rows.append({"term": cells[0], "use": cells[1], "note": cells[2]})
        elif not seen_table:
            intro.append(line)
    return rows, "\n".join(intro).strip()


def render_terms(rows, intro: str) -> str:
    def cell(s):
        return s.replace("|", "\\|")
    body = "".join(f"| {cell(r['term'])} | {cell(r['use'])} | {cell(r['note'])} |\n"
                   for r in rows)
    head = (intro.strip() + "\n\n") if intro.strip() else TERMS_HEAD
    return head + "| 原文 | 譯法 | 備註 |\n|---|---|---|\n" + body


def _write(path: Path, text: str) -> None:
    atomic.write_text(path, text)


def settings(work: Path) -> dict:
    """Everything the 譯文設定 panel shows: both levels of both files, the
    built-in defaults, and how far the translation has got."""
    paper_root, notes_dir, sections = survey(work)
    scopes = []
    for scope, folder in folders(work).items():
        terms_path, lang_path = folder / "TERMS.md", folder / "LANGUAGES.md"
        rows, _ = parse_terms(terms_path.read_text(encoding="utf-8")) if terms_path.is_file() else ([], "")
        scopes.append({
            "scope": scope, "label": SCOPE_LABEL[scope],
            "terms": {"path": str(terms_path), "rev": revision(terms_path), "rows": rows},
            "languages": {"path": str(lang_path), "rev": revision(lang_path),
                          "text": lang_path.read_text(encoding="utf-8") if lang_path.is_file() else ""},
        })
    scopes.sort(key=lambda s: SCOPES.index(s["scope"]))
    return {
        "scopes": scopes,
        "default": DEFAULT.read_text(encoding="utf-8") if DEFAULT.is_file() else "",
        "sections": [dict(id=Path(s["rel"]).stem, **counts(s)) for s in sections if s["blocks"]],
        "work": str(work),
    }


def _target(work: Path, scope: str, name: str) -> Path:
    where = folders(work)
    if scope not in where:
        raise ValueError("這篇論文不在書房裡，沒有書房共用的設定" if scope == "shelf" else "未知的範圍")
    return where[scope] / name


def _check_rev(path: Path, rev) -> None:
    if (rev or "") != revision(path):
        raise ValueError(f"{path.name} 在別的地方改過了，重新打開設定再改一次")


def save_terms(work: Path, scope: str, rows, rev) -> dict:
    path = _target(work, scope, "TERMS.md")
    _check_rev(path, rev)
    if not isinstance(rows, list):
        raise ValueError("術語表格式不對")
    clean, seen = [], {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("術語表格式不對")
        r = {k: str(row.get(k) or "").strip() for k in ("term", "use", "note")}
        if any("\n" in v for v in r.values()):
            raise ValueError("術語表的格子裡不能換行")
        if not r["term"]:
            continue
        if not r["use"]:
            raise ValueError(f"「{r['term']}」還沒填譯法")
        key = r["term"].casefold()
        if key in seen:
            raise ValueError(f"「{r['term']}」在這張表裡出現兩次")
        seen[key] = True
        clean.append(r)
    if not clean and not path.is_file():
        return settings(work)
    _, intro = parse_terms(path.read_text(encoding="utf-8")) if path.is_file() else ([], "")
    _write(path, render_terms(clean, intro))
    return settings(work)


def save_languages(work: Path, scope: str, text, rev) -> dict:
    path = _target(work, scope, "LANGUAGES.md")
    _check_rev(path, rev)
    if not isinstance(text, str) or len(text) > 50000:
        raise ValueError("語言偏好格式不對")
    if not text.strip() and not path.is_file():
        return settings(work)
    _write(path, text.strip() + "\n" if text.strip() else "")
    return settings(work)


def guides(work: Path):
    """What the translating agent reads first, nearest last."""
    out = [DEFAULT] if DEFAULT.is_file() else []
    for scope, folder in sorted(folders(work).items(), key=lambda kv: SCOPES.index(kv[0])):
        for name in ("TERMS.md", "LANGUAGES.md"):
            if (folder / name).is_file():
                out.append(folder / name)
    return out


# ---- command line ----------------------------------------------------------

def pick(sections, wanted):
    if not wanted:
        return sections
    return [s for s in sections
            if any(Path(s["rel"]).stem.lower().startswith(w.lower()) for w in wanted)]


def status(work: Path) -> int:
    paper_root, notes_dir, sections = survey(work)
    total = Counter()
    print(f"{'章節':<46} 已翻  待更新  未翻")
    for sec in sections:
        c = counts(sec)
        total.update(c)
        if not c["total"]:
            continue
        flag = f"  🟡 {c['orphans']} 段譯文對不到原文" if c["orphans"] else ""
        print(f"{Path(sec['rel']).stem[:46]:<46} {c['ok']:>4} {c['stale']:>6} {c['none']:>5}{flag}")
    print(f"合計：{total['total']} 段，已翻 {total['ok']}、待更新 {total['stale']}、"
          f"未翻 {total['none']}")
    if total["orphans"]:
        print(f"  🟡 {total['orphans']} 段譯文找不到對應的原文段落，保留在檔案最後，"
              "可以手動刪掉")
    print(f"譯文在 {notes_dir / DIRNAME}")
    return 0


def todo(work: Path, wanted) -> int:
    paper_root, notes_dir, sections = survey(work)
    chosen = pick(sections, wanted)
    if wanted and not chosen:
        print(f"沒有章節以 {'、'.join(wanted)} 開頭")
        return 1
    rows = []
    for sec in chosen:
        for (k, raw), state in zip(sec["blocks"], sec["state"]):
            if state is None or state[0] == "stale":
                rows.append((sec["rel"], k, raw, state))
    if not rows:
        print("這些章節都已經翻好了，沒有待更新的段落。")
        return 0
    stale = sum(1 for r in rows if r[3])
    print(f"# 待翻譯 {len(rows)} 段（未翻 {len(rows) - stale}、待更新 {stale}）")
    for path in guides(work):
        print(f"# 先讀：{path}")
    print("# 在每個 p: 底下寫譯文，原文那段註解可以留著；寫好後整份交給")
    print(f"#   python translate.py \"{work}\" --put <檔案>")
    last = None
    for rel, k, raw, state in rows:
        if rel != last:
            print(f"\n## {rel}")
            last = rel
        print(f"\n<!-- p:{k} -->\n<!-- 原文\n{raw}\n-->")
        if state:
            print(f"<!-- 舊譯文（原文改過）\n{state[1]}\n-->")
    return 0


def put(work: Path, text: str) -> int:
    paper_root, notes_dir, sections = survey(work)
    given = parse(text)
    if not given:
        print("讀不到任何 <!-- p:… --> 段落。")
        return 1
    where = {}
    for sec in sections:
        for k, raw in sec["blocks"]:
            where.setdefault(k, []).append((sec, raw))

    accepted, bad, unknown = {}, 0, []
    for k, body in given:
        if k not in where:
            unknown.append(k)
            continue
        errors, warnings = check(where[k][0][1], body)
        label = f"{Path(where[k][0][0]['rel']).stem[:24]} p:{k}"
        for why in errors:
            print(f"  🔴 {label}：{why}")
        for why in warnings:
            print(f"  🟡 {label}：{why}")
        if errors:
            bad += 1
            continue
        accepted[k] = body

    touched = []
    for sec in sections:
        if not any(k in accepted for k, _ in sec["blocks"]):
            continue
        out, seen = [], set()
        for (k, _), state in zip(sec["blocks"], sec["state"]):
            if k in seen:
                continue
            seen.add(k)
            if k in accepted:
                out.append((k, accepted[k]))
            elif state and state[0] == "ok":
                out.append((k, state[1]))
            elif state:
                out.append((state[2], state[1]))  # still stale, kept in place
        out += sec["orphans"]
        write_entries(notes_dir, sec["rel"], out)
        touched.append(Path(sec["rel"]).stem)

    for k in unknown:
        print(f"  🔴 p:{k} 對不到任何原文段落（原文改過？重新跑 --todo）")
    print(f"譯文收下 {len(accepted)} 段、退回 {bad + len(unknown)} 段，"
          f"寫進 {len(touched)} 個檔案")
    if touched:
        print("  接著跑 build_html.py 重建這一頁")
    return 0 if not (bad or unknown) else 1


def main(argv) -> int:
    cli.bootstrap()
    args = cli.positionals(argv, value_flags={"--put"})
    work = Path(args[0] if args else ".").resolve()
    if "--todo" in argv:
        return todo(work, args[1:])
    if "--put" in argv:
        src = cli.flag(argv, "put")
        # bytes, decoded here: a Windows console hands stdin over in its own
        # codepage, which turns every Chinese character into a surrogate
        raw = Path(src).read_bytes() if src else sys.stdin.buffer.read()
        text = raw.decode("utf-8-sig", errors="replace")
        return put(work, text)
    return status(work)

