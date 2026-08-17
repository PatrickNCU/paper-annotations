"""The workspace: notes/paper.yml and where generated output goes."""

from __future__ import annotations

from pathlib import Path

from . import miniyaml

SCHEMA = 2


def default_annotated(paper_root: Path, work_root: Path) -> Path:
    """Where the review page goes when nobody said.

    Beside the converted package rather than inside it: a paper folder normally
    holds the PDF plus a `<name>_md/` package of dozens of files, and a review
    page buried in there is a page nobody finds. One level up it sits next to
    the PDF, which is where the reader already looks.

    Only when the notes stayed with the paper. `--out` means the user placed the
    workspace deliberately, so the page stays with the notes they placed.
    """
    if work_root != paper_root:
        return work_root / "annotated"
    parent = paper_root.parent
    if parent == paper_root or parent == Path.home():
        return work_root / "annotated"
    package = paper_root.name.lower().endswith(("_md", "-md"))
    beside_pdf = any(parent.glob("*.pdf"))
    return parent / "annotated" if (package or beside_pdf) else work_root / "annotated"


def load_workspace(work_root: Path):
    """Locate the paper from the notes directory that points at it.

    Commands take the directory that holds notes/ -- which is the paper package
    itself unless probe.py was given --out. The review page is tracked
    separately: it may sit outside that directory entirely.
    """
    notes = work_root / "notes"
    config_path = notes / "paper.yml"
    if not config_path.is_file():
        raise SystemExit(f"找不到 {config_path}，請先執行 probe.py")
    config = miniyaml.load(config_path.read_text(encoding="utf-8"))
    if int(config.get("schema") or 1) < SCHEMA:
        raise SystemExit(
            f"{config_path} 是舊版格式，請重新執行一次 probe.py 以更新。"
        )
    paper_root = (work_root / str(config.get("paper_root") or ".")).resolve()
    # Older configs predate a movable review page; they meant work_root/annotated.
    annotated = (work_root / str(config.get("annotated_root") or "annotated")).resolve()
    return config, paper_root, notes, annotated
