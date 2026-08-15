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
--sec-stuck:#fdf1e3;--sec-answer:#f8f7f3;--sec-key:#edf3ee;--algo:#eef1f6;
--sel:rgba(138,79,36,.20);
--hl1:rgba(244,201,63,.45);--hl2:rgba(96,190,136,.36);--hl3:rgba(114,164,235,.34)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#15161a;--fg:#e8e5de;--muted:#9b978e;--line:#32353c;--card:#1e2026;
--sidebar:#191b20;--accent:#e0a76a;--open:#f0776a;--half:#e8b04b;--done:#6fc796;
--plate:#e9e7e2;--shadow:rgba(0,0,0,.35);--mark:#4a3a1f;
--sec-stuck:#2a2118;--sec-answer:#1b1d22;--sec-key:#17231e;--algo:#1a1e26;
--sel:rgba(224,167,106,.26);
--hl1:rgba(212,166,44,.34);--hl2:rgba(70,168,118,.30);--hl3:rgba(96,144,212,.34)}}
:root[data-theme="dark"]{
--bg:#15161a;--fg:#e8e5de;--muted:#9b978e;--line:#32353c;--card:#1e2026;
--sidebar:#191b20;--accent:#e0a76a;--open:#f0776a;--half:#e8b04b;--done:#6fc796;
--plate:#e9e7e2;--shadow:rgba(0,0,0,.35);--mark:#4a3a1f;
--sec-stuck:#2a2118;--sec-answer:#1b1d22;--sec-key:#17231e;--algo:#1a1e26;
--sel:rgba(224,167,106,.26);
--hl1:rgba(212,166,44,.34);--hl2:rgba(70,168,118,.30);--hl3:rgba(96,144,212,.34)}
*{box-sizing:border-box}
/* The sentence a card is anchored to. Tinted, never the browser's
   default yellow-on-black, which ignores the palette entirely. */
mark{background:var(--mark);color:inherit;padding:.05em .15em;border-radius:3px}
mark.off{background:none;padding:0}
/* Algorithm listings read as one unit rather than as loose numbered text. */
.algo{margin:20px 0;padding:12px 18px 6px;border-radius:8px;background:var(--algo);
border:1px solid var(--line);border-left:3px solid var(--accent);scroll-margin-top:24px}
.algo-t{font-weight:600;margin-bottom:6px;padding-bottom:6px;
border-bottom:1px dashed var(--line)}
.algo ol{margin:6px 0 10px;padding-left:26px}
.algo li{margin:1px 0;line-height:1.6}
.algo p{margin:4px 0}
/* Lettered sub-items keep the paper's own labels, so the list itself carries
   no markers. */
ol.sublist{list-style:none;padding-left:22px;margin:4px 0}
ol.sublist>li{margin:2px 0}
.li-key{color:var(--muted);margin-right:5px}
.algo:target{outline:2px solid var(--accent);outline-offset:3px}
/* "see Fig. 4" jumps to the figure. Underlined rather than coloured-only, so
   it stays visible to a reader who cannot separate the two colours. */
a.xref{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent)}
a.xref:hover{border-bottom-style:solid}
img[id^="fig-"],img[id^="tab-"]{scroll-margin-top:24px}
img[id]:target{outline:2px solid var(--accent);outline-offset:4px}
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
/* The reader's own highlighter. Painted through the Custom Highlight API
   rather than by wrapping the text: a dragged selection crosses element
   boundaries, overlaps the cards' own <mark>s and cuts into KaTeX subtrees,
   and none of those survive being wrapped in a tag. Painting ranges leaves the
   DOM untouched, so the mark-to-card join, the xref links and the rendered
   formulas all keep working. */
/* Literal colours rather than the --hl* tokens: a highlight pseudo-element
   inherits through its own chain, and how far custom properties reach into it
   is not uniform across browsers. The tokens still drive the palette buttons,
   where normal inheritance applies -- these two sets must stay in step. */
::highlight(pa-hl1){background-color:rgba(244,201,63,.45)}
::highlight(pa-hl2){background-color:rgba(96,190,136,.36)}
::highlight(pa-hl3){background-color:rgba(114,164,235,.34)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]) *::highlight(pa-hl1){
background-color:rgba(212,166,44,.34)}
:root:not([data-theme="light"]) *::highlight(pa-hl2){background-color:rgba(70,168,118,.30)}
:root:not([data-theme="light"]) *::highlight(pa-hl3){background-color:rgba(96,144,212,.34)}}
:root[data-theme="dark"] *::highlight(pa-hl1){background-color:rgba(212,166,44,.34)}
:root[data-theme="dark"] *::highlight(pa-hl2){background-color:rgba(70,168,118,.30)}
:root[data-theme="dark"] *::highlight(pa-hl3){background-color:rgba(96,144,212,.34)}
#hlbar{position:fixed;z-index:45;display:flex;gap:5px;padding:5px;
background:var(--card);border:1px solid var(--line);border-radius:8px;
box-shadow:0 4px 14px var(--shadow)}
#hlbar button{width:24px;height:24px;padding:0;font:inherit;font-size:12px;
display:grid;place-items:center;border:1px solid var(--line);border-radius:5px;
background:var(--bg);color:var(--fg);cursor:pointer}
#hlbar button:hover{border-color:var(--accent)}
#hlbar [data-c="1"]{background:var(--hl1)}
#hlbar [data-c="2"]{background:var(--hl2)}
#hlbar [data-c="3"]{background:var(--hl3)}
#hlstat{font-size:12.5px;color:var(--muted);padding:2px 6px;line-height:1.55}
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
.footnotes,.fn-key,.dot,.qtext,a.qlink,mark,.csec,.csec-t,.algo,.algo-t{
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
/* The reserved strip has to match the button bar, or the question runs under
   it -- which is exactly the text the reader is meant to be reading first. */
.ptitle{font-weight:600;font-size:17px;line-height:1.6;padding-right:82px;
margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed var(--line)}
.pbar{display:flex;gap:8px;position:absolute;top:14px;right:16px}
.pbar button{position:relative;width:30px;height:30px;padding:0;font:inherit;font-size:14px;
display:grid;place-items:center;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--fg);cursor:pointer}
.pbar button:hover{background:var(--line)}
/* Icons alone are ambiguous; the label arrives on hover instead of taking up
   room next to the question. */
.pbar button::after{content:attr(data-tip);position:absolute;top:calc(100% + 6px);right:0;
white-space:nowrap;font-size:12px;font-weight:400;padding:3px 8px;border-radius:6px;
background:var(--fg);color:var(--bg);opacity:0;pointer-events:none}
.pbar button:hover::after{opacity:1}
@media(prefers-reduced-motion:no-preference){.pbar button::after{transition:opacity .15s ease}}
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

  // file:// often refuses the async clipboard, so the old way stays as backup.
  function copyText(text,ok,fail){
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){ ok&&ok(); },manual);
    } else { manual(); }
    function manual(){
      var t=document.createElement('textarea');
      t.value=text; t.setAttribute('readonly','');
      t.style.cssText='position:fixed;top:-1000px;left:0;opacity:0';
      document.body.appendChild(t); t.select();
      var good=false;
      try{ good=document.execCommand('copy'); }catch(e){}
      document.body.removeChild(t);
      if(good){ ok&&ok(); } else { fail&&fail(); }
    }
  }

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
    copyText(pad.value,function(){ say('已複製'); },function(){ say('複製失敗，請手動選取'); });
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

  // ---- Highlighter -------------------------------------------------------
  // The reader's own marks, kept in the browser. This page is opened from
  // file:// with nothing behind it, so it cannot write into notes/; what it can
  // do is hold them and hand them back on request (「複製畫記」) for the agent
  // to file properly. They are a working layer, like the draft drawer -- the
  // cards remain the only thing the build treats as truth.
  var HL_OK=!!(window.CSS&&window.CSS.highlights&&window.Highlight&&window.Map);
  var hlBtn=document.getElementById('hlon');
  var hlBar=document.getElementById('hlbar');
  var hlStat=document.getElementById('hlstat');
  var hlDel=document.getElementById('hldel');
  // Keyed by the paper, not by the file's path or a digest of its text: the
  // page moves and gets rebuilt constantly, and either of those would drop
  // every mark the next time a card was added.
  var hlKey='pa-hl:'+(body.dataset.paper||document.title||'');
  var hlItems=[], hlOn=true, hlPick=-1, hlMaps={};

  function hlNorm(s){ return (s||'').replace(/\\s+/g,' ').trim(); }
  function hlSec(node){
    var el=node&&node.nodeType===3?node.parentElement:node;
    return el&&el.closest?el.closest('#main .chunk'):null;
  }
  // Text index over one section. The MathML twin is skipped for the same
  // reason it is unselectable: it repeats every formula, and counting it would
  // put every offset after a formula in the wrong place.
  function hlMap(sec){
    if(hlMaps[sec.id]) return hlMaps[sec.id];
    var walk=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
      var p=n.parentElement;
      if(!p||!n.nodeValue) return NodeFilter.FILTER_REJECT;
      return p.closest('.katex-mathml,.qcard')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT;
    }});
    var m={txt:'',nodes:[],offs:[],at:new Map()},n;
    while((n=walk.nextNode())){
      m.at.set(n,m.nodes.length); m.offs.push(m.txt.length);
      m.nodes.push(n); m.txt+=n.nodeValue;
    }
    hlMaps[sec.id]=m; return m;
  }
  function hlIndex(map,node,off){
    var i=map.at.get(node);
    if(i!==undefined) return map.offs[i]+off;
    // An element boundary: formulas select whole, so a selection edge often
    // lands beside a .katex rather than inside text. Take the first mapped
    // node at or after the boundary.
    var b=document.createRange();
    try{ b.setStart(node,off); }catch(e){ return 0; }
    b.collapse(true);
    var lo=0,hi=map.nodes.length;
    while(lo<hi){
      var mid=(lo+hi)>>1, cmp;
      try{ cmp=b.comparePoint(map.nodes[mid],0); }catch(e){ cmp=0; }
      if(cmp>=0) hi=mid; else lo=mid+1;
    }
    return lo<map.nodes.length?map.offs[lo]:map.txt.length;
  }
  function hlPos(map,idx){
    var lo=0,hi=map.nodes.length-1,i=0;
    while(lo<=hi){
      var mid=(lo+hi)>>1;
      if(map.offs[mid]<=idx){ i=mid; lo=mid+1; } else hi=mid-1; }
    var node=map.nodes[i];
    return {node:node,off:Math.max(0,Math.min(idx-map.offs[i],node.nodeValue.length))};
  }
  function hlRange(map,a,b){
    var s=hlPos(map,a), e=hlPos(map,b), r=document.createRange();
    try{ r.setStart(s.node,s.off); r.setEnd(e.node,e.off); }catch(err){ return null; }
    return r;
  }
  function hlHead(a,b){ var i=0; while(i<a.length&&i<b.length&&a[i]===b[i]) i++; return i; }
  function hlTail(a,b){
    var i=0;
    while(i<a.length&&i<b.length&&a[a.length-1-i]===b[b.length-1-i]) i++;
    return i;
  }
  // Re-find a stored mark after reload. Whitespace-tolerant, exactly like the
  // Python side: the rendered text wraps differently from the Markdown. When
  // the sentence occurs more than once the neighbours decide which one.
  function hlLocate(it){
    var sec=document.getElementById(it.sec);
    if(!sec||!it.exact) return null;
    var map=hlMap(sec), re;
    try{
      re=new RegExp(hlNorm(it.exact).split(' ').map(function(t){
        return t.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'); }).join('\\\\s+'),'g');
    }catch(e){ return null; }
    var hits=[],m;
    while((m=re.exec(map.txt))){
      hits.push(m);
      if(re.lastIndex<=m.index) re.lastIndex=m.index+1;
      if(hits.length>80) break;
    }
    if(!hits.length) return null;
    var best=hits[0];
    if(hits.length>1){
      var top=-1;
      hits.forEach(function(h){
        var end=h.index+h[0].length;
        var score=hlTail(hlNorm(map.txt.slice(Math.max(0,h.index-60),h.index)),it.prefix)
                 +hlHead(hlNorm(map.txt.slice(end,end+60)),it.suffix);
        if(score>top){ top=score; best=h; }
      });
    }
    return hlRange(map,best.index,best.index+best[0].length);
  }
  function hlPaint(){
    if(!HL_OK) return;
    ['1','2','3'].forEach(function(c){ CSS.highlights.delete('pa-hl'+c); });
    if(!hlOn) return;
    var by={};
    hlItems.forEach(function(it){
      if(it.range) (by[it.color]=by[it.color]||[]).push(it.range); });
    Object.keys(by).forEach(function(c){
      var h=new Highlight();
      by[c].forEach(function(r){ h.add(r); });
      CSS.highlights.set('pa-hl'+c,h);
    });
  }
  function hlSave(){
    try{
      localStorage.setItem(hlKey,JSON.stringify(hlItems.map(function(it){
        return {s:it.sec,e:it.exact,p:it.prefix,x:it.suffix,c:it.color}; })));
    }catch(e){}
  }
  // Marks that no longer resolve are kept, not dropped: they still carry the
  // sentence, and 「複製畫記」 lists them so nothing disappears silently.
  function hlStatus(){
    if(!HL_OK){ hlStat.textContent='這個瀏覽器不支援畫記（需要較新版 Chrome／Edge／Safari／Firefox）'; return; }
    var lost=0;
    hlItems.forEach(function(it){ if(!it.range) lost++; });
    var msg=hlItems.length?(hlItems.length+' 條畫記'):'選取正文就能畫記，存在瀏覽器本機';
    if(lost) msg+='；'+lost+' 條找不到原文（複製時仍會列出）';
    if(hlItems.length&&!hlOn) msg+='（已隱藏）';
    hlStat.textContent=msg;
  }
  var hlTimer=0;
  function hlSay(msg){
    hlStat.textContent=msg;
    clearTimeout(hlTimer);
    hlTimer=setTimeout(hlStatus,2200);
  }
  function hlHide(){ hlBar.hidden=true; hlPick=-1; }
  function hlPlace(rect){
    hlBar.hidden=false;
    var w=hlBar.offsetWidth, h=hlBar.offsetHeight;
    var x=Math.min(Math.max(6,rect.left+rect.width/2-w/2),window.innerWidth-w-6);
    var y=rect.top-h-8;
    if(y<6) y=rect.bottom+8;
    hlBar.style.left=x+'px'; hlBar.style.top=y+'px';
  }
  function hlAdd(color){
    var sel=window.getSelection();
    if(!sel||sel.isCollapsed||!sel.rangeCount) return;
    var r=sel.getRangeAt(0), sec=hlSec(r.startContainer);
    if(!sec){ hlSay('只能在正文裡畫記'); return; }
    if(hlSec(r.endContainer)!==sec){ hlSay('畫記不能跨章節，請分兩次'); return; }
    var map=hlMap(sec);
    var a=hlIndex(map,r.startContainer,r.startOffset);
    var b=hlIndex(map,r.endContainer,r.endOffset);
    if(b<a){ var t=a; a=b; b=t; }
    while(a<b&&/\\s/.test(map.txt.charAt(a))) a++;
    while(b>a&&/\\s/.test(map.txt.charAt(b-1))) b--;
    var exact=hlNorm(map.txt.slice(a,b));
    if(exact.length<2){ hlSay('選取太短'); return; }
    var it={sec:sec.id,exact:exact,color:color,
      prefix:hlNorm(map.txt.slice(Math.max(0,a-48),a)),
      suffix:hlNorm(map.txt.slice(b,b+48))};
    it.range=hlRange(map,a,b);
    if(!it.range){ hlSay('這段定位不到，請換個選取範圍'); return; }
    hlItems.push(it);
    if(!hlOn){ hlOn=true; hlBtn.classList.add('on'); }
    hlSave(); hlPaint(); hlStatus(); hlHide();
    sel.removeAllRanges();
  }
  function hlAt(x,y){
    var r=null;
    if(document.caretRangeFromPoint) r=document.caretRangeFromPoint(x,y);
    else if(document.caretPositionFromPoint){
      var p=document.caretPositionFromPoint(x,y);
      if(p){ r=document.createRange(); r.setStart(p.offsetNode,p.offset); }
    }
    if(!r) return -1;
    for(var i=hlItems.length-1;i>=0;i--){
      if(!hlItems[i].range) continue;
      try{
        if(hlItems[i].range.comparePoint(r.startContainer,r.startOffset)===0) return i;
      }catch(e){}
    }
    return -1;
  }
  // KaTeX seeds rendered formulas with zero-width breaks. They have to stay in
  // what is stored -- \\s does not match them, so stripping them would stop the
  // mark being found again -- but they are noise in the handed-over text.
  function hlPlain(s){ return (s||'').replace(/[\\u200b-\\u200f\\ufeff]/g,''); }
  function hlReport(){
    var names={'1':'黃','2':'綠','3':'藍'};
    var out=['螢光筆畫記 '+hlItems.length+' 條 — '+document.title.replace(' — 疑問註記',''),
             '（複習頁本機保存的畫記，貼回對話就能請 agent 依這些段落整理或建卡）',''];
    hlItems.forEach(function(it,i){
      out.push((i+1)+'. ['+it.sec+'] '+(names[it.color]||it.color)
        +(it.range?'':' ⚠️ 目前定位不到'));
      out.push('   「'+hlPlain(it.exact)+'」');
      out.push('   前後文：…'+hlPlain(it.prefix)+' ⟦…⟧ '+hlPlain(it.suffix)+'…');
    });
    return out.join('\\n');
  }

  if(HL_OK){
    [].slice.call(hlBar.querySelectorAll('[data-c]')).forEach(function(btn){
      btn.addEventListener('mousedown',function(e){ e.preventDefault(); });
      btn.addEventListener('click',function(){
        var c=btn.dataset.c;
        if(hlPick>=0){ hlItems[hlPick].color=c; hlSave(); hlPaint(); hlHide(); }
        else hlAdd(c);
      });
    });
    hlDel.addEventListener('mousedown',function(e){ e.preventDefault(); });
    hlDel.addEventListener('click',function(){
      if(hlPick<0) return;
      hlItems.splice(hlPick,1);
      hlSave(); hlPaint(); hlStatus(); hlHide();
    });
    // mouseup, not selectionchange: during a drag the bar would chase the
    // pointer. The timeout lets the selection settle first.
    document.addEventListener('mouseup',function(e){
      if(hlBar.contains(e.target)) return;
      setTimeout(function(){
        if(!panel.hidden){ hlHide(); return; }
        var sel=window.getSelection();
        if(sel&&!sel.isCollapsed&&sel.rangeCount&&hlSec(sel.getRangeAt(0).startContainer)){
          hlPick=-1; hlDel.hidden=true;
          hlPlace(sel.getRangeAt(0).getBoundingClientRect());
          return;
        }
        // clicking a mark opens its card -- that gesture stays as it was
        var onCard=e.target.closest&&e.target.closest('mark[data-id]');
        var i=onCard?-1:hlAt(e.clientX,e.clientY);
        if(i>=0&&hlOn){
          hlPick=i; hlDel.hidden=false;
          hlPlace(hlItems[i].range.getBoundingClientRect());
          return;
        }
        hlHide();
      },0);
    });
    document.addEventListener('selectionchange',function(){
      var sel=window.getSelection();
      if(hlPick<0&&(!sel||sel.isCollapsed)) hlHide();
    });
    window.addEventListener('scroll',hlHide,true);
    hlBtn.addEventListener('click',function(){
      hlOn=!hlOn;
      hlBtn.classList.toggle('on',hlOn);
      hlHide(); hlPaint(); hlStatus();
    });
    document.getElementById('hlcopy').addEventListener('click',function(){
      if(!hlItems.length){ hlSay('還沒有畫記'); return; }
      copyText(hlReport(),function(){ hlSay('已複製 '+hlItems.length+' 條'); },
               function(){ hlSay('複製失敗'); });
    });
    document.getElementById('hlclear').addEventListener('click',function(){
      if(!hlItems.length) return;
      if(!window.confirm('清空全部 '+hlItems.length+' 條畫記？這個動作無法復原。')) return;
      hlItems=[];
      try{ localStorage.removeItem(hlKey); }catch(e){}
      hlPaint(); hlStatus(); hlHide();
    });
  } else {
    hlBtn.disabled=true;
    document.getElementById('hlcopy').disabled=true;
    document.getElementById('hlclear').disabled=true;
  }
  // After KaTeX: it rewrites every formula into a subtree, and a range built
  // before that points at nodes which no longer exist. Its listener is
  // registered in <head>, so ours runs second.
  function hlInit(){
    if(HL_OK){
      var raw=null;
      try{ raw=localStorage.getItem(hlKey); }catch(e){}
      var data=[];
      if(raw){ try{ data=JSON.parse(raw)||[]; }catch(e){ data=[]; } }
      hlItems=data.map(function(d){
        var it={sec:d.s,exact:d.e,prefix:d.p||'',suffix:d.x||'',color:d.c||'1'};
        it.range=hlLocate(it);
        return it;
      });
      hlPaint();
    }
    hlStatus();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',hlInit);
  else setTimeout(hlInit,0);

  apply();
})();
"""


# An algorithm is a title paragraph followed by its numbered steps. Both
# conversions agree on that shape; only the title's emphasis differs.
# The title is short and its steps follow immediately (an "Input:/Output:"
# paragraph may sit between). Both bounds matter: prose that merely opens with
# "Algorithm 1 describes the procedure..." must not match, because a rejected
# match still consumes its span and would hide the next real listing.
_ALGO = re.compile(
    r"(<p>\s*(?:<strong>)?\s*Algorithm\s+(\d+)\b.{0,200}?</p>)"
    r"((?:\s*<p>.{0,400}?</p>){0,2}\s*<ol>.*?</ol>)",
    re.S | re.I,
)
_HEADING_TAG = re.compile(r"<h[1-6]\b", re.I)


def wrap_algorithms(body_html: str):
    """Box each listing. Anything that does not clearly end in its own list is
    left alone -- swallowing the following paragraphs would be worse than a
    plain-looking algorithm."""
    found = {}

    def wrap(match):
        title, number, rest = match.group(1), match.group(2), match.group(3)
        # a heading in between means the list belongs to something else
        if _HEADING_TAG.search(rest) or re.search(r"Algorithm\s+\d", rest, re.I):
            return match.group(0)
        if len(rest) > 12000:
            return match.group(0)
        anchor = f"alg-{number}"
        found[("algorithm", number)] = anchor
        inner = re.sub(r"^<p>\s*|\s*</p>$", "", title)
        inner = re.sub(r"^<strong>\s*|\s*</strong>$", "", inner.strip())
        return f'<div class="algo" id="{anchor}"><div class="algo-t">{inner}</div>{rest}</div>'

    return _ALGO.sub(wrap, body_html), found


# --------------------------------------------------------------------------
# cross-references ("see Fig. 4", "Table V")
# --------------------------------------------------------------------------

_ASSET_IMG = re.compile(
    r'<img\s+([^>]*?)src="([^"]*?(figure|table)-0*(\d+)\.[A-Za-z]+)"([^>]*?)>', re.I
)
_ALT = re.compile(r'alt="([^"]*)"', re.I)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
# "Fig. 4", "Figure 4", "FIG. 4", "Table V", "TABLE 8" -- the label varies from
# paper to paper, the shape does not.
_XREF = re.compile(r"\b(Figs?\.|Figures?|FIGs?\.|Tables?|TABLES?|Algorithms?|ALGORITHMS?)\s*(\d+|[IVXLCDM]+)\b")
# Inside these, a link would either fight the element's own click or jump the
# page out from under an open card.
_CITED = re.compile(r"\[\s*\d+\s*,\s*$")
_SKIP_OPEN = re.compile(r"<(details|a|mark|h[1-6])\b", re.I)
_SKIP_CLOSE = re.compile(r"</(details|a|mark|h[1-6])\s*>", re.I)


def roman_to_int(text: str):
    total, prev = 0, 0
    for char in reversed(text.upper()):
        value = _ROMAN.get(char)
        if value is None:
            return None
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total or None


def label_ids(body_html: str):
    """Give every figure/table image an id, and map what the text may call it.

    The number comes from the asset filename, which both conversions agree on;
    the alt text supplies the paper's own label (Roman or Arabic) when it has
    one, so "Table V" and "Table 5" both resolve without assuming they match.
    """
    targets = {}

    def stamp(match):
        head, src, kind, number, tail = match.groups()
        kind = kind.lower()
        num = int(number)
        anchor = f"{'fig' if kind == 'figure' else 'tab'}-{num}"
        targets[(kind, str(num))] = anchor
        alt = _ALT.search(head + tail)
        if alt:
            token = alt.group(1).split()[-1].strip(".:") if alt.group(1).split() else ""
            if token:
                targets[(kind, token.upper())] = anchor
                as_roman = roman_to_int(token)
                if as_roman:
                    targets[(kind, str(as_roman))] = anchor
        if re.search(r'\bid="', head + tail):
            return match.group(0)
        return f'<img {head}id="{anchor}" src="{src}"{tail}>'

    return _ASSET_IMG.sub(stamp, body_html), targets


def linkify_xrefs(body_html: str, targets):
    """Turn mentions into links, but only where the target actually exists."""
    linked, unresolved = 0, {}

    def repl(match):
        nonlocal linked
        word, number = match.group(1), match.group(2)
        # "[13, Table V]" is a table inside reference 13, not one of ours.
        if _CITED.search(match.string[: match.start()]):
            return match.group(0)
        first = word[0].lower()
        kind = "figure" if first == "f" else ("algorithm" if first == "a" else "table")
        key = (kind, number.upper() if not number.isdigit() else number)
        anchor = targets.get(key)
        if anchor is None and not number.isdigit():
            as_roman = roman_to_int(number)
            anchor = targets.get((kind, str(as_roman))) if as_roman else None
        if anchor is None:
            unresolved[f"{word} {number}"] = unresolved.get(f"{word} {number}", 0) + 1
            return match.group(0)
        linked += 1
        return f'<a class="xref" href="#{anchor}">{match.group(0)}</a>'

    out, depth = [], 0
    for segment in re.split(r"(<[^>]+>)", body_html):
        if segment.startswith("<"):
            if _SKIP_OPEN.match(segment) and not segment.startswith("</"):
                depth += 1
            elif _SKIP_CLOSE.match(segment):
                depth = max(0, depth - 1)
            out.append(segment)
        elif depth:
            out.append(segment)
        else:
            out.append(_XREF.sub(repl, segment))
    return "".join(out), linked, unresolved


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
    # One pass over the whole page: a section often points at a figure that
    # lives in another section, so the target table must be complete first.
    whole, algos = wrap_algorithms("".join(body_parts))
    whole, targets = label_ids(whole)
    targets.update(algos)
    whole, xrefs, xref_missing = linkify_xrefs(whole, targets)
    body_parts = [whole]
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
<body data-paper="{html.escape(paper_root.name)}">
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
  <h2>螢光筆</h2>
  <div class="controls">
    <button id="hlon" class="on">🖍 顯示畫記</button>
    <button id="hlcopy">複製畫記</button>
    <button id="hlclear">清空</button>
  </div>
  <div id="hlstat"></div>
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
選取正文會浮出<strong>螢光筆</strong>，畫記存在這台瀏覽器裡，要留下來請用側欄的「複製畫記」貼回對話。
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
<div id="hlbar" hidden>
<button data-c="1" title="黃色畫記" aria-label="黃色畫記"></button>
<button data-c="2" title="綠色畫記" aria-label="綠色畫記"></button>
<button data-c="3" title="藍色畫記" aria-label="藍色畫記"></button>
<button id="hldel" title="清除這條畫記" aria-label="清除這條畫記" hidden>✕</button>
</div>
<div id="ov" hidden></div>
<aside id="panel" hidden tabindex="-1" role="dialog" aria-modal="true"><div class="pbar">
<button id="pjump" data-tip="跳到原文" aria-label="跳到原文">⤴</button>
<button id="pclose" data-tip="關閉" aria-label="關閉">✕</button></div>
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
    print(f"            演算法區塊 {len(algos)} 個、圖表交叉引用 {xrefs} 處已可點擊")
    if xref_missing:
        listed = "、".join(f"{k}×{v}" for k, v in sorted(xref_missing.items())[:6])
        print(f"  🟡 這些引用找不到對應的圖或表，維持純文字：{listed}")
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
