"""JSON-per-player persistence. No DB, no accounts, no auth.

Profiles live in `$GAMEOFGIT_PROFILES_DIR` if set, else `~/.gameofgit/players/`.
Writes are atomic (tmp + rename). Reads tolerate corruption by treating it as
a fresh profile (see the brainstorm spec: torn writes shouldn't crash the game).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from gameofgit.player.model import Player


class InvalidName(ValueError):
    """Raised when a player name can't be turned into a valid slug."""


_SLUG_RE = re.compile(r"[^a-z0-9_]+")

# Stroked / ligature letters that NFKD won't decompose.
# Keep this list in sync with the JS `FOLD_MAP` in web/static/index.html.
_FOLD_MAP = str.maketrans({
    "ł": "l", "Ł": "l",
    "đ": "d", "Đ": "d",
    "ø": "o", "Ø": "o",
    "æ": "ae", "Æ": "ae",
    "œ": "oe", "Œ": "oe",
    "ß": "ss",
})


def _fold_to_ascii(text: str) -> str:
    """Map common non-ASCII Latin letters to their ASCII equivalents."""
    # NFKD decomposes "ó" -> "o" + combining acute; we then drop the marks.
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.translate(_FOLD_MAP)


def slugify(name: str) -> str:
    """Normalize a human-entered name to a filesystem-safe slug.

    Two names that normalize to the same slug share a profile. This is a
    feature for a LAN-local training tool; don't try to "fix" it.
    """
    folded = _fold_to_ascii(name.strip()).lower()
    slug = _SLUG_RE.sub("_", folded).strip("_")
    if not slug:
        raise InvalidName(
            "That name can't be written in the book — try another."
        )
    return slug


def _profiles_dir() -> Path:
    override = os.environ.get("GAMEOFGIT_PROFILES_DIR")
    if override:
        p = Path(override)
    else:
        p = Path.home() / ".gameofgit" / "players"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _path_for(slug: str) -> Path:
    return _profiles_dir() / f"{slug}.json"


def _recompute_xp(completed: set[str]) -> int:
    from gameofgit.quests import all_quests
    by_slug = {q.slug: q.xp for q in all_quests()}
    return sum(by_slug.get(s, 0) for s in completed)


def load_or_create(name: str) -> Player:
    """Load the profile for `name`, or create a fresh one if none exists.

    On corrupt JSON, returns a fresh profile (logs are the caller's concern).
    `xp` is always recomputed from `completed_quests` against the live catalog.
    """
    slug = slugify(name)
    path = _path_for(slug)
    if not path.exists():
        return Player(name=name.strip(), slug=slug, xp=0, completed_quests=set())
    try:
        data = json.loads(path.read_text())
        completed = set(data.get("completed_quests", []))
        return Player(
            name=data.get("name", name.strip()),
            slug=slug,
            xp=_recompute_xp(completed),
            completed_quests=completed,
        )
    except (json.JSONDecodeError, OSError):
        return Player(name=name.strip(), slug=slug, xp=0, completed_quests=set())


def save(player: Player) -> None:
    """Atomically persist `player` to disk."""
    path = _path_for(player.slug)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "name": player.name,
        "slug": player.slug,
        "completed_quests": sorted(player.completed_quests),
        "xp": player.xp,
        "updated_at": now,
    }
    # Preserve created_at if present; set it on first write.
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            payload["created_at"] = existing.get("created_at", now)
        except (json.JSONDecodeError, OSError):
            payload["created_at"] = now
    else:
        payload["created_at"] = now

    # Atomic write
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
