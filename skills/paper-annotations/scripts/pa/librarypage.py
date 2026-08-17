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
/* Above the list, not under it: this is the thing to read before clicking. */
#offline{margin:0 0 20px;padding:13px 16px;border-radius:10px;line-height:1.8;
border:1px solid var(--half);background:var(--sec-stuck);font-size:14px}
#offline b{color:var(--half)}
#offline code{display:inline-block;margin-top:6px;padding:3px 9px;border-radius:6px;
background:var(--plate);color:#22201d;font-size:13px}
.paper.dead{cursor:default}
.paper.dead:hover{border-color:var(--line)}
a.ptitle{display:block;color:inherit;text-decoration:none}
/* The filter bar and the section headings share a vocabulary on purpose: the
   chip you press and the block it takes you to read the same. */
.tbar{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 22px}
.tfilter{padding:5px 12px;border:1px solid var(--line);border-radius:14px;
background:var(--bg);color:var(--muted);font:inherit;font-size:13px;cursor:pointer}
.tfilter:hover{border-color:var(--accent);color:var(--accent)}
.tfilter.on{background:var(--accent);border-color:var(--accent);color:var(--plate)}
.tn{margin-left:6px;font-size:.86em;opacity:.75}
.tsec{margin:0 0 30px}
.th{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;
color:var(--muted)}
/* A topic the reader chose and one we guessed must not look the same. */
.topics{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px;padding-top:10px;
border-top:1px dashed var(--line)}
.tchip{padding:3px 10px;border:1px solid var(--line);border-radius:12px;
background:var(--sec-answer);color:var(--fg);font:inherit;font-size:12px;cursor:pointer}
.tchip.auto{border-style:dashed;color:var(--muted)}
.tchip:hover{border-color:var(--open);color:var(--open)}
.tchip::after{content:"";margin-left:0}
.tchip:hover::after{content:" ✕";margin-left:1px}
.tadd{padding:3px 10px;border:1px dashed var(--line);border-radius:12px;
background:none;color:var(--muted);font:inherit;font-size:12px;cursor:pointer}
.tadd:hover{border-color:var(--accent);color:var(--accent)}
.tpick{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;width:100%}
.tpick button{padding:3px 10px;border:1px solid var(--accent);border-radius:12px;
background:var(--bg);color:var(--accent);font:inherit;font-size:12px;cursor:pointer}
#tsay{margin-left:8px;font-size:12px;color:var(--muted)}
"""

JS = """
(function(){
  // Opened by double-click, every paper link is dead: they are absolute /p/…
  // paths that only a running server can answer, and from file:// they resolve
  // to nowhere. Saying so in a footnote is saying so too late -- you click
  // first and read the small print afterwards. So the page checks where it is
  // and puts the answer above everything else, with the command to run.
  var live=(location.protocol==='http:'||location.protocol==='https:');
  if(!live){
    var warn=document.getElementById('offline');
    if(warn) warn.hidden=false;
    [].slice.call(document.querySelectorAll('a.paper')).forEach(function(a){
      a.classList.add('dead');
      a.removeAttribute('href');
      a.setAttribute('title','需要 serve.py --library 才打得開');
    });
  }

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
  // A paper in three topics is rendered three times, so every update has to
  // touch all of its copies -- querySelector would silently refresh only the
  // first section and leave the others showing yesterday.
  fetch('/_pa/library').then(function(r){ return r.ok?r.json():null; }).then(function(d){
    if(!d) return;
    d.papers.forEach(function(p){
      [].slice.call(document.querySelectorAll('.paper[data-slug="'+CSS.escape(p.slug)+'"]'))
        .forEach(function(el){
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
    });
    var s=document.getElementById('stamp');
    if(s) s.textContent='數字為即時（server 在跑）';
  }).catch(function(){});

  // ---- 分類篩選 ---------------------------------------------------------
  var filters=[].slice.call(document.querySelectorAll('.tfilter'));
  var secs=[].slice.call(document.querySelectorAll('.tsec'));
  filters.forEach(function(b){
    b.addEventListener('click',function(){
      var want=b.dataset.topic;
      filters.forEach(function(x){ x.classList.toggle('on',x===b); });
      secs.forEach(function(s){ s.hidden = !!want && s.dataset.topic!==want; });
    });
  });

  // ---- 加入／移除分類 ----------------------------------------------------
  // Writing to papers.yml, so it needs the server -- same rule as saving a
  // highlight or grading a card. Without one the buttons never appear rather
  // than appearing and failing.
  var VOCAB=JSON.parse(document.getElementById('pa-topics').textContent);
  var token='';
  function say(msg){
    var s=document.getElementById('stamp');
    if(s) s.textContent=msg;
  }
  function post(slug,topic,action){
    return fetch('/_pa/topic',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-PA-Token':token},
      body:JSON.stringify({paper:slug,topic:topic,action:action})
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.error){ say('沒改成：'+d.error); return; }
      location.reload();
    }).catch(function(){ say('沒改成，server 可能停了'); });
  }
  function wire(){
    [].slice.call(document.querySelectorAll('.tadd')).forEach(function(b){
      b.hidden=false;
      b.addEventListener('click',function(){
        var card=b.closest('.paper');
        var have=(card.dataset.topics||'').split(' ').filter(Boolean);
        var old=card.querySelector('.tpick');
        if(old){ old.remove(); return; }
        var left=Object.keys(VOCAB).filter(function(t){ return have.indexOf(t)<0; });
        var box=document.createElement('div');
        box.className='tpick';
        if(!left.length){
          box.textContent='已經在全部分類裡了。要新增分類請改 papers.yml 的 topics。';
        } else {
          left.forEach(function(t){
            var x=document.createElement('button');
            x.textContent=VOCAB[t];
            x.addEventListener('click',function(){ post(card.dataset.slug,t,'add'); });
            box.appendChild(x);
          });
        }
        b.parentNode.appendChild(box);
      });
    });
    [].slice.call(document.querySelectorAll('.tchip')).forEach(function(c){
      c.title='從這個分類移除';
      c.addEventListener('click',function(){
        var card=c.closest('.paper');
        post(card.dataset.slug,c.dataset.topic,'remove');
      });
    });
  }
  if(live){
    fetch('/_pa/hello',{headers:{'Accept':'application/json'}})
      .then(function(r){ return r.ok?r.json():null; })
      .then(function(d){ if(d&&d.token){ token=d.token; wire(); } })
      .catch(function(){});
  }
})();
"""


def esc(text) -> str:
    return html.escape(str(text or ""))


def render(registry: Path) -> str:
    papers = library.entries(registry)
    edges = library.citation_edges(papers)
    named = {p["slug"]: p["title"] for p in papers}
    vocab = library.vocabulary(registry)

    # A topic used by a paper but never defined would otherwise become a
    # silent extra section, and "3d-ic" beside "3D-IC" is exactly the drift the
    # vocabulary exists to prevent. Collected here and reported by main().
    undefined = set()
    for paper in papers:
        for topic in paper["topics"] + paper["topics_auto"]:
            if topic not in vocab:
                undefined.add(topic)

    cards = {}
    for paper in papers:
        if not paper["alive"]:
            cards[paper["slug"]] = (
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
        # Topic chips carry their own origin, same rule as suggested cards and
        # agent-written points: the reader must always be able to tell which
        # of these he decided and which one of us guessed.
        chips = "".join(
            f'<button class="tchip{"" if own else " auto"}" data-topic="{esc(t)}">'
            f'{esc(vocab.get(t, t))}</button>'
            for own, t in [(True, t) for t in paper["topics"]]
            + [(False, t) for t in paper["topics_auto"]]
        )
        cards[paper["slug"]] = (
            f'<div class="paper" data-slug="{esc(paper["slug"])}" '
            f'data-topics="{esc(" ".join(paper["topics"] + paper["topics_auto"]))}">'
            f'<a class="ptitle" href="/p/{esc(paper["slug"])}/">'
            f'<h2>{esc(paper["title"])}</h2>'
            f'<div class="pfacts">{esc(" · ".join(f for f in facts if f))}'
            f' · <code>{esc(paper["slug"])}</code></div>'
            f"<div>{''.join(pills)}</div></a>"
            f'<div class="topics">{chips}'
            '<button class="tadd" hidden>＋ 加入分類</button>'
            "</div></div>"
        )

    # Sections in vocabulary order, then whatever is filed nowhere. A paper in
    # three topics is rendered three times -- that is the point of the layout,
    # and the chip filter is what stops it becoming a wall once the shelf grows.
    groups, loose = [], []
    for slug, name in vocab.items():
        members = [p for p in papers if slug in p["topics"] + p["topics_auto"]]
        if members:
            groups.append((slug, name, members))
    loose = [p for p in papers if not (p["topics"] + p["topics_auto"])]

    bar = ['<button class="tfilter on" data-topic="">全部</button>']
    bar += [
        f'<button class="tfilter" data-topic="{esc(slug)}">{esc(name)}'
        f'<span class="tn">{len(members)}</span></button>'
        for slug, name, members in groups
    ]
    if loose:
        bar.append(
            f'<button class="tfilter" data-topic="_none">未分類'
            f'<span class="tn">{len(loose)}</span></button>'
        )

    sections = [
        f'<section class="tsec" data-topic="{esc(slug)}">'
        f'<h2 class="th">{esc(name)}<span class="tn">{len(members)}</span></h2>'
        + "".join(cards[p["slug"]] for p in members)
        + "</section>"
        for slug, name, members in groups
    ]
    if loose:
        sections.append(
            '<section class="tsec" data-topic="_none">'
            '<h2 class="th">未分類<span class="tn">' + str(len(loose)) + "</span></h2>"
            + "".join(cards[p["slug"]] for p in loose)
            + "</section>"
        )
    if not sections:
        sections = ['<div class="qempty">登記簿裡還沒有論文。</div>']

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
    vocab_json = json.dumps(vocab, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html>
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
<div id="offline" hidden>
<b>這是從磁碟直接開的，下面的論文連結點不動。</b><br>
論文各自掛在 server 的路徑底下，要有 server 在跑才連得過去。點兩下同一層的
<b>開啟書房</b>，或執行：<br>
<code>python &lt;scripts&gt;/serve.py --library</code>
</div>
<div class="tbar">{''.join(bar)}</div>
{''.join(sections)}
{cite_html}
<div class="note">
論文連結只有在 <code>serve.py --library</code> 跑著時才打得開——每篇論文掛在自己的
路徑底下，各自只開放自己的資料夾。<br>
這一頁由 <code>build_library.py</code> 產生，改 <code>papers.yml</code> 後重跑即可。
</div>
</main>
<button id="theme">🌗 跟隨系統</button>
<script id="pa-topics" type="application/json">{vocab_json}</script>
<script>{JS}</script>
</body>
</html>
"""
    return page, sorted(undefined)


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
    page, undefined = render(registry)
    out.write_text(page, encoding="utf-8", newline="\n")

    papers = library.entries(registry)
    alive = sum(1 for p in papers if p["alive"])
    size = out.stat().st_size / 1024
    print(f"書房頁  {alive}/{len(papers)} 篇 · {size:,.0f} KB")
    print(f"        {out}")
    # A topic nobody declared gets no section, so the paper filed under it just
    # is not there -- silently. Say so instead.
    for topic in undefined:
        print(f"  ⚠️  分類 {topic} 沒有定義，用到它的論文不會出現在任何區塊")
    if undefined:
        print("      把它加進 papers.yml 的 topics（slug: 顯示名稱）就好")
    for paper in papers:
        if not paper["alive"]:
            print(f"  🟡 {paper['slug']} 登記的位置找不到筆記：{paper['work']}")
        elif library.read_catalog(paper["work"]) is None:
            print(f"  🟡 {paper['slug']} 還沒有 catalog.json，跑一次 build_annotated.py")
    print("        用 serve.py --library 開，論文連結才會通")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
