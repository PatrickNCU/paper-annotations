"""Render the annotated Markdown into one self-contained review page.

Reads what build_annotated.py already produced -- so question placement is
decided in exactly one place and the two views can never disagree.

Usage:
    python build_html.py <paper_root> [--embed-assets]

--embed-assets inlines every image as a data: URI, producing one large file
that can be sent to someone else as-is. Without it, images are referenced by
relative path (much smaller and faster to open).
"""

from __future__ import annotations

import base64
import html
import mimetypes
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import minimd
import miniyaml
import paperkit

paperkit.bootstrap()

VENDOR = Path(__file__).resolve().parent / "vendor" / "katex"

# Runs before the body paints, so a reader who picked dark never sees a white
# flash on load. file:// may refuse localStorage, hence the try/catch.
THEME_BOOT = """<script>
(function(){try{var t=localStorage.getItem("pa-theme");
if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}catch(e){}})();
</script>"""

KATEX_INIT = """
document.addEventListener("DOMContentLoaded", function(){
  // the sidebar too: question labels quote formulas straight from the paper
  ["main","side"].forEach(function(id){
    var el=document.getElementById(id);
    if(!el) return;
    renderMathInElement(el, {
      delimiters:[{left:"$$",right:"$$",display:true},{left:"$",right:"$",display:false}],
      ignoredClasses:["no-math"], throwOnError:false, strict:false
    });
  });
});
"""


def katex_assets() -> str:
    """Inline KaTeX (CSS + fonts + JS) so the page renders math with no network.

    Fonts become data: URIs and the woff/ttf fallbacks are dropped, because only
    woff2 is vendored -- leaving them would make the browser chase dead paths.
    """
    if not (VENDOR / "katex.min.js").is_file():
        raise SystemExit(
            f"找不到 KaTeX：{VENDOR}\n"
            "請重新取得：npm pack katex，並把 dist 的 css/js/fonts 放進 vendor/katex/"
        )
    css = (VENDOR / "katex.min.css").read_text(encoding="utf-8")

    def font(match):
        path = VENDOR / "fonts" / match.group(1)
        if not path.is_file():
            return match.group(0)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'url(data:font/woff2;base64,{data}) format("woff2")'

    css = re.sub(r'url\(fonts/([\w.-]+\.woff2)\)\s*format\("woff2"\)', font, css)
    css = re.sub(r',\s*url\(fonts/[^)]+\)\s*format\("(?:woff|truetype)"\)', "", css)

    js = (VENDOR / "katex.min.js").read_text(encoding="utf-8")
    auto = (VENDOR / "auto-render.min.js").read_text(encoding="utf-8")
    return (
        f"<style>{css}</style>\n"
        f"<script>{js}</script>\n<script>{auto}</script>\n<script>{KATEX_INIT}</script>"
    )

STYLE = """
/* Light is the base palette; dark is applied either by system preference
   (unless the reader forced light) or by an explicit data-theme="dark". */
:root{--bg:#fbfaf7;--fg:#22201d;--muted:#6d685f;--line:#e4dfd5;--card:#f5f2ea;
--sidebar:#f2efe8;--accent:#8a4f24;--open:#b3261e;--half:#96631a;--done:#2f6f4a;
--plate:#fff;--shadow:rgba(0,0,0,.05);--mark:#f7e3a9;
--sec-stuck:#fdf1e3;--sec-answer:#f8f7f3;--sec-key:#edf3ee;
--sel:rgba(138,79,36,.20)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#15161a;--fg:#e8e5de;--muted:#9b978e;--line:#32353c;--card:#1e2026;
--sidebar:#191b20;--accent:#e0a76a;--open:#f0776a;--half:#e8b04b;--done:#6fc796;
--plate:#e9e7e2;--shadow:rgba(0,0,0,.35);--mark:#4a3a1f;
--sec-stuck:#2a2118;--sec-answer:#1b1d22;--sec-key:#17231e;
--sel:rgba(224,167,106,.26)}}
:root[data-theme="dark"]{
--bg:#15161a;--fg:#e8e5de;--muted:#9b978e;--line:#32353c;--card:#1e2026;
--sidebar:#191b20;--accent:#e0a76a;--open:#f0776a;--half:#e8b04b;--done:#6fc796;
--plate:#e9e7e2;--shadow:rgba(0,0,0,.35);--mark:#4a3a1f;
--sec-stuck:#2a2118;--sec-answer:#1b1d22;--sec-key:#17231e;
--sel:rgba(224,167,106,.26)}
*{box-sizing:border-box}
/* The sentence a card is anchored to. Tinted, never the browser's
   default yellow-on-black, which ignores the palette entirely. */
mark{background:var(--mark);color:inherit;padding:.05em .15em;border-radius:3px}
mark.off{background:none;padding:0}
/* Selection: the browser default is an opaque blue that swallows glyph colour,
   and across KaTeX's many small spans it reads as a broken band. A translucent
   tint keeps the text its own colour and blends the boxes into one wash. */
::selection{background:var(--sel);color:inherit;text-shadow:none}
::-moz-selection{background:var(--sel);color:inherit;text-shadow:none}
/* A rendered formula is taken whole rather than half-caught mid-symbol. */
.katex{user-select:all;-webkit-user-select:all}
/* Inside a formula the browser paints one selection box per span -- for a
   single sentence that measured 72 boxes at 8 different heights, which is the
   ragged, patchy band you see. Those are switched off; script.js lights the
   whole formula instead, one flat block per line. */
.katex ::selection{background:transparent}
.katex::selection{background:transparent}
.katex.sel .katex-base{background:var(--sel);border-radius:3px}
/* KaTeX emits the formula twice -- hidden MathML for screen readers, spans for
   sight -- and selecting it copied both, so every pasted formula came out
   doubled. The MathML stays for assistive tech; it just is not selectable. */
.katex-mathml{user-select:none;-webkit-user-select:none}
/* The three parts of an opened card, each its own block. */
.csec{margin:12px 0;padding:10px 14px 2px;border-radius:8px;
border-left:3px solid var(--line);background:var(--sec-answer)}
.csec-t{display:block;margin-bottom:2px;font-size:.82em;letter-spacing:.04em;color:var(--muted)}
.csec p:last-child{margin-bottom:10px}
.csec-stuck{background:var(--sec-stuck);border-left-color:var(--half)}
.csec-stuck .csec-t{color:var(--half)}
.csec-answer{background:var(--sec-answer);border-left-color:var(--line)}
.csec-key{background:var(--sec-key);border-left-color:var(--done)}
.csec-key .csec-t{color:var(--done)}
/* Colour changes ease across; layout and motion are left alone. Scoped to the
   surfaces that actually carry a palette colour rather than "*", so a 30000px
   page does not repaint every node. Nested text inherits the animating value,
   so rendered formulas fade with their container. */
@media(prefers-reduced-motion:no-preference){
body,#side,#main,#side a,.controls button,.controls select,.controls input,
.qcard,.qcard>summary,.banner,.meta,blockquote,pre,code,table,th,td,img,
.footnotes,.fn-key,.dot,.qtext,a.qlink,mark,.csec,.csec-t{
transition:background-color .3s ease,color .3s ease,border-color .3s ease,
box-shadow .3s ease,outline-color .3s ease}}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:-apple-system,"Segoe UI","Noto Sans TC",system-ui,sans-serif;
line-height:1.75;font-size:16.5px}
#layout{display:block}
/* The sidebar floats over the paper rather than sitting beside it: opening it
   used to reflow the text mid-sentence, which is the last thing you want while
   reading. Hovering the tab slides it in; the paper does not move at all. */
/* The drawer and its handle move as one piece, and the handle sits flush
   against the drawer's edge. That contiguity is what makes hover stable: at
   every point of the slide, the pointer that opened it is still over one of
   the two. Hiding the handle on hover -- the obvious way to write this --
   makes the drawer flicker open and shut, because the moment it disappears
   the hover is lost and the drawer starts sliding back. */
#sidewrap{position:fixed;top:0;left:0;height:100vh;z-index:30;
transform:translateX(-310px)}
#sidewrap:hover,body.side-pin #sidewrap{transform:none}
#side{position:absolute;top:0;left:0;height:100vh;width:310px;overflow-y:auto;
background:var(--sidebar);border-right:1px solid var(--line);padding:18px 16px;font-size:14px;
box-shadow:0 0 24px var(--shadow)}
#main{max-width:900px;margin:0 auto;padding:28px 34px 120px}
#side h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
margin:20px 0 8px}
#side a{display:block;color:var(--fg);text-decoration:none;padding:3px 6px;border-radius:4px}
#side a:hover{background:var(--line)}
#side .lv1{font-weight:600;margin-top:8px}
#side .lv2{padding-left:16px;font-size:13.5px;color:var(--muted)}
#side .lv3{padding-left:28px;font-size:13px;color:var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.controls button,.controls select,.controls input{font:inherit;font-size:13px;
padding:5px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);
color:var(--fg);cursor:pointer}
.controls input{cursor:text;width:100%}
.controls button.on{background:var(--accent);color:var(--bg);border-color:var(--accent)}
h1{font-size:30px;line-height:1.3;margin:0 0 6px}
h2{font-size:23px;margin:44px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:19px;margin:32px 0 8px}
h4,h5,h6{font-size:17px;margin:24px 0 6px}
img{max-width:100%;height:auto;display:block;margin:18px auto;
background:var(--plate);border-radius:6px;padding:6px;box-shadow:0 1px 3px var(--shadow)}
.table-wrap{overflow-x:auto;margin:18px 0}
table{border-collapse:collapse;font-size:14.5px;min-width:100%}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--card)}
blockquote{margin:16px 0;padding:6px 16px;border-left:3px solid var(--accent);color:var(--muted)}
pre{background:var(--card);padding:12px 14px;border-radius:8px;overflow-x:auto;font-size:14px}
code{background:var(--card);padding:1px 5px;border-radius:4px;font-size:.92em}
pre code{background:none;padding:0}
.math-display{overflow-x:auto;margin:16px 0}
.footnotes{margin-top:40px;padding-top:10px;border-top:1px solid var(--line);
font-size:14px;color:var(--muted)}
.fn-item{display:flex;gap:10px;margin:6px 0}
.fn-key{flex:0 0 auto;font-weight:600;color:var(--accent)}
.fn-back{text-decoration:none;color:var(--accent)}
sup.fn a{text-decoration:none;color:var(--accent)}
/* Cards never sit in the flow: with enough of them the paper becomes
   unreadable. They live in a panel opened from the highlighted sentence, so
   the page stays a paper and a question is one click away. */
.qcard{display:none}
.qcard sub{font-size:11.5px;color:var(--muted);font-weight:400}
mark[data-id]{cursor:pointer}
mark[data-id]:hover{box-shadow:inset 0 -2px 0 var(--accent)}
mark.off{cursor:auto}
#ov{position:fixed;inset:0;background:rgba(0,0,0,.38);z-index:40}
#panel{position:fixed;z-index:41;left:50%;top:50%;transform:translate(-50%,-50%);
width:min(760px,92vw);max-height:82vh;overflow:auto;background:var(--card);
border:1px solid var(--line);border-left:4px solid var(--muted);border-radius:12px;
box-shadow:0 18px 50px var(--shadow);padding:20px 26px 24px}
#panel[data-status=open]{border-left-color:var(--open)}
#panel[data-status=half]{border-left-color:var(--half)}
#panel[data-status=resolved]{border-left-color:var(--done)}
.ptitle{font-weight:600;font-size:17px;line-height:1.6;padding-right:34px;
margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed var(--line)}
.pbar{display:flex;gap:8px;position:absolute;top:14px;right:16px}
.pbar button{font:inherit;font-size:13px;padding:3px 9px;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--fg);cursor:pointer}
.pbar button:hover{background:var(--line)}
/* nowrap matters: the handle is positioned against a zero-width wrapper, so
   without it the label shrink-to-fits to one character per line. */
#sidetoggle{position:absolute;top:12px;left:310px;white-space:nowrap;font:inherit;font-size:13px;
padding:6px 11px;border:1px solid var(--line);border-left:none;
border-radius:0 8px 8px 0;background:var(--card);
color:var(--fg);cursor:pointer;box-shadow:2px 2px 8px var(--shadow)}
#sidetoggle:hover{background:var(--line)}
/* open, the handle is just a grip: the label would only cover the paper */
#sidewrap:hover .stxt,body.side-pin .stxt{display:none}
/* Motion is the point here, but not for readers who asked for less of it. */
@media(prefers-reduced-motion:no-preference){
#sidewrap,#note{transition:transform .22s ease}}

/* Somewhere to draft a question while reading, instead of interrupting the
   paragraph to ask. Nothing is sent from here -- copy it into the chat. */
#notewrap{position:fixed;top:0;right:0;height:100vh;z-index:29;pointer-events:none}
#notewrap>*{pointer-events:auto}
/* nowrap for the same reason as #sidetoggle: positioned against a zero-width
   wrapper, the label otherwise collapses to one character per line. */
#notetab{position:absolute;top:12px;right:12px;white-space:nowrap;font:inherit;font-size:13px;
padding:6px 11px;border:1px solid var(--line);border-radius:8px;background:var(--card);
color:var(--fg);cursor:pointer;box-shadow:0 2px 8px var(--shadow)}
#notetab:hover{background:var(--line)}
body.note-on #notetab{opacity:0;pointer-events:none}
#note{position:absolute;top:0;right:0;width:min(360px,90vw);height:100vh;
display:flex;flex-direction:column;gap:8px;padding:16px 14px;
background:var(--sidebar);border-left:1px solid var(--line);box-shadow:0 0 24px var(--shadow);
transform:translateX(100%)}
body.note-on #note{transform:none}
/* The drawer is a working surface, not a passing hover like the sidebar: while
   it is open the column steps aside so it never covers the text being written
   about. Same width, so the line breaks do not change. */
@media(min-width:1000px){body.note-on #layout{padding-right:calc(min(360px,90vw) + 20px)}}
.nhead{display:flex;align-items:baseline;gap:8px;font-size:13px;font-weight:600}
.nhint{font-weight:400;font-size:12px;color:var(--muted)}
#notepad{flex:1;min-height:0;resize:none;font:inherit;font-size:14px;line-height:1.7;
padding:10px 12px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--fg)}
.nbar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.nbar button{font:inherit;font-size:13px;padding:4px 10px;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--fg);cursor:pointer}
.nbar button:hover{background:var(--line)}
#qlist{margin-bottom:6px}
/* #side a above is an ID selector and outranks a bare .qlink rule, so scope
   these to #qlist -- otherwise display:block wins and the dots collapse. */
#qlist a.qlink{display:flex;gap:7px;align-items:flex-start;padding:5px 6px;
line-height:1.45;font-size:13px;color:var(--muted);border-radius:4px}
#qlist a.qlink:hover{background:var(--line);color:var(--fg)}
#qlist a.qlink.hidden{display:none}
.qtext{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
/* a glyph, not an empty box: it stays visible whatever the display model */
.dot{flex:0 0 auto;font-size:10px;line-height:2.1}
.dot.open{color:var(--open)}.dot.half{color:var(--half)}
.dot.resolved{color:var(--done)}
.qempty{font-size:13px;color:var(--muted);padding:4px 6px}
.banner{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:12px 16px;margin-bottom:24px;font-size:14px;color:var(--muted)}
.warn{border-color:var(--open);color:var(--fg)}
.meta{color:var(--muted);font-size:14px;margin-bottom:20px}
@media(max-width:900px){
#side{width:min(310px,88vw)}
#main{padding:20px 18px 90px}}
"""

SCRIPT = """
(function(){
  var cards=[].slice.call(document.querySelectorAll('.qcard'));
  var showAI=document.getElementById('showai');
  var filter=document.getElementById('statusf');
  var search=document.getElementById('q');
  var links=[].slice.call(document.querySelectorAll('a.qlink'));
  // A highlight is its card's footprint in the text, so it follows the card:
  // hide the card and the mark goes with it, leaving the sentence untouched.
  var marks=[].slice.call(document.querySelectorAll('mark[data-id]'));

  var themeBtn=document.getElementById('theme');
  var modes=[['system','🌗 跟隨系統'],['light','☀️ 淺色'],['dark','🌙 深色']];
  // memory holds the truth; storage is only persistence. Reading the mode back
  // from storage would leave the toggle stuck wherever storage is unavailable
  // (file:// in some browsers, private mode).
  var mode='system';
  try{var saved=localStorage.getItem('pa-theme');
      if(saved==='light'||saved==='dark'||saved==='system') mode=saved;}catch(e){}
  function setMode(m){
    mode=m;
    if(m==='system'){document.documentElement.removeAttribute('data-theme');}
    else{document.documentElement.setAttribute('data-theme',m);}
    try{localStorage.setItem('pa-theme',m);}catch(e){}
    for(var i=0;i<modes.length;i++){ if(modes[i][0]===m) themeBtn.textContent=modes[i][1]; }
  }
  setMode(mode);
  themeBtn.addEventListener('click',function(){
    var i=0;
    for(var j=0;j<modes.length;j++){ if(modes[j][0]===mode) i=j; }
    setMode(modes[(i+1)%modes.length][0]);
  });

  function apply(){
    var want=filter.value, ai=showAI.classList.contains('on');
    var term=(search.value||'').toLowerCase();
    var shown={};
    cards.forEach(function(c){
      var ok=true;
      if(want==='none') ok=false;
      else if(want!=='all'&&c.dataset.status!==want) ok=false;
      if(!ai&&c.dataset.origin==='suggested') ok=false;
      if(term&&c.textContent.toLowerCase().indexOf(term)<0) ok=false;
      c.classList.toggle('hidden',!ok);
      shown[c.dataset.id]=ok;
    });
    // the list mirrors the cards, so a filtered-out question cannot be clicked
    links.forEach(function(a){
      var id=a.getAttribute('href').replace('#card-','');
      a.classList.toggle('hidden', shown[id]===false);
    });
    marks.forEach(function(k){
      k.classList.toggle('off', shown[k.dataset.id]===false);
    });
    if(current&&shown[current]===false) closeCard();
  }
  showAI.addEventListener('click',function(){ showAI.classList.toggle('on'); apply(); });
  filter.addEventListener('change',apply);
  search.addEventListener('input',apply);

  // Hover opens the sidebar (CSS); the pin is for touch, where there is no
  // hover, and for anyone who wants it to stay put.
  var body=document.body;
  var pin=document.getElementById('sidepin');
  function setPin(on){
    body.classList.toggle('side-pin',on);
    pin.classList.toggle('on',on);
    pin.textContent=on?'📌 已釘住':'📌 釘住';
  }
  document.getElementById('sidetoggle').addEventListener('click',function(){
    setPin(!body.classList.contains('side-pin'));
  });
  pin.addEventListener('click',function(){ setPin(!body.classList.contains('side-pin')); });

  // Draft area. Nothing leaves the page from here -- the copy button is the
  // whole point: read the paragraph, write the question, paste it into chat.
  var pad=document.getElementById('notepad');
  var stat=document.getElementById('nstat');
  var KEY='pa-draft:'+(document.title||'');
  try{ var kept=localStorage.getItem(KEY); if(kept) pad.value=kept; }catch(e){}
  function say(msg){ stat.textContent=msg; setTimeout(function(){ stat.textContent=''; },1600); }
  pad.addEventListener('input',function(){
    try{ localStorage.setItem(KEY,pad.value); }catch(e){}
  });
  document.getElementById('notetab').addEventListener('click',function(){
    body.classList.add('note-on'); pad.focus();
  });
  document.getElementById('noteclose').addEventListener('click',function(){
    body.classList.remove('note-on');
  });
  document.getElementById('ncopy').addEventListener('click',function(){
    if(!pad.value){ say('還沒有內容'); return; }
    var done=function(){ say('已複製'); };
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(pad.value).then(done,fallback);
    } else { fallback(); }
    // file:// often refuses the async clipboard, so keep the old way around
    function fallback(){
      pad.select();
      try{ document.execCommand('copy'); done(); }catch(e){ say('複製失敗，請手動選取'); }
      pad.setSelectionRange(pad.value.length,pad.value.length);
    }
  });
  document.getElementById('nclear').addEventListener('click',function(){
    if(!pad.value) return;
    pad.value=''; try{ localStorage.removeItem(KEY); }catch(e){} say('已清空'); pad.focus();
  });

  // A card opens over the paper and closes again -- it never pushes the text
  // around, so the page reads as a paper however many questions pile up.
  var panel=document.getElementById('panel');
  var panelIn=document.getElementById('panel-in');
  var ov=document.getElementById('ov');
  var jump=document.getElementById('pjump');
  var current=null;
  function openCard(id){
    var card=document.getElementById('card-'+id);
    if(!card||card.classList.contains('hidden')) return;
    var parts=[].slice.call(card.children), head='', rest='';
    parts.forEach(function(n){
      if(n.tagName==='SUMMARY') head=n.innerHTML; else rest+=n.outerHTML;
    });
    panelIn.innerHTML='<div class="ptitle">'+head+'</div>'+rest;
    panel.dataset.status=card.dataset.status||'open';
    current=id;
    jump.hidden=!document.querySelector('mark[data-id="'+id+'"]');
    panel.hidden=false; ov.hidden=false;
    panel.scrollTop=0;
    panel.focus();
  }
  function closeCard(){ panel.hidden=true; ov.hidden=true; current=null; }
  document.getElementById('main').addEventListener('click',function(e){
    var m=e.target.closest?e.target.closest('mark[data-id]'):null;
    if(m&&!m.classList.contains('off')) openCard(m.dataset.id);
  });
  links.forEach(function(a){
    a.addEventListener('click',function(e){
      e.preventDefault();
      openCard(a.getAttribute('href').replace('#card-',''));
    });
  });
  jump.addEventListener('click',function(){
    var m=current&&document.querySelector('mark[data-id="'+current+'"]');
    closeCard();
    if(m) m.scrollIntoView({block:'center'});
  });
  document.getElementById('pclose').addEventListener('click',closeCard);
  ov.addEventListener('click',closeCard);
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape') return;
    if(!panel.hidden){ closeCard(); return; }
    if(body.classList.contains('note-on')&&document.activeElement!==pad){
      body.classList.remove('note-on');
    }
  });
  // Formulas light up as a whole while selected -- see the .katex rules in the
  // stylesheet for why the browser's own painting is switched off there.
  var lit=[],pending=0;
  function relight(){
    pending=0;
    while(lit.length) lit.pop().classList.remove('sel');
    var s=window.getSelection();
    if(!s||s.isCollapsed||!s.rangeCount) return;
    var scope=s.getRangeAt(0).commonAncestorContainer;
    if(scope.nodeType===3) scope=scope.parentNode;
    if(!scope||!scope.querySelectorAll) return;
    // a selection sitting entirely inside one formula has no .katex below it
    var own=scope.closest?scope.closest('.katex'):null;
    if(own){ own.classList.add('sel'); lit.push(own); }
    var found=scope.querySelectorAll('.katex');
    for(var i=0;i<found.length;i++){
      if(s.containsNode(found[i],true)){ found[i].classList.add('sel'); lit.push(found[i]); }
    }
  }
  // setTimeout rather than requestAnimationFrame: rAF is suspended while the
  // page is not being painted, which would leave the class stale.
  document.addEventListener('selectionchange',function(){
    if(pending) return;
    pending=setTimeout(relight,0);
  });

  apply();
})();
"""


_CARD_OPEN = re.compile(r"<details([^>]*class=\"qcard\"[^>]*)>\s*<summary>(.*?)</summary>", re.S)
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')
_MARK_RE = re.compile(r"<mark>(.*?)</mark>", re.S)


def tag_marks(body_html: str, cards) -> str:
    """Attach each highlight to the card that put it there.

    The mark is written as plain ==…== in the Markdown so that view stays
    portable; the id is joined back on here, by quote, so a filtered-out card
    takes its highlight with it. An ambiguous match gets no id and simply stays
    lit -- the harmless failure of the two.
    """
    quotes = []
    for card in cards:
        anchor = card["meta"].get("anchor") or {}
        quote = paperkit.quote_text(anchor.get("quote"))
        if quote:
            quotes.append(
                (quote, str(card["meta"].get("id")), str(card["meta"].get("origin") or "asked"))
            )

    def sub(match):
        inner = paperkit.normalize(re.sub(r"<[^>]+>", "", match.group(1)))
        if not inner:
            return match.group(0)
        hits = [(cid, origin) for quote, cid, origin in quotes if inner in quote or quote in inner]
        if len(hits) != 1:
            return match.group(0)
        return f'<mark data-id="{hits[0][0]}" data-origin="{hits[0][1]}">{match.group(1)}</mark>'

    return _MARK_RE.sub(sub, body_html)


def collect_questions(body_html: str):
    """Every question in the order it appears in the paper.

    Taken from the assembled page rather than from the card files, so the list
    order is the anchor order -- the same order the reader meets them.
    """
    found = []
    for match in _CARD_OPEN.finditer(body_html):
        attrs = dict(_ATTR.findall(match.group(1)))
        summary = match.group(2)
        label = re.search(r"</b>\s*·\s*(.*?)\s*<sub>", summary, re.S)
        text = re.sub(r"<[^>]+>", "", label.group(1) if label else summary).strip()
        found.append(
            {
                "id": attrs.get("data-id", "?"),
                "status": attrs.get("data-status", "open"),
                "origin": attrs.get("data-origin", "asked"),
                "text": text,
            }
        )
    return found


def slugify(text: str, used: dict) -> str:
    base = re.sub(r"[^\w一-鿿]+", "-", text.strip().lower()).strip("-") or "sec"
    n = used.get(base, 0)
    used[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def embed_images(html_text: str, base_dir: Path) -> str:
    """Inline every local image as a data: URI so one file travels alone."""

    def sub(match):
        src = match.group(1)
        if src.startswith(("data:", "http:", "https:")):
            return match.group(0)
        path = (base_dir / src).resolve()
        if not path.is_file():
            return match.group(0)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]+)"', sub, html_text)


def build(work_root: Path, embed: bool = False) -> int:
    config, paper_root, notes, annotated = paperkit.load_workspace(work_root)
    if not annotated.is_dir():
        raise SystemExit(f"找不到註記檢視 {annotated}，請先執行 build_annotated.py")
    out = annotated / "index.html"

    sources = [Path(p) for p in (config.get("sources") or [])]
    body_parts, toc, used = [], [], {}
    missing = []

    for rel in sources:
        src = annotated / rel
        if not src.is_file():
            missing.append(rel.as_posix())
            continue
        text = src.read_text(encoding="utf-8")
        text = paperkit.FRONTMATTER_RE.sub("", text, count=1)
        text = re.sub(r"<!--\s*GENERATED by paper-annotations.*?-->", "", text, flags=re.DOTALL)
        # links inside annotated/sections/X.md are relative to that folder;
        # the page lives at annotated/index.html
        text = paperkit.rewrite_links(text, src.parent, out.parent)

        def hook(level, title, _used=used):
            anchor = slugify(title, _used)
            toc.append((level, title, anchor))
            return anchor

        rendered, _ = minimd.render(text, heading_hook=hook)
        body_parts.append(f'<section class="chunk" id="{rel.stem}">{rendered}</section>')

    cards = paperkit.load_cards(notes)
    body_parts = [tag_marks(part, cards) for part in body_parts]
    counts = {"open": 0, "half": 0, "resolved": 0}
    for card in cards:
        counts[str(card["meta"].get("status", "open"))] = (
            counts.get(str(card["meta"].get("status", "open")), 0) + 1
        )

    nav = "".join(
        f'<a class="lv{min(level, 3)}" href="#{anchor}">{html.escape(title)}</a>'
        for level, title, anchor in toc
    )

    questions = collect_questions("".join(body_parts))
    qlist = "".join(
        f'<a class="qlink" href="#card-{q["id"]}" data-status="{q["status"]}" '
        f'data-origin="{q["origin"]}">'
        f'<span class="dot {q["status"]}">●</span>'
        f'<span class="qtext">{html.escape(q["text"])}</span></a>'
        for q in questions
    ) or '<div class="qempty">還沒有任何疑問</div>'

    title = paper_root.name
    manifest = paper_root / "manifest.json"
    if manifest.is_file():
        import json

        try:
            title = json.loads(manifest.read_text(encoding="utf-8")).get("title") or title
        except (ValueError, OSError):
            pass

    warn = ""
    if missing:
        warn = (
            '<div class="banner warn">下列章節在 annotated/ 裡找不到，'
            "請重新執行 build_annotated.py：" + html.escape("、".join(missing)) + "</div>"
        )

    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — 疑問註記</title>
{THEME_BOOT}
<style>{STYLE}</style>
{katex_assets()}
</head>
<body>
<div id="layout">
<div id="sidewrap">
<button id="sidetoggle" title="目錄與疑問">☰<span class="stxt"> 目錄與疑問</span></button>
<nav id="side">
  <div class="controls">
    <button id="theme">🌗 跟隨系統</button>
    <button id="sidepin">📌 釘住</button>
  </div>
  <div class="controls">
    <select id="statusf">
      <option value="all">全部狀態</option>
      <option value="open">未解決</option>
      <option value="half">半懂</option>
      <option value="resolved">已解決</option>
      <option value="none">不顯示疑問</option>
    </select>
    <button id="showai" class="on">AI 提示卡</button>
  </div>
  <div class="controls"><input id="q" type="search" placeholder="搜尋疑問內容…"></div>
  <h2>疑問（{len(questions)}）</h2>
  <div id="qlist">{qlist}</div>
  <h2>目錄</h2>
  {nav}
</nav>
</div>
<main id="main">
<div class="meta">疑問 {len(cards)} 則 —
🔴 未解決 {counts.get('open', 0)} ·
🟡 半懂 {counts.get('half', 0)} ·
🟢 已解決 {counts.get('resolved', 0)} ·
產生於 {date.today().isoformat()}</div>
{warn}
<div class="banner">
本頁是<strong>衍生檔</strong>，由論文原文與 <code>notes/cards/</code> 合併產生，請勿直接編輯。
摺疊區塊裡的內容是<strong>你的提問與 AI 的解說，不是論文內容</strong>。
正文裡<strong>反白的句子</strong>就是你當初卡住的地方，點它會叫出當時的問題；
先自己想過再看解答。滑鼠移到左上角會滑出目錄與疑問清單，右上角有提問草稿區。
</div>
{''.join(body_parts)}
</main>
</div>
<div id="notewrap">
<button id="notetab">✎ 提問草稿</button>
<section id="note">
  <div class="nhead">提問草稿 <span class="nhint">讀完整段再一次問，複製後貼回對話</span></div>
  <textarea id="notepad" placeholder="例：IV-B 的 dc removal 為什麼要扣掉平均密度？&#10;（這裡只是草稿，不會送出，也不會變成卡片）"></textarea>
  <div class="nbar"><button id="ncopy">複製</button><button id="nclear">清空</button>
  <button id="noteclose">✕ 收起</button><span id="nstat"></span></div>
</section>
</div>
<div id="ov" hidden></div>
<aside id="panel" hidden tabindex="-1" role="dialog" aria-modal="true"><div class="pbar">
<button id="pjump">跳到原文</button><button id="pclose">✕</button></div>
<div id="panel-in"></div></aside>
<script>{SCRIPT}</script>
</body>
</html>
"""

    if embed:
        page = embed_images(page, annotated)

    out.write_text(page, encoding="utf-8", newline="\n")
    size = out.stat().st_size / 1024
    print(f"index.html  {len(sources)} 個章節、{len(cards)} 則疑問、{size:,.0f} KB")
    print(f"  {out}")
    if embed:
        print("  已內嵌圖片：這個檔案可以單獨寄給別人。")
    else:
        print("  圖片使用相對路徑；要單檔攜帶請加 --embed-assets。")
    if missing:
        print("  ⚠️  有章節缺漏，請先重新執行 build_annotated.py")
    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    return build(Path(args[0] if args else ".").resolve(), embed="--embed-assets" in argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
