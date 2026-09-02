"""Section checkpoints: answer once before reading on.

What the reader asked for was "a summary of every section, and being forced to
answer questions until I get them right, ending with the conclusions so far".
Three parts of that are deliberately not built the way it was asked, and the
reasons are the whole design:

  * **No separate section summaries.** This tool refuses to write paper
    summaries (references/digests.md); anything general enough to summarise a
    paper is done better by a general tool. But the points ARE the section's
    skeleton -- so 「這一節的結論」 is that section's points, and 「到目前為止的
    總結」 is the points of every section already passed, stacked up. They stay
    covered until the checkpoint is answered, or the answer is sitting on screen
    while the question is asked.
  * **Not "until you get it right" -- twice.** There is no model on this page.
    The only judge of whether he answered is him, exactly as with grading. A
    third identical prompt is not a third attempt, it is a button to click
    through. So the second attempt swaps in a differently-worded hint, and a
    second miss stops asking and becomes a `origin: suggested` card instead --
    the review loop is where "until you know it" belongs, and that loop already
    exists.
  * **It never blocks reading.** A checkpoint sits in the text at the end of its
    section and can be skipped; skipping is a visible state in the contents, not
    a silent pass.

The questions are notes like any other, hand-editable, one file each. The
answers are an append-only log per checkpoint, replayed rather than stored --
the same discipline as review history (docs/adr/0003), because what he wrote
and whether he got it cannot be regenerated either.

    notes/checks/0001-why-remove-dc.md      the question
    notes/checks/answers/0001.md            what happened, append-only
"""

from __future__ import annotations

import re
from pathlib import Path

from . import miniyaml, notes

# Attempts before a checkpoint gives up and becomes a card. Two, not three:
# see the module docstring.
MAX_TRIES = 2
# Below this many points, a paper's checkpoints would be quizzing the reader on
# a skeleton that is not there yet. Better to have none (roadmap item 10).
MIN_POINTS = 6

VERDICTS = ("pass", "miss", "skip")
LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\w+)(?:\s+(\w+))?\s*$")

QUESTION_HEADING = "問題"
HINT_HEADING = "提示"


def load_checks(notes_dir: Path, problems=None):
    """Load the checkpoints, reporting the ones that cannot be used.

    Same refuse-to-lose rule as every other loader here: a checkpoint that
    silently disappears looks exactly like one that was never written.
    """
    out = []
    checks_dir = notes_dir / "checks"
    if not checks_dir.is_dir():
        return out

    def complain(path, message):
        if problems is not None:
            problems.append((path, message))

    for path in sorted(checks_dir.glob("*.md")):
        meta, body = notes.read_doc(path)
        if not isinstance(meta, dict) or not meta:
            complain(path, "檔案開頭讀不到 --- YAML 區塊，這個檢查點沒有被使用")
            continue
        meta.setdefault("id", path.stem.split("-")[0])
        section = str(meta.get("section") or "")
        if not section:
            complain(path, "沒有 section 欄位，不知道這個檢查點長在哪一節結尾")
            continue
        parts = notes.card_sections(body)
        question = " ".join(parts.get(QUESTION_HEADING, "").split())
        if not question:
            complain(path, f"沒有寫「## {QUESTION_HEADING}」，檢查點會是一個空問題")
            continue
        out.append({
            "path": path,
            "meta": meta,
            "id": str(meta.get("id")),
            "section": section,
            "target": str(meta.get("target") or ""),
            "question": question,
            "hint": " ".join(parts.get(HINT_HEADING, "").split()),
        })

    seen = {}
    for check in out:
        if check["id"] in seen:
            complain(check["path"], f"編號 {check['id']} 和 {seen[check['id']].name} 重複")
        else:
            seen[check["id"]] = check["path"]
    by_section = {}
    for check in out:
        by_section.setdefault(check["section"], []).append(check)
    for section, group in by_section.items():
        if len(group) > 1:
            for check in group[1:]:
                complain(check["path"],
                         f"這一節（{section}）已經有檢查點 {group[0]['id']} 了，一節只放一個")
    return out


def log_path(notes_dir: Path, check_id: str) -> Path:
    return notes_dir / "checks" / "answers" / f"{check_id}.md"


def read_log(notes_dir: Path, check_id: str):
    """Every attempt at this checkpoint, oldest first, as (date, verdict, card)."""
    path = log_path(notes_dir, check_id)
    if not path.is_file():
        return []
    _, body = notes.read_doc(path)
    out = []
    for line in body.splitlines():
        match = LINE.match(line.strip())
        if match and match.group(2) in VERDICTS:
            out.append((match.group(1), match.group(2), match.group(3) or ""))
    return out


def append(notes_dir: Path, check_id: str, verdict: str, today: str, card: str = "") -> Path:
    """Add one attempt. Append-only: nothing here ever rewrites a past line."""
    if verdict not in VERDICTS:
        raise ValueError(verdict)
    line = f"{today} {verdict}" + (f" {card}" if card else "")
    path = log_path(notes_dir, check_id)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'---\ncheck: "{check_id}"\n---\n\n{line}\n', encoding="utf-8", newline="\n"
        )
        return path
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + line + "\n", encoding="utf-8", newline="\n")
    return path


def state(entries):
    """Replay the log into one of five states, never stored anywhere.

    Order matters: getting there in the end beats how it went on the way, and a
    checkpoint that already became a card must never start asking again.
    """
    verdicts = [v for _, v, _ in entries]
    if "pass" in verdicts:
        return "pass"
    if any(card for _, _, card in entries):
        return "card"
    misses = verdicts.count("miss")
    if misses >= MAX_TRIES:
        return "card"
    if verdicts and verdicts[-1] == "skip":
        return "skip"
    if misses:
        return "again"
    return "todo"


def card_of(entries) -> str:
    for _, _, card in entries:
        if card:
            return card
    return ""


def tally(notes_dir: Path, checks):
    """Where every checkpoint stands right now, plus the counts for one line."""
    rows, counts = [], {"todo": 0, "again": 0, "pass": 0, "skip": 0, "card": 0}
    for check in checks:
        entries = read_log(notes_dir, check["id"])
        st = state(entries)
        counts[st] = counts.get(st, 0) + 1
        rows.append({
            "id": check["id"],
            "section": check["section"],
            "target": check["target"],
            "question": check["question"],
            "hint": check["hint"],
            "state": st,
            "tries": sum(1 for _, v, _ in entries if v in ("pass", "miss")),
            "card": card_of(entries),
        })
    return rows, counts


def next_card_id(notes_dir: Path) -> str:
    used = set()
    cards_dir = notes_dir / "cards"
    if cards_dir.is_dir():
        for path in cards_dir.glob("*.md"):
            used.add(path.stem.split("-")[0])
    num = 1
    while f"{num:04d}" in used:
        num += 1
    return f"{num:04d}"


def make_card(notes_dir: Path, check, point, answers, today: str):
    """Turn a twice-missed checkpoint into a suggested card.

    The one place anything creates a card file. It is written from a fixed
    template plus his own two attempts, with an id generated here and an anchor
    copied from the point the question was about -- so nothing in the request
    reaches the filesystem, and the card lands beside the same sentence (see
    docs/adr/0005).

    Returns (card_id, path) or (None, why).
    """
    if not point:
        return None, "這個檢查點對應的要點不見了，沒辦法決定卡片要掛在哪裡"
    anchor = (point["meta"].get("anchor") or {})
    if not isinstance(anchor, dict) or not anchor.get("file"):
        return None, "那則要點沒有可用的 anchor，沒辦法決定卡片要掛在哪裡"

    from . import marks as marklib  # local: only this function needs the slug

    cid = next_card_id(notes_dir)
    meta = {
        "id": cid,
        "created": today,
        "updated": today,
        "status": "open",
        # He never asked this: the checkpoint did. That is exactly what
        # `suggested` is for, and it keeps these out of the schedule by default.
        "origin": "suggested",
        "tags": [str(t) for t in (point["meta"].get("tags") or [])] or ["段落檢查點"],
        "anchor": {"file": anchor.get("file"), "quote": anchor.get("quote") or {}},
    }
    body = [
        "## 問題",
        check["question"],
        "",
        "## 卡點",
        f"讀到 {check['section']} 結尾的段落檢查點時，兩次都沒答到。",
        "",
        "## 解答",
        f"這一節的要點說：{point['text']}",
        "",
        "（這張卡是檢查點自動建立的，解答只有要點那一句。下一回合請 agent 展開，"
        "或你自己補完再標成已解決。）",
        "",
        f"## {notes.SELF_HEADING}",
    ]
    for index, text in enumerate(answers, start=1):
        flat = " ".join(str(text).split())
        if flat:
            body.append(f"{today} 第 {index} 次：{flat}")
    path = notes_dir / "cards" / f"{cid}-{marklib.slug(check['question'])}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + miniyaml.dump(meta) + "\n---\n\n" + "\n".join(body) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return cid, path
