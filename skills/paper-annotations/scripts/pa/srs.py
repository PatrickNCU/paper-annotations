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

# Anki's SM-2 defaults, which is what the reader compared this against.
EASE_START = 2.5
EASE_MIN = 1.3
EASE_STEP = {"again": -0.20, "hard": -0.15, "good": 0.0, "easy": 0.15}
FIRST_INTERVAL = {"hard": 1, "good": 1, "easy": 4}
HARD_FACTOR = 1.2
EASY_BONUS = 1.3
# A year is enough for a paper you may re-read. Anki allows a century, but a
# note that will not resurface until 2031 is a note you have thrown away.
MAX_INTERVAL = 365

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\w+)\s*$")


def log_path(notes_dir: Path, card_id: str) -> Path:
    # The id, never the filename: slugs change when a card is retitled, ids do
    # not, and reanchor.py rewrites anchors without ever touching an id.
    return notes_dir / "reviews" / f"{card_id}.md"


def read_log(notes_dir: Path, card_id: str):
    """Every grading of this card, oldest first. Unparseable lines are dropped."""
    path = log_path(notes_dir, card_id)
    if not path.is_file():
        return []
    _, body = notes.read_doc(path)
    out = []
    for line in body.splitlines():
        match = LINE.match(line.strip())
        if match and match.group(2) in GRADES:
            out.append((match.group(1), match.group(2)))
    return out


def append(notes_dir: Path, card_id: str, grade: str, today: str) -> Path:
    """Add one grading. Append-only: nothing here ever rewrites a past line."""
    if grade not in GRADES:
        raise ValueError(grade)
    path = log_path(notes_dir, card_id)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'---\ncard: "{card_id}"\n---\n\n{today} {grade}\n',
            encoding="utf-8",
            newline="\n",
        )
        return path
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + f"{today} {grade}\n", encoding="utf-8", newline="\n")
    return path


def replay(entries):
    """Turn a grading history into a schedule. SM-2, simplified.

    Returns interval in days, ease, lapses, and the date of the last review.
    An empty history is a card that has never been seen: interval 0, due now.
    """
    interval, ease, lapses, last = 0, EASE_START, 0, ""
    for when, grade in entries:
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
        grade: replay(list(entries) + [(today, grade)])["interval"] for grade in GRADES
    }


def eligible(meta) -> bool:
    """Cards that take part in scheduling at all -- the reader's rule."""
    return (
        str(meta.get("status", "open")) == "resolved"
        and str(meta.get("origin", "asked")) != "suggested"
    )


def schedule(notes_dir: Path, cards, today: str):
    """The full picture the review tab and the library page both read.

    `queue` is what to do now, in the order to do it: half-understood cards
    first because they are the ones that are actually unfinished, then whatever
    is due, oldest due date first.
    """
    scheduled, standing, orphans = [], [], []
    known = {str(card["meta"].get("id")) for card in cards}

    for card in cards:
        meta = card["meta"]
        cid = str(meta.get("id"))
        question = " ".join(
            (notes.card_sections(card["body"]).get("問題") or "").split()
        ) or "(未填問題)"
        if str(meta.get("status", "open")) == "half":
            standing.append({"id": cid, "question": question, "kind": "half"})
            continue
        if not eligible(meta):
            continue
        entries = read_log(notes_dir, cid)
        state = replay(entries)
        due = due_date(state)
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
                "ready": (not due) or due <= today,
                "preview": preview(entries, today),
            }
        )

    reviews_dir = notes_dir / "reviews"
    if reviews_dir.is_dir():
        for path in sorted(reviews_dir.glob("*.md")):
            if path.stem not in known:
                orphans.append(path.name)

    ready = sorted(
        (item for item in scheduled if item["ready"]),
        key=lambda item: (item["due"] or "", item["id"]),
    )
    return {
        "today": today,
        "queue": standing + ready,
        "scheduled": sorted(scheduled, key=lambda item: (item["due"] or "", item["id"])),
        "half": len(standing),
        "due": len(ready),
        "tracked": len(scheduled),
        # A card the reader deleted leaves its history behind on purpose:
        # silently discarding it is the one thing ADR 0003 refuses to do.
        "orphans": orphans,
    }


def counts(notes_dir: Path, cards, today: str):
    """Just the numbers, for the index and the cross-paper catalog."""
    state = schedule(notes_dir, cards, today)
    return {"due": state["due"], "half": state["half"], "tracked": state["tracked"]}
