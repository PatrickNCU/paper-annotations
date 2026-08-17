"""Serve the review page locally so its 儲存 button can actually save.

A page opened from disk cannot write a file or start a program -- that is the
browser's security model, not a gap in this tool. This is the smallest thing
that closes it: a local HTTP server that hands out the review page and accepts
its highlights back, writing them into notes/marks/ and rebuilding the page.

    python serve.py <work> [--port 8975] [--no-open]
    python serve.py <work> --launcher        # 只放一個點兩下就能開的啟動器

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
import re
import secrets
import socket
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from datetime import date

from . import cli, marks as marklib, notes, srs, workspace

cli.bootstrap()

# The CLI wrappers in scripts/ are what launchers and the rebuild subprocess
# invoke -- pa/ is an implementation detail nothing outside may point at.
SCRIPTS = Path(__file__).resolve().parent.parent
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
            # the paper is named so that a second run can tell "already serving
            # this one" from "something else has the port" -- see main()
            self._json(200, {"ok": True, "token": self.token, "paper": self.work.name})
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", self.index_url)
            self.end_headers()
            return
        if path == "/_pa/reviews":
            if not self._same_origin():
                self._json(403, {"error": "cross-origin"})
                return
            # Read-only, so no token: it says which of the reader's own cards
            # are due, which is no more than the page already shows.
            self._json(200, self._schedule())
            return
        if path == "/favicon.ico":  # browsers always ask; there is not one
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def _schedule(self):
        return srs.schedule(self.notes, notes.load_cards(self.notes), date.today().isoformat())

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/_pa/marks", "/_pa/mark", "/_pa/review"):
            self._json(404, {"error": "unknown endpoint"})
            return
        if not self._same_origin():
            self._json(403, {"error": "cross-origin"})
            return
        if self.headers.get("X-PA-Token") != self.token:
            self._json(403, {"error": "bad token"})
            return
        if path == "/_pa/mark":
            self._one_mark()
            return
        if path == "/_pa/review":
            self._grade()
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
            result = marklib.write_marks(self.paper_root, self.notes, clean)
            rebuilt, log = self._rebuild() if result["written"] else (True, "")
        self._json(200, {
            "written": result["written"],
            "skipped": result["skipped"],
            "bad": [f"{q}… {why}" for q, why in result["bad"]],
            "soft": [f"{q}… {why}" for q, why in result["soft"]],
            "rebuilt": rebuilt,
            "log": log,
        })

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _one_mark(self):
        """Change or remove a mark that is already filed.

        The id is looked up among the marks actually on disk and the path comes
        from that record -- a path in the request would be a way to write, or
        delete, anywhere on the machine.
        """
        payload = self._body()
        if not isinstance(payload, dict):
            self._json(400, {"error": "bad payload"})
            return
        wanted = str(payload.get("id") or "")
        action = str(payload.get("action") or "")
        if action == "clear":
            with self.lock:
                gone = 0
                for mark in notes.load_marks(self.notes):
                    mark["path"].unlink()
                    gone += 1
                rebuilt, log = self._rebuild()
            self._json(200, {"ok": True, "action": "clear", "deleted": gone,
                             "rebuilt": rebuilt, "log": log})
            return
        if action not in ("update", "delete") or not wanted:
            self._json(400, {"error": "bad action"})
            return

        with self.lock:
            found = None
            for mark in notes.load_marks(self.notes):
                if str(mark["meta"].get("id")) == wanted:
                    found = mark
                    break
            if found is None:
                self._json(404, {"error": f"找不到畫記 {wanted}"})
                return
            if action == "delete":
                found["path"].unlink()
            else:
                marklib.save_mark(
                    found,
                    str(payload.get("color") or found["color"]),
                    str(payload.get("note") or ""),
                )
            rebuilt, log = self._rebuild()
        self._json(200, {"ok": True, "action": action, "rebuilt": rebuilt, "log": log})

    def _grade(self):
        """Record one grading of one card.

        The card id is looked up among the cards actually on disk and the log
        path is built from that id -- nothing in the request ever becomes a
        path. Deliberately does NOT rebuild: grading changes the schedule, not
        the page, and a reader working through a dozen cards should not pay for
        a dozen rebuilds. The page asks for the fresh schedule instead, and it
        is returned right here (see docs/adr/0003).
        """
        payload = self._body()
        if not isinstance(payload, dict):
            self._json(400, {"error": "bad payload"})
            return
        wanted = str(payload.get("id") or "")
        grade = str(payload.get("grade") or "")
        if grade not in srs.GRADES:
            self._json(400, {"error": f"grade 只能是 {' / '.join(srs.GRADES)}"})
            return

        with self.lock:
            cards = notes.load_cards(self.notes)
            card = next(
                (c for c in cards if str(c["meta"].get("id")) == wanted), None
            )
            if card is None:
                self._json(404, {"error": f"找不到卡片 {wanted}"})
                return
            if not srs.eligible(card["meta"]):
                self._json(400, {"error": f"Q{wanted} 不在排程裡（只有你自己問過、且已解決的卡才排程）"})
                return
            srs.append(self.notes, wanted, grade, date.today().isoformat())
            state = self._schedule()
        self._json(200, {"ok": True, "id": wanted, "grade": grade, "schedule": state})

    def _rebuild(self):
        """Only the HTML: marks never touch the annotated Markdown."""
        # encoding spelled out: text=True decodes with the console codepage,
        # which on a zh-TW Windows is cp950 and cannot read the build's UTF-8
        # output at all -- the reader thread died and took the log with it.
        run = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_html.py"), str(self.work)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = (run.stdout or "") + (run.stderr or "")
        sys.stderr.write(out)
        return run.returncode == 0, out.strip().splitlines()[:6]


def write_launcher(work: Path, annotated: Path, port: int) -> Path:
    """Drop a double-clickable launcher beside the review page.

    The body is ASCII only, deliberately: cmd.exe parses a .cmd in the OEM
    codepage, so UTF-8 text inside breaks the script itself rather than merely
    printing badly. The filename is free to be Chinese -- that goes through the
    filesystem, not the parser.
    """
    home = annotated.parent
    try:
        target = work.relative_to(home).as_posix().replace("/", os.sep)
    except ValueError:
        target = str(work)
    tag = "".join(c for c in work.name if c.isascii() and (c.isalnum() or c in "-_")) or "paper"
    script = str(SCRIPTS / "serve.py")
    # Installed as a plugin, this file sits under .../<plugin>/<version>/…, and
    # that version directory changes every time the plugin is updated -- a
    # launcher naming it would break on the next release. Look the newest one
    # up at run time instead, and keep today's path only as the fallback.
    versioned = ""
    if re.fullmatch(r"\d+(\.\d+)*", SCRIPTS.parents[2].name):
        versioned = str(SCRIPTS.parents[3])

    if os.name == "nt":
        path = home / "開啟複習頁.cmd"
        # backslashes throughout: "for /d" will not glob a mixed-separator path
        win = script.replace("/", "\\")
        find = ""
        if versioned:
            find = (
                'set "PA="\n'
                f'for /d %%d in ("{versioned.replace("/", chr(92))}\\*") do set '
                '"PA=%%d\\skills\\paper-annotations\\scripts\\serve.py"\n'
                f'if not exist "%PA%" set "PA={win}"\n'
            )
        run = "%PA%" if versioned else win
        body = (
            "@echo off\n"
            "rem ASCII only: cmd.exe parses this file in the OEM codepage.\n"
            "chcp 65001 >nul\n"
            'cd /d "%~dp0"\n'
            f"title {tag} review page\n"
            "echo Close this window to stop the server.\n"
            "echo.\n"
            + find
            + f'python "{run}" "{target}" --port {port}\n'
            "echo.\n"
            "echo Server stopped.\n"
            "pause\n"
        )
    else:
        path = home / "開啟複習頁.command"
        body = (
            "#!/bin/sh\n"
            "# Close this window to stop the server.\n"
            'cd "$(dirname "$0")" || exit 1\n'
            + (
                f'PA="$(ls -d "{versioned}"/*/skills/paper-annotations/scripts/serve.py'
                ' 2>/dev/null | sort -V | tail -1)"\n'
                f'[ -f "$PA" ] || PA="{script}"\n'
                f'exec python3 "$PA" "{target}" --port {port}\n'
                if versioned
                else f'exec python3 "{script}" "{target}" --port {port}\n'
            )
        )
    path.write_text(body, encoding="ascii", newline="\r\n" if os.name == "nt" else "\n")
    if os.name != "nt":
        path.chmod(0o755)
    return path


def taken(port: int) -> bool:
    """Is anything already listening here?

    Asked before binding rather than after failing to, because HTTPServer sets
    SO_REUSEADDR and Windows takes that to mean a second socket may bind the
    same address -- no error is raised, and the second server just sits there
    while the first one keeps answering.
    """
    with socket.socket() as probe_socket:
        probe_socket.settimeout(0.4)
        return probe_socket.connect_ex(("127.0.0.1", port)) == 0


def probe(port: int):
    """Which paper, if any, the thing already on this port is serving."""
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/_pa/hello", timeout=2
        ) as reply:
            return json.loads(reply.read().decode("utf-8")).get("paper") or ""
    except Exception:  # noqa: BLE001 - anything at all means "not one of ours"
        return ""


def main(argv) -> int:
    # --port takes a value: skip it, or "--port 9000 <work>" reads 9000 as work
    args = cli.positionals(argv, value_flags={"--port"})
    work = Path(args[0] if args else ".").resolve()
    config, paper_root, notes_dir, annotated = workspace.load_workspace(work)
    if not (annotated / "index.html").is_file():
        raise SystemExit(f"找不到 {annotated / 'index.html'}，請先執行 build_html.py")

    port = int(cli.flag(argv, "port", "8975"))
    if "--launcher" in argv:
        print(f"啟動器       {write_launcher(work, annotated, port)}")
        print("             點兩下就會起 server 並開複習頁")
        return 0

    Handler.token = secrets.token_urlsafe(24)
    Handler.work, Handler.paper_root, Handler.notes = work, paper_root, notes_dir
    Handler.sources = {Path(p).as_posix() for p in (config.get("sources") or [])}

    # The review page points at images that live in the package next door, so
    # serving annotated/ alone gives a page with every figure missing. Root at
    # the folder holding both and let the links resolve exactly as they do on
    # disk; "/" redirects to wherever the page actually sits. The stdlib
    # handler still refuses to walk above whatever root it is given.
    root = Path(os.path.commonpath([str(annotated), str(paper_root)]))
    # percent-encoded: http.server writes headers in latin-1, so a Chinese
    # directory name in the redirect target would crash the "/" handler
    Handler.index_url = "/" + quote((annotated / "index.html").relative_to(root).as_posix())

    url = f"http://127.0.0.1:{port}/"
    # Double-clicking the launcher twice is the common case, and "address
    # already in use" tells the reader nothing. Ask whoever holds the port who
    # they are before deciding what to say.
    if taken(port):
        holder = probe(port)
        if holder == work.name:
            print(f"複習頁       {url}")
            print("             這篇已經在跑了，直接用這條網址就好")
            if "--no-open" not in argv:
                webbrowser.open(url)
            return 0
        if holder:
            raise SystemExit(
                f"port {port} 正在服務另一篇論文（{holder}）。\n"
                f"請換一個，例如 --port {port + 1}"
            )
        raise SystemExit(f"port {port} 被其他程式佔用了，請換一個，例如 --port {port + 1}")

    server = ThreadingHTTPServer(
        ("127.0.0.1", port), partial(Handler, directory=str(root))
    )
    print(f"複習頁       {url}")
    print(f"             畫記會直接寫進 {notes_dir / 'marks'}，並重建複習頁")
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
