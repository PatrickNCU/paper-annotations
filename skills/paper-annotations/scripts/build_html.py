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
#layout{display:flex;align-items:flex-start}
#side{position:sticky;top:0;height:100vh;width:310px;flex:0 0 310px;overflow-y:auto;
background:var(--sidebar);border-right:1px solid var(--line);padding:18px 16px;font-size:14px}
#main{flex:1;min-width:0;max-width:900px;margin:0 auto;padding:28px 34px 120px}
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
.qcard{margin:18px 0;border:1px solid var(--line);border-left:4px solid var(--muted);
border-radius:8px;background:var(--card);padding:10px 16px}
.qcard[data-status=open]{border-left-color:var(--open)}
.qcard[data-status=half]{border-left-color:var(--half)}
.qcard[data-status=resolved]{border-left-color:var(--done)}
.qcard>summary{cursor:pointer;font-weight:600;list-style:none;outline:none}
.qcard>summary::-webkit-details-marker{display:none}
.qcard>summary::before{content:"▸ ";color:var(--muted)}
.qcard[open]>summary::before{content:"▾ "}
.qcard[open]>summary{margin-bottom:8px;padding-bottom:8px;border-bottom:1px dashed var(--line)}
.qcard sub{font-size:11.5px;color:var(--muted);font-weight:400}
.qcard.hidden{display:none}
.qcard{scroll-margin-top:14px}
.qcard:target{outline:2px solid var(--accent);outline-offset:3px}
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
#layout{display:block}
#side{position:static;height:auto;max-height:56vh;width:auto;flex:none;
border-right:none;border-bottom:1px solid var(--line)}
#main{padding:20px 18px 90px}}
"""

SCRIPT = """
(function(){
  var cards=[].slice.call(document.querySelectorAll('.qcard'));
  var recall=document.getElementById('recall');
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
      if(want!=='all'&&c.dataset.status!==want) ok=false;
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
  }
  recall.addEventListener('click',function(){
    cards.forEach(function(c){ c.open=false; });
  });
  showAI.addEventListener('click',function(){ showAI.classList.toggle('on'); apply(); });
  filter.addEventListener('change',apply);
  search.addEventListener('input',apply);
  document.getElementById('expand').addEventListener('click',function(){
    cards.forEach(function(c){ c.open=true; });
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
<nav id="side">
  <div class="controls">
    <button id="theme">🌗 跟隨系統</button>
    <button id="recall">全部收合</button>
    <button id="expand">全部展開</button>
  </div>
  <div class="controls">
    <select id="statusf">
      <option value="all">全部狀態</option>
      <option value="open">未解決</option>
      <option value="half">半懂</option>
      <option value="resolved">已解決</option>
    </select>
    <button id="showai" class="on">AI 提示卡</button>
  </div>
  <div class="controls"><input id="q" type="search" placeholder="搜尋疑問內容…"></div>
  <h2>疑問（{len(questions)}）</h2>
  <div id="qlist">{qlist}</div>
  <h2>目錄</h2>
  {nav}
</nav>
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
疑問預設<strong>收合</strong>：你會先看到自己當初的問題，想過再展開答案。
</div>
{''.join(body_parts)}
</main>
</div>
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
