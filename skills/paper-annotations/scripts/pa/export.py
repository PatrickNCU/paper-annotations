"""Export the question cards to a file some other tool can read.

This tool deliberately has no scheduling algorithm -- Anki and friends have
spent decades on that. What it owes them is a clean way out, so the cards stay
the user's data rather than something locked in one HTML page.

Nothing here writes to notes/ or annotated/: export is read-only.

Usage:
    python export_cards.py <work> [--format anki|csv|json] [--out <file>]
                                  [--status open,half] [--tag density]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from . import anchors, cli, notes, workspace

cli.bootstrap()

STATUS_LABEL = {"open": "未解決", "half": "半懂", "resolved": "已解決"}


def card_rows(work_root: Path, statuses, tags):
    config, paper_root, notes_dir, _ = workspace.load_workspace(work_root)
    rows = []
    for card in notes.load_cards(notes_dir):
        meta = card["meta"]
        status = str(meta.get("status") or "open")
        card_tags = [str(t) for t in (meta.get("tags") or [])]
        if statuses and status not in statuses:
            continue
        if tags and not (set(tags) & set(card_tags)):
            continue
        sections = notes.card_sections(card["body"])
        anchor = meta.get("anchor") or {}
        quote = anchor.get("quote")
        rows.append(
            {
                "id": str(meta.get("id") or ""),
                # Front/back are the card as written: the question the reader
                # asked, and what they worked out. No reformatting, no summary.
                "front": " ".join(sections.get("問題", "").split()),
                "back": sections.get("解答", "").strip(),
                "stuck": sections.get("卡點", "").strip(),
                "intuition": " ".join(sections.get("一句話直覺", "").split()),
                "quote": anchors.quote_text(quote),
                "source": f"{paper_root.name} · {anchor.get('file') or ''}",
                "status": status,
                "tags": " ".join(card_tags),
                "updated": str(meta.get("updated") or ""),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return rows, paper_root


def to_anki_html(text: str) -> str:
    """Markdown-ish card text as Anki renders it.

    Anki's MathJax uses \\( \\) and \\[ \\], not $ $ -- exported without this
    every formula arrives as literal dollar signs, which on a physics-heavy
    paper is most of the card.
    """
    import re

    text = re.sub(r"\$\$(.+?)\$\$", lambda m: f"\\[{m.group(1)}\\]", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", lambda m: f"\\({m.group(1)}\\)", text)
    text = re.sub(r"`([^`\n]+)`", lambda m: f"<code>{m.group(1)}</code>", text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", lambda m: f"<b>{m.group(1)}</b>", text)
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.M)
    return text.replace("\t", " ").replace("\n", "<br>")


def write_anki(rows, out: Path):
    """Tab-separated, the shape Anki's plain-text importer expects.

    Field order is fixed and stated in the header comment so a re-import maps
    to the same fields as the first one.
    """
    lines = [
        "#separator:tab",
        "#html:true",
        "#columns:Front\tBack\tExtra\tSource\tTags",
    ]
    for row in rows:
        extra = []
        if row["stuck"]:
            extra.append("卡點：" + to_anki_html(row["stuck"]))
        if row["intuition"]:
            extra.append("直覺：" + to_anki_html(row["intuition"]))
        if row["quote"]:
            extra.append("原文：" + to_anki_html(row["quote"]))
        fields = [
            to_anki_html(row["front"]),
            to_anki_html(row["back"]),
            "<br>".join(extra),
            row["source"],
            row["tags"],
        ]
        lines.append("\t".join(fields))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_csv(rows, out: Path):
    cols = ["id", "front", "back", "stuck", "intuition", "quote", "source", "status", "tags", "updated"]
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(rows, out: Path):
    out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv):
    positional = cli.positionals(argv, value_flags={"--format", "--out", "--status", "--tag"})
    work_root = Path(positional[0] if positional else ".").resolve()
    fmt = (cli.flag(argv, "format", "anki") or "anki").lower()
    if fmt not in ("anki", "csv", "json"):
        raise SystemExit(f"不認得的格式 {fmt}，可用：anki、csv、json")

    statuses = [s.strip() for s in (cli.flag(argv, "status", "") or "").split(",") if s.strip()]
    tags = [t.strip() for t in (cli.flag(argv, "tag", "") or "").split(",") if t.strip()]

    rows, paper_root = card_rows(work_root, statuses, tags)
    if not rows:
        print("沒有符合條件的卡片，沒有產生檔案。")
        return 1

    suffix = {"anki": ".txt", "csv": ".csv", "json": ".json"}[fmt]
    target = cli.flag(argv, "out")
    out = Path(target).resolve() if target else (work_root / "notes" / f"cards-export{suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    {"anki": write_anki, "csv": write_csv, "json": write_json}[fmt](rows, out)

    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    breakdown = "、".join(f"{STATUS_LABEL.get(k, k)} {v}" for k, v in sorted(counts.items()))
    print(f"匯出 {len(rows)} 張卡（{breakdown}）→ {out}")
    if fmt == "anki":
        print("Anki：檔案 → 匯入，欄位依序是 Front／Back／Extra／Source／Tags。")
        print("已解答的卡才適合拿去背；只想匯出這些的話加 --status resolved。")
    print("匯出是唯讀的，卡片本身沒有被改動。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
