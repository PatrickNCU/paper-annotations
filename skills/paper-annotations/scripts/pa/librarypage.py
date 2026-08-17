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
/* Text sitting on top of a filled --accent block. --plate is white in the
   light palette and reads fine, but in the dark one it is near-white on a pale
   orange accent -- about 1.6:1, which is not readable at 12px. A category with
   its own colour gets this worked out arithmetically (--tc-ink below); the
   default accent only needs it stated once per theme. */
:root{--accent-ink:#fff}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--accent-ink:#20170e}}
:root[data-theme="dark"]{--accent-ink:#20170e}
#main{max-width:900px}
.lhead{margin:0 0 24px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.lhead h1{margin:0 0 6px;font-size:1.6em}
.lmeta{font-size:13px;color:var(--muted)}
.paper{display:block;margin:0 0 14px;padding:15px 18px;border:1px solid var(--line);
border-radius:10px;background:var(--card);color:inherit;text-decoration:none;
scroll-margin-top:22px}
.paper:hover{border-color:var(--accent)}
body.offline .paper:hover{border-color:var(--line)}
.paper h2{margin:0 0 4px;font-size:1.04em;line-height:1.5}
.pfacts{font-size:12.5px;color:var(--muted)}
.pill{display:inline-block;margin:6px 6px 0 0;padding:2px 9px;border-radius:11px;
font-size:12px;line-height:1.7}
.pill.open{background:var(--sec-stuck);color:var(--open)}
.pill.half{background:var(--sec-stuck);color:var(--half)}
.pill.done{background:var(--sec-key);color:var(--done)}
.pill.due{background:var(--accent);color:var(--accent-ink);font-weight:600}
.pill.quiet{background:var(--sec-answer);color:var(--muted)}
.dead{border-style:dashed;opacity:.72}
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
/* Every colour below reads through --tc with the old value as its fallback, so
   a category that was never given one renders byte-for-byte as it did before
   colours existed. --tc-ink is the readable text colour on top of --tc and
   --tc-dim is the same hue at low alpha; both are computed at build time
   because CSS cannot work out a contrasting colour by itself. */
.tbar{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 22px;align-items:center}
.tslot{display:inline-flex;align-items:center;gap:4px}
.tfilter{padding:5px 12px;border:1px solid var(--tc,var(--line));border-radius:14px;
background:var(--bg);color:var(--tc,var(--muted));font:inherit;font-size:13px;cursor:pointer}
.tfilter:hover{border-color:var(--tc,var(--accent));color:var(--tc,var(--accent));
background:var(--tc-dim,var(--bg))}
.tfilter.on{background:var(--tc,var(--accent));border-color:var(--tc,var(--accent));
color:var(--tc-ink,var(--accent-ink))}
/* A category with nothing in it still belongs on the bar -- otherwise creating
   one looks exactly like failing to create one. Dashed and faded says empty. */
.tfilter.bare{border-style:dashed;opacity:.62}
.tn{margin-left:6px;font-size:.86em;opacity:.75}
#tnew,#tedit{padding:5px 12px;border:1px dashed var(--line);border-radius:14px;
background:none;color:var(--muted);font:inherit;font-size:13px;cursor:pointer}
#tnew:hover,#tedit:hover{border-color:var(--accent);color:var(--accent)}
#tedit.on{border-style:solid;border-color:var(--accent);color:var(--accent)}
/* The per-category controls only exist inside 管理分類: three extra buttons on
   every chip would drown the one thing the bar is for, which is filtering. */
.tcolor,.treset,.tkill{display:none}
body.tediting .tcolor,body.tediting .treset,body.tediting .tkill{display:inline-block}
.tcolor{width:24px;height:24px;padding:0;border:1px solid var(--line);border-radius:6px;
background:none;cursor:pointer;vertical-align:middle}
.treset,.tkill{padding:2px 7px;border:1px solid var(--line);border-radius:7px;
background:var(--bg);color:var(--muted);font:inherit;font-size:12px;line-height:1.5;
cursor:pointer}
.treset:hover{border-color:var(--accent);color:var(--accent)}
.tkill:hover{border-color:var(--open);color:var(--open)}
#thelp{display:none;margin:-12px 0 18px;font-size:12.5px;color:var(--muted);line-height:1.8}
body.tediting #thelp{display:block}
#tform{display:flex;gap:8px;margin:0 0 20px;flex-wrap:wrap;align-items:center}
#tname{flex:1 1 220px;padding:6px 11px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--fg);font:inherit;font-size:14px}
#tform button{padding:6px 14px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--fg);font:inherit;font-size:13px;cursor:pointer}
#tform input[type=color]{width:34px;height:32px;padding:0;border:1px solid var(--line);
border-radius:8px;background:none;cursor:pointer}
#tok{border-color:var(--accent);color:var(--accent)}
.tmk{border-style:dashed !important}
/* A topic the reader chose and one we guessed must not look the same. */
.topics{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px;padding-top:10px;
border-top:1px dashed var(--line)}
.tchip{padding:3px 10px;border:1px solid var(--tc,var(--line));border-radius:12px;
background:var(--tc-dim,var(--sec-answer));color:var(--tc,var(--fg));font:inherit;
font-size:12px;cursor:pointer}
.tchip.auto{border-style:dashed;color:var(--tc,var(--muted))}
.tchip:hover{border-color:var(--open);color:var(--open)}
.tchip::after{content:"";margin-left:0}
.tchip:hover::after{content:" ✕";margin-left:1px}
.tadd{padding:3px 10px;border:1px dashed var(--line);border-radius:12px;
background:none;color:var(--muted);font:inherit;font-size:12px;cursor:pointer}
.tadd:hover{border-color:var(--accent);color:var(--accent)}
/* Pressed, it stays lit until pressed again -- the picker below it is a mode,
   and a mode with no visible state is a mode nobody knows how to leave. */
.tadd.on{border-style:solid;border-color:var(--accent);background:var(--accent);
color:var(--accent-ink);box-shadow:0 0 0 3px var(--sel)}
.tpick{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;width:100%}
.tpick button{padding:3px 10px;border:1px solid var(--accent);border-radius:12px;
background:var(--bg);color:var(--accent);font:inherit;font-size:12px;cursor:pointer}
.thint{width:100%;margin:0 0 2px;font-size:12px;color:var(--muted);line-height:1.6}
#tsay{margin-left:8px;font-size:12px;color:var(--muted)}
/* Citations sit on the card that makes the claim, not in a table at the foot of
   the page: "who does this one talk to" is a question about this paper. */
.cxs{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;padding-top:9px;
border-top:1px dashed var(--line)}
.cx{max-width:100%;padding:3px 10px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--muted);font:inherit;font-size:12.5px;line-height:1.65;
text-align:left;cursor:pointer}
.cx:hover{border-color:var(--accent);color:var(--accent)}
.cx b{font-weight:600;color:var(--fg)}
.cx:hover b{color:var(--accent)}
.cn{margin-left:5px;opacity:.7}
/* Jumping to a card that looks like every other card is jumping nowhere. */
@keyframes ping{
0%{border-color:var(--accent);box-shadow:0 0 0 0 var(--sel)}
70%{border-color:var(--accent);box-shadow:0 0 0 11px rgba(128,128,128,0)}
100%{border-color:var(--line);box-shadow:0 0 0 0 rgba(128,128,128,0)}
}
.paper.ping,.tfilter.ping{animation:ping .85s ease-out 2}
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
    document.body.classList.add('offline');
    // a.ptitle, not a.paper: the card is a div and the link is the title
    // inside it, so the old selector matched nothing and every dead link
    // stayed clickable under a banner saying it was not.
    [].slice.call(document.querySelectorAll('a.ptitle')).forEach(function(a){
      a.classList.add('dead');
      a.removeAttribute('href');
      a.setAttribute('title','需要 serve.py --library 才打得開');
    });
  }

  function say(msg){
    var s=document.getElementById('stamp');
    if(s) s.textContent=msg;
  }
  // Every write reloads the page, which would otherwise throw away all trace
  // of what just happened -- including whether it happened at all. What to
  // point at afterwards is parked here across the reload.
  var flash=null;
  try{
    var raw=sessionStorage.getItem('pa-flash');
    if(raw){ flash=JSON.parse(raw); sessionStorage.removeItem('pa-flash'); }
  }catch(e){}

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
  var allCards=[].slice.call(document.querySelectorAll('.paper'));
  function has(card,topic){
    var mine=(card.dataset.topics||'').split(' ').filter(Boolean);
    if(topic==='_none') return mine.length===0;
    return mine.indexOf(topic)>=0;
  }
  function applyFilter(want){
    var shown=0;
    allCards.forEach(function(c){
      var ok = !want || has(c,want);
      c.hidden=!ok;
      if(ok) shown++;
    });
    document.getElementById('tempty').hidden = shown>0;
  }
  function chipFor(topic){
    for(var i=0;i<filters.length;i++){
      if(filters[i].dataset.topic===topic) return filters[i];
    }
    return null;
  }
  function select(topic){
    var want=chipFor(topic)||filters[0];
    filters.forEach(function(x){ x.classList.toggle('on',x===want); });
    applyFilter(want.dataset.topic);
    return want;
  }
  filters.forEach(function(b){
    b.addEventListener('click',function(){ select(b.dataset.topic); });
  });
  // Restarting an animation needs the class gone and a layout read in between,
  // or a second click on the same target does nothing at all.
  function ping(el){
    if(!el) return;
    el.classList.remove('ping');
    void el.offsetWidth;
    el.classList.add('ping');
  }

  // ---- 引用：跳過去並讓對方閃一下 ----------------------------------------
  function jump(slug){
    var card=document.querySelector('.paper[data-slug="'+CSS.escape(slug)+'"]');
    if(!card) return;
    // Scrolling to something the current filter is hiding scrolls to nothing.
    if(card.hidden) select('');
    card.scrollIntoView({behavior:'smooth',block:'center'});
    ping(card);
  }
  [].slice.call(document.querySelectorAll('.cx')).forEach(function(b){
    b.addEventListener('click',function(){ jump(b.dataset.go); });
  });

  // ---- 加入／移除分類 ----------------------------------------------------
  // Writing to papers.yml, so it needs the server -- same rule as saving a
  // highlight or grading a card. Without one the buttons never appear rather
  // than appearing and failing.
  var TOPICS=JSON.parse(document.getElementById('pa-topics').textContent);
  var VOCAB=TOPICS.names;
  var token='';
  function post(body,after){
    return fetch('/_pa/topic',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-PA-Token':token},
      body:JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.error){ say('沒改成：'+d.error); return; }
      var note=after||{};
      // Come back to the category that was being looked at, and keep whatever
      // management mode was open -- a reload that resets the view makes a
      // second edit start from scratch every time.
      var on=document.querySelector('.tfilter.on');
      if(note.sel===undefined) note.sel=on?on.dataset.topic:'';
      // The reply names the category this touched, which is how a brand new
      // one -- whose slug the page could not have known -- gets pointed at.
      if(!note.topic&&d.topic) note.topic=d.topic;
      note.editing=document.body.classList.contains('tediting');
      try{ sessionStorage.setItem('pa-flash',JSON.stringify(note)); }catch(e){}
      location.reload();
    }).catch(function(){ say('沒改成，server 可能停了'); });
  }

  // A category the reader invents ("已讀過") is not a topic of the paper at
  // all, and that is fine -- the shelf is his, not the literature's. Defining
  // one from the page beats hand-editing papers.yml for the one case where he
  // knows exactly what he wants and it does not exist yet.
  var form=document.getElementById('tform');
  var nameBox=document.getElementById('tname');
  var hueBox=document.getElementById('thue');
  var picked=false;      // did the reader actually choose a colour?
  var pendingFor=null;   // set when the new category should also be assigned
  hueBox.addEventListener('input',function(){ picked=true; });
  function openForm(slug){
    pendingFor=slug||null;
    form.hidden=false;
    nameBox.value='';
    picked=false;
    nameBox.focus();
  }
  function submitForm(){
    var name=(nameBox.value||'').trim();
    if(!name){ say('分類名稱不能空白'); return; }
    var body={action:'define',name:name};
    if(picked){ body.color=hueBox.value; }
    if(pendingFor){ body.paper=pendingFor; }
    post(body,{msg:'已建立分類「'+name+'」'+(pendingFor?'，並加到這篇論文':'')});
  }
  document.getElementById('tok').addEventListener('click',submitForm);
  nameBox.addEventListener('keydown',function(e){ if(e.key==='Enter') submitForm(); });
  document.getElementById('tcancel').addEventListener('click',function(){
    form.hidden=true; pendingFor=null;
  });

  function closePick(b){
    var box=b.parentNode.querySelector('.tpick');
    if(box) box.remove();
    b.classList.remove('on');
  }
  function wire(){
    var edit=document.getElementById('tedit');
    document.getElementById('tnew').hidden=false;
    document.getElementById('tnew').addEventListener('click',function(){ openForm(null); });
    edit.hidden=false;
    edit.addEventListener('click',function(){
      var on=document.body.classList.toggle('tediting');
      edit.classList.toggle('on',on);
    });
    [].slice.call(document.querySelectorAll('.tcolor')).forEach(function(inp){
      inp.addEventListener('change',function(){
        post({action:'color',topic:inp.dataset.topic,color:inp.value},
             {topic:inp.dataset.topic,msg:'換了顏色'});
      });
    });
    [].slice.call(document.querySelectorAll('.treset')).forEach(function(b){
      b.addEventListener('click',function(){
        post({action:'color',topic:b.dataset.topic,color:''},
             {topic:b.dataset.topic,msg:'顏色回到預設'});
      });
    });
    [].slice.call(document.querySelectorAll('.tkill')).forEach(function(b){
      b.addEventListener('click',function(){
        if(!confirm('刪掉分類「'+b.dataset.name+'」？')) return;
        // whatever was selected may be the thing being deleted
        post({action:'undefine',topic:b.dataset.topic},
             {sel:'',msg:'已刪掉分類「'+b.dataset.name+'」'});
      });
    });
    [].slice.call(document.querySelectorAll('.tadd')).forEach(function(b){
      b.hidden=false;
      b.title='再按一下取消';
      b.addEventListener('click',function(){
        var card=b.closest('.paper');
        var have=(card.dataset.topics||'').split(' ').filter(Boolean);
        if(b.classList.contains('on')){ closePick(b); return; }
        var left=Object.keys(VOCAB).filter(function(t){ return have.indexOf(t)<0; });
        var box=document.createElement('div');
        box.className='tpick';
        var tip=document.createElement('div');
        tip.className='thint';
        tip.textContent=left.length
          ? '挑一個分類加進這篇論文；再按一次上面的「加入分類」就取消。'
          : '這篇論文已經在所有分類裡了。再按一次上面的「加入分類」就取消。';
        box.appendChild(tip);
        left.forEach(function(t){
          var x=document.createElement('button');
          x.textContent=VOCAB[t];
          if(TOPICS.colors[t]){ x.style.borderColor=TOPICS.colors[t];
                                x.style.color=TOPICS.colors[t]; }
          x.addEventListener('click',function(){
            post({paper:card.dataset.slug,topic:t,action:'add'},
                 {topic:t,msg:'加進「'+VOCAB[t]+'」了'});
          });
          box.appendChild(x);
        });
        var mk=document.createElement('button');
        mk.className='tmk';
        mk.textContent='＋ 自訂新分類';
        mk.addEventListener('click',function(){ openForm(card.dataset.slug); });
        box.appendChild(mk);
        b.parentNode.appendChild(box);
        b.classList.add('on');
      });
    });
    document.addEventListener('keydown',function(e){
      if(e.key!=='Escape') return;
      [].slice.call(document.querySelectorAll('.tadd.on')).forEach(closePick);
      form.hidden=true; pendingFor=null;
    });
    [].slice.call(document.querySelectorAll('.tchip')).forEach(function(c){
      c.title='從這個分類移除';
      c.addEventListener('click',function(){
        var card=c.closest('.paper');
        post({paper:card.dataset.slug,topic:c.dataset.topic,action:'remove'},
             {topic:c.dataset.topic,msg:'移出「'+(VOCAB[c.dataset.topic]||c.dataset.topic)+'」了'});
      });
    });
    if(flash){
      if(flash.editing){ document.body.classList.add('tediting'); edit.classList.add('on'); }
      if(flash.sel!==undefined) select(flash.sel);
      // A category created empty has no papers, so nothing on the page moves;
      // pointing at its chip is the only proof the reader gets that it worked.
      var chip=flash.topic?chipFor(flash.topic):null;
      if(chip){ ping(chip); chip.scrollIntoView({block:'nearest'}); }
      if(flash.msg) say(flash.msg);
    }
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


def tint(color: str) -> str:
    """The inline custom properties a coloured category carries.

    Empty for a category with no colour, which is what keeps the default
    appearance exactly what it was: every rule reads var(--tc, <old value>),
    so an element that declares nothing renders unchanged.
    """
    if not color or not library.COLOR.match(color):
        return ""
    channels = [int(color[i : i + 2], 16) for i in (1, 3, 5)]

    def linear(value: float) -> float:
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    lum = sum(w * linear(c) for w, c in zip((0.2126, 0.7152, 0.0722), channels))
    # Which of black or white sits readably on top is arithmetic, not taste,
    # and CSS has no way to ask -- so it is decided here and written in.
    ink = "#17150f" if lum > 0.35 else "#ffffff"
    dim = "rgba(%d,%d,%d,.16)" % tuple(channels)
    return f" style=\"--tc:{color};--tc-ink:{ink};--tc-dim:{dim}\""


def render(registry: Path) -> str:
    papers = library.entries(registry)
    edges = library.citation_edges(papers)
    named = {p["slug"]: p["title"] for p in papers}
    vocab = library.vocabulary(registry)
    colors = library.topic_colors(registry)

    # A citation belongs on both cards it concerns: the paper that made the
    # reference wants "who am I building on", the paper referenced wants "who
    # picked this up". Same edge, read from either end.
    cites_out, cites_in = {}, {}
    for edge in edges:
        cites_out.setdefault(edge["from"], []).append(edge)
        cites_in.setdefault(edge["to"], []).append(edge)

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
            f'<button class="tchip{"" if own else " auto"}" data-topic="{esc(t)}"'
            f'{tint(colors.get(t, ""))}>{esc(vocab.get(t, t))}</button>'
            for own, t in [(True, t) for t in paper["topics"]]
            + [(False, t) for t in paper["topics_auto"]]
        )
        links = "".join(
            f'<button class="cx" data-go="{esc(e["to"])}">→ 引用了 '
            f'<b>{esc(named.get(e["to"], e["to"]))}</b>'
            f'<span class="cn">[{esc(e["n"])}]</span></button>'
            for e in cites_out.get(paper["slug"], [])
        ) + "".join(
            f'<button class="cx" data-go="{esc(e["from"])}">← 被 '
            f'<b>{esc(named.get(e["from"], e["from"]))}</b> 引用'
            f'<span class="cn">[{esc(e["n"])}]</span></button>'
            for e in cites_in.get(paper["slug"], [])
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
            "</div>"
            + (f'<div class="cxs">{links}</div>' if links else "")
            + "</div>"
        )

    # One card per paper, filtered rather than duplicated. A paper's several
    # topics all show on its own card; the bar decides which papers are listed.
    # Duplicating a paper into one section per topic was the other reading of
    # "show them all", and it turns a shelf of 50 papers into 150 cards.
    counts = {
        slug: sum(1 for p in papers if slug in p["topics"] + p["topics_auto"])
        for slug in vocab
    }
    loose = sum(1 for p in papers if not (p["topics"] + p["topics_auto"]))

    # Every declared category is listed, including the ones nothing is filed
    # under. Hiding the empty ones made creating a category indistinguishable
    # from failing to create one -- the reader typed a name, pressed 建立, and
    # the page came back looking exactly as before.
    bar = [
        '<span class="tslot"><button class="tfilter on" data-topic="">全部'
        f'<span class="tn">{len(papers)}</span></button></span>'
    ]
    for slug, name in vocab.items():
        color = colors.get(slug, "")
        controls = (
            f'<input class="tcolor" type="color" data-topic="{esc(slug)}" '
            f'value="{esc(color or "#8a4f24")}" title="換一個顏色">'
        )
        if color:
            controls += (
                f'<button class="treset" data-topic="{esc(slug)}" '
                'title="回到預設顏色">↺</button>'
            )
        if not counts[slug]:
            # Only ever offered for an empty category, so deleting one cannot
            # take a paper's filing down with it.
            controls += (
                f'<button class="tkill" data-topic="{esc(slug)}" '
                f'data-name="{esc(name)}" title="刪掉這個分類">✕</button>'
            )
        bar.append(
            f'<span class="tslot">'
            f'<button class="tfilter{"" if counts[slug] else " bare"}" '
            f'data-topic="{esc(slug)}"{tint(color)}>{esc(name)}'
            f'<span class="tn">{counts[slug]}</span></button>{controls}</span>'
        )
    if loose:
        bar.append(
            f'<span class="tslot"><button class="tfilter" data-topic="_none">未分類'
            f'<span class="tn">{loose}</span></button></span>'
        )
    bar.append('<button id="tnew" hidden>＋ 新增分類</button>')
    bar.append('<button id="tedit" hidden>⚙ 管理分類</button>')

    listing = (
        "".join(cards[p["slug"]] for p in papers)
        or '<div class="qempty">登記簿裡還沒有論文。</div>'
    )

    alive = sum(1 for p in papers if p["alive"])
    vocab_json = json.dumps(
        {"names": vocab, "colors": colors}, ensure_ascii=False
    ).replace("</", "<\\/")
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
<div id="thelp">每個分類旁邊的色塊可以換顏色，<b>↺</b> 回到預設，<b>✕</b> 刪掉分類——
只有沒有任何論文的分類刪得掉。顏色深淺兩種主題共用，選中間調的最保險。</div>
<div id="tform" hidden><input id="tname" type="text" placeholder="分類名稱，例如「已讀過」" maxlength="40">
<input id="thue" type="color" value="#8a4f24" title="這個分類的顏色（不改就用預設樣式）">
<button id="tok">建立</button><button id="tcancel">取消</button></div>
<div id="tlist">{listing}</div>
<div id="tempty" hidden class="qempty">這個分類底下還沒有論文。</div>
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
    # A topic nobody declared gets no chip on the filter bar, so nothing can be
    # filtered by it and its display name is whatever the slug happens to be.
    for topic in undefined:
        print(f"  ⚠️  分類 {topic} 沒有定義，篩選列上不會有它，也沒有顯示名稱")
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
