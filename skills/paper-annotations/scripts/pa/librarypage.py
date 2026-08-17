"""The shelf: one page listing every paper the reader has read.

A static file beside papers.yml, for the same reason the review page is one --
it opens without a server, from a double-click, on a machine that has nothing
installed. Served by serve.py --library it goes further and asks for live
counts, because a due count baked in yesterday is a lie today.

Citations between papers appear here and nowhere else: they are the one
cross-paper fact that needs no judgement, so the shelf is where you see the
shape of what you have read.

Usage:
    python build_library.py [<起點>] [--to <檔案>]
"""

from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

from . import cli, library
from .page import ASSETS, THEME_BOOT

cli.bootstrap()

CSS = """
#main{max-width:900px}
.lhead{margin:0 0 24px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.lhead h1{margin:0 0 6px;font-size:1.6em}
.lmeta{font-size:13px;color:var(--muted)}
.paper{display:block;margin:0 0 14px;padding:15px 18px;border:1px solid var(--line);
border-radius:10px;background:var(--card);color:inherit;text-decoration:none}
.paper:hover{border-color:var(--accent)}
.paper h2{margin:0 0 4px;font-size:1.04em;line-height:1.5}
.pfacts{font-size:12.5px;color:var(--muted)}
.pill{display:inline-block;margin:6px 6px 0 0;padding:2px 9px;border-radius:11px;
font-size:12px;line-height:1.7}
.pill.open{background:var(--sec-stuck);color:var(--open)}
.pill.half{background:var(--sec-stuck);color:var(--half)}
.pill.done{background:var(--sec-key);color:var(--done)}
.pill.due{background:var(--accent);color:var(--plate);font-weight:600}
.pill.quiet{background:var(--sec-answer);color:var(--muted)}
.dead{border-style:dashed;opacity:.72}
.cites{margin:26px 0 0;padding-top:16px;border-top:1px solid var(--line)}
.cites h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
margin:0 0 10px}
.cite{margin:0 0 8px;font-size:14px}
.cite code{font-size:12.5px}
.note{margin-top:26px;font-size:12.5px;color:var(--muted);line-height:1.75}
"""

JS = """
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

  // Counts baked in at build time are a snapshot; with serve.py behind the
  // page they are replaced by the real ones. Due counts especially: yesterday's
  // is wrong every single day.
  fetch('/_pa/library').then(function(r){ return r.ok?r.json():null; }).then(function(d){
    if(!d) return;
    d.papers.forEach(function(p){
      var el=document.querySelector('[data-slug="'+CSS.escape(p.slug)+'"]');
      if(!el) return;
      var due=el.querySelector('.pill.due');
      if(due){
        due.textContent='今天要複習 '+p.due;
        due.hidden=!p.due;
      }
      var sched=el.querySelector('.pill.sched');
      if(sched){ sched.textContent=p.tracked?('排程 '+p.tracked+' 張'):'還沒有排程'; }
      var pts=el.querySelector('.pill.points');
      if(pts){ pts.textContent='要點 '+p.points; }
    });
    var s=document.getElementById('stamp');
    if(s) s.textContent='數字為即時（server 在跑）';
  }).catch(function(){});
})();
"""


def esc(text) -> str:
    return html.escape(str(text or ""))


def render(registry: Path) -> str:
    papers = library.entries(registry)
    edges = library.citation_edges(papers)
    named = {p["slug"]: p["title"] for p in papers}

    cards = []
    for paper in papers:
        if not paper["alive"]:
            cards.append(
                f'<div class="paper dead" data-slug="{esc(paper["slug"])}">'
                f'<h2>{esc(paper["title"])}</h2>'
                f'<div class="pfacts">登記的位置找不到筆記：<code>{esc(paper["work"])}</code>'
                "<br>資料夾可能搬走了。改 papers.yml 的 work，或重跑 probe.py。</div></div>"
            )
            continue
        catalog = library.read_catalog(paper["work"]) or {}
        tally = {"open": 0, "half": 0, "resolved": 0}
        for card in catalog.get("cards") or []:
            key = str(card.get("status") or "open")
            tally[key] = tally.get(key, 0) + 1
        review = catalog.get("review") or {}
        facts = [f"Tier {paper['tier']}" if paper.get("tier") else "", str(paper.get("year") or "")]
        pills = []
        if tally["open"]:
            pills.append(f'<span class="pill open">未解決 {tally["open"]}</span>')
        if tally["half"]:
            pills.append(f'<span class="pill half">半懂 {tally["half"]}</span>')
        if tally["resolved"]:
            pills.append(f'<span class="pill done">已解決 {tally["resolved"]}</span>')
        points = len(catalog.get("points") or [])
        # Distinct classes, not two ".quiet": the live update looks each one up
        # by name, and a shared class means it overwrites whichever comes first.
        pills.append(f'<span class="pill quiet points">要點 {points}</span>')
        due = int(review.get("due") or 0)
        pills.append(
            f'<span class="pill due"{"" if due else " hidden"}>今天要複習 {due}</span>'
        )
        pills.append(
            f'<span class="pill quiet sched">'
            + (f'排程 {review.get("tracked", 0)} 張' if review.get("tracked") else "還沒有排程")
            + "</span>"
        )
        cards.append(
            f'<a class="paper" data-slug="{esc(paper["slug"])}" '
            f'href="/p/{esc(paper["slug"])}/">'
            f'<h2>{esc(paper["title"])}</h2>'
            f'<div class="pfacts">{esc(" · ".join(f for f in facts if f))}'
            f' · <code>{esc(paper["slug"])}</code></div>'
            f"<div>{''.join(pills)}</div></a>"
        )

    cite_html = ""
    if edges:
        rows = "".join(
            f'<div class="cite">'
            f'<code>{esc(e["from"])}</code> 的參考文獻 [{esc(e["n"])}] → '
            f'<code>{esc(e["to"])}</code>　{esc(named.get(e["to"], ""))}</div>'
            for e in edges
        )
        cite_html = f'<div class="cites"><h2>互相引用</h2>{rows}</div>'

    alive = sum(1 for p in papers if p["alive"])
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>書房 — {alive} 篇論文</title>
{THEME_BOOT}
<style>{(ASSETS / "style.css").read_text(encoding="utf-8")}</style>
<style>{CSS}</style>
</head>
<body>
<main id="main">
<div class="lhead">
<h1>書房</h1>
<div class="lmeta">{alive} 篇論文 · 產生於 {date.today().isoformat()} ·
<span id="stamp">數字為上次建置時的快照</span></div>
</div>
{''.join(cards) or '<div class="qempty">登記簿裡還沒有論文。</div>'}
{cite_html}
<div class="note">
論文連結只有在 <code>serve.py --library</code> 跑著時才打得開——每篇論文掛在自己的
路徑底下，各自只開放自己的資料夾。<br>
這一頁由 <code>build_library.py</code> 產生，改 <code>papers.yml</code> 後重跑即可。
</div>
</main>
<button id="theme">🌗 跟隨系統</button>
<script>{JS}</script>
</body>
</html>
"""


def main(argv) -> int:
    args = cli.positionals(argv, value_flags={"--to"})
    start = Path(args[0] if args else ".").resolve()
    registry = library.find_registry(start)
    if registry is None:
        print(f"還沒有論文登記簿。從 {start} 往上找不到 {library.REGISTRY_NAME}。")
        print("對任何一篇論文執行 probe.py 就會建立一份。")
        return 0

    target = cli.flag(argv, "to", "") or ""
    out = Path(target).resolve() if target else registry.parent / "library.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(registry), encoding="utf-8", newline="\n")

    papers = library.entries(registry)
    alive = sum(1 for p in papers if p["alive"])
    size = out.stat().st_size / 1024
    print(f"書房頁  {alive}/{len(papers)} 篇 · {size:,.0f} KB")
    print(f"        {out}")
    for paper in papers:
        if not paper["alive"]:
            print(f"  🟡 {paper['slug']} 登記的位置找不到筆記：{paper['work']}")
        elif library.read_catalog(paper["work"]) is None:
            print(f"  🟡 {paper['slug']} 還沒有 catalog.json，跑一次 build_annotated.py")
    print("        用 serve.py --library 開，論文連結才會通")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
