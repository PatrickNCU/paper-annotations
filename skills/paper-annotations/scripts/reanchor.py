"""Re-attach cards after the source text was re-converted or re-split.

Only rewrites a card when its quote matches EXACTLY ONE place in the whole
paper. Ambiguous and missing quotes are reported for a human decision -- papers
repeat sentences constantly, and a plausible-but-wrong re-anchor is worse than
an obviously broken one.

Usage:
    python reanchor.py <paper_root> [--dry-run]
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import miniyaml
import paperkit

paperkit.bootstrap()


def enclosing_headings(lines, index: int):
    """Heading path (outermost first) for the line at index."""
    stack = {}
    for i in range(index + 1):
        line = lines[i]
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            stack[level] = paperkit.normalize(line.lstrip("#"))
            for deeper in [k for k in stack if k > level]:
                del stack[deeper]
    return [stack[k] for k in sorted(stack)]


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in argv
    work_root = Path(args[0] if args else ".").resolve()
    config, paper_root, notes, _ = paperkit.load_workspace(work_root)
    config_path = notes / "paper.yml"

    sources = paperkit.discover_sources(paper_root)
    texts = {rel: (paper_root / rel).read_text(encoding="utf-8").splitlines() for rel in sources}

    card_problems = []
    cards = paperkit.load_cards(notes, card_problems)
    fixed, ok, ambiguous, lost = [], [], [], []

    for card in cards:
        anchor = card["meta"].get("anchor") or {}
        declared = Path(str(anchor.get("file") or ""))
        if declared in texts:
            index, _ = paperkit.resolve_anchor(anchor, texts[declared])
            if index is not None:
                ok.append(card)
                continue

        quote = anchor.get("quote") or {}
        exact = paperkit.normalize(str(quote.get("exact") or "")) if isinstance(quote, dict) else ""
        if len(exact) < 12:
            lost.append((card, "這張卡沒有指定要掛在哪一句原文旁，無法自動找回"))
            continue

        hits = []
        for rel, lines in texts.items():
            haystack, spans = paperkit._norm_map(lines)
            pos = haystack.find(exact)
            while pos >= 0:
                line_idx = next((idx for s, e, idx in spans if s <= pos < e), 0)
                hits.append((rel, line_idx))
                pos = haystack.find(exact, pos + 1)

        if len(hits) == 1:
            rel, line_idx = hits[0]
            anchor["file"] = rel.as_posix()
            anchor["heading"] = enclosing_headings(texts[rel], line_idx)
            if anchor.get("ref"):
                probe_anchor = {"ref": anchor["ref"]}
                if paperkit.resolve_anchor(probe_anchor, texts[rel])[0] is None:
                    anchor.pop("ref")
            card["meta"]["anchor"] = anchor
            card["meta"]["updated"] = date.today().isoformat()
            fixed.append((card, rel))
            if not dry_run:
                paperkit.write_doc(card["path"], card["meta"], card["body"])
        elif hits:
            ambiguous.append((card, hits))
        else:
            lost.append((card, "目前的原文裡找不到你指定的那句話"))

    for path, message in card_problems:
        print(f"  ⚠️  {path.name} — {message}")
    print(f"疑問卡 {len(cards)} 張：仍正確 {len(ok)}、自動修復 {len(fixed)}、"
          f"多重命中 {len(ambiguous)}、找不到 {len(lost)}")
    for card, rel in fixed:
        print(f"  ✅ Q{card['meta'].get('id')} → {rel.as_posix()}")
    for card, hits in ambiguous:
        print(f"  ❓ Q{card['meta'].get('id')} 命中 {len(hits)} 處，需人工裁決：")
        for rel, idx in hits:
            print(f"       {rel.as_posix()}:{idx + 1}")
    for card, reason in lost:
        print(f"  ⚠️  Q{card['meta'].get('id')} — {reason}")

    if dry_run:
        print("\n（--dry-run：沒有寫入任何檔案）")
        return 0

    if config:
        config["sources"] = [rel.as_posix() for rel in sources]
        config["fingerprint"] = {
            "manifest_sha256": (config.get("fingerprint") or {}).get("manifest_sha256"),
            "chunk_count": len(sources),
            "files": {
                rel.as_posix(): paperkit.file_fingerprint(paper_root / rel) for rel in sources
            },
        }
        config["generated"] = date.today().isoformat()
        config_path.write_text(
            "# 由 probe.py 產生；可手改，但 build 仍會對實際內容重新驗證。\n"
            + miniyaml.dump(config)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\n已更新 {config_path.name} 的指紋，可以重新 build。")
    if ambiguous or lost:
        print("仍有卡片需要人工處理，build 後會列在 QUESTIONS.md 的『找不到位置的疑問』區塊。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
