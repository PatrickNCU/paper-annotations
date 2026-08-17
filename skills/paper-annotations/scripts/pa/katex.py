"""Inline KaTeX (CSS + fonts + JS) so the page renders math with no network."""

from __future__ import annotations

import base64
import re
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "katex"

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
