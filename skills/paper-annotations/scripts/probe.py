"""Probe a paper package and write notes/paper.yml.

Detects which anchor kinds this particular paper can actually support, and
records a fingerprint so a later build can tell that the source was replaced.
The result is a hint about what to try FIRST -- never a promise. See ADR 0001.

Usage:
    python probe.py <paper_root> [--out <notes_dir>] [--review <annotated_dir>]
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import miniyaml
import paperkit

paperkit.bootstrap()

TIER_BLURB = {
    "A": "完整轉檔套件，筆記可以精準掛在公式、圖、表和小節上。",
    "B": "一般 Markdown（有章節標題），筆記可以掛在小節上，或掛在你指定的某一句原文旁。",
    "C": "純文字（沒有章節標題），筆記只能靠比對一句原文來定位，論文一改就容易失效。",
}

# 終端機訊息給的是第一次接觸這套工具的人看的，用白話描述行為，
# 專有名詞（錨點、Tier）留在 CONTEXT.md 與 AGENTS.md 給 agent 和開發者。
CAP_LABEL = {
    "headings": "章節標題",
    "equation_tags": "公式編號",
    "figures": "圖片",
    "tables": "表格",
    "chunked": "已切分的章節檔",
    "index_file": "索引檔",
    "equation_index": "公式索引",
    "frontmatter_chunk_ids": "章節編號",
}


def find_rules() -> Path:
    """Locate pdf2md_rules.md by looking for it, not by assuming a layout.

    This file has already moved once (tools/… → skills/<name>/scripts/), and the
    hardcoded relative path then printed a path that did not exist — the worst
    kind of wrong, because the user goes looking and finds nothing.
    """
    here = Path(__file__).resolve()
    for base in (here.parent, here.parent.parent, here.parent.parent.parent):
        candidate = base / "references" / "pdf2md_rules.md"
        if candidate.is_file():
            return candidate
    return here.parent.parent / "references" / "pdf2md_rules.md"


def no_source_guidance(paper_root: Path) -> None:
    """The most common first contact: the user has a PDF and nothing else."""
    pdfs = sorted(paper_root.glob("*.pdf")) + sorted(paper_root.glob("**/*.pdf"))
    rules = find_rules()

    print(f"這個資料夾裡沒有可用的論文 Markdown：{paper_root}")
    if pdfs:
        print("只找到 PDF：")
        for pdf in dict.fromkeys(pdfs):
            print(f"    {pdf.relative_to(paper_root)}")
    print("\n先把 PDF 轉成 Markdown 再回來。建議做法（也是這套工具假設的輸入）：")
    print("  1. 開 ChatGPT 網頁版，上傳這兩個檔案：")
    print(f"       {rules}")
    print(f"       {pdfs[0].name if pdfs else '<你的論文>.pdf'}")
    print("  2. 貼上該規則檔 §0「使用方式」裡的指令。")
    print("  3. 把回傳的 ZIP 解壓到這個資料夾，再重新執行 probe.py。")
    print("\n提醒：")
    print("  - 轉檔很花時間，一篇 IEEE 期刊論文通常需要多次來回。")
    print("  - 模型與推理強度會顯著影響結果；實測 GPT-5.6 Sol + 高推理較佳。")
    print("  - 想用自己的 pdf2md 工具也可以：只要轉出來的 Markdown 有章節標題就能用，")
    print("    只是筆記沒辦法精準掛在公式或圖表上，論文改版時比較容易對不上位置。")


def detect(paper_root: Path):
    sources = paperkit.discover_sources(paper_root)
    if not sources:
        no_source_guidance(paper_root)
        raise SystemExit(1)

    if paperkit.looks_generated(paper_root, sources):
        print("這個資料夾裝的是 paper-annotations 自己產生的註記檢視，不是論文原文。")
        print("對它建立筆記會把註記疊在註記上。")
        print(f"請改用原文所在的資料夾，通常是它的上一層：{paper_root.parent}")
        raise SystemExit(1)

    # normalised first, so a package that writes ![alt][label] is not reported
    # as having no figures
    texts = {
        rel: "\n".join(
            paperkit.normalize_ref_links((paper_root / rel).read_text(encoding="utf-8").splitlines())
        )
        for rel in sources
    }
    joined = "\n".join(texts.values())

    caps = {
        "headings": any(re.search(r"^#{1,6} \S", t, re.M) for t in texts.values()),
        "equation_tags": bool(re.search(r"\\tag\{\s*\d+\s*\}", joined)),
        "figures": bool(re.search(r"!\[[^\]]*\]\([^)]*figure-\d+", joined)),
        "tables": (paper_root / "tables").is_dir(),
        "chunked": any(rel.parts and rel.parts[0] == "sections" for rel in sources),
        "index_file": (paper_root / "INDEX.md").is_file(),
        "equation_index": False,
        "frontmatter_chunk_ids": False,
    }

    index_path = paper_root / "INDEX.md"
    if index_path.is_file():
        index_text = index_path.read_text(encoding="utf-8")
        caps["equation_index"] = bool(re.search(r"equation index", index_text, re.I))
    first_meta, _ = paperkit.read_doc(paper_root / sources[0])
    caps["frontmatter_chunk_ids"] = "chunk_id" in first_meta

    if caps["chunked"] and caps["index_file"] and caps["headings"]:
        tier = "A"
    elif caps["headings"]:
        tier = "B"
    else:
        tier = "C"

    # "files" are what notes hang on -- changing one stops a build.
    # "companions" hold the same text or its metadata; they cannot break an
    # anchor, but a change means the package is half-updated, so we say so.
    fingerprint = {
        "manifest_sha256": None,
        "chunk_count": len(sources),
        "files": {
            rel.as_posix(): paperkit.file_fingerprint(paper_root / rel) for rel in sources
        },
        "companions": {
            name: paperkit.file_fingerprint(paper_root / name)
            for name in ("document.md", "INDEX.md", "index.csv", "manifest.json")
            if (paper_root / name).is_file()
        },
    }
    manifest = paper_root / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            fingerprint["manifest_sha256"] = data.get("source_sha256") or None
        except (ValueError, OSError):
            pass

    return {
        "schema": paperkit.SCHEMA,
        "generated": date.today().isoformat(),
        "tier": tier,
        "tier_note": TIER_BLURB[tier],
        "capabilities": caps,
        "sources": [rel.as_posix() for rel in sources],
        "fingerprint": fingerprint,
    }


def flag_value(argv, name):
    """--name <path> or --name=<path>; returns None when absent."""
    prefix = f"--{name}="
    for arg in argv:
        if arg.startswith(prefix):
            return arg[len(prefix) :]
    if f"--{name}" in argv and argv.index(f"--{name}") + 1 < len(argv):
        nxt = argv[argv.index(f"--{name}") + 1]
        if not nxt.startswith("--"):
            return nxt
    return None


def main(argv):
    flags = {"--out", "--review"}
    rest = argv[1:]
    args = []
    skip = False
    for arg in rest:
        if skip:
            skip = False
            continue
        if arg.startswith("--"):
            skip = arg in flags and "=" not in arg
            continue
        args.append(arg)
    paper_root = Path(args[0] if args else ".").resolve()

    # --out puts the notes anywhere; --review puts the page anywhere;
    # the paper itself never moves.
    out_dir = flag_value(rest, "out")
    work_root = Path(out_dir).resolve() if out_dir else paper_root
    review = flag_value(rest, "review")
    annotated_root = (
        Path(review).resolve() if review else paperkit.default_annotated(paper_root, work_root)
    )

    config = detect(paper_root)
    config["paper_root"] = os.path.relpath(paper_root, work_root).replace("\\", "/")
    config["annotated_root"] = os.path.relpath(annotated_root, work_root).replace("\\", "/")

    work_root.mkdir(parents=True, exist_ok=True)
    notes = work_root / "notes"
    notes.mkdir(exist_ok=True)
    (notes / "cards").mkdir(exist_ok=True)
    out_path = notes / "paper.yml"
    out_path.write_text(
        "# 由 probe.py 產生；可手改，但 build 仍會對實際內容重新驗證。\n"
        + miniyaml.dump(config)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    caps = config["capabilities"]
    # "Tier" means nothing to someone meeting this tool for the first time,
    # so the label never appears without the scale and the consequence.
    print(f"支援程度：Tier {config['tier']}（分 A／B／C 三級，A 最完整）")
    print(f"  {config['tier_note']}")
    print(f"正文檔案 {len(config['sources'])} 個")

    have = [CAP_LABEL.get(k, k) for k, v in caps.items() if v]
    missing = [CAP_LABEL.get(k, k) for k, v in caps.items() if not v]
    print("這份論文有：", "、".join(have) if have else "（只有純文字）")
    if missing:
        print("這份論文沒有：", "、".join(missing))

    # Only these four are places a note can actually hang.
    spots = [CAP_LABEL[k] for k in ("headings", "equation_tags", "figures", "tables") if caps.get(k)]
    spots.append("你指定的某一句原文旁")
    print("→ 筆記可以掛在：", "、".join(spots))

    if config["tier"] != "A":
        print(
            "\n提示：用 references/pdf2md_rules.md 重新轉檔可以升到 Tier A，"
            "讓筆記能精準掛在公式與圖表上，日後論文改版也比較不會對不上位置。"
            "轉檔較耗時，且模型與推理強度會顯著影響品質。"
        )
    print(f"\n寫入 {out_path}")
    print(f"疑問卡放在   {notes}")
    print(f"複習頁會產生在 {annotated_root / 'index.html'}")
    if work_root != paper_root:
        print(f"之後的 build / reanchor 請傳 {work_root}，不是論文路徑。")

    # Writing into a directory that already holds someone's own Markdown would
    # look like we ate it; the build also prunes stale .md there.
    if annotated_root.is_dir() and not (annotated_root / "AGENTS.md").is_file():
        strays = [p.name for p in annotated_root.glob("*.md")]
        if strays:
            print(
                f"\n🟡 {annotated_root} 裡已經有 Markdown（{'、'.join(strays[:3])}…），"
                "這個資料夾會被複習頁的建置接管。想換一個位置就重跑 probe.py --review <路徑>。"
            )


if __name__ == "__main__":
    main(sys.argv)
