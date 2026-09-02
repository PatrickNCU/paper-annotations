"""What a button on a page is allowed to run.

Every action here is something the reader could already do by typing a command;
the buttons only remove the typing. So a page sends an action NAME and this
table turns it into a command line built entirely from paths the server itself
resolved at startup. Nothing in a request ever becomes a path or an argument --
the same red line the marks, grading and topic endpoints already hold.

Both sides read this file, which is the point of it existing:

  * ``server.py`` looks a name up here and runs the steps.
  * ``page.py`` and ``librarypage.py`` bake the labels in at build time, along
    with the command each button is equivalent to -- so a page opened with no
    server behind it can grey a button out and still say what it would have
    done, instead of hiding it and leaving the reader to guess.

Adding a button means adding an entry here. There is deliberately no way to
run anything else.
"""

from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent

PAPER = "paper"  # runs against one mounted paper
SHELF = "shelf"  # runs against the registry, so only under --library

# Menu order. Flags, all optional:
#   reload  -- replaces the page you are standing on, so ask before reloading
#   stdin   -- takes pasted text, fed to the script's stdin (never argv)
#   hidden  -- not printed in the menu; reached from another action's result
#   writes  -- changes notes/, so it is offered only after its dry run
ACTIONS = [
    {"name": "rebuild", "scope": PAPER, "label": "重建這一篇",
     "hint": "原文或卡片改過之後，重做註記檢視與這一頁", "reload": True},
    {"name": "export", "scope": PAPER, "label": "匯出 Anki",
     "hint": "把卡片寫成 Anki 匯入得了的檔案，複習紀錄一起帶走"},
    {"name": "package", "scope": PAPER, "label": "打包分享頁",
     "hint": "圖片全部內嵌成一個檔案，可以直接寄給別人"},
    {"name": "marks", "scope": PAPER, "label": "匯入畫記（貼上）",
     "hint": "把別的地方複製出來的畫記貼回來落檔", "stdin": True, "reload": True},
    {"name": "reanchor", "scope": PAPER, "label": "重新對位（先看差異）",
     "hint": "原文換版本後，檢查卡片還掛不掛得住。這一步不動任何檔案"},
    {"name": "reanchor-apply", "scope": PAPER, "label": "把差異寫進卡片",
     "hint": "套用剛才看過的那份差異", "reload": True, "hidden": True,
     "writes": "reanchor"},
    {"name": "shelf", "scope": SHELF, "label": "更新書房頁",
     "hint": "重數每一篇的卡片與到期張數", "reload": True},
    {"name": "inventory", "scope": SHELF, "label": "盤點（誰引用誰、還有什麼沒解決）",
     "hint": "掃過登記簿裡的每一篇，印出引用關係與還沒解決的疑問"},
    {"name": "rebuild-all", "scope": SHELF, "label": "全部重建",
     "hint": "每一篇都重做註記檢視與複習頁，最後更新書房頁。會跑一陣子",
     "reload": True},
]

BY_NAME = {a["name"]: a for a in ACTIONS}


def steps(name: str, ctx: dict):
    """The command lines this action runs, as ``[script, *args]`` lists.

    ``ctx`` carries paths the caller has already resolved: ``work`` (the folder
    holding notes/), ``share`` (where a packaged page goes), ``home`` (the
    folder with papers.yml) and ``works`` (every paper, for the shelf actions).
    """
    work = str(ctx.get("work") or "")
    home = str(ctx.get("home") or "")
    if name == "rebuild":
        return [["build_annotated.py", work], ["build_html.py", work]]
    if name == "export":
        return [["export_cards.py", work, "--format", "anki"]]
    if name == "package":
        return [["build_html.py", work, "--embed-assets", "--to", str(ctx.get("share") or "")]]
    if name == "marks":
        return [["import_marks.py", work]]
    if name == "reanchor":
        return [["reanchor.py", work, "--dry-run"]]
    if name == "reanchor-apply":
        return [["reanchor.py", work]]
    if name == "shelf":
        return [["build_library.py", home]]
    if name == "inventory":
        return [["library.py", home]]
    if name == "rebuild-all":
        plan = []
        for one in ctx.get("works") or []:
            plan.append(["build_annotated.py", str(one)])
            plan.append(["build_html.py", str(one)])
        plan.append(["build_library.py", home])
        return plan
    return []


def produces(name: str, ctx: dict) -> str:
    """The file this action leaves behind, if it leaves one.

    A page cannot hand the reader a file -- it can only tell them where it is,
    which is why this comes back with the result and turns into a 複製路徑.
    """
    if name == "export":
        return str(Path(ctx.get("work") or ".") / "notes" / "cards-export.txt")
    if name == "package":
        return str(ctx.get("share") or "")
    return ""


def command_line(step) -> str:
    """One step as it would be typed by hand -- what a greyed-out button shows."""
    parts = [f"python <scripts>/{step[0]}"]
    for arg in step[1:]:
        parts.append(f'"{arg}"' if (" " in arg or "\\" in arg or "/" in arg) else arg)
    return " ".join(parts)


def equivalent(name: str, ctx: dict) -> str:
    """Every step of an action, for the tooltip.

    Long expansions are cut rather than pasted in full: 全部重建 over twenty
    papers is forty commands, and a tooltip that long says less than a short
    one. The count keeps it honest about what was cut.
    """
    plan = steps(name, ctx)
    if not plan:
        return ""
    if len(plan) <= 2:
        return "\n".join(command_line(s) for s in plan)
    shown = "\n".join(command_line(s) for s in plan[:2])
    return f"{shown}\n…共 {len(plan)} 個指令"


def catalog(scope: str, ctx: dict):
    """What one page bakes in: every action it may offer, with its equivalent.

    Hidden actions are included -- the page needs the label to offer 套用 after
    a dry run -- and marked, so the menu can skip them.
    """
    out = []
    for action in ACTIONS:
        if action["scope"] != scope:
            continue
        out.append({
            "name": action["name"],
            "label": action["label"],
            "hint": action["hint"],
            "cmd": equivalent(action["name"], ctx),
            "reload": bool(action.get("reload")),
            "stdin": bool(action.get("stdin")),
            "hidden": bool(action.get("hidden")),
            "writes": action.get("writes", ""),
            "out": produces(action["name"], ctx),
        })
    return out
