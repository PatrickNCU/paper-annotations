"""Serve the review page locally so its 儲存 button can actually save.

A page opened from disk cannot write a file or start a program -- that is the
browser's security model, not a gap in this tool. This is the smallest thing
that closes it: a local HTTP server that hands out the review page and accepts
its highlights back, writing them into notes/marks/ and rebuilding the page.

    python serve.py <work> [--port 8975] [--no-open]
    python serve.py <work> --launcher        # 只放一個點兩下就能開的啟動器
    python serve.py --library [<起點>]        # 登記簿裡的每一篇，加上書房頁

Without it everything still works; highlights simply stay in the browser until
they are copied out by hand, and grading is unavailable (docs/adr/0003).

Safety, in the order it matters:

  * Bound to 127.0.0.1 only. Never 0.0.0.0 -- that would let anyone on the
    same network write files onto this machine.
  * Each paper is mounted under /p/<slug>/ and resolved inside ITS OWN root.
    There is deliberately no shared root: commonpath over papers scattered
    across a disk collapses to the drive letter, which would put everything on
    the machine behind an HTTP server.
  * Writes are confined to notes/, and filenames are generated here. A request
    names a paper by slug, looked up in a table built at startup; nothing in a
    request is ever used as a path.
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
from urllib.parse import parse_qs, quote, unquote, urlparse

from datetime import date

from . import cli, library, marks as marklib, notes, srs, workspace

cli.bootstrap()

# The CLI wrappers in scripts/ are what launchers and the rebuild subprocess
# invoke -- pa/ is an implementation detail nothing outside may point at.
SCRIPTS = Path(__file__).resolve().parent.parent
MAX_BODY = 4 << 20  # a paper's worth of highlights is kilobytes; this is slack


class Handler(SimpleHTTPRequestHandler):
    token = ""
    # slug -> Paper. Every path and every write is resolved through this map,
    # which is built once at startup from the registry. A request names a paper
    # by slug and never by path -- see _paper().
    papers = {}
    default = ""
    shelf = None  # the one library.html file, served by name and never by folder
    registry = None  # papers.yml, only in --library mode
    lock = threading.Lock()

    # ---- routing ---------------------------------------------------------

    def _route(self, path: str):
        """Split "/p/<slug>/rest" into (slug, rest). (None, path) otherwise."""
        parts = path.split("/", 3)
        if len(parts) >= 3 and parts[1] == "p":
            slug = unquote(parts[2])
            if slug in self.papers:
                return slug, (parts[3] if len(parts) > 3 else "")
        return None, path

    def _paper(self, slug):
        """The paper a request is about, or None.

        A missing slug means the single-paper case, which is what every
        existing launcher produces. Anything else has to name a paper that was
        mounted at startup; an unknown name is refused rather than guessed.
        """
        slug = str(slug or "") or self.default
        return self.papers.get(slug)

    def translate_path(self, path: str) -> str:
        """Map a URL onto disk inside ONE paper's root.

        Never a shared root. The obvious implementation -- commonpath over
        every mounted paper -- collapses to C:\\ the moment two papers live on
        different branches of the disk, which would put the whole drive behind
        an HTTP server. Each paper is resolved against its own root instead, so
        the worst a traversal can reach is the paper it was already allowed to
        read.
        """
        slug, rest = self._route(path.split("?")[0].split("#")[0])
        paper = self._paper(slug)
        if paper is None:
            # Nothing is mounted here. A path no file can occupy, so send_head
            # answers 404 for GET and HEAD alike -- os.devnull would not: it
            # opens fine and would serve an empty 200.
            return os.path.join(os.path.dirname(__file__), "__no_such_paper__", "x")
        # Same filtering the stdlib applies: drop empties, "." and "..", and
        # anything carrying a path separator or a drive letter.
        parts = []
        for word in unquote(rest, errors="surrogatepass").split("/"):
            if not word or word in (".", ".."):
                continue
            _, word = os.path.splitdrive(word)
            _, word = os.path.split(word)
            if word in (".", ".."):
                continue
            parts.append(word)
        return str(paper["root"].joinpath(*parts))

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
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        want = (query.get("p") or [""])[0]

        if path == "/_pa/hello":
            if not self._same_origin():
                self._json(403, {"error": "cross-origin"})
                return
            # the papers are named so that a second run can tell "already
            # serving this one" from "something else has the port" -- see main()
            self._json(200, {
                "ok": True,
                "token": self.token,
                "paper": self.papers[self.default]["work"].name if self.default else "",
                "papers": sorted(self.papers),
            })
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", self.home_url)
            self.end_headers()
            return
        if path == "/_pa/reviews":
            if not self._same_origin():
                self._json(403, {"error": "cross-origin"})
                return
            paper = self._paper(want)
            if paper is None:
                self._json(404, {"error": f"沒有這篇論文：{want}"})
                return
            # Read-only, so no token: it says which of the reader's own cards
            # are due, which is no more than the page already shows.
            self._json(200, self._schedule(paper))
            return
        if path == "/_pa/library":
            if not self._same_origin():
                self._json(403, {"error": "cross-origin"})
                return
            self._json(200, self._library())
            return
        if path == "/_pa/shelf":
            # One named file, read and returned here. Mounting its folder as a
            # paper would put the whole workspace -- papers.yml, every package,
            # anything else sitting there -- behind the server, which is the
            # exact thing the per-paper roots exist to prevent.
            if self.shelf and self.shelf.is_file():
                body = self.shelf.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404, "no shelf page")
            return
        if path == "/favicon.ico":  # browsers always ask; there is not one
            self.send_response(204)
            self.end_headers()
            return
        slug, rest = self._route(path)
        if slug is not None and rest in ("", "/"):
            self.send_response(302)
            self.send_header("Location", self.papers[slug]["index_url"])
            self.end_headers()
            return
        if self._paper(slug) is None:
            # Serving several papers there is no default, so a bare path names
            # nothing. Say so rather than let it fall through to a file lookup.
            self.send_error(404, "no such paper")
            return
        super().do_GET()

    def _schedule(self, paper):
        return srs.schedule(
            paper["notes"], notes.load_cards(paper["notes"]), date.today().isoformat()
        )

    def _library(self):
        """Live counts for the library page, so it is never stale while served."""
        today = date.today().isoformat()
        out = []
        for slug, paper in sorted(self.papers.items()):
            cards = notes.load_cards(paper["notes"])
            tally = {"open": 0, "half": 0, "resolved": 0}
            for card in cards:
                key = str(card["meta"].get("status", "open"))
                tally[key] = tally.get(key, 0) + 1
            plan = srs.schedule(paper["notes"], cards, today)
            out.append({
                "slug": slug,
                "title": paper["title"],
                "url": paper["index_url"],
                "cards": len(cards),
                "points": len(notes.load_points(paper["notes"])),
                "open": tally["open"], "half": tally["half"], "resolved": tally["resolved"],
                "due": plan["due"], "tracked": plan["tracked"],
            })
        return {"today": today, "papers": out}

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/_pa/marks", "/_pa/mark", "/_pa/review", "/_pa/topic"):
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
        if path == "/_pa/topic":
            self._topic()
            return
        payload = self._body()
        if not isinstance(payload, dict) or not isinstance(payload.get("marks"), list):
            self._json(400, {"error": "bad payload"})
            return
        paper = self._paper(payload.get("paper"))
        if paper is None:
            self._json(404, {"error": f"沒有這篇論文：{payload.get('paper')}"})
            return

        clean = []
        for item in payload["marks"]:
            if not isinstance(item, dict):
                continue
            rec = {k: str(item.get(k) or "") for k in
                   ("file", "color", "exact", "prefix", "suffix", "note")}
            # a path from the network is never trusted; it only has to name one
            # of the sources this paper already declares
            if rec["exact"] and rec["file"] in paper["sources"]:
                clean.append(rec)
        if not clean:
            self._json(400, {"error": "沒有可用的畫記"})
            return

        with self.lock:  # one writer at a time: ids are handed out by scanning
            result = marklib.write_marks(paper["paper_root"], paper["notes"], clean)
            rebuilt, log = self._rebuild(paper) if result["written"] else (True, "")
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
        paper = self._paper(payload.get("paper"))
        if paper is None:
            self._json(404, {"error": f"沒有這篇論文：{payload.get('paper')}"})
            return
        wanted = str(payload.get("id") or "")
        action = str(payload.get("action") or "")
        if action == "clear":
            with self.lock:
                gone = 0
                for mark in notes.load_marks(paper["notes"]):
                    mark["path"].unlink()
                    gone += 1
                rebuilt, log = self._rebuild(paper)
            self._json(200, {"ok": True, "action": "clear", "deleted": gone,
                             "rebuilt": rebuilt, "log": log})
            return
        if action not in ("update", "delete") or not wanted:
            self._json(400, {"error": "bad action"})
            return

        with self.lock:
            found = None
            for mark in notes.load_marks(paper["notes"]):
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
            rebuilt, log = self._rebuild(paper)
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
        paper = self._paper(payload.get("paper"))
        if paper is None:
            self._json(404, {"error": f"沒有這篇論文：{payload.get('paper')}"})
            return
        wanted = str(payload.get("id") or "")
        grade = str(payload.get("grade") or "")
        if grade not in srs.GRADES:
            self._json(400, {"error": f"grade 只能是 {' / '.join(srs.GRADES)}"})
            return

        with self.lock:
            cards = notes.load_cards(paper["notes"])
            card = next(
                (c for c in cards if str(c["meta"].get("id")) == wanted), None
            )
            if card is None:
                self._json(404, {"error": f"找不到卡片 {wanted}"})
                return
            if not srs.eligible(card["meta"]):
                self._json(400, {"error": f"Q{wanted} 不在排程裡（只有你自己問過、且已解決的卡才排程）"})
                return
            srs.append(paper["notes"], wanted, grade, date.today().isoformat())
            state = self._schedule(paper)
        self._json(200, {"ok": True, "id": wanted, "grade": grade, "schedule": state})

    def _topic(self):
        """Put one paper into a topic, or take it out of one.

        Both the paper and the topic are names checked against things that
        already exist -- the registry's papers and its declared vocabulary --
        so neither can turn into a path or invent a category. Rebuilds the
        shelf afterwards, unlike grading: this one does change the page.
        """
        if self.registry is None:
            self._json(400, {"error": "這個 server 不是用 --library 起的，沒有登記簿"})
            return
        payload = self._body()
        if not isinstance(payload, dict):
            self._json(400, {"error": "bad payload"})
            return
        paper = self._paper(payload.get("paper"))
        if paper is None:
            self._json(404, {"error": f"沒有這篇論文：{payload.get('paper')}"})
            return
        action = str(payload.get("action") or "")
        if action not in ("add", "remove"):
            self._json(400, {"error": "action 只能是 add 或 remove"})
            return

        with self.lock:
            ok, why = library.set_topic(
                self.registry, paper["slug"], str(payload.get("topic") or ""),
                action == "add",
            )
            if not ok:
                self._json(400, {"error": why})
                return
            rebuilt, log = self._rebuild_shelf()
        self._json(200, {"ok": True, "note": why, "rebuilt": rebuilt, "log": log})

    def _rebuild_shelf(self):
        run = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_library.py"), str(self.registry.parent)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = (run.stdout or "") + (run.stderr or "")
        sys.stderr.write(out)
        return run.returncode == 0, out.strip().splitlines()[:6]

    def _rebuild(self, paper):
        """Only the HTML: marks never touch the annotated Markdown."""
        # encoding spelled out: text=True decodes with the console codepage,
        # which on a zh-TW Windows is cp950 and cannot read the build's UTF-8
        # output at all -- the reader thread died and took the log with it.
        run = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_html.py"), str(paper["work"])],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = (run.stdout or "") + (run.stderr or "")
        sys.stderr.write(out)
        return run.returncode == 0, out.strip().splitlines()[:6]


def _launcher(home: Path, stem: str, tag: str, target: str, port: int) -> Path:
    """Write a double-clickable launcher that runs serve.py with `target`.

    The body is ASCII only, deliberately: cmd.exe parses a .cmd in the OEM
    codepage, so UTF-8 text inside breaks the script itself rather than merely
    printing badly. The filename is free to be Chinese -- that goes through the
    filesystem, not the parser.
    """
    script = str(SCRIPTS / "serve.py")
    # Installed as a plugin, this file sits under .../<plugin>/<version>/…, and
    # that version directory changes every time the plugin is updated -- a
    # launcher naming it would break on the next release. Look the newest one
    # up at run time instead, and keep today's path only as the fallback.
    versioned = ""
    if re.fullmatch(r"\d+(\.\d+)*", SCRIPTS.parents[2].name):
        versioned = str(SCRIPTS.parents[3])

    if os.name == "nt":
        path = home / f"{stem}.cmd"
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
            f"title {tag}\n"
            "echo Close this window to stop the server.\n"
            "echo.\n"
            + find
            + f'python "{run}" {target} --port {port}\n'
            "echo.\n"
            "echo Server stopped.\n"
            "pause\n"
        )
    else:
        path = home / f"{stem}.command"
        body = (
            "#!/bin/sh\n"
            "# Close this window to stop the server.\n"
            'cd "$(dirname "$0")" || exit 1\n'
            + (
                f'PA="$(ls -d "{versioned}"/*/skills/paper-annotations/scripts/serve.py'
                ' 2>/dev/null | sort -V | tail -1)"\n'
                f'[ -f "$PA" ] || PA="{script}"\n'
                f'exec python3 "$PA" {target} --port {port}\n'
                if versioned
                else f'exec python3 "{script}" {target} --port {port}\n'
            )
        )
    path.write_text(body, encoding="ascii", newline="\r\n" if os.name == "nt" else "\n")
    if os.name != "nt":
        path.chmod(0o755)
    return path


def write_launcher(work: Path, annotated: Path, port: int) -> Path:
    """One paper's launcher, beside its review page."""
    home = annotated.parent
    try:
        target = work.relative_to(home).as_posix().replace("/", os.sep)
    except ValueError:
        target = str(work)
    tag = "".join(c for c in work.name if c.isascii() and (c.isalnum() or c in "-_")) or "paper"
    return _launcher(home, "開啟複習頁", f"{tag} review page", f'"{target}"', port)


def write_library_launcher(registry: Path, port: int) -> Path:
    """The shelf's launcher, beside papers.yml.

    No path argument at all: --library finds the registry by walking up from
    the working directory, and the launcher has already cd'd to the folder it
    sits in. So this file keeps working if the whole workspace is moved or
    cloned onto another machine -- which is the point of the registry living in
    the repository in the first place.
    """
    return _launcher(registry.parent, "開啟書房", "paper library", "--library", port)


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


def mount(work: Path, slug: str):
    """Everything the handler needs to serve one paper, resolved once.

    The root is per paper and is the folder holding both the review page and
    the package it points at -- the page's images live next door, so serving
    annotated/ alone gives a page with every figure missing.
    """
    config, paper_root, notes_dir, annotated = workspace.load_workspace(work)
    if not (annotated / "index.html").is_file():
        raise SystemExit(f"找不到 {annotated / 'index.html'}，請先執行 build_html.py")
    root = Path(os.path.commonpath([str(annotated), str(paper_root)]))
    inside = (annotated / "index.html").relative_to(root).as_posix()
    # percent-encoded: http.server writes headers in latin-1, so a Chinese
    # directory name in the redirect target would crash the redirect handlers
    return {
        "slug": slug,
        "work": work,
        "paper_root": paper_root,
        "notes": notes_dir,
        "annotated": annotated,
        "root": root,
        "title": library.paper_title(paper_root)[0],
        "sources": {Path(p).as_posix() for p in (config.get("sources") or [])},
        "index_url": f"/p/{quote(slug)}/{quote(inside)}",
    }


def collect(argv, args):
    """Which papers this run serves, and which is the default.

    Two modes, and the single-paper one is unchanged on purpose: every launcher
    already written points at `serve.py <work>`, and those must keep working
    exactly as they did.
    """
    if "--library" in argv:
        start = Path(args[0]).resolve() if args else Path(".").resolve()
        registry = library.find_registry(start)
        if registry is None:
            raise SystemExit(
                f"從 {start} 往上找不到 papers.yml。\n"
                "對任何一篇論文執行 probe.py 就會建立一份，或改用 serve.py <論文路徑>。"
            )
        papers, skipped = {}, []
        for entry in library.entries(registry):
            if not entry["alive"]:
                skipped.append((entry["slug"], "登記的位置找不到筆記"))
                continue
            try:
                papers[entry["slug"]] = mount(entry["work"], entry["slug"])
            except SystemExit as why:
                skipped.append((entry["slug"], str(why)))
        if not papers:
            raise SystemExit("登記簿裡沒有任何一篇是可以服務的（都還沒 build？）")
        return papers, "", registry, skipped

    work = Path(args[0] if args else ".").resolve()
    slug = library.paper_name(work)
    return {slug: mount(work, slug)}, slug, None, []


def main(argv) -> int:
    # --port takes a value: skip it, or "--port 9000 <work>" reads 9000 as work
    args = cli.positionals(argv, value_flags={"--port"})
    port = int(cli.flag(argv, "port", "8975"))

    if "--launcher" in argv:
        if "--library" in argv:
            start = Path(args[0]).resolve() if args else Path(".").resolve()
            registry = library.find_registry(start)
            if registry is None:
                raise SystemExit(
                    f"從 {start} 往上找不到 {library.REGISTRY_NAME}，還沒有任何論文登記。"
                )
            print(f"啟動器       {write_library_launcher(registry, port)}")
            print("             點兩下就會起 server 並開書房頁")
            return 0
        work = Path(args[0] if args else ".").resolve()
        _, _, _, annotated = workspace.load_workspace(work)
        print(f"啟動器       {write_launcher(work, annotated, port)}")
        print("             點兩下就會起 server 並開複習頁")
        return 0

    papers, default, registry, skipped = collect(argv, args)
    Handler.token = secrets.token_urlsafe(24)
    Handler.papers = papers
    Handler.default = default
    # One paper goes straight to its page; a shelf full of them lands on the
    # shelf. Either way "/" is somewhere useful rather than a directory listing.
    Handler.home_url = papers[default]["index_url"] if default else "/_pa/shelf"
    if not default:
        shelf = registry.parent / "library.html"
        if not shelf.is_file():
            raise SystemExit(
                f"找不到書房頁 {shelf}，請先執行：\n"
                f"    python <scripts>/build_library.py"
            )
        Handler.shelf = shelf
        Handler.registry = registry

    url = f"http://127.0.0.1:{port}/"
    # Double-clicking the launcher twice is the common case, and "address
    # already in use" tells the reader nothing. Ask whoever holds the port who
    # they are before deciding what to say.
    if taken(port):
        holder = probe(port)
        if default and holder == papers[default]["work"].name:
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

    # No shared directory= is passed: translate_path resolves every request
    # inside the one paper it names, and never against a root spanning them.
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if default:
        paper = papers[default]
        print(f"複習頁       {url}")
        print(f"             畫記會直接寫進 {paper['notes'] / 'marks'}，並重建複習頁")
        print(f"             檔案根目錄 {paper['root']}（只有本機連得到）")
    else:
        real = [s for s in papers if s != "_shelf"]
        print(f"書房         {url}")
        print(f"             {len(real)} 篇論文，各自只開放自己的資料夾")
        for slug in sorted(real):
            print(f"               {slug:<16} {papers[slug]['root']}")
        for slug, why in skipped:
            print(f"             🟡 略過 {slug}：{why}")
    print("             評分與畫記存檔都需要這個視窗開著")
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
