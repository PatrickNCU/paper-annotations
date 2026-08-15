"""A focused Markdown renderer for converted-paper Markdown.

Not a CommonMark implementation. It handles exactly the vocabulary the pdf2md
rules produce -- headings, paragraphs, images, links, emphasis, code, ordered
and unordered lists, pipe tables, blockquotes, footnotes, raw HTML blocks --
plus LaTeX math, which is pulled out before any Markdown processing so that
underscores and asterisks inside formulas survive untouched.
"""

from __future__ import annotations

import re

NUL = "\x00"

# Escape a bare "&" but leave real entities (&emsp; is used for algorithm indent).
_AMP = re.compile(r"&(?!#?\w+;)")


def esc(text: str) -> str:
    return _AMP.sub("&amp;", text).replace("<", "&lt;").replace(">", "&gt;")


class _Vault:
    """Holds extracted spans so Markdown rules cannot corrupt them."""

    def __init__(self):
        self.items = []

    def stash(self, text: str) -> str:
        self.items.append(text)
        return f"{NUL}{len(self.items) - 1}{NUL}"

    def restore(self, text: str) -> str:
        def sub(match):
            return self.items[int(match.group(1))]

        for _ in range(3):  # placeholders may nest one level (math inside a table)
            new = re.sub(NUL + r"(\d+)" + NUL, sub, text)
            if new == text:
                break
            text = new
        return text


def _extract(md: str, vault: _Vault):
    # fenced code first: everything inside is literal
    def code_block(match):
        lang = (match.group(1) or "").strip()
        body = esc(match.group(2))
        cls = f' class="lang-{lang}"' if lang else ""
        return vault.stash(f"<pre><code{cls}>{body}</code></pre>")

    md = re.sub(r"```([^\n]*)\n(.*?)```", code_block, md, flags=re.DOTALL)

    # display math -- kept as $$...$$ text for MathJax, but HTML-escaped so a
    # "<" inside a formula is never parsed as a tag
    md = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: vault.stash(f'<div class="math-display">$${esc(m.group(1))}$$</div>'),
        md,
        flags=re.DOTALL,
    )
    md = re.sub(
        r"(?<!\$)\$([^\$\n]+?)\$(?!\$)",
        lambda m: vault.stash(f"<span class=\"math\">${esc(m.group(1))}$</span>"),
        md,
    )
    md = re.sub(r"`([^`\n]+)`", lambda m: vault.stash(f"<code>{esc(m.group(1))}</code>"), md)
    return md


_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FOOTREF = re.compile(r"\[\^([\w-]+)\]")
_MARK = re.compile(r"==(?=\S)(.+?)(?<=\S)==")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.DOTALL)
_ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")


def _inline(text: str) -> str:
    text = esc(text)
    text = _IMG.sub(lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}">', text)
    text = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = _FOOTREF.sub(
        lambda m: f'<sup class="fn"><a href="#fn-{m.group(1)}" id="fnref-{m.group(1)}">{m.group(1)}</a></sup>',
        text,
    )
    text = _MARK.sub(lambda m: f"<mark>{m.group(1)}</mark>", text)
    text = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", text)
    return text


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_ULI = re.compile(r"^\s*[-*+]\s+(.*)$")
_OLI = re.compile(r"^\s*(\d+)\.\s+(.*)$")
_FOOTDEF = re.compile(r"^\[\^([\w-]+)\]:\s*(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def _cells(row: str):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def render(md: str, heading_hook=None) -> tuple:
    """Return (html, headings). headings is [(level, text, anchor_id)]."""
    vault = _Vault()
    md = _extract(md, vault)
    lines = md.split("\n")

    out, headings, footnotes = [], [], []
    para, i = [], 0

    def flush():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush()
            i += 1
            continue

        # raw HTML block (our question cards, <sub> footers, &c.)
        if stripped.startswith("<") and not stripped.startswith("<http"):
            flush()
            out.append(line)
            i += 1
            continue

        if stripped.startswith(NUL) and stripped.endswith(NUL):
            flush()
            out.append(vault.restore(stripped))
            i += 1
            continue

        match = _HEADING.match(stripped)
        if match:
            flush()
            level = len(match.group(1))
            text = _inline(match.group(2))
            anchor = heading_hook(level, match.group(2)) if heading_hook else f"h{len(headings)}"
            headings.append((level, match.group(2), anchor))
            out.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            i += 1
            continue

        match = _FOOTDEF.match(stripped)
        if match:
            flush()
            footnotes.append((match.group(1), _inline(match.group(2))))
            i += 1
            continue

        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{_inline(' '.join(quote))}</blockquote>")
            continue

        if "|" in stripped and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            flush()
            header = _cells(stripped)
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(_cells(lines[i]))
                i += 1
            head = "".join(f"<th>{_inline(c)}</th>" for c in header)
            body = "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            out.append(
                f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
                f"<tbody>{body}</tbody></table></div>"
            )
            continue

        match = _OLI.match(line)
        if match:
            flush()
            start = match.group(1)
            items = []
            while i < len(lines):
                m2 = _OLI.match(lines[i])
                if not m2:
                    break
                items.append(f"<li>{_inline(m2.group(2))}</li>")
                i += 1
            attr = f' start="{start}"' if start != "1" else ""
            out.append(f"<ol{attr}>" + "".join(items) + "</ol>")
            continue

        match = _ULI.match(line)
        if match:
            flush()
            items = []
            while i < len(lines):
                m2 = _ULI.match(lines[i])
                if not m2:
                    break
                items.append(f"<li>{_inline(m2.group(1))}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        para.append(stripped)
        i += 1

    flush()

    if footnotes:
        # Keep the paper's own footnote label. An <ol> would renumber from 1,
        # so a footnote the paper calls 3 would silently become 1.
        notes = "".join(
            f'<div class="fn-item" id="fn-{key}">'
            f'<span class="fn-key">{esc(key)}</span>'
            f'<span>{text} <a class="fn-back" href="#fnref-{key}">↩</a></span>'
            f"</div>"
            for key, text in footnotes
        )
        out.append(f'<section class="footnotes">{notes}</section>')

    return vault.restore("\n".join(out)), headings
