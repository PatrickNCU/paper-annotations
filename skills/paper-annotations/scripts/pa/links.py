"""Link rewriting for the mirrored tree."""

from __future__ import annotations

import re
from pathlib import Path

# Reference-style links: ![alt][label] with [label]: url defined elsewhere.
# Standard Markdown, and one converter run emits them while another emits the
# inline form -- so the text is normalised once, here, and every later stage
# (link rewriting, rendering, figure detection) only ever sees inline links.
# The negative lookahead keeps footnote definitions ([^7]: ...) out of it.
_REF_DEF = re.compile(r"^ {0,3}\[(?!\^)([^\]]+)\]:\s*(\S+)\s*(?:[\"'(].*)?$")
_REF_USE = re.compile(r"(!?)\[([^\]]*)\]\[([^\]]*)\]")


def normalize_ref_links(lines):
    """Rewrite reference-style links inline. Line count is preserved, because
    anchors are resolved by line index against this same list."""
    defs = {}
    for line in lines:
        found = _REF_DEF.match(line)
        if found:
            defs[found.group(1).strip().lower()] = found.group(2)
    if not defs:
        return list(lines)

    def sub(match):
        label = (match.group(3) or match.group(2)).strip().lower()
        url = defs.get(label)
        if not url:
            return match.group(0)
        return f"{match.group(1)}[{match.group(2)}]({url})"

    out = []
    for line in lines:
        if _REF_DEF.match(line):
            out.append("")  # the definition now lives in the link itself
        else:
            out.append(_REF_USE.sub(sub, line))
    return out


_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\s*(?:\"[^\"]*\")?\))")
# Cards are emitted as raw HTML, so their back-links live in an attribute and
# the Markdown pattern never saw them -- they broke silently on every rebase.
_ATTR_RE = re.compile(r"(\b(?:href|src)=\")([^\"]+)(\")")


def rewrite_links(text: str, src_dir: Path, dst_dir: Path) -> str:
    """Re-relativize relative links so the mirrored file still resolves assets.

    Works on absolute directories, so the annotated tree may live anywhere --
    inside the paper package, beside it, or on the other side of the disk.
    """
    import posixpath

    def fix(match):
        target = match.group(2)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith(("/", "#")):
            return match.group(0)
        anchor = ""
        if "#" in target:
            target, _, anchor = target.partition("#")
            anchor = "#" + anchor
        if not target:
            return match.group(0)
        absolute = posixpath.normpath(posixpath.join(src_dir.as_posix(), target))
        rebased = posixpath.relpath(absolute, dst_dir.as_posix())
        return match.group(1) + rebased + anchor + match.group(3)

    return _ATTR_RE.sub(fix, _LINK_RE.sub(fix, text))


def rel_href(from_file: Path, to_file: Path) -> str:
    """A link from one generated file to another, both given as real paths."""
    import posixpath

    return posixpath.relpath(to_file.as_posix(), from_file.parent.as_posix())
