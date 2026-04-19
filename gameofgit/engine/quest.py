from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a quest predicate. `detail` is an optional human-readable
    explanation the UI can surface when the player explicitly asks 'am I done yet?'."""

    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class SessionState:
    """Snapshot of what the player has executed so far in the current quest.

    `last_argv` is the most recent successful (exit 0) command; `all_argv` is
    the full ordered history of successful commands. Checks that need to verify
    'did the player run X?' inspect these — repo state alone can't tell us that.
    """

    last_argv: tuple[str, ...] | None
    all_argv: list[tuple[str, ...]] = field(default_factory=list)


@dataclass(frozen=True)
class Quest:
    """A single quest: data plus a predicate and optional seed."""

    slug: str
    title: str
    brief: str
    hints: tuple[str, ...]
    allowed: frozenset[str]
    check: Callable[[Path, SessionState], CheckResult]
    xp: int
    level: int
    seed: Callable[[Path], None] | None = None
