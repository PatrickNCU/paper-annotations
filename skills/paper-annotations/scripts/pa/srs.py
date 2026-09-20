"""Spaced repetition: when a card should come back.

Review history is the first data in this tool that cannot be regenerated --
see docs/adr/0003. It is stored as one append-only text log per card, and the
schedule is never stored at all: it is replayed from the log every time it is
needed. Changing the algorithm therefore needs no migration, because nothing
derived from the old one was ever written down.

    notes/reviews/0001.md
    ---
    card: "0001"
    ---
    2026-08-17 good
    2026-08-24 again
    2026-09-02 good sure

The optional third word is how sure the reader said he was BEFORE seeing the
answer (sure / vague / blank). It never touches the schedule; it exists so the
page can say "你說想得起來，結果按了重來" and so a later reader of the log can
see where his confidence and his memory disagreed. Readers older than 1.17.0
drop a three-word line entirely, so a log written here is not readable by them.

Which cards take part is the reader's decision, recorded here:

  * resolved + asked      -> scheduled. He understood it; now he has to keep it.
  * half                  -> a standing queue, never scheduled. Always on top,
                             because a half-understood card is not a memory
                             problem and pretending otherwise buries it.
  * open                  -> not here at all. It is already in the question list.
  * origin: suggested     -> not scheduled by default; he never asked it.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from . import notes

GRADES = ("again", "hard", "good", "easy")
# How sure he said he was before the reveal. Not a grade: it changes nothing
# about when the card comes back.
JOLS = ("sure", "vague", "blank")

# Anki's SM-2 defaults, which is what the reader compared this against.
EASE_START = 2.5
EASE_MIN = 1.3
EASE_STEP = {"again": -0.20, "hard": -0.15, "good": 0.0, "easy": 0.15}
# good is 2 rather than Anki's 1 so the three buttons on a first review do not
# all promise the same day -- a button that cannot differ from its neighbour
# carries no information.
FIRST_INTERVAL = {"hard": 1, "good": 2, "easy": 4}
HARD_FACTOR = 1.2
EASY_BONUS = 1.3
# A year is enough for a paper you may re-read. Anki allows a century, but a
# note that will not resurface until 2031 is a note you have thrown away.
MAX_INTERVAL = 365
# A card failed three times in one sitting is not going to be learned by a
# fourth try tonight. It comes back tomorrow like any other lapse.
RETRIES_PER_DAY = 3

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\w+)(?:\s+(\w+))?\s*$")


def log_path(notes_dir: Path, card_id: str) -> Path:
    # The id, never the filename: slugs change when a card is retitled, ids do
    # not, and reanchor.py rewrites anchors without ever touching an id.
    return notes_dir / "reviews" / f"{card_id}.md"


def read_log(notes_dir: Path, card_id: str):
    """Every grading of this card, oldest first, as (date, grade, jol).

    jol is None on the two-word lines every log started with. Unparseable
    lines are dropped.
    """
    path = log_path(notes_dir, card_id)
    if not path.is_file():
        return []
    _, body = notes.read_doc(path)
    out = []
    for line in body.splitlines():
        match = LINE.match(line.strip())
        if match and match.group(2) in GRADES:
            jol = match.group(3) if match.group(3) in JOLS else None
            out.append((match.group(1), match.group(2), jol))
    return out


def append(notes_dir: Path, card_id: str, grade: str, today: str, jol: str = "") -> Path:
    """Add one grading. Append-only: nothing here ever rewrites a past line."""
    if grade not in GRADES:
        raise ValueError(grade)
    if jol and jol not in JOLS:
        raise ValueError(jol)
    line = f"{today} {grade}" + (f" {jol}" if jol else "")
    path = log_path(notes_dir, card_id)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'---\ncard: "{card_id}"\n---\n\n{line}\n',
            encoding="utf-8",
            newline="\n",
        )
        return path
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + line + "\n", encoding="utf-8", newline="\n")
    return path


def replay(entries):
    """Turn a grading history into a schedule. SM-2, simplified.

    Returns interval in days, ease, lapses, and the date of the last review.
    An empty history is a card that has never been seen: interval 0, due now.
    """
    interval, ease, lapses, last = 0, EASE_START, 0, ""
    for when, grade, *_ in entries:
        last = when
        ease = max(EASE_MIN, ease + EASE_STEP[grade])
        if grade == "again":
            # Back to the start of the ladder rather than a fractional step:
            # a card you could not answer is a card you do not know.
            interval, lapses = 1, lapses + 1
            continue
        if interval == 0:
            interval = FIRST_INTERVAL[grade]
        elif grade == "hard":
            interval = interval * HARD_FACTOR
        elif grade == "good":
            interval = interval * ease
        else:
            interval = interval * ease * EASY_BONUS
        interval = min(MAX_INTERVAL, max(1, round(interval)))
    return {"interval": interval, "ease": round(ease, 2), "lapses": lapses, "last": last}


def due_date(state) -> str:
    if not state["last"]:
        return ""
    try:
        stamp = date.fromisoformat(state["last"])
    except ValueError:
        return ""
    return (stamp + timedelta(days=state["interval"])).isoformat()


def preview(entries, today: str):
    """What each grade would do to the interval, in days.

    Computed here rather than in the page so the algorithm lives in exactly one
    place -- a button promising "4 天" that the replay disagrees with would be
    the kind of quiet mismatch nobody notices until the schedule is wrong.
    """
    return {
        grade: replay(list(entries) + [(today, grade, None)])["interval"]
        for grade in GRADES
    }


def eligible(meta) -> bool:
    """Cards that take part in scheduling at all -- the reader's rule."""
    return (
        str(meta.get("status", "open")) == "resolved"
        and str(meta.get("origin", "asked")) != "suggested"
    )


def mismatch(jol, grade) -> str:
    """The one sentence worth saying after a grade: only when what he expected
    and what happened disagree. Everything else is noise."""
    if jol == "sure" and grade == "again":
        return "你說想得起來，結果按了重來。"
    if jol == "blank" and grade in ("good", "easy"):
        return "你說想不起來，結果按了" + ("良好" if grade == "good" else "簡單") + "。"
    return ""


def _days_since(meta, today: str):
    """How long a half card has sat there, from `updated` (or `created`)."""
    for key in ("updated", "created"):
        raw = str(meta.get(key) or "")
        try:
            return (date.fromisoformat(today) - date.fromisoformat(raw)).days
        except ValueError:
            continue
    return None


def schedule(notes_dir: Path, cards, today: str):
    """The full picture the review tab and the library page both read.

    `queue` is what to do now, in the order to do it: half-understood cards
    first because they are the ones that are actually unfinished (oldest
    first, so the one that has waited longest is on top), then whatever is
    due, oldest due date first, then today's failures last -- a card graded
    重來 stays in today's queue to be answered once more before the day ends,
    and after RETRIES_PER_DAY failures it is parked until tomorrow.
    """
    scheduled, standing, orphans = [], [], []
    known = {str(card["meta"].get("id")) for card in cards}
    try:
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    except ValueError:
        tomorrow = today

    for card in cards:
        meta = card["meta"]
        cid = str(meta.get("id"))
        question = " ".join(
            (notes.card_sections(card["body"]).get("問題") or "").split()
        ) or "(未填問題)"
        if str(meta.get("status", "open")) == "half":
            standing.append({
                "id": cid, "question": question, "kind": "half",
                "since": _days_since(meta, today),
            })
            continue
        if not eligible(meta):
            continue
        entries = read_log(notes_dir, cid)
        state = replay(entries)
        due = due_date(state)
        again_today = sum(
            1 for when, grade, *_ in entries if when == today and grade == "again"
        )
        failed_last = bool(entries) and entries[-1][0] == today and entries[-1][1] == "again"
        parked = failed_last and again_today >= RETRIES_PER_DAY
        retry = failed_last and not parked
        scheduled.append(
            {
                "id": cid,
                "question": question,
                "kind": "scheduled",
                "due": due,
                "interval": state["interval"],
                "ease": state["ease"],
                "lapses": state["lapses"],
                "last": state["last"],
                # never reviewed -> due today, so a newly resolved card shows up
                "ready": retry or (not parked and ((not due) or due <= today)),
                "retry": retry,
                "parked": parked,
                "again_today": again_today,
                "preview": preview(entries, today),
            }
        )

    reviews_dir = notes_dir / "reviews"
    if reviews_dir.is_dir():
        for path in sorted(reviews_dir.glob("*.md")):
            if path.stem not in known:
                orphans.append(path.name)

    standing.sort(key=lambda item: (-(item["since"] or 0), item["id"]))
    ready = sorted(
        (item for item in scheduled if item["ready"] and not item["retry"]),
        key=lambda item: (item["due"] or "", item["id"]),
    )
    retries = sorted((item for item in scheduled if item["retry"]), key=lambda item: item["id"])
    parked_items = [item for item in scheduled if item["parked"]]
    later = sorted(
        (item for item in scheduled if not item["ready"] and not item["parked"] and item["due"] > today),
        key=lambda item: item["due"],
    )
    next_due = later[0]["due"] if later else ""
    if parked_items and (not next_due or tomorrow < next_due):
        next_due = tomorrow
    return {
        "today": today,
        "queue": standing + ready + retries,
        "scheduled": sorted(scheduled, key=lambda item: (item["due"] or "", item["id"])),
        "half": len(standing),
        "due": len(ready) + len(retries),
        "tracked": len(scheduled),
        # what the opening line says after "今天到期 N 張"
        "next": next_due,
        "tomorrow": len(parked_items) + sum(1 for item in later if item["due"] <= tomorrow),
        "parked": [{"id": item["id"], "question": item["question"]} for item in parked_items],
        "done_today": any(item["last"] == today for item in scheduled),
        # A card the reader deleted leaves its history behind on purpose:
        # silently discarding it is the one thing ADR 0003 refuses to do.
        "orphans": orphans,
    }


def counts(notes_dir: Path, cards, today: str):
    """Just the numbers, for the index and the cross-paper catalog."""
    state = schedule(notes_dir, cards, today)
    return {"due": state["due"], "half": state["half"], "tracked": state["tracked"]}


# The shelf reads this one; a single paper's page reads schedule() above. The
# queue is merged rather than concatenated per paper: what is due today is one
# job, and splitting it by paper would make the reader decide which paper to do
# first -- a decision the schedule has already made for him.
QUEUE_LIMIT = 60


def today_across(registry_path, today=None):
    """Everything due across every registered paper, as one queue.

    Imports lazily for the same reason due_line() does: library and workspace
    sit above this module, and importing them at the top would close a loop.

    Each item carries `key` -- paper plus id -- because card ids start at 0001
    in every paper, so an id alone stops being an identity the moment two
    papers are on screen together.
    """
    from datetime import date as _date

    from . import library, workspace

    today = today or _date.today().isoformat()
    standing, ready, retries, ahead, parked = [], [], [], [], []
    per, due, half, tracked, tomorrow = [], 0, 0, 0, 0
    next_due, done_today = "", False

    for paper in library.entries(registry_path):
        if not paper["alive"]:
            continue
        try:
            _, _, notes_dir, _ = workspace.load_workspace(paper["work"])
        except SystemExit:
            # A registered folder that no longer holds a paper package. The
            # shelf card already says so; the queue just leaves it out.
            continue
        plan = schedule(notes_dir, notes.load_cards(notes_dir), today)

        def tag(item):
            item = dict(item)
            item["paper"] = paper["slug"]
            item["paper_title"] = paper["title"]
            item["key"] = f"{paper['slug']}#{item['id']}"
            return item

        for item in plan["queue"]:
            if item["kind"] == "half":
                standing.append(tag(item))
            elif item.get("retry"):
                retries.append(tag(item))
            else:
                ready.append(tag(item))
        ahead += [
            tag(item) for item in plan["scheduled"]
            if not item["ready"] and not item["parked"]
        ]
        parked += [tag(item) for item in plan["scheduled"] if item["parked"]]

        due += plan["due"]
        half += plan["half"]
        tracked += plan["tracked"]
        tomorrow += plan["tomorrow"]
        done_today = done_today or plan["done_today"]
        if plan["next"] and (not next_due or plan["next"] < next_due):
            next_due = plan["next"]
        if plan["due"] or plan["half"]:
            per.append({
                "slug": paper["slug"], "title": paper["title"],
                "due": plan["due"], "half": plan["half"],
            })

    standing.sort(key=lambda i: (-(i["since"] or 0), i["paper"], i["id"]))
    ready.sort(key=lambda i: (i["due"] or "", i["paper"], i["id"]))
    retries.sort(key=lambda i: (i["paper"], i["id"]))
    ahead.sort(key=lambda i: (i["due"], i["paper"], i["id"]))
    queue = standing + ready + retries
    return {
        "today": today,
        # Truncated rather than paged: a day with more than QUEUE_LIMIT due is
        # a day the reader will not finish anyway, and the honest thing is to
        # hand him the top of the queue and the real total.
        "queue": queue[:QUEUE_LIMIT],
        "queue_total": len(queue),
        # Only the next one ahead is ever offered, so only it needs to travel.
        "scheduled": ahead[:1],
        "parked": [{"key": i["key"], "id": i["id"], "paper": i["paper"],
                    "question": i["question"]} for i in parked],
        "papers": per,
        "due": due, "half": half, "tracked": tracked,
        "next": next_due,
        # Each paper already counted its own parked cards and its own due-by-
        # tomorrow; summing those is the whole answer. Counting `ahead` again
        # here would count every one of them twice.
        "tomorrow": tomorrow,
        "done_today": done_today,
    }
