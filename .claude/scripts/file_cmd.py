#!/usr/bin/env python3
"""file_cmd — workhorse behind the /file slash command.

Usage:
    file_cmd add    <path> [content...]
    file_cmd edit   <path> [note...]
    file_cmd delete <path>

Exit codes:
    0 success
    1 operation-level error (file missing, already exists, ...)
    2 usage error (bad verb, missing arg)
"""

from __future__ import annotations

import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

_RULE = "━" * 59

_BASENAME_LEADERS = {"Dockerfile": "#", "Makefile": "#"}

_LINE_LEADERS: dict[str, str] = {}
for _ext in (".py", ".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".ini", ".conf"):
    _LINE_LEADERS[_ext] = "#"
for _ext in (
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".c", ".h", ".cpp", ".hpp", ".java", ".go",
    ".rs", ".swift", ".kt", ".scala", ".css", ".scss",
):
    _LINE_LEADERS[_ext] = "//"
_LINE_LEADERS[".sql"] = "--"
for _ext in (".lisp", ".clj", ".el"):
    _LINE_LEADERS[_ext] = ";;"

_HTML_EXTS = frozenset({".html", ".xml", ".svg", ".vue", ".md"})


def _leader_for(path: Path) -> str | None:
    """Return a per-line comment leader, or None to signal HTML-block wrapping."""
    if path.name in _BASENAME_LEADERS:
        return _BASENAME_LEADERS[path.name]
    ext = path.suffix.lower()
    if ext in _HTML_EXTS:
        return None
    return _LINE_LEADERS.get(ext, "#")


def _stamp_lines(timestamp: str, note: str, ident: str) -> list[str]:
    return [
        _RULE,
        f"▶ /file edit  ·  {timestamp}",
        f"▶ note: {note}",
        f"▶ id:   {ident}",
        _RULE,
    ]


def _format_stamp(path: Path, timestamp: str, note: str, ident: str) -> str:
    lines = _stamp_lines(timestamp, note, ident)
    leader = _leader_for(path)
    if leader is None:
        return "<!--\n" + "\n".join(lines) + "\n-->\n"
    return "\n".join(f"{leader} {line}" for line in lines) + "\n"


def _new_id() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(50))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_add(path: Path, content: str) -> int:
    if path.exists():
        print(f"error: {path} already exists", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    if content and not content.endswith("\n"):
        content += "\n"
    path.write_text(content)
    print(f"added {path}")
    return 0


def cmd_edit(path: Path, note: str) -> int:
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 1
    if path.is_dir():
        print(f"error: {path} is a directory", file=sys.stderr)
        return 1
    existing = path.read_text()
    if existing and not existing.endswith("\n"):
        existing += "\n"
    timestamp = _utc_now_iso()
    ident = _new_id()
    stamp = _format_stamp(path, timestamp, note or "no note", ident)
    path.write_text(existing + stamp)
    print(f"stamped {path} with id {ident[:8]}…")
    return 0


def cmd_delete(path: Path) -> int:
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 1
    if path.is_dir():
        print(f"error: {path} is a directory — refusing to delete", file=sys.stderr)
        return 1
    path.unlink()
    print(f"deleted {path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__ or "", file=sys.stderr)
        return 2
    verb = argv[1]
    if verb not in {"add", "edit", "delete"}:
        print(f"unknown verb: {verb} (use add/edit/delete)", file=sys.stderr)
        return 2
    if len(argv) < 3:
        print(f"{verb} requires a <path>", file=sys.stderr)
        return 2
    path = Path(argv[2]).expanduser().resolve()
    tail = " ".join(argv[3:])
    if verb == "add":
        return cmd_add(path, tail)
    if verb == "edit":
        return cmd_edit(path, tail)
    return cmd_delete(path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
