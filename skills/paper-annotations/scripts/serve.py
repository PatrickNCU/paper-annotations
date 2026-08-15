"""Serve the review page locally so its 儲存 button can actually save.

A page opened from disk cannot write a file or start a program -- that is the
browser's security model, not a gap in this tool. This is the smallest thing
that closes it: a local HTTP server that hands out the review page and accepts
its highlights back, writing them into notes/marks/ and rebuilding the page.

    python serve.py <work> [--port 8975] [--no-open]

Without it everything still works; highlights simply stay in the browser until
they are copied out by hand. Nothing else about the page changes.

Safety, in the order it matters:

  * Bound to 127.0.0.1 only. Never 0.0.0.0 -- that would let anyone on the
    same network write files onto this machine.
  * Writes are confined to notes/marks/, and filenames are generated here.
    Nothing in a request is ever used as a path.
  * Saving requires a custom header carrying a token minted at startup. A page
    on another origin cannot send a custom header without a CORS preflight,
    and the preflight is refused; it cannot read the token either, because no
    CORS headers are sent anywhere.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_marks
import paperkit

paperkit.bootstrap()

HERE = Path(__file__).resolve().parent
MAX_BODY = 4 << 20  # a paper's worth of highlights is kilobytes; this is slack


class Handler(SimpleHTTPRequestHandler):
    token = ""
    work = Path(".")
    paper_root = Path(".")
    notes = Path(".")
    lock = threading.Lock()

    # Quieter than the default, but str() first: log_error passes an HTTPStatus
    # here, not a string, and testing it for membership raised inside the
    # error handler -- which turned every missing file into a stack trace.
    def log_message(self, fmt, *args):  # noqa: A003
        line = fmt % args
        if "_pa/" in line or " 4" in line or " 5" in line:
            sys.stderr.write(f"  {line}\n")

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # no CORS headers anywhere: another origin may not read these replies
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # same-origin GETs do not send one
        host = self.headers.get("Host", "")
        return origin in (f"http://{host}", f"https://{host}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/_pa/hello":
            if not self._same_origin():
                self._json(403, {"error": "cross-origin"})
                return
            self._json(200, {"ok": True, "token": self.token})
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", self.index_url)
            self.end_headers()
            return
        if path == "/favicon.ico":  # browsers always ask; there is not one
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/_pa/marks":
            self._json(404, {"error": "unknown endpoint"})
            return
        if not self._same_origin():
            self._json(403, {"error": "cross-origin"})
            return
        if self.headers.get("X-PA-Token") != self.token:
            self._json(403, {"error": "bad token"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._json(400, {"error": "bad length"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            records = payload["marks"]
            if not isinstance(records, list):
                raise ValueError
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            self._json(400, {"error": "bad payload"})
            return

        clean = []
        for item in records:
            if not isinstance(item, dict):
                continue
            rec = {k: str(item.get(k) or "") for k in
                   ("file", "color", "exact", "prefix", "suffix", "note")}
            # a path from the network is never trusted; it only has to name one
            # of the sources this paper already declares
            if rec["exact"] and rec["file"] in self.sources:
                clean.append(rec)
        if not clean:
            self._json(400, {"error": "沒有可用的畫記"})
            return

        with self.lock:  # one writer at a time: ids are handed out by scanning
            result = import_marks.write_marks(self.paper_root, self.notes, clean)
            rebuilt, log = self._rebuild() if result["written"] else (True, "")
        self._json(200, {
            "written": result["written"],
            "skipped": result["skipped"],
            "bad": [f"{q}… {why}" for q, why in result["bad"]],
            "soft": [f"{q}… {why}" for q, why in result["soft"]],
            "rebuilt": rebuilt,
            "log": log,
        })

    def _rebuild(self):
        """Only the HTML: marks never touch the annotated Markdown."""
        # encoding spelled out: text=True decodes with the console codepage,
        # which on a zh-TW Windows is cp950 and cannot read the build's UTF-8
        # output at all -- the reader thread died and took the log with it.
        run = subprocess.run(
            [sys.executable, str(HERE / "build_html.py"), str(self.work)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = (run.stdout or "") + (run.stderr or "")
        sys.stderr.write(out)
        return run.returncode == 0, out.strip().splitlines()[:6]


def flag(argv, name, fallback=None):
    prefix = f"--{name}="
    for arg in argv:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    if f"--{name}" in argv:
        idx = argv.index(f"--{name}")
        if idx + 1 < len(argv) and not argv[idx + 1].startswith("--"):
            return argv[idx + 1]
    return fallback


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    work = Path(args[0] if args else ".").resolve()
    config, paper_root, notes, annotated = paperkit.load_workspace(work)
    if not (annotated / "index.html").is_file():
        raise SystemExit(f"找不到 {annotated / 'index.html'}，請先執行 build_html.py")

    port = int(flag(argv, "port", "8975"))
    Handler.token = secrets.token_urlsafe(24)
    Handler.work, Handler.paper_root, Handler.notes = work, paper_root, notes
    Handler.sources = {Path(p).as_posix() for p in (config.get("sources") or [])}

    # The review page points at images that live in the package next door, so
    # serving annotated/ alone gives a page with every figure missing. Root at
    # the folder holding both and let the links resolve exactly as they do on
    # disk; "/" redirects to wherever the page actually sits. The stdlib
    # handler still refuses to walk above whatever root it is given.
    root = Path(os.path.commonpath([str(annotated), str(paper_root)]))
    Handler.index_url = "/" + (annotated / "index.html").relative_to(root).as_posix()

    server = ThreadingHTTPServer(
        ("127.0.0.1", port), partial(Handler, directory=str(root))
    )
    url = f"http://127.0.0.1:{port}/"
    print(f"複習頁       {url}")
    print(f"             畫記會直接寫進 {notes / 'marks'}，並重建複習頁")
    print(f"             檔案根目錄 {root}（只有本機連得到）")
    print("             Ctrl+C 結束")
    if "--no-open" not in argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已結束。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
