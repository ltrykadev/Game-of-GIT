from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a quest predicate. `detail` is an optional human-readable
    explanation the UI can surface when the player explicitly asks 'am I done yet?'."""

    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class Quest:
    """A single quest: data plus a predicate and optional seed."""

    slug: str
    title: str
    brief: str
    hints: tuple[str, ...]
    allowed: frozenset[str]
    check: Callable[[Path], CheckResult]
    seed: Callable[[Path], None] | None = None
