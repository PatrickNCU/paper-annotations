"""Render digests into pages that open in a browser.

The digest itself stays Markdown -- that is what the agent writes, what git
diffs, and what anyone can edit. This produces a derived view beside it, for
the same reason the review page exists: a digest about placement is half
formulas, and `$\\lambda$` in a text editor is not something you can read at a
glance. Nobody should need a Markdown editor installed to read their own notes.

Same machinery as the review page -- one stylesheet, one vendored KaTeX, no
network -- so the two look like they came from the same tool, which they did.

Usage:
    python build_digest.py <work> [--only <檔名或前綴>]
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from . import cli, katex, minimd, notes, workspace
from .page import ASSETS, THEME_BOOT

cli.bootstrap()

MODE_LABEL = {
    "review-sheet": "回顧單",
    "theme-map": "主題聚合",
    "prerequisites": "前提盤點",
    "connections": "接線",
}

# The review page's stylesheet dresses a whole application; a digest is one
# column of prose. Only the pieces it lacks are added here.
EXTRA_CSS = """
#main{max-width:820px}
.dhead{margin:0 0 26px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.dhead h1{margin:0 0 6px;font-size:1.6em}
.dmeta{font-size:13px;color:var(--muted)}
.dmeta code{font-size:12px}
#main table{font-size:.95em}
#main blockquote{color:var(--muted);font-size:.94em}
"""

TOGGLE_JS = """
(function(){
  var b=document.getElementById('theme');
  var modes=[['system','🌗 跟隨系統'],['light','☀️ 淺色'],['dark','🌙 深色']];
  var mode='system';
  try{var s=localStorage.getItem('pa-theme');
      if(s==='light'||s==='dark'||s==='system') mode=s;}catch(e){}
  function set(m){
    mode=m;
    if(m==='system'){document.documentElement.removeAttribute('data-theme');}
    else{document.documentElement.setAttribute('data-theme',m);}
    try{localStorage.setItem('pa-theme',m);}catch(e){}
    for(var i=0;i<modes.length;i++){ if(modes[i][0]===m) b.textContent=modes[i][1]; }
  }
  set(mode);
  b.addEventListener('click',function(){
    var i=0;
    for(var j=0;j<modes.length;j++){ if(modes[j][0]===mode) i=j; }
    set(modes[(i+1)%modes.length][0]);
  });
})();
"""


def meta_line(meta: dict) -> str:
    """What this digest is, from its own frontmatter -- never guessed."""
    bits = []
    mode = str(meta.get("mode") or "")
    if mode:
        bits.append(MODE_LABEL.get(mode, mode))
    if meta.get("generated"):
        bits.append(f"產生於 {html.escape(str(meta['generated']))}")
    papers = meta.get("papers") or []
    if isinstance(papers, list) and papers:
        bits.append("涉及論文 " + "、".join(f"<code>{html.escape(str(p))}</code>" for p in papers))
    cards = meta.get("cards") or []
    if isinstance(cards, list) and cards:
        bits.append("涵蓋卡片 " + "、".join(f"Q{html.escape(str(c))}" for c in cards))
    bits.append("由 AI 撰寫，非論文內容")
    return " · ".join(bits)


def title_of(meta: dict, path: Path) -> str:
    mode = MODE_LABEL.get(str(meta.get("mode") or ""), "")
    if mode and meta.get("generated"):
        return f"{mode} {meta['generated']}"
    return mode or path.stem


def render_one(src: Path) -> Path:
    meta, body = notes.read_doc(src)
    # The disclaimer is the digest's own first line; leaving it in the body is
    # deliberate -- it must survive being copied out of this page.
    rendered, _ = minimd.render(body)
    title = title_of(meta, src)

    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — 整理</title>
{THEME_BOOT}
<style>{(ASSETS / "style.css").read_text(encoding="utf-8")}</style>
<style>{EXTRA_CSS}</style>
{katex.katex_assets()}
</head>
<body>
<main id="main">
<div class="dhead">
<h1>{html.escape(title)}</h1>
<div class="dmeta">{meta_line(meta)}</div>
</div>
{rendered}
</main>
<button id="theme">🌗 跟隨系統</button>
<script>{TOGGLE_JS}</script>
</body>
</html>
"""
    out = src.with_suffix(".html")
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def main(argv) -> int:
    args = cli.positionals(argv, value_flags={"--only"})
    work = Path(args[0] if args else ".").resolve()
    _, _, notes_dir, _ = workspace.load_workspace(work)

    digests = notes_dir / "digests"
    if not digests.is_dir():
        print(f"還沒有任何整理（{digests} 不存在）。")
        print("整理由 agent 撰寫，見 /paper-annotations:digest。")
        return 0

    only = cli.flag(argv, "only", "") or ""
    sources = sorted(p for p in digests.glob("*.md") if not only or p.stem.startswith(only))
    if not sources:
        print(f"{digests} 裡沒有符合的 .md" + (f"（--only {only}）" if only else ""))
        return 0

    for src in sources:
        out = render_one(src)
        size = out.stat().st_size / 1024
        print(f"整理  {out.name}  {size:,.0f} KB")
        print(f"      {out}")
    print("      公式已離線渲染；.md 仍是可編輯的來源，改完重跑這支就好。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
