"""Reminders: what is due today, said where the reader will see it.

Three outlets, each the most it can honestly do (docs/adr/0007):

- `--due`: today's numbers across every registered paper, without a server.
  Everything else here is built on this one line.
- The desktop: a scheduled task runs a small PowerShell notifier, which asks
  `--due` and, only when something is actually due, puts a balloon and a tray
  icon up. Clicking either opens the shelf. Nothing is pushed in front of the
  reader and nothing appears on a day with nothing to do -- a reminder that
  fires every day regardless is a reminder that gets dismissed unread.
- The phone: a calendar file with one daily event. It cannot know the count;
  it says so, and links to the shelf. Real push would need VAPID's ES256
  signatures and payload encryption, neither of which the standard library
  has, and this tool installs nothing.

Windows only for the desktop part. The scheduled task belongs to the reader's
account and runs only while he is logged in, because a balloon nobody is
there to see is not a reminder.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from . import cli, icon, library, srs

SCRIPTS = Path(__file__).resolve().parent.parent
TASK_NAME = "paper-annotations 複習提醒"
NOTIFIER = "複習提醒.ps1"
CALENDAR = "複習提醒.ics"
# How long the tray icon stays after the balloon: long enough to still be
# there when he comes back to the desk, short enough not to become furniture.
LINGER_MINUTES = 30


def summary(registry: Path, today: str | None = None) -> dict:
    """The part of today_across a reminder needs: counts, never the queue."""
    plan = srs.today_across(registry, today)
    return {
        "today": plan["today"],
        "due": plan["due"],
        "half": plan["half"],
        "next": plan["next"],
        "tomorrow": plan["tomorrow"],
        "papers": [
            {"slug": p["slug"], "title": p["title"], "due": p["due"], "half": p["half"]}
            for p in plan["papers"]
        ],
    }


def sentence(s: dict) -> str:
    """One line a person reads: what is due, from where, and what else waits."""
    if not s["due"]:
        bits = ["今天沒有到期的卡"]
        if s["half"]:
            bits.append(f"半懂 {s['half']} 張還在等你寫自己的話")
        if s["next"]:
            bits.append(f"下一張 {s['next'][5:]}")
        return "，".join(bits) + "。"
    where = "、".join(
        f"{p['slug']} {p['due']} 張" for p in s["papers"] if p["due"]
    )
    tail = f"另有半懂 {s['half']} 張。" if s["half"] else ""
    return f"今天到期 {s['due']} 張：{where}。{tail}"


# ---- the desktop notifier --------------------------------------------------

def _versions_root() -> str:
    """The plugin cache folder holding one folder per version, or "".

    Same reason as the launchers: the notifier outlives the version that wrote
    it, so it looks up the highest installed version every time it runs.
    """
    if re.fullmatch(r"\d+(\.\d+)*", SCRIPTS.parents[2].name):
        return str(SCRIPTS.parents[3])
    return ""


def notifier_script(home: Path, port: int) -> str:
    """The PowerShell the scheduled task runs. Plain text, readable, editable."""
    serve = str(SCRIPTS / "remind.py")
    root = _versions_root()
    launcher = home / "開啟書房.cmd"
    picture = base64.b64encode(icon.icon_png(64)).decode("ascii")

    def q(text: str) -> str:  # a PowerShell single-quoted literal
        return "'" + str(text).replace("'", "''") + "'"

    return f"""# 複習提醒：由 paper-annotations 產生（python remind.py --install）。
# 工作排程器每天跑這一支；今天沒有到期的卡就什麼都不做。
# 要停掉：python remind.py --uninstall

$ErrorActionPreference = 'Stop'
$home_ = {q(home)}
$root = {q(root)}
$fallback = {q(serve)}
$launcher = {q(launcher)}
$port = {port}

# The highest installed version, compared as a version.
$script = $fallback
if ($root -and (Test-Path -LiteralPath $root)) {{
  $best = Get-ChildItem -Directory -LiteralPath $root |
    Where-Object {{ $_.Name -match '^\\d+(\\.\\d+)+$' -and
      (Test-Path (Join-Path $_.FullName 'skills\\paper-annotations\\scripts\\remind.py')) }} |
    Sort-Object {{ [version]$_.Name }} -Descending | Select-Object -First 1
  if ($best) {{ $script = Join-Path $best.FullName 'skills\\paper-annotations\\scripts\\remind.py' }}
}}

$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$raw = & python $script --due --json $home_ 2>$null | Out-String
if (-not $raw) {{ exit 0 }}
$d = $raw | ConvertFrom-Json
if ($d.due -lt 1) {{ exit 0 }}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Open the shelf. If a server already answers on the port -- even with 403,
# which the phone mode gives without a cookie -- the browser goes straight
# there; otherwise the launcher starts one and opens the page itself.
function Open-Shelf {{
  $up = $false
  try {{
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$port/_pa/hello" | Out-Null
    $up = $true
  }} catch {{
    if ($_.Exception.Response) {{ $up = $true }}
  }}
  if ($up) {{ Start-Process "http://127.0.0.1:$port/_pa/shelf" }}
  elseif (Test-Path -LiteralPath $launcher) {{ Start-Process -FilePath $launcher -WorkingDirectory $home_ }}
}}

$bytes = [Convert]::FromBase64String('{picture}')
$bitmap = New-Object System.Drawing.Bitmap (New-Object System.IO.MemoryStream (,$bytes))
$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
$title = "今天要複習 $($d.due) 張"
$tray.Text = $title
$tray.BalloonTipTitle = $title
$tray.BalloonTipText = $d.line + '點這裡開書房。'
$tray.Visible = $true

$done = {{ $tray.Visible = $false; [System.Windows.Forms.Application]::Exit() }}
$tray.add_BalloonTipClicked({{ Open-Shelf; & $done }})
$tray.add_MouseClick({{ Open-Shelf; & $done }})
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = {LINGER_MINUTES} * 60 * 1000
$timer.add_Tick({{ & $done }})

$tray.ShowBalloonTip(15000)
$timer.Start()
[System.Windows.Forms.Application]::Run()
$tray.Dispose()
"""


def write_notifier(home: Path, port: int) -> Path:
    path = home / NOTIFIER
    # With a BOM, or Windows PowerShell 5.1 reads the file in the ANSI
    # codepage and every Chinese string in the balloon comes out garbled.
    path.write_text(notifier_script(home, port), encoding="utf-8-sig", newline="\r\n")
    return path


def _powershell(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def install(home: Path, at: str, port: int) -> Path:
    """Write the notifier and register the daily task for the current user."""
    if os.name != "nt":
        raise SystemExit("桌面提醒目前只做了 Windows（工作排程器＋工作列氣泡）。")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", at):
        raise SystemExit(f"--at 要是 HH:MM，例如 09:00：{at}")
    script = write_notifier(home, port)
    # StartWhenAvailable: the computer was off at the hour, so it runs at the
    # next chance instead of skipping the day. Interactive logon only, so the
    # balloon lands on a desktop someone is looking at.
    command = (
        "$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "
        f"('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"{script}\"'); "
        f"$t = New-ScheduledTaskTrigger -Daily -At '{at}'; "
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 40) -MultipleInstances IgnoreNew; "
        "$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive; "
        f"Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $a -Trigger $t "
        "-Settings $s -Principal $p -Force | Out-Null"
    )
    done = _powershell(command)
    if done.returncode:
        raise SystemExit(f"工作排程器沒有接受：\n{done.stderr.strip()}")
    return script


def uninstall() -> bool:
    if os.name != "nt":
        return False
    done = _powershell(
        f"if (Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue) "
        f"{{ Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false; 'removed' }}"
    )
    return "removed" in done.stdout


def installed() -> str:
    """When the task fires, or "" if it is not registered."""
    if os.name != "nt":
        return ""
    done = _powershell(
        f"$t = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
        "if ($t) { ([datetime]$t.Triggers[0].StartBoundary).ToString('HH:mm') }"
    )
    return done.stdout.strip()


# ---- the phone: a calendar file --------------------------------------------

def _fold(line: str) -> str:
    """RFC 5545 folding: lines over 75 octets continue with a leading space.
    Counted in UTF-8 bytes, never splitting a character."""
    out, current = [], b""
    for ch in line:
        piece = ch.encode("utf-8")
        if len(current) + len(piece) > 75:
            out.append(current.decode("utf-8"))
            current = b" " + piece
        else:
            current += piece
    out.append(current.decode("utf-8"))
    return "\r\n".join(out)


def _escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def calendar(home: Path, at: str, url: str = "") -> str:
    """One event, every day at `at`, with an alarm at its start.

    Floating local time (no time zone): the event follows the phone wherever
    it is, which is what "every morning at nine" means. The UID is derived
    from the shelf's folder so importing a regenerated file updates the event
    instead of adding a second one. The URL never carries the key: a calendar
    syncs to someone's cloud, and the installed app already has its cookie.
    """
    hh, mm = at.split(":")
    uid = hashlib.sha1(str(home.resolve()).encode("utf-8")).hexdigest()[:16]
    note = ("書房開起來就知道今天有幾張。數字只有電腦算得出來，"
            "這個行事曆事件不知道，所以每天都會響。電腦要開著。")
    if url:
        note += f"\n{url}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//paper-annotations//remind//ZH",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}@paper-annotations",
        f"DTSTAMP:{date.today().strftime('%Y%m%d')}T000000Z",
        f"DTSTART:{date.today().strftime('%Y%m%d')}T{hh}{mm}00",
        "DURATION:PT10M",
        "RRULE:FREQ=DAILY",
        "SUMMARY:" + _escape("複習論文卡片"),
        "DESCRIPTION:" + _escape(note),
    ]
    if url:
        lines.append(f"URL:{url}")
    lines += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:" + _escape("複習論文卡片"),
        "TRIGGER:PT0M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def write_calendar(home: Path, at: str, url: str = "") -> Path:
    path = home / CALENDAR
    path.write_bytes(calendar(home, at, url).encode("utf-8"))
    return path


# ---- command line ----------------------------------------------------------

USAGE = """用法：
  python remind.py --due [--json] [書房資料夾]       今天到期多少，不必開 server
  python remind.py --install [--at 09:00] [書房資料夾] 每天這個時間檢查，有到期才跳氣泡
  python remind.py --uninstall                        拿掉排程
  python remind.py --status                           排程在不在、幾點
  python remind.py --ics [--at 09:00] [--url https://…] [書房資料夾]
                                                      給手機行事曆的每日提醒"""


def _registry(args) -> Path:
    start = Path(args[0]).resolve() if args else Path(".").resolve()
    registry = library.find_registry(start)
    if registry is None:
        raise SystemExit(f"從 {start} 往上找不到 {library.REGISTRY_NAME}。")
    return registry


def main(argv) -> int:
    cli.bootstrap()
    args = cli.positionals(argv, value_flags={"--at", "--url", "--port"})
    at = cli.flag(argv, "at", "09:00") or "09:00"
    port = int(cli.flag(argv, "port", "8975"))

    if "--due" in argv:
        s = summary(_registry(args))
        s["line"] = sentence(s)
        if "--json" in argv:
            print(json.dumps(s, ensure_ascii=False))
        else:
            print(s["line"])
        return 0
    if "--install" in argv:
        registry = _registry(args)
        script = install(registry.parent, at, port)
        print(f"提醒         每天 {at}，有到期的卡才會跳工作列氣泡；點它開書房")
        print(f"             {script}")
        print(f"             電腦在 {at} 沒開機的話，開機登入後補跑一次")
        print("             要拿掉：python remind.py --uninstall")
        return 0
    if "--uninstall" in argv:
        print("已拿掉排程。" if uninstall() else "本來就沒有排程。")
        return 0
    if "--status" in argv:
        when = installed()
        print(f"排程在，每天 {when}。" if when else "沒有排程。")
        return 0
    if "--ics" in argv:
        registry = _registry(args)
        url = (cli.flag(argv, "url", "") or "").rstrip("/")
        path = write_calendar(registry.parent, at, url)
        print(f"行事曆       {path}")
        print(f"             每天 {at} 響一次；傳到手機打開就會加進行事曆")
        print("             它不知道今天有幾張——數字只有電腦算得出來")
        return 0
    print(USAGE)
    return 0
