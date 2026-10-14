"""Write a notes file so that it is either the old version or the new one.

Path.write_text truncates the file first and then fills it: a crash, a
power cut or a full disk in between leaves a card, a mark or a review log cut
short -- and the review log is the one file here nothing can regenerate
(docs/adr/0003). So the new text goes to a temporary file beside it, is
flushed to disk, and then takes the old file's place in one rename.

Only for files that are the source of truth (notes/, papers.yml, paper.yml).
Generated pages can be rebuilt and keep their plain writes.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path


def write_text(path, text: str, encoding: str = "utf-8", newline: str = "\n") -> None:
    """Path.write_text with the same arguments, made atomic.

    `newline` is honoured the way Path.write_text honours it for the two
    values this tool uses: "\\n" writes the text as it is, "\\r\\n" turns
    every line ending into CRLF.
    """
    path = Path(path)
    if newline == "\r\n":
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    data = text.encode(encoding)
    # A dotted name ending in .tmp: no glob for *.md ever picks it up, even if
    # it is left behind. Unique per thread, since the server writes from
    # several at once.
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        # Windows refuses the rename for a moment while something else has
        # the file open -- an editor, a sync client, a virus scanner.
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
