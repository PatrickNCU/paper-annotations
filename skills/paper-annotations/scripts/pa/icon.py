"""The app icon, drawn here instead of shipped as a file.

Adding a .png to the repo would mean a binary nobody can review in a diff and
a second place the palette is written down. It is a rounded square with two
sheets of paper on it, computed from the same accent colour the pages use, so
changing the theme changes the icon.

Only the phone's home screen needs this (docs/roadmap 第 14 項): a manifest
without icons installs as a blank square on Android.
"""

from __future__ import annotations

import struct
import zlib

# The light palette's --accent and --bg, copied rather than parsed: the icon
# has to look the same on a phone whose owner runs the dark theme, so it does
# not follow the theme at all -- it follows the tool's identity.
ACCENT = (138, 79, 36)
PAPER = (251, 250, 247)
SHADE = (240, 236, 226)

_CACHE: dict[int, bytes] = {}


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _cover(px: float, py: float, x: float, y: float, w: float, h: float, r: float) -> float:
    """How much of this pixel the rounded rectangle covers, 0..1.

    The signed distance to the shape, clamped over one pixel. That one line is
    the whole anti-aliasing story: without it the corners come out as stairs.
    """
    cx = min(max(px, x + r), x + w - r)
    cy = min(max(py, y + r), y + h - r)
    dx, dy = px - cx, py - cy
    return min(1.0, max(0.0, 0.5 - ((dx * dx + dy * dy) ** 0.5 - r)))


def _draw(rows, size, rect, color, alpha=1.0):
    x, y, w, h, r = (v * size for v in rect)
    x0, x1 = max(0, int(x - 1)), min(size, int(x + w + 2))
    y0, y1 = max(0, int(y - 1)), min(size, int(y + h + 2))
    red, green, blue = color
    for py in range(y0, y1):
        row = rows[py]
        for px in range(x0, x1):
            a = _cover(px + 0.5, py + 0.5, x, y, w, h, r) * alpha
            if a <= 0:
                continue
            i = px * 4
            row[i] = int(row[i] + (red - row[i]) * a)
            row[i + 1] = int(row[i + 1] + (green - row[i + 1]) * a)
            row[i + 2] = int(row[i + 2] + (blue - row[i + 2]) * a)
            row[i + 3] = max(row[i + 3], int(255 * a))


def icon_png(size: int = 512) -> bytes:
    """One square PNG, transparent outside the rounded corners."""
    if size in _CACHE:
        return _CACHE[size]
    rows = [bytearray(size * 4) for _ in range(size)]
    _draw(rows, size, (0, 0, 1, 1, 0.22), ACCENT)
    _draw(rows, size, (0.30, 0.19, 0.42, 0.56, 0.05), SHADE)
    _draw(rows, size, (0.21, 0.25, 0.42, 0.56, 0.05), PAPER)
    # three lines of text and, under them, the one that is highlighted: the
    # tool is about the sentence you got stuck on, not about pages in general
    for top, width in ((0.35, 0.28), (0.44, 0.30), (0.53, 0.20)):
        _draw(rows, size, (0.27, top, width, 0.035, 0.018), ACCENT, 0.32)
    _draw(rows, size, (0.27, 0.62, 0.24, 0.05, 0.022), ACCENT, 0.85)

    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    _CACHE[size] = png
    return png
