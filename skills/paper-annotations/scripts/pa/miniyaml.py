"""Dependency-free YAML subset used by paper-annotations.

Supports exactly what the card / paper.yml schema needs:

  * nested mappings (indentation based)
  * block sequences ("- item") of scalars
  * inline flow sequences ("[a, b]")
  * block scalars ("|" and "|-") -- how quoted paper text is stored
  * single/double quoted and plain scalars
  * null / ~ / true / false / int / float

Full-line "#" comments are ignored. Inline "#" is NOT treated as a comment,
because a quoted sentence from a paper may legitimately contain one.

Deliberately not supported: anchors, aliases, tags, multi-document streams,
complex keys, sequences of mappings.
"""

from __future__ import annotations


class MiniYamlError(ValueError):
    pass


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _split_key(line: str):
    """Split "key: value" respecting quotes. Returns (key, rest)."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == ":" and (i + 1 == len(line) or line[i + 1] == " "):
            return line[:i].strip(), line[i + 1 :].strip()
    raise MiniYamlError(f"not a mapping entry: {line!r}")


def _parse_scalar(text: str):
    text = text.strip()
    if text == "" or text in ("null", "~"):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        body = text[1:-1]
        if text[0] == '"':
            body = (
                body.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            )
        return body
    # dump() writes an empty mapping as {}; without this it came back as the
    # string "{}" and every .items() on it blew up.
    if text == "{}":
        return {}
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_flow(inner)]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _split_flow(inner: str):
    parts, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf += ch
            continue
        if ch == ",":
            parts.append(buf.strip())
            buf = ""
            continue
        buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


class _Parser:
    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.i = 0

    def peek(self):
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip() or line.lstrip().startswith("#"):
                self.i += 1
                continue
            return line
        return None

    def parse_node(self, indent: int):
        line = self.peek()
        if line is None or _indent_of(line) < indent:
            return None
        if line.lstrip().startswith("- "):
            return self.parse_sequence(_indent_of(line))
        return self.parse_mapping(_indent_of(line))

    def parse_sequence(self, indent: int):
        items = []
        while True:
            line = self.peek()
            if line is None or _indent_of(line) != indent:
                break
            stripped = line.strip()
            if not stripped.startswith("- "):
                break
            self.i += 1
            items.append(_parse_scalar(stripped[2:]))
        return items

    def parse_mapping(self, indent: int):
        result = {}
        while True:
            line = self.peek()
            if line is None or _indent_of(line) != indent:
                break
            if line.strip().startswith("- "):
                break
            key, rest = _split_key(line.strip())
            self.i += 1
            if rest in ("|", "|-", "|+", ">", ">-"):
                result[key] = self._block_scalar(indent, keep=rest.endswith("+"),
                                                 chomp=rest.endswith("-"),
                                                 folded=rest.startswith(">"))
            elif rest == "":
                nxt = self.peek()
                if nxt is not None and _indent_of(nxt) > indent:
                    result[key] = self.parse_node(_indent_of(nxt))
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(rest)
        return result

    def _block_scalar(self, parent_indent: int, keep=False, chomp=False, folded=False):
        raw = []
        base = None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip():
                raw.append("")
                self.i += 1
                continue
            ind = _indent_of(line)
            if ind <= parent_indent:
                break
            if base is None:
                base = ind
            raw.append(line[base:] if len(line) >= base else line.lstrip())
            self.i += 1
        while raw and raw[-1] == "":
            raw.pop()
        text = ("\n".join(raw) if not folded else " ".join(x for x in raw if x))
        if chomp:
            return text
        return text + "\n" if text else ""


def load(text: str):
    parser = _Parser(text)
    line = parser.peek()
    if line is None:
        return {}
    return parser.parse_node(_indent_of(line)) or {}


# --------------------------------------------------------------------------
# dumping
# --------------------------------------------------------------------------

_PLAIN_UNSAFE_PREFIX = "-?:,[]{}#&*!|>'\"%@`"


def _needs_quotes(text: str) -> bool:
    if text == "":
        return True
    if text.strip() != text:
        return True
    if text[0] in _PLAIN_UNSAFE_PREFIX:
        return True
    if ": " in text or text.endswith(":"):
        return True
    if text in ("true", "false", "null", "~"):
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False


def _dump_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if _needs_quotes(text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def dump(data, indent: int = 0) -> str:
    pad = " " * indent
    out = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) and value:
                out.append(f"{pad}{key}:")
                out.append(dump(value, indent + 2))
            elif isinstance(value, list) and value:
                out.append(f"{pad}{key}:")
                for item in value:
                    out.append(f"{pad}  - {_dump_scalar(item)}")
            elif isinstance(value, list):
                out.append(f"{pad}{key}: []")
            elif isinstance(value, dict):
                out.append(f"{pad}{key}: {{}}")
            elif isinstance(value, str) and "\n" in value:
                out.append(f"{pad}{key}: |-")
                for line in value.rstrip("\n").split("\n"):
                    out.append(f"{pad}  {line}" if line else "")
            else:
                out.append(f"{pad}{key}: {_dump_scalar(value)}")
        return "\n".join(out)
    if isinstance(data, list):
        for item in data:
            out.append(f"{pad}- {_dump_scalar(item)}")
        return "\n".join(out)
    return f"{pad}{_dump_scalar(data)}"
