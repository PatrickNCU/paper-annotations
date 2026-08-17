"""Shared entry-point plumbing: interpreter guard and argv parsing.

Every command reads "--flag value / --flag=value" plus positionals. Parsing
lives here once because each script used to hand-roll the loop, and two of
them read a flag's value as the work directory when the flag came first.
"""

from __future__ import annotations

import sys

MIN_PYTHON = (3, 8)


def bootstrap() -> None:
    """Guard the interpreter version and make the console printable.

    Windows consoles default to a legacy codepage that cannot print emoji;
    without the reconfigure, one warning symbol crashes the run with
    UnicodeEncodeError -- on exactly the code path that reports problems.
    """
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(
            f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 以上，"
            f"目前是 {sys.version.split()[0]}"
        )
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def flag(argv, name, fallback=None):
    """--name <value> or --name=<value>; fallback when absent."""
    prefix = f"--{name}="
    for arg in argv:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    if f"--{name}" in argv:
        idx = argv.index(f"--{name}")
        if idx + 1 < len(argv) and not argv[idx + 1].startswith("--"):
            return argv[idx + 1]
    return fallback


def positionals(argv, value_flags=()):
    """argv[1:] minus flags, and minus the values of the given value flags.

    value_flags lists the flags that consume the next token ("--port", "--from"
    ...), so "--port 9000 <work>" never reads 9000 as the work directory.
    """
    out = []
    skip = False
    for arg in argv[1:]:
        if skip:
            skip = False
            continue
        if arg.startswith("--"):
            skip = "=" not in arg and arg in value_flags
            continue
        out.append(arg)
    return out
