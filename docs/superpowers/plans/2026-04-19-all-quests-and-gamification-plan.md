# All Quests + Gamification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 29 new quests (Levels 2–10) and a gamification layer — named player profiles, XP per quest, and Junior/Senior/Expert tier progression.

**Architecture:** Keep Level 1's file-per-level pattern; add a new `gameofgit/player/` package for profile persistence; extend `Quest`/`QuestSession` so content quests can inspect "did the player run `git log`?" in checks. All state lives in `~/.gameofgit/players/<slug>.json`; no DB.

**Tech Stack:** Python 3.12, FastAPI, pytest, vanilla JS (no build step). Spec: `docs/superpowers/specs/2026-04-19-all-quests-and-gamification-design.md`.

---

## Phase 1 — Engine foundation

### Task 1: Add `xp` + `level` fields and `SessionState` to `Quest`

**Files:**
- Modify: `gameofgit/engine/quest.py`
- Test: `tests/test_quest.py`

- [ ] **Step 1: Write the failing tests**

Replace the contents of `tests/test_quest.py` with:

```python
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from gameofgit.engine.quest import CheckResult, Quest, SessionState


def _always_pass(_: Path, __: SessionState) -> CheckResult:
    return CheckResult(passed=True)


def test_check_result_defaults_to_no_detail():
    r = CheckResult(passed=True)
    assert r.passed is True
    assert r.detail is None


def test_check_result_with_detail():
    r = CheckResult(passed=False, detail="nope")
    assert r.detail == "nope"


def test_check_result_is_frozen():
    r = CheckResult(passed=True)
    with pytest.raises(FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def test_session_state_empty():
    s = SessionState(last_argv=None, all_argv=[])
    assert s.last_argv is None
    assert s.all_argv == []


def test_quest_is_frozen():
    q = Quest(
        slug="demo",
        title="Demo",
        brief="a demo",
        hints=("hint",),
        allowed=frozenset({"status"}),
        check=_always_pass,
        xp=100,
        level=1,
    )
    with pytest.raises(FrozenInstanceError):
        q.title = "Other"  # type: ignore[misc]


def test_quest_seed_defaults_to_none():
    q = Quest(
        slug="demo",
        title="Demo",
        brief="a demo",
        hints=(),
        allowed=frozenset(),
        check=_always_pass,
        xp=50,
        level=1,
    )
    assert q.seed is None


def test_quest_requires_xp_and_level():
    with pytest.raises(TypeError):
        Quest(  # type: ignore[call-arg]
            slug="no-xp",
            title="",
            brief="",
            hints=(),
            allowed=frozenset(),
            check=_always_pass,
        )


def test_quest_is_hashable_via_slug():
    q1 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass, xp=1, level=1)
    q2 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass, xp=1, level=1)
    assert q1 == q2
    assert hash(q1) == hash(q2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_quest.py -v`
Expected: FAIL — `SessionState` not importable, `Quest` doesn't accept `xp`/`level`.

- [ ] **Step 3: Update `Quest` dataclass**

Replace `gameofgit/engine/quest.py` with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_quest.py -v`
Expected: PASS (all 8 tests green).

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/quest.py tests/test_quest.py
git commit -m "engine: Quest gains xp/level fields + SessionState in check signature

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Track last-argv / all-argv in `QuestSession`

**Files:**
- Modify: `gameofgit/engine/session.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: Read the current session test to understand the style**

Run: `cat tests/test_session.py | head -60`

- [ ] **Step 2: Add failing tests**

Append to `tests/test_session.py`:

```python
def test_session_tracks_last_argv_on_success(tmp_path, monkeypatch):
    """Successful commands are recorded in SessionState passed to the check."""
    from pathlib import Path
    from gameofgit.engine.quest import CheckResult, Quest, SessionState
    from gameofgit.engine.session import QuestSession

    captured: list[SessionState] = []

    def check(_: Path, state: SessionState) -> CheckResult:
        captured.append(state)
        return CheckResult(passed=False)

    q = Quest(
        slug="t", title="", brief="", hints=(),
        allowed=frozenset({"init", "status"}),
        check=check, xp=1, level=1, seed=None,
    )
    s = QuestSession(q)
    try:
        s.run("git init")
        s.run("git status")
    finally:
        s.close()

    # First capture is the initial post-seed check (no commands run yet)
    assert captured[0].last_argv is None
    assert captured[0].all_argv == []
    # After git init
    assert captured[1].last_argv == ("git", "init")
    # After git status — all_argv has both
    assert captured[-1].last_argv == ("git", "status")
    assert captured[-1].all_argv == [("git", "init"), ("git", "status")]


def test_session_does_not_record_failed_commands(tmp_path):
    """Commands that exit non-zero are not added to all_argv."""
    from pathlib import Path
    from gameofgit.engine.quest import CheckResult, Quest, SessionState
    from gameofgit.engine.session import QuestSession

    captured: list[SessionState] = []

    def check(_: Path, state: SessionState) -> CheckResult:
        captured.append(state)
        return CheckResult(passed=False)

    q = Quest(
        slug="t", title="", brief="", hints=(),
        allowed=frozenset({"status", "log"}),
        check=check, xp=1, level=1, seed=None,
    )
    s = QuestSession(q)
    try:
        # git log in an empty (non-initialized) dir fails
        s.run("git log")
    finally:
        s.close()

    # Only the initial pre-command capture exists; the failed log was not added
    assert all(c.all_argv == [] for c in captured)
```

Also update every **existing** test in `tests/test_session.py` that constructs a `Quest` — each needs `xp=1, level=1` added, and any inline `check` closures need to accept a second `SessionState` argument. Read the current file and adjust all `Quest(...)` call sites accordingly.

- [ ] **Step 3: Run tests to verify the new ones fail**

Run: `pytest tests/test_session.py -v`
Expected: the new `test_session_tracks_last_argv_on_success` and `test_session_does_not_record_failed_commands` FAIL (no `last_argv` tracking yet); previously existing tests should already be green if you adjusted `Quest(...)` sites for xp/level.

- [ ] **Step 4: Update `QuestSession` to track argv**

Replace `gameofgit/engine/session.py` with:

```python
import shlex
from dataclasses import dataclass
from pathlib import Path

from .executor import execute
from .parser import (
    EmptyCommand,
    EngineError,
    parse,
)
from .quest import CheckResult, Quest, SessionState
from .sandbox import Sandbox


@dataclass(frozen=True)
class Outcome:
    stdout: str
    stderr: str
    exit_code: int
    check: CheckResult


class QuestSession:
    """One session per quest. Owns a sandbox; the UI talks only to this class."""

    def __init__(self, quest: Quest) -> None:
        self._quest = quest
        self._sandbox = Sandbox()
        self._last_argv: tuple[str, ...] | None = None
        self._all_argv: list[tuple[str, ...]] = []
        try:
            if quest.seed is not None:
                quest.seed(self._sandbox.path)
            self._last_check: CheckResult = self._run_check()
        except Exception:
            self._sandbox.close()
            raise

    def _state(self) -> SessionState:
        return SessionState(last_argv=self._last_argv, all_argv=list(self._all_argv))

    def _run_check(self) -> CheckResult:
        return self._quest.check(self._sandbox.path, self._state())

    def run(self, cmdline: str) -> Outcome:
        try:
            argv = parse(cmdline, self._quest.allowed)
        except EmptyCommand:
            return Outcome("", "", 0, self._last_check)
        except EngineError as e:
            return Outcome(
                stdout="",
                stderr=str(e),
                exit_code=127,
                check=self._last_check,
            )

        result = execute(argv, cwd=self._sandbox.path)
        # Only record successful runs — failed commands don't count as "done this".
        if result.exit_code == 0:
            recorded = tuple(argv)
            self._last_argv = recorded
            self._all_argv.append(recorded)
        self._last_check = self._run_check()
        return Outcome(result.stdout, result.stderr, result.exit_code, self._last_check)

    def close(self) -> None:
        self._sandbox.close()

    def __enter__(self) -> "QuestSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

- [ ] **Step 5: Run all engine tests to verify they pass**

Run: `pytest tests/test_session.py tests/test_session_e2e.py tests/test_quest.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/engine/session.py tests/test_session.py
git commit -m "engine: QuestSession tracks argv history and passes SessionState to checks

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Update Level 1 quests for new Quest signature

**Files:**
- Modify: `gameofgit/quests/level1.py`
- Test: `tests/test_level1_quests.py` (already exists)

- [ ] **Step 1: Read the current Level 1 test to understand expectations**

Run: `cat tests/test_level1_quests.py | head -40`

- [ ] **Step 2: Update every `_check_*` function in `level1.py`**

Each check function must now accept `(sandbox: Path, _state: SessionState) -> CheckResult`. Update `gameofgit/quests/level1.py`:

- Add import: `from gameofgit.engine.quest import CheckResult, Quest, SessionState`
- Change `_check_init_repo(sandbox: Path)` → `_check_init_repo(sandbox: Path, _state: SessionState)`
- Change `_check_stage_a_file(sandbox: Path)` → `_check_stage_a_file(sandbox: Path, _state: SessionState)`
- Change `_check_first_commit(sandbox: Path)` → `_check_first_commit(sandbox: Path, _state: SessionState)`
- Change `_check_meaningful_message(sandbox: Path)` → `_check_meaningful_message(sandbox: Path, _state: SessionState)`

Also add `xp` + `level` to each of the four `Quest(...)` constants:
- `INIT_REPO`: `xp=50, level=1`
- `STAGE_A_FILE`: `xp=50, level=1`
- `FIRST_COMMIT`: `xp=75, level=1`
- `MEANINGFUL_MESSAGE`: `xp=75, level=1`

- [ ] **Step 3: Update any Level 1 tests that call check functions directly**

If `tests/test_level1_quests.py` calls `quest.check(path)` directly, change each call to `quest.check(path, SessionState(last_argv=None, all_argv=[]))` and import `SessionState`.

- [ ] **Step 4: Run the full test suite**

Run: `pytest -q`
Expected: all existing tests green.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/quests/level1.py tests/test_level1_quests.py
git commit -m "quests(level1): xp/level tags + SessionState in check signatures

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Shared quest-authoring helpers

**Files:**
- Create: `gameofgit/quests/_helpers.py`
- Test: `tests/quests/__init__.py` (new empty file)
- Test: `tests/quests/test_helpers.py`

- [ ] **Step 1: Create the empty tests package**

```bash
mkdir -p tests/quests
touch tests/quests/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `tests/quests/test_helpers.py`:

```python
"""Tests for gameofgit.quests._helpers — shared quest-authoring primitives."""
from pathlib import Path

from gameofgit.quests._helpers import (
    branch_exists,
    commit_count,
    commit_file,
    head_exists,
    head_message,
    run_git,
    set_identity,
    working_tree_clean,
)


def test_run_git_returns_completed_process(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    result = run_git(["git", "status", "--porcelain"], cwd=tmp_path, capture=True)
    assert result.returncode == 0
    assert result.stdout == ""


def test_set_identity_configures_user(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    email = run_git(["git", "config", "user.email"], cwd=tmp_path, capture=True).stdout.strip()
    name = run_git(["git", "config", "user.name"], cwd=tmp_path, capture=True).stdout.strip()
    assert email and name


def test_commit_file_creates_a_commit(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "hello.txt", "world\n", "first")
    assert head_exists(tmp_path)
    assert commit_count(tmp_path) == 1
    assert head_message(tmp_path) == "first"


def test_head_exists_false_on_fresh_repo(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    assert head_exists(tmp_path) is False


def test_branch_exists_detects_named_branches(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "a.txt", "a\n", "a")
    run_git(["git", "branch", "feature"], cwd=tmp_path)
    assert branch_exists(tmp_path, "feature")
    assert not branch_exists(tmp_path, "ghost")


def test_working_tree_clean_detects_modifications(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "a.txt", "a\n", "a")
    assert working_tree_clean(tmp_path)
    (tmp_path / "a.txt").write_text("changed\n")
    assert not working_tree_clean(tmp_path)
```

- [ ] **Step 3: Run to verify fail**

Run: `pytest tests/quests/test_helpers.py -v`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement the helpers**

Create `gameofgit/quests/_helpers.py`:

```python
"""Shared primitives for quest authoring.

These wrap the hardened subprocess runner and common repo-state queries so
individual quest files stay focused on *what* they test, not *how* to run git.
"""
import subprocess
from pathlib import Path

from gameofgit.engine.env import hardened_env


def run_git(
    args: list[str],
    cwd: Path,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git (or any) command under the hardened env, from `cwd`.

    Raises CalledProcessError on non-zero exit by default (check=True). Pass
    check=False when the failure is an expected outcome you want to inspect.
    """
    return subprocess.run(
        args,
        cwd=cwd,
        env=hardened_env(),
        capture_output=capture,
        text=True,
        check=check,
    )


def set_identity(cwd: Path) -> None:
    """Configure a local git identity so commits can succeed regardless of
    the player's global ~/.gitconfig."""
    run_git(["git", "config", "user.email", "player@gameofgit.local"], cwd=cwd)
    run_git(["git", "config", "user.name", "Player"], cwd=cwd)


def commit_file(cwd: Path, path: str, content: str, msg: str) -> None:
    """Write `content` to `path` (relative to cwd), stage, and commit with `msg`.

    Assumes `cwd` is already an initialized repo with an identity set.
    """
    file = cwd / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    run_git(["git", "add", path], cwd=cwd)
    run_git(["git", "commit", "-q", "-m", msg], cwd=cwd)


def head_exists(cwd: Path) -> bool:
    result = run_git(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=cwd,
        capture=True,
        check=False,
    )
    return result.returncode == 0


def commit_count(cwd: Path) -> int:
    if not head_exists(cwd):
        return 0
    result = run_git(["git", "rev-list", "--count", "HEAD"], cwd=cwd, capture=True)
    return int(result.stdout.strip() or 0)


def branch_exists(cwd: Path, name: str) -> bool:
    result = run_git(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"],
        cwd=cwd,
        check=False,
    )
    return result.returncode == 0


def working_tree_clean(cwd: Path) -> bool:
    result = run_git(["git", "status", "--porcelain"], cwd=cwd, capture=True)
    return result.stdout.strip() == ""


def head_message(cwd: Path) -> str:
    result = run_git(["git", "log", "-1", "--pretty=%s", "HEAD"], cwd=cwd, capture=True)
    return result.stdout.strip()
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/quests/test_helpers.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/_helpers.py tests/quests/__init__.py tests/quests/test_helpers.py
git commit -m "quests: shared authoring helpers (run_git, commit_file, etc.)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2 — Player subsystem

### Task 5: `Player` dataclass + tier logic

**Files:**
- Create: `gameofgit/player/__init__.py`
- Create: `gameofgit/player/tiers.py`
- Create: `gameofgit/player/model.py`
- Test: `tests/player/__init__.py`
- Test: `tests/player/test_tiers.py`
- Test: `tests/player/test_model.py`

- [ ] **Step 1: Create the test package**

```bash
mkdir -p tests/player
touch tests/player/__init__.py
```

- [ ] **Step 2: Write failing tests for tiers module**

Create `tests/player/test_tiers.py`:

```python
from gameofgit.player.tiers import TIERS, tier_for_levels_completed, xp_required_for


def test_tier_names_are_three():
    assert TIERS == ("Junior", "Senior", "Expert")


def test_tier_boundaries():
    assert tier_for_levels_completed(0) == "Junior"
    assert tier_for_levels_completed(4) == "Junior"
    assert tier_for_levels_completed(5) == "Senior"
    assert tier_for_levels_completed(9) == "Senior"
    assert tier_for_levels_completed(10) == "Expert"


def test_tier_clamps_above_10():
    assert tier_for_levels_completed(11) == "Expert"
    assert tier_for_levels_completed(99) == "Expert"


def test_xp_required_for_milestones():
    # Placeholder: will be refined in model tests. Here we just check the API shape.
    assert xp_required_for("Junior") == 0
    assert xp_required_for("Senior") >= 0
    assert xp_required_for("Expert") >= xp_required_for("Senior")
```

- [ ] **Step 3: Run to verify fail**

Run: `pytest tests/player/test_tiers.py -v`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement tiers**

Create `gameofgit/player/__init__.py` (empty) and `gameofgit/player/tiers.py`:

```python
"""Tier constants and boundary logic.

A tier is a function of *levels completed* — not raw XP — so the player
always knows what milestone stands between them and the next title.
"""
from typing import Literal

TierName = Literal["Junior", "Senior", "Expert"]
TIERS: tuple[TierName, ...] = ("Junior", "Senior", "Expert")

_JUNIOR_MAX = 4   # 0..4 levels => Junior
_SENIOR_MAX = 9   # 5..9 levels => Senior
# 10 => Expert


def tier_for_levels_completed(n: int) -> TierName:
    if n <= _JUNIOR_MAX:
        return "Junior"
    if n <= _SENIOR_MAX:
        return "Senior"
    return "Expert"


def xp_required_for(tier: TierName) -> int:
    """Minimum cumulative XP needed to be *eligible* to first reach `tier`.

    This is informational — the actual gate is levels-complete. Returns 0 for
    Junior (everyone starts there).

    Concrete numbers are wired up in `model.xp_to_next_tier` using the
    current catalog. This function is a stable constant surface for tests
    that don't need catalog access.
    """
    if tier == "Junior":
        return 0
    if tier == "Senior":
        return 0  # level-gated, not XP-gated
    return 0      # level-gated, not XP-gated
```

- [ ] **Step 5: Write failing tests for model**

Create `tests/player/test_model.py`:

```python
from gameofgit.player.model import Player


def _all_slugs_for_levels(n: int) -> set[str]:
    """Return every quest slug in Levels 1..n from the current catalog."""
    from gameofgit.quests import all_quests
    return {q.slug for q in all_quests() if q.level <= n}


def test_empty_player_is_junior():
    p = Player(name="Robb Stark", slug="robb_stark", xp=0, completed_quests=set())
    assert p.tier == "Junior"
    assert p.levels_completed == 0


def test_player_with_level_1_complete():
    p = Player(name="a", slug="a", xp=250, completed_quests=_all_slugs_for_levels(1))
    assert p.levels_completed == 1
    assert p.tier == "Junior"


def test_player_with_5_levels_is_senior():
    p = Player(name="a", slug="a", xp=0, completed_quests=_all_slugs_for_levels(5))
    assert p.levels_completed == 5
    assert p.tier == "Senior"


def test_player_with_all_10_levels_is_expert():
    from gameofgit.quests import all_quests
    p = Player(
        name="a",
        slug="a",
        xp=0,
        completed_quests={q.slug for q in all_quests()},
    )
    assert p.levels_completed == 10
    assert p.tier == "Expert"


def test_partial_level_does_not_count():
    # All of Level 1 except the last slug -> level is not counted complete
    slugs = _all_slugs_for_levels(1)
    slugs.pop()  # drop one slug
    p = Player(name="a", slug="a", xp=0, completed_quests=slugs)
    assert p.levels_completed == 0


def test_xp_to_next_tier_is_none_for_expert():
    from gameofgit.quests import all_quests
    p = Player(name="a", slug="a", xp=0, completed_quests={q.slug for q in all_quests()})
    assert p.xp_to_next_tier is None


def test_xp_to_next_tier_positive_for_junior():
    p = Player(name="a", slug="a", xp=0, completed_quests=set())
    # Junior, needs Level 5 completion to promote — there's definitely XP between here and there.
    assert p.xp_to_next_tier is not None
    assert p.xp_to_next_tier > 0
```

- [ ] **Step 6: Run to verify fail**

Run: `pytest tests/player/test_model.py -v`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement `Player`**

Create `gameofgit/player/model.py`:

```python
"""Player profile + tier derivation.

`completed_quests` is the source of truth. `xp` is denormalized for display
but is always recomputable from the quest catalog.
"""
from dataclasses import dataclass, field
from typing import Optional

from gameofgit.player.tiers import TierName, tier_for_levels_completed


@dataclass
class Player:
    name: str
    slug: str
    xp: int = 0
    completed_quests: set[str] = field(default_factory=set)

    @property
    def levels_completed(self) -> int:
        """Number of levels where every quest slug has been completed."""
        from gameofgit.quests import all_quests
        quests = list(all_quests())
        by_level: dict[int, set[str]] = {}
        for q in quests:
            by_level.setdefault(q.level, set()).add(q.slug)
        count = 0
        for level_slugs in by_level.values():
            if level_slugs.issubset(self.completed_quests):
                count += 1
        return count

    @property
    def tier(self) -> TierName:
        return tier_for_levels_completed(self.levels_completed)

    @property
    def xp_to_next_tier(self) -> Optional[int]:
        """XP remaining to the *next* tier title, or None if already Expert.

        Computed as: sum of XP for all quests in levels 1..N (where N is the
        first level count that promotes the player) minus current xp, clamped
        at 0.
        """
        from gameofgit.quests import all_quests
        current_tier = self.tier
        if current_tier == "Expert":
            return None
        target_levels_completed = 5 if current_tier == "Junior" else 10
        target_xp = sum(
            q.xp for q in all_quests() if q.level <= target_levels_completed
        )
        remaining = target_xp - self.xp
        return max(remaining, 0)
```

- [ ] **Step 8: Run tests**

Run: `pytest tests/player/ -v`
Expected: PASS (all tests in tiers + model).

- [ ] **Step 9: Commit**

```bash
git add gameofgit/player/ tests/player/__init__.py tests/player/test_tiers.py tests/player/test_model.py
git commit -m "player: Player dataclass + tier derivation (Junior/Senior/Expert)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Profile persistence (`store.py`)

**Files:**
- Create: `gameofgit/player/store.py`
- Test: `tests/player/test_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/player/test_store.py`:

```python
import json

import pytest

from gameofgit.player.store import (
    InvalidName,
    load_or_create,
    save,
    slugify,
)


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def test_slugify_lowercases_and_strips():
    assert slugify("Robb Stark") == "robb_stark"
    assert slugify("ROBB STARK") == "robb_stark"
    assert slugify("  robb   stark  ") == "robb_stark"


def test_slugify_rejects_empty_after_normalization():
    with pytest.raises(InvalidName):
        slugify("   ")
    with pytest.raises(InvalidName):
        slugify("!!!")
    with pytest.raises(InvalidName):
        slugify("")


def test_load_or_create_creates_new_profile(_profiles_dir):
    p = load_or_create("Robb Stark")
    assert p.name == "Robb Stark"
    assert p.slug == "robb_stark"
    assert p.xp == 0
    assert p.completed_quests == set()
    # File was NOT written yet — creation without explicit save is in-memory only.
    assert not (_profiles_dir / "robb_stark.json").exists()


def test_save_then_load_roundtrip(_profiles_dir):
    p = load_or_create("Robb Stark")
    p.completed_quests = {"init-repo", "stage-a-file"}
    p.xp = 999  # wrong on purpose — should be recomputed on load
    save(p)

    # File exists
    data = json.loads((_profiles_dir / "robb_stark.json").read_text())
    assert data["slug"] == "robb_stark"
    assert set(data["completed_quests"]) == {"init-repo", "stage-a-file"}

    # Reload: xp is recomputed from catalog (not the stale 999)
    reloaded = load_or_create("Robb Stark")
    assert reloaded.completed_quests == {"init-repo", "stage-a-file"}
    assert reloaded.xp == 100  # 50 + 50 from Level 1


def test_slug_collision_shares_profile(_profiles_dir):
    a = load_or_create("Robb Stark")
    a.completed_quests = {"init-repo"}
    save(a)
    b = load_or_create("ROBB STARK")
    assert b.slug == "robb_stark"
    assert b.completed_quests == {"init-repo"}


def test_corrupt_json_falls_back_to_fresh(_profiles_dir):
    path = _profiles_dir / "corrupt.json"
    path.write_text("not json at all {{{")
    # Directly write a file under a slug the caller expects to exist
    p = load_or_create("corrupt")
    assert p.xp == 0
    assert p.completed_quests == set()


def test_invalid_name_raises(_profiles_dir):
    with pytest.raises(InvalidName):
        load_or_create("   ")
```

- [ ] **Step 2: Run tests, observe fail**

Run: `pytest tests/player/test_store.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `store.py`**

Create `gameofgit/player/store.py`:

```python
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
from datetime import datetime, timezone
from pathlib import Path

from gameofgit.player.model import Player


class InvalidName(ValueError):
    """Raised when a player name can't be turned into a valid slug."""


_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def slugify(name: str) -> str:
    """Normalize a human-entered name to a filesystem-safe slug.

    Two names that normalize to the same slug share a profile. This is a
    feature for a LAN-local training tool; don't try to "fix" it.
    """
    base = name.strip().lower()
    slug = _SLUG_RE.sub("_", base).strip("_")
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/player/test_store.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/player/store.py tests/player/test_store.py
git commit -m "player: JSON-per-player profile store with atomic writes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 3 — Web API

### Task 7: Extend Pydantic schemas

**Files:**
- Modify: `gameofgit/web/schemas.py`
- Test: `tests/test_web_schemas.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_schemas.py`:

```python
from gameofgit.web.schemas import PlayerView, QuestView, RunResponse


def test_player_view_expert_has_null_xp_to_next():
    v = PlayerView(
        name="n",
        tier="Expert",
        xp=4175,
        xp_to_next_tier=None,
        levels_completed=10,
        total_levels=10,
    )
    assert v.xp_to_next_tier is None


def test_quest_view_has_xp_and_level():
    v = QuestView(
        slug="s", title="t", brief="b",
        allowed=["init"], quest_index=0, total=1,
        hints_revealed=[], total_hints=0,
        check_passed=False, check_detail=None,
        xp=50, level=1,
    )
    assert v.xp == 50
    assert v.level == 1


def test_run_response_has_xp_awarded_and_player():
    qv = QuestView(
        slug="s", title="t", brief="b",
        allowed=["init"], quest_index=0, total=1,
        hints_revealed=[], total_hints=0,
        check_passed=False, check_detail=None,
        xp=50, level=1,
    )
    pv = PlayerView(
        name="n", tier="Junior", xp=0,
        xp_to_next_tier=1000, levels_completed=0, total_levels=10,
    )
    r = RunResponse(
        stdout="", stderr="", exit_code=0,
        quest=qv, advanced=False, level_complete=False,
        xp_awarded=50, player=pv,
    )
    assert r.xp_awarded == 50
    assert r.player.tier == "Junior"
```

- [ ] **Step 2: Run, observe fail**

Run: `pytest tests/test_web_schemas.py -v`
Expected: FAIL (fields don't exist).

- [ ] **Step 3: Update `schemas.py`**

Replace `gameofgit/web/schemas.py` with:

```python
"""Pydantic models for the Game of GIT web API request/response payloads."""

from typing import Literal

from pydantic import BaseModel

from gameofgit.player.model import Player
from gameofgit.web.games import Game, total_quests


class QuestView(BaseModel):
    slug: str
    title: str
    brief: str
    allowed: list[str]
    quest_index: int
    total: int
    hints_revealed: list[str]
    total_hints: int
    check_passed: bool
    check_detail: str | None
    xp: int
    level: int


class PlayerView(BaseModel):
    name: str
    tier: Literal["Junior", "Senior", "Expert"]
    xp: int
    xp_to_next_tier: int | None
    levels_completed: int
    total_levels: int


class RunRequest(BaseModel):
    cmdline: str


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    quest: QuestView
    advanced: bool
    level_complete: bool
    xp_awarded: int
    player: "PlayerView"


class SuggestRequest(BaseModel):
    cmdline: str


class SuggestResponse(BaseModel):
    suggestion: str | None


class CreatePlayerRequest(BaseModel):
    name: str


class CreateGameRequest(BaseModel):
    player_slug: str


class GameCreatedResponse(BaseModel):
    game_id: str
    quest: QuestView
    player: "PlayerView"


def player_view(player: Player) -> PlayerView:
    return PlayerView(
        name=player.name,
        tier=player.tier,
        xp=player.xp,
        xp_to_next_tier=player.xp_to_next_tier,
        levels_completed=player.levels_completed,
        total_levels=10,
    )


def quest_view(g: Game) -> QuestView:
    q = g.quest
    check = g.session._last_check
    return QuestView(
        slug=q.slug,
        title=q.title,
        brief=q.brief,
        allowed=sorted(q.allowed),
        quest_index=g.quest_index,
        total=total_quests(),
        hints_revealed=list(q.hints[: g.hints_revealed]),
        total_hints=len(q.hints),
        check_passed=check.passed,
        check_detail=check.detail,
        xp=q.xp,
        level=q.level,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_web_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/web/schemas.py tests/test_web_schemas.py
git commit -m "web: schemas gain PlayerView, xp/level on QuestView, xp_awarded on RunResponse

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: `Game` holds a `Player`; update `new_game`

**Files:**
- Modify: `gameofgit/web/games.py`
- Test: existing `tests/test_web_api.py` will be updated later

- [ ] **Step 1: Read current `games.py` to confirm the existing shape**

Run: `cat gameofgit/web/games.py`

- [ ] **Step 2: Replace `games.py`**

```python
"""In-memory game registry.

Thread-safety is not required — FastAPI runs single-process for this local game.
"""

import uuid
from dataclasses import dataclass

from gameofgit.engine import QuestSession
from gameofgit.player.model import Player
from gameofgit.player.store import load_or_create
from gameofgit.quests import all_quests

_QUESTS = list(all_quests())


@dataclass
class Game:
    id: str
    quest_index: int
    session: QuestSession
    player: Player
    hints_revealed: int = 0

    @property
    def quest(self):
        return _QUESTS[self.quest_index]

    @property
    def is_last_quest(self) -> bool:
        return self.quest_index >= len(_QUESTS) - 1

    def advance(self) -> None:
        self.session.close()
        self.quest_index += 1
        self.session = QuestSession(self.quest)
        self.hints_revealed = 0

    def close(self) -> None:
        self.session.close()


_GAMES: dict[str, Game] = {}


def new_game(player_slug: str) -> Game:
    """Start a fresh game for the given player slug. Profile must already exist.

    Raises `KeyError` if no profile file exists for the slug.
    """
    player = load_or_create(player_slug)  # slugify-by-name path; works because slug==slug
    gid = uuid.uuid4().hex
    quest = _QUESTS[0]
    g = Game(
        id=gid,
        quest_index=0,
        session=QuestSession(quest),
        player=player,
    )
    _GAMES[gid] = g
    return g


def get_game(gid: str) -> Game | None:
    return _GAMES.get(gid)


def close_game(gid: str) -> None:
    g = _GAMES.pop(gid, None)
    if g is not None:
        g.close()


def total_quests() -> int:
    return len(_QUESTS)
```

- [ ] **Step 3: Run the existing engine/player tests**

Run: `pytest tests/test_quest.py tests/test_session.py tests/player/ -v`
Expected: PASS (web tests will be fixed in a later task).

- [ ] **Step 4: Commit**

```bash
git add gameofgit/web/games.py
git commit -m "web: Game carries a Player; new_game requires a player slug

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Player routes + updated game routes

**Files:**
- Modify: `gameofgit/web/server.py`
- Test: `tests/test_web_player_routes.py` (new)
- Test: `tests/test_web_api.py` (update)

- [ ] **Step 1: Write failing tests for player routes**

Create `tests/test_web_player_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from gameofgit.web.server import app


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def test_post_player_creates_and_returns_view():
    with TestClient(app) as client:
        r = client.post("/api/player", json={"name": "Robb Stark"})
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Robb Stark"
        assert body["tier"] == "Junior"
        assert body["xp"] == 0
        assert body["levels_completed"] == 0
        assert body["total_levels"] == 10


def test_post_player_rejects_empty_name():
    with TestClient(app) as client:
        r = client.post("/api/player", json={"name": "   "})
        assert r.status_code == 400


def test_post_player_is_idempotent():
    with TestClient(app) as client:
        r1 = client.post("/api/player", json={"name": "Arya"})
        assert r1.status_code == 200
        r2 = client.post("/api/player", json={"name": "arya"})
        assert r2.status_code == 200
        assert r2.json()["name"] in ("Arya", "arya")  # keeps latest-entered form


def test_get_player_returns_404_if_missing():
    with TestClient(app) as client:
        r = client.get("/api/player/does_not_exist")
        assert r.status_code == 404


def test_get_player_returns_existing_profile():
    with TestClient(app) as client:
        client.post("/api/player", json={"name": "Jon"})
        r = client.get("/api/player/jon")
        assert r.status_code == 200
        assert r.json()["name"] == "Jon"
```

- [ ] **Step 2: Write the failing game-route tests**

Update `tests/test_web_api.py` — every `client.post("/api/game")` call needs a `player_slug` body. Replace the file contents with:

```python
"""Tests for the FastAPI web API layer."""

import pytest
from fastapi.testclient import TestClient

from gameofgit.web.server import app


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def _start_game(client: TestClient, name: str = "Tester") -> str:
    client.post("/api/player", json={"name": name})
    r = client.post("/api/game", json={"player_slug": name.lower()})
    assert r.status_code == 200
    return r.json()["game_id"]


def test_index_page_loads():
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "GAME OF GIT" in r.text or "Game of GIT" in r.text
        assert "PLAY" in r.text.upper()


def test_play_page_loads():
    with TestClient(app) as client:
        r = client.get("/play")
        assert r.status_code == 200
        assert "app.js" in r.text


def test_create_game_requires_known_player():
    with TestClient(app) as client:
        r = client.post("/api/game", json={"player_slug": "ghost"})
        assert r.status_code == 400


def test_create_game_and_run_init():
    with TestClient(app) as client:
        game_id = _start_game(client)
        r = client.post(f"/api/game/{game_id}/run", json={"cmdline": "git init"})
        assert r.status_code == 200
        body = r.json()
        assert body["exit_code"] == 0
        assert body["advanced"] is True
        assert body["xp_awarded"] == 50
        assert body["player"]["xp"] == 50
        assert body["quest"]["slug"] == "stage-a-file"
        client.delete(f"/api/game/{game_id}")


def test_xp_not_double_awarded_across_games():
    with TestClient(app) as client:
        # Game 1 — pass init-repo
        g1 = _start_game(client, "Dup")
        client.post(f"/api/game/{g1}/run", json={"cmdline": "git init"})
        client.delete(f"/api/game/{g1}")
        # Game 2 — same player, pass init-repo again
        g2 = _start_game(client, "Dup")
        r = client.post(f"/api/game/{g2}/run", json={"cmdline": "git init"})
        assert r.json()["xp_awarded"] == 0
        assert r.json()["player"]["xp"] == 50
        client.delete(f"/api/game/{g2}")


def test_hint_reveals_one_at_a_time():
    with TestClient(app) as client:
        gid = _start_game(client)
        assert client.post(f"/api/game/{gid}/hint").json()["hints_revealed"] != []
        client.delete(f"/api/game/{gid}")


def test_suggest_endpoint_returns_correction_for_typo():
    with TestClient(app) as client:
        gid = _start_game(client)
        r = client.post(f"/api/game/{gid}/suggest", json={"cmdline": "git innit"})
        assert r.status_code == 200
        assert r.json().get("suggestion")
        client.delete(f"/api/game/{gid}")
```

- [ ] **Step 3: Run all tests, observe failures**

Run: `pytest tests/test_web_api.py tests/test_web_player_routes.py -v`
Expected: FAIL — routes not yet implemented.

- [ ] **Step 4: Rewrite `server.py`**

Replace `gameofgit/web/server.py` with:

```python
"""FastAPI application — routes, static file serving, game API."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gameofgit.engine import suggest
from gameofgit.player.store import InvalidName, load_or_create, save
from gameofgit.web.games import close_game, get_game, new_game
from gameofgit.web.schemas import (
    CreateGameRequest,
    CreatePlayerRequest,
    GameCreatedResponse,
    PlayerView,
    QuestView,
    RunRequest,
    RunResponse,
    SuggestRequest,
    SuggestResponse,
    player_view,
    quest_view,
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Game of GIT")

app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.middleware("http")
async def _no_cache_assets(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path in ("/", "/play"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def index_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")


@app.get("/play", response_class=FileResponse, include_in_schema=False)
async def play_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "play.html", media_type="text/html")


# ---------------------------------------------------------------------------
# Player API
# ---------------------------------------------------------------------------


@app.post("/api/player", response_model=PlayerView)
async def create_or_load_player(req: CreatePlayerRequest) -> PlayerView:
    try:
        player = load_or_create(req.name)
    except InvalidName as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Persist at least the name so /api/player/{slug} works on later requests.
    save(player)
    return player_view(player)


@app.get("/api/player/{slug}", response_model=PlayerView)
async def get_player(slug: str) -> PlayerView:
    # A slug here maps back to a real file if-and-only-if a profile exists.
    from pathlib import Path as _P
    from gameofgit.player.store import _path_for  # type: ignore[attr-defined]
    if not _path_for(slug).exists():
        raise HTTPException(status_code=404, detail="No such player.")
    player = load_or_create(slug)
    return player_view(player)


# ---------------------------------------------------------------------------
# Game API
# ---------------------------------------------------------------------------


@app.post("/api/game", response_model=GameCreatedResponse)
async def create_game(req: CreateGameRequest) -> GameCreatedResponse:
    from gameofgit.player.store import _path_for  # type: ignore[attr-defined]
    if not _path_for(req.player_slug).exists():
        raise HTTPException(
            status_code=400,
            detail="Unknown player. Create a profile first via POST /api/player.",
        )
    game = new_game(req.player_slug)
    return GameCreatedResponse(
        game_id=game.id,
        quest=quest_view(game),
        player=player_view(game.player),
    )


@app.post("/api/game/{gid}/run", response_model=RunResponse)
async def run_command(gid: str, req: RunRequest) -> RunResponse:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    prev_passed = game.session._last_check.passed
    outcome = game.session.run(req.cmdline)

    advanced = False
    level_complete = False
    xp_awarded = 0

    if outcome.check.passed and not prev_passed:
        slug = game.quest.slug
        if slug not in game.player.completed_quests:
            game.player.completed_quests.add(slug)
            game.player.xp += game.quest.xp
            xp_awarded = game.quest.xp
            save(game.player)

        if game.is_last_quest:
            level_complete = True
        else:
            game.advance()
            advanced = True

    return RunResponse(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        exit_code=outcome.exit_code,
        quest=quest_view(game),
        advanced=advanced,
        level_complete=level_complete,
        xp_awarded=xp_awarded,
        player=player_view(game.player),
    )


@app.post("/api/game/{gid}/hint", response_model=QuestView)
async def reveal_hint(gid: str) -> QuestView:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    quest = game.quest
    if game.hints_revealed < len(quest.hints):
        game.hints_revealed += 1

    return quest_view(game)


@app.post("/api/game/{gid}/suggest", response_model=SuggestResponse)
async def get_suggestion(gid: str, req: SuggestRequest) -> SuggestResponse:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    correction = suggest(req.cmdline, game.quest.allowed)
    return SuggestResponse(suggestion=correction)


@app.delete("/api/game/{gid}", status_code=204)
async def delete_game(gid: str) -> None:
    close_game(gid)
```

- [ ] **Step 5: Run all backend tests**

Run: `pytest -q`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add gameofgit/web/server.py tests/test_web_api.py tests/test_web_player_routes.py
git commit -m "web: POST/GET /api/player routes; game routes require player_slug; XP accrual wired

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 4 — Frontend (home + play)

### Task 10: Home page — name input + PLAY flow

**Files:**
- Modify: `gameofgit/web/static/index.html`
- Modify: `gameofgit/web/static/style.css`

- [ ] **Step 1: Read current index.html to locate the PLAY button**

Run: `grep -n "PLAY" gameofgit/web/static/index.html | head -10`

- [ ] **Step 2: Add the name input block**

In `gameofgit/web/static/index.html`, locate the existing PLAY-button container and replace just that container with:

```html
<div class="play-gate">
    <label for="player-name" class="name-label">Enter your name, ser:</label>
    <input
        id="player-name"
        class="name-input"
        type="text"
        maxlength="40"
        autocomplete="off"
        autocorrect="off"
        autocapitalize="words"
        spellcheck="false"
        placeholder="Robb Stark"
    />
    <button id="play-btn" class="play-btn" type="button" disabled>PLAY</button>
    <p id="play-greeting" class="play-greeting hidden"></p>
</div>

<script>
(function() {
    var input = document.getElementById("player-name");
    var btn = document.getElementById("play-btn");
    var greet = document.getElementById("play-greeting");

    // Prefill from localStorage
    var cached = localStorage.getItem("gog.playerName");
    if (cached) input.value = cached;
    btn.disabled = input.value.trim().length === 0;

    input.addEventListener("input", function() {
        btn.disabled = input.value.trim().length === 0;
    });

    btn.addEventListener("click", async function() {
        var name = input.value.trim();
        if (!name) return;
        btn.disabled = true;
        try {
            var res = await fetch("/api/player", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: name }),
            });
            if (!res.ok) {
                var txt = await res.text().catch(function() { return ""; });
                greet.textContent = "The maesters could not write that name.";
                greet.classList.remove("hidden");
                btn.disabled = false;
                return;
            }
            var player = await res.json();
            localStorage.setItem("gog.playerName", name);
            localStorage.setItem("gog.playerSlug", slugify(name));
            if (player.xp > 0) {
                greet.textContent =
                    "Welcome back, " + player.name + " — Tier: " +
                    player.tier + ", " + player.xp + " XP";
                greet.classList.remove("hidden");
                setTimeout(function() {
                    window.location.href = "/play";
                }, 1500);
            } else {
                window.location.href = "/play";
            }
        } catch (err) {
            greet.textContent = "The scribes dropped their quill. Try again.";
            greet.classList.remove("hidden");
            btn.disabled = false;
        }
    });

    function slugify(s) {
        return s.trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "");
    }
})();
</script>
```

- [ ] **Step 3: Add styles in `style.css`**

Append to `gameofgit/web/static/style.css`:

```css
.play-gate {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.8rem;
    margin-top: 1.5rem;
}
.name-label {
    font-family: var(--font-display);
    font-size: 1rem;
    letter-spacing: 0.15em;
    color: #d4af37;
}
.name-input {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(212, 175, 55, 0.45);
    color: #f4d77e;
    font-family: var(--font-body);
    font-size: 1.1rem;
    padding: 0.6rem 1rem;
    width: min(360px, 80vw);
    text-align: center;
    border-radius: 2px;
    outline: none;
}
.name-input:focus {
    border-color: rgba(212, 175, 55, 0.95);
    box-shadow: 0 0 8px rgba(212, 175, 55, 0.4);
}
.play-btn[disabled] {
    opacity: 0.45;
    cursor: not-allowed;
    filter: grayscale(0.6);
}
.play-greeting {
    font-family: var(--font-body);
    font-style: italic;
    color: #f4d77e;
    margin-top: 0.4rem;
}
.hidden { display: none !important; }
```

- [ ] **Step 4: Bump the cache-buster version**

Change every `?v=3` in `index.html` to `?v=4`.

- [ ] **Step 5: Manual smoke test**

```bash
./venv/bin/python -m gameofgit &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8000/ | grep -q "Enter your name" && echo OK || echo FAIL
kill $SERVER_PID
```
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/web/static/index.html gameofgit/web/static/style.css
git commit -m "web(ui): home page name input gates PLAY button; loads/creates profile

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Play page — status bar + `app.js` wiring

**Files:**
- Modify: `gameofgit/web/static/play.html`
- Modify: `gameofgit/web/static/app.js`
- Modify: `gameofgit/web/static/style.css`

- [ ] **Step 1: Replace the play-page header**

In `gameofgit/web/static/play.html`, replace the existing `<header class="game-header">...</header>` block with:

```html
<header class="game-header">
    <a href="/" class="mini-logo">GAME OF GIT</a>
    <div class="status-bar" id="status-bar">
        <span class="tier-pill" id="tier-pill">Junior</span>
        <span class="xp-label"><span id="xp-value">0</span> XP</span>
        <div class="xp-bar-wrap"><div class="xp-bar-fill" id="xp-bar-fill"></div></div>
    </div>
    <span class="progress-indicator" id="progress">Level 1 · Quest 1 of 4</span>
</header>
```

Also bump `?v=3` to `?v=4` on the stylesheet and script lines.

- [ ] **Step 2: Add styles for the status bar and tier pill**

Append to `gameofgit/web/static/style.css`:

```css
.status-bar {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    font-family: var(--font-body);
    color: #f4d77e;
    font-size: 0.95rem;
}
.tier-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    background: linear-gradient(180deg,
        #6b4a0d 0%, #8b6914 15%, #d4af37 35%,
        #f4d77e 50%, #d4af37 65%, #8b6914 85%, #6b4a0d 100%);
    color: #1a0d00;
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.8rem;
    border: 1px solid rgba(0, 0, 0, 0.4);
    box-shadow: 0 0 6px rgba(212, 175, 55, 0.35);
}
.xp-label { min-width: 5ch; text-align: right; }
.xp-bar-wrap {
    width: 120px;
    height: 6px;
    border: 1px solid rgba(212, 175, 55, 0.5);
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.5);
    overflow: hidden;
}
.xp-bar-fill {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #8b6914, #d4af37, #f4d77e);
    transition: width 400ms ease-out;
}

/* Tier-up toast */
.tier-toast {
    position: fixed;
    top: 30%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(20, 10, 0, 0.9);
    border: 1px solid #d4af37;
    padding: 1.4rem 2.6rem;
    font-family: var(--font-display);
    font-size: 1.4rem;
    color: #f4d77e;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    box-shadow: 0 0 40px rgba(212, 175, 55, 0.4);
    z-index: 200;
    animation: toastFade 2s ease-in-out forwards;
}
@keyframes toastFade {
    0%   { opacity: 0; transform: translate(-50%, -60%); }
    15%  { opacity: 1; transform: translate(-50%, -50%); }
    85%  { opacity: 1; }
    100% { opacity: 0; }
}
```

- [ ] **Step 3: Rewrite `app.js` sections — state, API, rendering**

In `gameofgit/web/static/app.js`, at the top of the "Module state" block, add after `let pendingExit = false;`:

```javascript
let currentPlayer = null;
let previousTier = null;
```

Replace `createGame` with:

```javascript
async function createGame() {
    var slug = localStorage.getItem("gog.playerSlug");
    if (!slug) {
        window.location.href = "/";
        return null;
    }
    return apiFetch("/api/game", {
        method: "POST",
        body: JSON.stringify({ player_slug: slug }),
    });
}
```

Add after `renderQuest`:

```javascript
function renderPlayer(player) {
    currentPlayer = player;
    if (previousTier === null) previousTier = player.tier;

    getEl("tier-pill").textContent = player.tier;
    getEl("xp-value").textContent = player.xp;

    var fill = getEl("xp-bar-fill");
    var pct;
    if (player.xp_to_next_tier === null || player.xp_to_next_tier === 0) {
        pct = 100;
    } else {
        var denom = player.xp + player.xp_to_next_tier;
        pct = denom > 0 ? Math.round((player.xp / denom) * 100) : 0;
    }
    fill.style.width = pct + "%";
}

function renderProgress(quest) {
    getEl("progress").textContent =
        "Level " + quest.level + " · Quest " +
        (quest.quest_index + 1) + " of " + quest.total;
}

function showTierUpToast(newTier) {
    var toast = document.createElement("div");
    toast.className = "tier-toast";
    toast.textContent = "You have risen to " + newTier + ".";
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 2000);
}
```

Replace the existing body of `renderQuest` with:

```javascript
function renderQuest(quest) {
    currentQuest = quest;
    getEl("quest-title").textContent = quest.title;
    getEl("quest-brief").textContent = quest.brief;

    renderProgress(quest);

    var pillsEl = getEl("allowed-pills");
    clearChildren(pillsEl);
    for (var i = 0; i < quest.allowed.length; i++) {
        var pill = document.createElement("span");
        pill.className = "allowed-pill";
        pill.textContent = quest.allowed[i];
        pillsEl.appendChild(pill);
    }

    renderHints(quest);
    renderStatus(quest);
}
```

Update `handleEnter`'s command-run branch — after `renderQuest(body.quest);`, add:

```javascript
if (body.player) {
    var oldTier = previousTier;
    renderPlayer(body.player);
    if (body.xp_awarded && body.xp_awarded > 0) {
        appendLog("+" + body.xp_awarded + " XP earned. Onward.", "log-info");
    }
    if (body.player.tier !== oldTier) {
        showTierUpToast(body.player.tier);
        previousTier = body.player.tier;
    }
}
```

Update `init()` — after `renderQuest(gameData.quest);`, add:

```javascript
if (gameData.player) {
    renderPlayer(gameData.player);
}
```

- [ ] **Step 4: Run the backend tests to confirm nothing regressed**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Manual smoke test**

```bash
./venv/bin/python -m gameofgit &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8000/play | grep -q "status-bar" && echo OK || echo FAIL
kill $SERVER_PID
```
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/web/static/
git commit -m "web(ui): play-page status bar with tier pill, XP count, and progress bar

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: `/exit` summary + level-complete overlay XP lines

**Files:**
- Modify: `gameofgit/web/static/app.js`
- Modify: `gameofgit/web/static/play.html`

- [ ] **Step 1: Update `showExitSummary`**

In `gameofgit/web/static/app.js`, replace the whole `showExitSummary` function with:

```javascript
function showExitSummary() {
    var completed = 0;
    var total = 0;
    var hintsUsed = 0;
    if (currentQuest) {
        completed = currentQuest.quest_index + (currentQuest.check_passed ? 1 : 0);
        total = currentQuest.total;
        hintsUsed = currentQuest.hints_revealed ? currentQuest.hints_revealed.length : 0;
    }

    var rule = "\u2500".repeat(49);
    appendLog("", "log-stdout");
    appendLog(rule, "log-info");
    appendLog("  Farewell, brave soul.", "log-info");
    appendLog(rule, "log-info");

    if (currentPlayer) {
        appendLog("  Tier             : " + currentPlayer.tier + " \u2694", "log-info");
        appendLog(
            "  Total XP         : " + currentPlayer.xp + " / " +
            (currentPlayer.xp + (currentPlayer.xp_to_next_tier || 0)) +
            (currentPlayer.tier === "Expert" ? " (Master of the Realm)" : ""),
            "log-info"
        );
    }
    appendLog("  Quests completed : " + completed + " of " + total, "log-info");
    if (currentPlayer && currentPlayer.xp_to_next_tier !== null && currentPlayer.tier !== "Expert") {
        var nextTier = currentPlayer.tier === "Junior" ? "Senior" : "Expert";
        appendLog("  " + currentPlayer.xp_to_next_tier + " XP from " + nextTier, "log-info");
    } else if (currentPlayer && currentPlayer.tier === "Expert") {
        appendLog("  The title of Expert is yours.", "log-info");
    }
    appendLog("  Hints revealed   : " + hintsUsed, "log-info");
    appendLog("", "log-stdout");

    var msg;
    if (total > 0 && completed >= total) {
        msg = "You have mastered this level. The realm sings your name.";
    } else if (total > 0 && completed >= Math.ceil(total / 2)) {
        msg = "A worthy showing. The sword grows lighter in your hand.";
    } else if (completed > 0) {
        msg = "Every maester began with a single scroll. Return when ready.";
    } else {
        msg = "The path awaits you still. Return when you are prepared.";
    }
    appendLog("  " + msg, "log-info");
    appendLog("", "log-stdout");
    appendLog("  Returning to the Keep\u2026", "log-info");

    var input = getEl("shell-input");
    input.disabled = true;
    input.placeholder = "game ended";

    closeGame();
    setTimeout(function() { window.location.href = "/"; }, 2500);
}
```

- [ ] **Step 2: Add level-complete overlay lines**

Locate the existing `<div class="level-complete-overlay ...">` block in `gameofgit/web/static/play.html` and replace it with:

```html
<div class="level-complete-overlay hidden" id="level-complete-overlay" role="dialog" aria-modal="true" aria-label="Level complete">
    <h2 class="level-complete-title">Level Complete!</h2>
    <p class="level-complete-sub" id="level-complete-sub">
        The realm remembers your valor. You have mastered the foundations
        of the sacred art of <em>git</em>.
    </p>
    <p class="level-complete-xp" id="level-complete-xp"></p>
    <a href="/" class="level-complete-btn">Return to the Keep</a>
</div>
```

- [ ] **Step 3: Track per-session XP and populate the overlay**

In `gameofgit/web/static/app.js`, add after `let previousTier = null;`:

```javascript
let sessionXpStart = 0;
```

In `init()` after `renderPlayer(gameData.player);`, add:

```javascript
sessionXpStart = gameData.player.xp;
```

Replace the existing `showLevelComplete` with:

```javascript
function showLevelComplete() {
    var overlay = getEl("level-complete-overlay");
    var xpLine = getEl("level-complete-xp");
    if (currentPlayer) {
        var earned = currentPlayer.xp - sessionXpStart;
        xpLine.textContent =
            "+ " + earned + " XP earned this session  ·  Tier: " + currentPlayer.tier;
    } else {
        xpLine.textContent = "";
    }
    overlay.classList.remove("hidden");
}
```

- [ ] **Step 4: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/web/static/app.js gameofgit/web/static/play.html
git commit -m "web(ui): /exit and level-complete show tier + XP + progression

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 5 — Quest content, Levels 2–10

> All Level-2-through-10 tasks follow the same shape:
> 1. Write a `tests/quests/test_levelN.py` that asserts, for every quest: seed runs, `check` is False post-seed, a happy-path command sequence makes `check` return True.
> 2. Implement `gameofgit/quests/levelN.py`.
> 3. Register the level in `gameofgit/quests/__init__.py`.
> 4. Run full suite, commit.

### Task 13: Level 2 — TIME TRAVELER

**Files:**
- Create: `gameofgit/quests/level2.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level2.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level2.py`:

```python
"""Level 2 — TIME TRAVELER quest tests."""
from pathlib import Path

from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level2 import INSPECT_A_COMMIT, READ_THE_LOG, SPOT_THE_DIFF


def _blank_state():
    return SessionState(last_argv=None, all_argv=[])


def test_read_the_log_pass_after_running_log(tmp_path):
    READ_THE_LOG.seed(tmp_path)
    assert READ_THE_LOG.check(tmp_path, _blank_state()).passed is False
    state_after_log = SessionState(
        last_argv=("git", "log"),
        all_argv=[("git", "log")],
    )
    assert READ_THE_LOG.check(tmp_path, state_after_log).passed is True


def test_spot_the_diff_pass_after_running_diff(tmp_path):
    SPOT_THE_DIFF.seed(tmp_path)
    assert SPOT_THE_DIFF.check(tmp_path, _blank_state()).passed is False
    state = SessionState(last_argv=("git", "diff"), all_argv=[("git", "diff")])
    assert SPOT_THE_DIFF.check(tmp_path, state).passed is True


def test_inspect_a_commit_pass_after_show(tmp_path):
    INSPECT_A_COMMIT.seed(tmp_path)
    assert INSPECT_A_COMMIT.check(tmp_path, _blank_state()).passed is False
    # Get any real commit sha
    sha = run_git(
        ["git", "log", "--pretty=%H", "-n", "2"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[-1]  # not HEAD
    state = SessionState(
        last_argv=("git", "show", sha),
        all_argv=[("git", "show", sha)],
    )
    assert INSPECT_A_COMMIT.check(tmp_path, state).passed is True
```

- [ ] **Step 2: Run to observe fail**

Run: `pytest tests/quests/test_level2.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `level2.py`**

Create `gameofgit/quests/level2.py`:

```python
"""Level 2 — TIME TRAVELER.

Learn to read history: `git log`, `git diff`, `git show`.
"""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import commit_file, head_exists, run_git, set_identity

_ALLOWED = frozenset({"log", "show", "diff", "status"})


def _seed_five_commits(sandbox: Path) -> None:
    run_git(["git", "init", "-q"], cwd=sandbox)
    set_identity(sandbox)
    for i in range(1, 6):
        commit_file(sandbox, f"chapter_{i}.txt", f"line {i}\n", f"chapter {i}")


def _has_run(state: SessionState, subcommand: str) -> bool:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == subcommand:
            return True
    return False


def _check_read_the_log(sandbox: Path, state: SessionState) -> CheckResult:
    if not head_exists(sandbox):
        return CheckResult(False, "The chronicle is empty — no history to read.")
    if _has_run(state, "log"):
        return CheckResult(True)
    return CheckResult(False, "You haven't consulted the chronicle yet. Try `git log`.")


READ_THE_LOG = Quest(
    slug="read-the-log",
    title="Read the chronicle of what has passed.",
    brief=(
        "Every commit is a chapter. Call up the list of chapters written so "
        "far to see how this place came to be."
    ),
    hints=(
        "There's a git command that prints history in reverse-chronological order.",
        "Try `git log`. If the output is long, press `q` to leave the pager.",
    ),
    allowed=_ALLOWED,
    check=_check_read_the_log,
    xp=75,
    level=2,
    seed=_seed_five_commits,
)


def _seed_dirty_working_tree(sandbox: Path) -> None:
    _seed_five_commits(sandbox)
    # Modify a tracked file without staging
    (sandbox / "chapter_3.txt").write_text("line 3 — amended in shadow\n")


def _check_spot_the_diff(sandbox: Path, state: SessionState) -> CheckResult:
    if _has_run(state, "diff"):
        return CheckResult(True)
    return CheckResult(
        False,
        "A change has been made but not reviewed. Try `git diff`.",
    )


SPOT_THE_DIFF = Quest(
    slug="spot-the-diff",
    title="Spot what has changed in the present.",
    brief=(
        "Someone has altered a tracked file but not yet staged the change. "
        "Reveal the difference between the working tree and the last recorded chapter."
    ),
    hints=(
        "`git status` names changed files. `git diff` shows the content of the change.",
        "Try `git diff` with no arguments.",
    ),
    allowed=_ALLOWED,
    check=_check_spot_the_diff,
    xp=100,
    level=2,
    seed=_seed_dirty_working_tree,
)


def _check_inspect_a_commit(sandbox: Path, state: SessionState) -> CheckResult:
    # Build a set of all non-HEAD commit shas
    head = run_git(["git", "rev-parse", "HEAD"], cwd=sandbox, capture=True).stdout.strip()
    log = run_git(
        ["git", "log", "--pretty=%H"], cwd=sandbox, capture=True
    ).stdout.splitlines()
    other_shas = {s for s in log if s != head}

    for argv in state.all_argv:
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "show":
            arg = argv[2]
            # Accept any prefix that resolves in this repo
            try:
                resolved = run_git(
                    ["git", "rev-parse", "--verify", arg + "^{commit}"],
                    cwd=sandbox,
                    capture=True,
                ).stdout.strip()
            except Exception:
                continue
            if resolved in other_shas:
                return CheckResult(True)
    return CheckResult(
        False,
        "You haven't inspected an older commit yet. Try `git show <hash>`.",
    )


INSPECT_A_COMMIT = Quest(
    slug="inspect-a-commit",
    title="Examine a chapter from the past.",
    brief=(
        "Every commit has a unique hash. Find an older commit (not the most "
        "recent) and read it with `git show`."
    ),
    hints=(
        "`git log --oneline` gives you short hashes you can copy.",
        "`git show <hash>` prints the commit and its full diff.",
    ),
    allowed=_ALLOWED,
    check=_check_inspect_a_commit,
    xp=100,
    level=2,
    seed=_seed_five_commits,
)
```

- [ ] **Step 4: Register Level 2**

Update `gameofgit/quests/__init__.py`:

```python
from collections.abc import Iterable

from gameofgit.engine.quest import Quest
from gameofgit.quests.level1 import (
    FIRST_COMMIT,
    INIT_REPO,
    MEANINGFUL_MESSAGE,
    STAGE_A_FILE,
)
from gameofgit.quests.level2 import (
    INSPECT_A_COMMIT,
    READ_THE_LOG,
    SPOT_THE_DIFF,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)
_LEVEL2 = (READ_THE_LOG, SPOT_THE_DIFF, INSPECT_A_COMMIT)


def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2


__all__ = ["all_quests"]
```

- [ ] **Step 5: Run all tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level2.py gameofgit/quests/__init__.py tests/quests/test_level2.py
git commit -m "quests(level2): TIME TRAVELER — log, diff, show

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: Level 3 — BRANCH MASTER

**Files:**
- Create: `gameofgit/quests/level3.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level3.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level3.py`:

```python
"""Level 3 — BRANCH MASTER quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level3 import (
    LIST_THE_BRANCHES,
    MAKE_A_BRANCH,
    SWITCH_AND_RETURN,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_list_the_branches_pass_after_branch(tmp_path):
    LIST_THE_BRANCHES.seed(tmp_path)
    assert LIST_THE_BRANCHES.check(tmp_path, _blank()).passed is False
    state = SessionState(last_argv=("git", "branch"), all_argv=[("git", "branch")])
    assert LIST_THE_BRANCHES.check(tmp_path, state).passed is True


def test_make_a_branch_pass_after_creating_one(tmp_path):
    MAKE_A_BRANCH.seed(tmp_path)
    assert MAKE_A_BRANCH.check(tmp_path, _blank()).passed is False
    run_git(["git", "branch", "kingsguard"], cwd=tmp_path)
    assert MAKE_A_BRANCH.check(tmp_path, _blank()).passed is True


def test_switch_and_return_pass_after_round_trip(tmp_path):
    SWITCH_AND_RETURN.seed(tmp_path)
    assert SWITCH_AND_RETURN.check(tmp_path, _blank()).passed is False
    run_git(["git", "checkout", "dragonstone"], cwd=tmp_path)
    run_git(["git", "checkout", "main"], cwd=tmp_path)
    assert SWITCH_AND_RETURN.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level3.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `level3.py`**

Create `gameofgit/quests/level3.py`:

```python
"""Level 3 — BRANCH MASTER. Branches, checkout, switch."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_file,
    head_exists,
    run_git,
    set_identity,
)

_ALLOWED = frozenset({"branch", "checkout", "switch", "log", "status"})


def _seed_three_branches(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "realm.txt", "Westeros\n", "found the realm")
    run_git(["git", "branch", "dragonstone"], cwd=sandbox)
    run_git(["git", "branch", "winterfell"], cwd=sandbox)


def _count_branches(sandbox: Path) -> int:
    out = run_git(["git", "branch", "--list"], cwd=sandbox, capture=True).stdout
    return len([line for line in out.splitlines() if line.strip()])


def _check_list_the_branches(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        # `git branch` with no further args is the "list" form
        if argv == ("git", "branch"):
            return CheckResult(True)
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "branch" and \
                len(argv) == 3 and argv[2] in ("-l", "--list"):
            return CheckResult(True)
    return CheckResult(False, "Try `git branch` to see what exists.")


LIST_THE_BRANCHES = Quest(
    slug="list-the-branches",
    title="Count the banners.",
    brief=(
        "Three houses have pledged their banners to this repo. "
        "Ask git to show you which branches exist."
    ),
    hints=(
        "`git branch` with no extra arguments prints the list.",
        "The current branch is marked with a `*`.",
    ),
    allowed=_ALLOWED,
    check=_check_list_the_branches,
    xp=75,
    level=3,
    seed=_seed_three_branches,
)


def _check_make_a_branch(sandbox: Path, _state: SessionState) -> CheckResult:
    if _count_branches(sandbox) >= 4:
        return CheckResult(True)
    return CheckResult(False, "Still only three branches — raise another banner.")


MAKE_A_BRANCH = Quest(
    slug="make-a-branch",
    title="Raise a new banner.",
    brief=(
        "Create a fourth branch under any name you choose. The house of your "
        "making."
    ),
    hints=(
        "`git branch <name>` creates a branch without switching to it.",
        "`git checkout -b <name>` or `git switch -c <name>` creates and switches.",
    ),
    allowed=_ALLOWED,
    check=_check_make_a_branch,
    xp=100,
    level=3,
    seed=_seed_three_branches,
)


def _seed_main_and_dragonstone(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "kingsroad.txt", "stone\n", "pave the road")
    run_git(["git", "branch", "dragonstone"], cwd=sandbox)


def _current_branch(sandbox: Path) -> str:
    return run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=sandbox,
        capture=True,
    ).stdout.strip()


def _reflog_mentions(sandbox: Path, name: str) -> bool:
    out = run_git(["git", "reflog"], cwd=sandbox, capture=True).stdout
    return name in out


def _check_switch_and_return(sandbox: Path, _state: SessionState) -> CheckResult:
    if not head_exists(sandbox):
        return CheckResult(False, "No HEAD yet.")
    if _current_branch(sandbox) != "main":
        return CheckResult(False, "You're not on main. Come home.")
    if not _reflog_mentions(sandbox, "dragonstone"):
        return CheckResult(False, "You haven't visited Dragonstone yet.")
    return CheckResult(True)


SWITCH_AND_RETURN = Quest(
    slug="switch-and-return",
    title="Ride to Dragonstone — and return to your keep.",
    brief=(
        "Switch from `main` to `dragonstone`, then switch back to `main`. "
        "The reflog must show that you made the journey."
    ),
    hints=(
        "`git checkout dragonstone` or `git switch dragonstone` to go there.",
        "`git checkout main` (or `git switch main`) to return.",
    ),
    allowed=_ALLOWED,
    check=_check_switch_and_return,
    xp=125,
    level=3,
    seed=_seed_main_and_dragonstone,
)
```

- [ ] **Step 4: Register Level 3**

In `gameofgit/quests/__init__.py`:

```python
from gameofgit.quests.level3 import (
    LIST_THE_BRANCHES,
    MAKE_A_BRANCH,
    SWITCH_AND_RETURN,
)
# ...
_LEVEL3 = (LIST_THE_BRANCHES, MAKE_A_BRANCH, SWITCH_AND_RETURN)
# ...
def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2 + _LEVEL3
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level3.py gameofgit/quests/__init__.py tests/quests/test_level3.py
git commit -m "quests(level3): BRANCH MASTER — list, create, switch-and-return

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: Level 4 — MERGE WARRIOR (boss)

**Files:**
- Create: `gameofgit/quests/level4.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level4.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level4.py`:

```python
"""Level 4 — MERGE WARRIOR quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity
from gameofgit.quests.level4 import (
    CHERRY_PICK_ONE,
    FAST_FORWARD_MERGE,
    REBASE_A_BRANCH,
    RESOLVE_THE_CONFLICT,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_fast_forward_merge_pass(tmp_path):
    FAST_FORWARD_MERGE.seed(tmp_path)
    assert FAST_FORWARD_MERGE.check(tmp_path, _blank()).passed is False
    run_git(["git", "merge", "feature", "-q"], cwd=tmp_path)
    assert FAST_FORWARD_MERGE.check(tmp_path, _blank()).passed is True


def test_rebase_a_branch_pass(tmp_path):
    REBASE_A_BRANCH.seed(tmp_path)
    assert REBASE_A_BRANCH.check(tmp_path, _blank()).passed is False
    run_git(["git", "checkout", "feature", "-q"], cwd=tmp_path)
    run_git(["git", "rebase", "main", "-q"], cwd=tmp_path)
    assert REBASE_A_BRANCH.check(tmp_path, _blank()).passed is True


def test_cherry_pick_one_pass(tmp_path):
    CHERRY_PICK_ONE.seed(tmp_path)
    assert CHERRY_PICK_ONE.check(tmp_path, _blank()).passed is False
    middle_sha = run_git(
        ["git", "log", "experiment", "--pretty=%H"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[1]
    run_git(["git", "cherry-pick", middle_sha, "-q"], cwd=tmp_path)
    assert CHERRY_PICK_ONE.check(tmp_path, _blank()).passed is True


def test_resolve_the_conflict_pass(tmp_path):
    RESOLVE_THE_CONFLICT.seed(tmp_path)
    assert RESOLVE_THE_CONFLICT.check(tmp_path, _blank()).passed is False
    # Trigger the conflict
    merge = run_git(
        ["git", "merge", "rebellion"], cwd=tmp_path, capture=True, check=False
    )
    assert merge.returncode != 0  # conflict expected
    # Resolve: pick our content, remove markers
    (tmp_path / "throne.txt").write_text("The Iron Throne stands resolute.\n")
    run_git(["git", "add", "throne.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "--no-edit"], cwd=tmp_path)
    assert RESOLVE_THE_CONFLICT.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level4.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `level4.py`**

Create `gameofgit/quests/level4.py`:

```python
"""Level 4 — MERGE WARRIOR. Boss-fight level. Merges, rebases, cherry-picks,
and the sacred art of resolving conflicts.
"""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_file,
    run_git,
    set_identity,
    working_tree_clean,
)

_ALLOWED = frozenset({
    "merge", "rebase", "cherry-pick", "branch", "checkout", "switch",
    "status", "log", "add", "commit", "diff",
})


# -------------------- fast-forward merge --------------------

def _seed_ff_branches(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "chronicle.txt", "chapter 1\n", "the realm")
    run_git(["git", "checkout", "-q", "-b", "feature"], cwd=sandbox)
    commit_file(sandbox, "chronicle.txt", "chapter 1\nchapter 2\n", "added ch2")
    commit_file(sandbox, "chronicle.txt", "chapter 1\nchapter 2\nchapter 3\n", "added ch3")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_fast_forward_merge(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "You must be on main to take the banners home.")
    main_sha = run_git(["git", "rev-parse", "main"], cwd=sandbox, capture=True).stdout.strip()
    feature_sha = run_git(
        ["git", "rev-parse", "feature"], cwd=sandbox, capture=True
    ).stdout.strip()
    if main_sha == feature_sha:
        return CheckResult(True)
    return CheckResult(False, "`main` has not caught up to `feature` yet.")


FAST_FORWARD_MERGE = Quest(
    slug="fast-forward-merge",
    title="Bring the banner home.",
    brief=(
        "The `feature` branch has two commits `main` hasn't seen yet, and "
        "`main` has no commits of its own since they diverged. Merge cleanly — "
        "no new commit needed."
    ),
    hints=(
        "Make sure you're on `main` before merging.",
        "`git merge feature` will fast-forward when there's no divergence.",
    ),
    allowed=_ALLOWED,
    check=_check_fast_forward_merge,
    xp=150,
    level=4,
    seed=_seed_ff_branches,
)


# -------------------- rebase --------------------

def _seed_rebase_repo(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "base.txt", "base\n", "base")
    run_git(["git", "checkout", "-q", "-b", "feature"], cwd=sandbox)
    commit_file(sandbox, "feature.txt", "f1\n", "feature: f1")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)
    commit_file(sandbox, "main.txt", "m1\n", "main: m1")
    commit_file(sandbox, "main.txt", "m1\nm2\n", "main: m2")


def _check_rebase_a_branch(sandbox: Path, _state: SessionState) -> CheckResult:
    # main must be ancestor of feature
    r = run_git(
        ["git", "merge-base", "--is-ancestor", "main", "feature"],
        cwd=sandbox,
        check=False,
    )
    if r.returncode != 0:
        return CheckResult(False, "`main` is not yet an ancestor of `feature`.")
    # No merge commits on feature
    out = run_git(
        ["git", "log", "--merges", "main..feature", "--pretty=%H"],
        cwd=sandbox,
        capture=True,
    ).stdout.strip()
    if out:
        return CheckResult(False, "`feature` has merge commits — a true rebase is linear.")
    return CheckResult(True)


REBASE_A_BRANCH = Quest(
    slug="rebase-a-branch",
    title="Rewrite the feature's lineage.",
    brief=(
        "`main` has moved on while `feature` waited. Rebase `feature` onto "
        "the new tip of `main` so its commits descend cleanly from today's main."
    ),
    hints=(
        "Switch to `feature`, then run `git rebase main`.",
        "After rebasing, `git log feature` should show main's commits before feature's.",
    ),
    allowed=_ALLOWED,
    check=_check_rebase_a_branch,
    xp=175,
    level=4,
    seed=_seed_rebase_repo,
)


# -------------------- cherry-pick --------------------

def _seed_experiment(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "realm.txt", "realm\n", "found")
    run_git(["git", "checkout", "-q", "-b", "experiment"], cwd=sandbox)
    commit_file(sandbox, "potion_1.txt", "wolfsbane\n", "exp: first potion")
    commit_file(sandbox, "potion_2.txt", "nightshade\n", "exp: the chosen one")
    commit_file(sandbox, "potion_3.txt", "moonflower\n", "exp: third potion")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_cherry_pick_one(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "You must be on main.")
    # potion_2.txt must exist on main; potion_1 / potion_3 must NOT
    out = run_git(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True
    ).stdout.split()
    has_2 = "potion_2.txt" in out
    has_1 = "potion_1.txt" in out
    has_3 = "potion_3.txt" in out
    if has_2 and not has_1 and not has_3:
        return CheckResult(True)
    return CheckResult(
        False,
        "You need exactly the middle potion on main — not the first or third.",
    )


CHERRY_PICK_ONE = Quest(
    slug="cherry-pick-one",
    title="Pick the chosen one.",
    brief=(
        "The `experiment` branch has three commits. Bring only the middle one "
        "over to `main` — no first, no third."
    ),
    hints=(
        "`git log experiment` shows all three in reverse order. The middle is second from the top.",
        "`git cherry-pick <hash>` copies one commit onto your current branch.",
    ),
    allowed=_ALLOWED,
    check=_check_cherry_pick_one,
    xp=175,
    level=4,
    seed=_seed_experiment,
)


# -------------------- conflict resolution (boss) --------------------

def _seed_conflict_repo(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne is empty.\n", "empty throne")
    run_git(["git", "checkout", "-q", "-b", "rebellion"], cwd=sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne belongs to the rebels.\n", "rebels")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne stands resolute.\n", "loyalist")


def _check_resolve_the_conflict(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "Finish the fight on main.")
    # HEAD must be a merge commit
    parents = run_git(
        ["git", "log", "-1", "--pretty=%P"], cwd=sandbox, capture=True
    ).stdout.split()
    if len(parents) < 2:
        return CheckResult(False, "HEAD is not a merge commit — combine the branches.")
    # throne.txt must not contain conflict markers
    content = (sandbox / "throne.txt").read_text()
    if "<<<<<<<" in content or ">>>>>>>" in content or "=======" in content:
        return CheckResult(False, "Conflict markers remain in throne.txt.")
    if not working_tree_clean(sandbox):
        return CheckResult(False, "Working tree not clean — finish the commit.")
    return CheckResult(True)


RESOLVE_THE_CONFLICT = Quest(
    slug="resolve-the-conflict",
    title="BOSS: Settle the war of the throne.",
    brief=(
        "Both `main` and `rebellion` have rewritten `throne.txt` in ways that "
        "cannot both be true. Merge `rebellion` into `main`, resolve the "
        "conflict by hand (edit the file so no markers remain), stage it, "
        "and commit."
    ),
    hints=(
        "`git merge rebellion` — it will stop at the conflict.",
        "Open `throne.txt`, remove `<<<<<<<` / `=======` / `>>>>>>>` lines, keep the text you want. Then `git add throne.txt` and `git commit`.",
    ),
    allowed=_ALLOWED,
    check=_check_resolve_the_conflict,
    xp=250,
    level=4,
    seed=_seed_conflict_repo,
)
```

- [ ] **Step 4: Register Level 4**

In `gameofgit/quests/__init__.py` add imports and tuple, then update `all_quests()`:

```python
from gameofgit.quests.level4 import (
    CHERRY_PICK_ONE,
    FAST_FORWARD_MERGE,
    REBASE_A_BRANCH,
    RESOLVE_THE_CONFLICT,
)
# ...
_LEVEL4 = (FAST_FORWARD_MERGE, REBASE_A_BRANCH, CHERRY_PICK_ONE, RESOLVE_THE_CONFLICT)
# ...
def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2 + _LEVEL3 + _LEVEL4
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level4.py gameofgit/quests/__init__.py tests/quests/test_level4.py
git commit -m "quests(level4): MERGE WARRIOR — ff-merge, rebase, cherry-pick, conflict boss

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: Level 5 — REMOTE HACKER

**Files:**
- Create: `gameofgit/quests/level5.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level5.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level5.py`:

```python
"""Level 5 — REMOTE HACKER quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity
from gameofgit.quests.level5 import FETCH_THE_NEWS, INSPECT_REMOTES, PUSH_YOUR_WORK


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_inspect_remotes_pass_after_remote_v(tmp_path):
    INSPECT_REMOTES.seed(tmp_path)
    assert INSPECT_REMOTES.check(tmp_path, _blank()).passed is False
    state = SessionState(last_argv=("git", "remote", "-v"), all_argv=[("git", "remote", "-v")])
    assert INSPECT_REMOTES.check(tmp_path, state).passed is True


def test_fetch_the_news_pass_after_fetch(tmp_path):
    FETCH_THE_NEWS.seed(tmp_path)
    assert FETCH_THE_NEWS.check(tmp_path, _blank()).passed is False
    run_git(["git", "fetch", "origin"], cwd=tmp_path)
    assert FETCH_THE_NEWS.check(tmp_path, _blank()).passed is True


def test_push_your_work_pass_after_push(tmp_path):
    PUSH_YOUR_WORK.seed(tmp_path)
    assert PUSH_YOUR_WORK.check(tmp_path, _blank()).passed is False
    run_git(["git", "push", "origin", "main"], cwd=tmp_path)
    assert PUSH_YOUR_WORK.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level5.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `level5.py`**

Create `gameofgit/quests/level5.py`:

```python
"""Level 5 — REMOTE HACKER. Bare-repo origin, fetch, push."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity

_ALLOWED = frozenset({
    "remote", "fetch", "pull", "push", "log", "branch", "status",
})


def _bare_repo_for(sandbox: Path) -> Path:
    """Sibling dir to `sandbox` that serves as origin."""
    return sandbox.parent / (sandbox.name + ".origin.git")


def _seed_with_origin(sandbox: Path) -> None:
    bare = _bare_repo_for(sandbox)
    bare.mkdir(parents=True, exist_ok=True)
    run_git(["git", "init", "--bare", "-q", "-b", "main"], cwd=bare)

    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "readme.txt", "raven post\n", "first raven")
    run_git(["git", "remote", "add", "origin", str(bare)], cwd=sandbox)
    run_git(["git", "push", "-q", "-u", "origin", "main"], cwd=sandbox)


def _seed_remote_ahead(sandbox: Path) -> None:
    """Origin has a commit local doesn't yet have. Player must fetch to learn of it."""
    _seed_with_origin(sandbox)
    bare = _bare_repo_for(sandbox)
    # Spawn a helper clone, add a commit, push back to bare
    helper = sandbox.parent / (sandbox.name + ".helper")
    helper.mkdir(parents=True, exist_ok=True)
    run_git(["git", "clone", "-q", str(bare), "."], cwd=helper)
    set_identity(helper)
    commit_file(helper, "raven2.txt", "second raven\n", "raven from the Wall")
    run_git(["git", "push", "-q", "origin", "main"], cwd=helper)


def _seed_local_ahead(sandbox: Path) -> None:
    """Local is one commit ahead of origin. Player must push."""
    _seed_with_origin(sandbox)
    commit_file(sandbox, "raven_local.txt", "local raven\n", "from the keep")


def _check_inspect_remotes(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "remote":
            return CheckResult(True)
    return CheckResult(False, "Check who your remotes are with `git remote -v`.")


INSPECT_REMOTES = Quest(
    slug="inspect-remotes",
    title="Know the ravens.",
    brief="An `origin` remote is already configured. Ask git to list your remotes and their URLs.",
    hints=(
        "`git remote` alone just prints names. Add `-v` for verbose (URLs too).",
        "Try `git remote -v`.",
    ),
    allowed=_ALLOWED,
    check=_check_inspect_remotes,
    xp=75,
    level=5,
    seed=_seed_with_origin,
)


def _check_fetch_the_news(sandbox: Path, _state: SessionState) -> CheckResult:
    bare = _bare_repo_for(sandbox)
    bare_sha = run_git(
        ["git", "rev-parse", "main"], cwd=bare, capture=True
    ).stdout.strip()
    try:
        origin_ref = run_git(
            ["git", "rev-parse", "refs/remotes/origin/main"],
            cwd=sandbox,
            capture=True,
        ).stdout.strip()
    except Exception:
        return CheckResult(False, "origin/main isn't known yet — try `git fetch`.")
    if origin_ref == bare_sha:
        return CheckResult(True)
    return CheckResult(False, "origin/main is still out of date — `git fetch` to catch up.")


FETCH_THE_NEWS = Quest(
    slug="fetch-the-news",
    title="Gather the ravens from the Wall.",
    brief=(
        "A scout at the Wall has posted a new commit to `origin`. "
        "Pull the news down — without touching your working branch."
    ),
    hints=(
        "`git fetch` updates `origin/main` without merging.",
        "After fetching, `git log origin/main` shows what the remote has.",
    ),
    allowed=_ALLOWED,
    check=_check_fetch_the_news,
    xp=125,
    level=5,
    seed=_seed_remote_ahead,
)


def _check_push_your_work(sandbox: Path, _state: SessionState) -> CheckResult:
    bare = _bare_repo_for(sandbox)
    bare_sha = run_git(
        ["git", "rev-parse", "main"], cwd=bare, capture=True
    ).stdout.strip()
    local_sha = run_git(
        ["git", "rev-parse", "main"], cwd=sandbox, capture=True
    ).stdout.strip()
    if local_sha == bare_sha:
        return CheckResult(True)
    return CheckResult(False, "Origin's main still trails your local — push it.")


PUSH_YOUR_WORK = Quest(
    slug="push-your-work",
    title="Send your decree across the realm.",
    brief=(
        "You have one local commit that `origin` hasn't yet seen. "
        "Push it so the whole realm shares the same history."
    ),
    hints=(
        "`git push` with no args pushes the current branch to its tracked upstream.",
        "`git push origin main` is the explicit form.",
    ),
    allowed=_ALLOWED,
    check=_check_push_your_work,
    xp=150,
    level=5,
    seed=_seed_local_ahead,
)
```

- [ ] **Step 4: Register Level 5**

In `gameofgit/quests/__init__.py`:

```python
from gameofgit.quests.level5 import FETCH_THE_NEWS, INSPECT_REMOTES, PUSH_YOUR_WORK
_LEVEL5 = (INSPECT_REMOTES, FETCH_THE_NEWS, PUSH_YOUR_WORK)
# update all_quests() to include _LEVEL5
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level5.py gameofgit/quests/__init__.py tests/quests/test_level5.py
git commit -m "quests(level5): REMOTE HACKER — remote -v, fetch, push via local bare repo

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 17: Level 6 — DAMAGE CONTROL

**Files:**
- Create: `gameofgit/quests/level6.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level6.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level6.py`:

```python
"""Level 6 — DAMAGE CONTROL quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level6 import (
    REVERT_A_PUBLIC_COMMIT,
    UNDO_A_COMMIT_KEEP_WORK,
    UNSTAGE_A_FILE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_unstage_a_file_pass(tmp_path):
    UNSTAGE_A_FILE.seed(tmp_path)
    assert UNSTAGE_A_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "restore", "--staged", "oath.txt"], cwd=tmp_path)
    assert UNSTAGE_A_FILE.check(tmp_path, _blank()).passed is True


def test_undo_a_commit_keep_work_pass(tmp_path):
    UNDO_A_COMMIT_KEEP_WORK.seed(tmp_path)
    assert UNDO_A_COMMIT_KEEP_WORK.check(tmp_path, _blank()).passed is False
    run_git(["git", "reset", "--soft", "HEAD~1"], cwd=tmp_path)
    assert UNDO_A_COMMIT_KEEP_WORK.check(tmp_path, _blank()).passed is True


def test_revert_a_public_commit_pass(tmp_path):
    REVERT_A_PUBLIC_COMMIT.seed(tmp_path)
    assert REVERT_A_PUBLIC_COMMIT.check(tmp_path, _blank()).passed is False
    bad_sha = run_git(
        ["git", "log", "--pretty=%H"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[1]
    run_git(["git", "revert", "--no-edit", "-q", bad_sha], cwd=tmp_path)
    assert REVERT_A_PUBLIC_COMMIT.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level6.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `level6.py`**

Create `gameofgit/quests/level6.py`:

```python
"""Level 6 — DAMAGE CONTROL. reset, revert, restore."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_count,
    commit_file,
    run_git,
    set_identity,
)

_ALLOWED = frozenset({"reset", "revert", "restore", "log", "status", "add", "commit", "diff"})


def _seed_with_staged_oath(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "keep.txt", "keep\n", "found keep")
    (sandbox / "oath.txt").write_text("I pledge.\n")
    run_git(["git", "add", "oath.txt"], cwd=sandbox)


def _check_unstage_a_file(sandbox: Path, _state: SessionState) -> CheckResult:
    staged = run_git(
        ["git", "diff", "--cached", "--name-only"], cwd=sandbox, capture=True
    ).stdout.strip()
    if not staged:
        return CheckResult(True)
    return CheckResult(False, f"Still staged: {staged}. Unstage it.")


UNSTAGE_A_FILE = Quest(
    slug="unstage-a-file",
    title="Take back an oath unspoken.",
    brief=(
        "`oath.txt` is already staged, but you're not ready to commit it. "
        "Unstage the file — keep the content in your working tree."
    ),
    hints=(
        "`git restore --staged <file>` unstages without touching the working tree.",
        "`git reset HEAD <file>` is the older form of the same thing.",
    ),
    allowed=_ALLOWED,
    check=_check_unstage_a_file,
    xp=100,
    level=6,
    seed=_seed_with_staged_oath,
)


def _seed_bad_commit_on_top(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "plan.txt", "plan a\n", "plan a")
    commit_file(sandbox, "plan.txt", "plan a\nplan b\n", "plan b")
    commit_file(sandbox, "plan.txt", "plan a\nplan b\noops\n", "BAD: premature")


def _check_undo_a_commit_keep_work(sandbox: Path, _state: SessionState) -> CheckResult:
    if commit_count(sandbox) != 2:
        return CheckResult(
            False,
            f"You need exactly 2 commits (currently {commit_count(sandbox)}).",
        )
    # plan.txt in the working tree should still have 'oops' (soft reset)
    content = (sandbox / "plan.txt").read_text()
    if "oops" not in content:
        return CheckResult(False, "Your working tree lost the bad changes — use --soft or --mixed, not --hard.")
    return CheckResult(True)


UNDO_A_COMMIT_KEEP_WORK = Quest(
    slug="undo-a-commit-keep-work",
    title="Swallow your words — but keep the parchment.",
    brief=(
        "The last commit was made in haste. Undo the commit, but keep the "
        "changes in your working tree so you can rewrite them properly later."
    ),
    hints=(
        "`git reset --soft HEAD~1` keeps the changes staged.",
        "`git reset --mixed HEAD~1` (the default) keeps them unstaged.",
    ),
    allowed=_ALLOWED,
    check=_check_undo_a_commit_keep_work,
    xp=125,
    level=6,
    seed=_seed_bad_commit_on_top,
)


def _seed_bug_in_history(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "a.txt", "a\n", "a")
    commit_file(sandbox, "bug.txt", "DANGER\n", "BAD: added bug.txt")
    commit_file(sandbox, "c.txt", "c\n", "c")


def _check_revert_a_public_commit(sandbox: Path, _state: SessionState) -> CheckResult:
    if commit_count(sandbox) != 4:
        return CheckResult(
            False,
            f"Expected 4 commits after a revert (have {commit_count(sandbox)}). "
            "Use `git revert`, not `reset`.",
        )
    tree = run_git(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True
    ).stdout.split()
    if "bug.txt" in tree:
        return CheckResult(False, "bug.txt is still in the tree — the revert didn't remove it.")
    return CheckResult(True)


REVERT_A_PUBLIC_COMMIT = Quest(
    slug="revert-a-public-commit",
    title="Undo a chapter that's already public.",
    brief=(
        "There are 3 commits. The middle one introduced `bug.txt` — a "
        "mistake. You can't erase it (others may have the history), so "
        "create a NEW commit that undoes it."
    ),
    hints=(
        "`git revert <hash>` creates a new commit that inverts the target commit.",
        "Use `--no-edit` to accept the default revert message.",
    ),
    allowed=_ALLOWED,
    check=_check_revert_a_public_commit,
    xp=150,
    level=6,
    seed=_seed_bug_in_history,
)
```

- [ ] **Step 4: Register Level 6**

In `gameofgit/quests/__init__.py`:

```python
from gameofgit.quests.level6 import (
    REVERT_A_PUBLIC_COMMIT,
    UNDO_A_COMMIT_KEEP_WORK,
    UNSTAGE_A_FILE,
)
_LEVEL6 = (UNSTAGE_A_FILE, UNDO_A_COMMIT_KEEP_WORK, REVERT_A_PUBLIC_COMMIT)
# update all_quests()
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level6.py gameofgit/quests/__init__.py tests/quests/test_level6.py
git commit -m "quests(level6): DAMAGE CONTROL — restore, reset --soft, revert

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: Level 7 — STEALTH MODE

**Files:**
- Create: `gameofgit/quests/level7.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level7.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level7.py`:

```python
"""Level 7 — STEALTH MODE quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level7 import (
    LIST_THE_STASHES,
    POP_A_STASH,
    STASH_YOUR_CHANGES,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_stash_your_changes_pass(tmp_path):
    STASH_YOUR_CHANGES.seed(tmp_path)
    assert STASH_YOUR_CHANGES.check(tmp_path, _blank()).passed is False
    run_git(["git", "stash"], cwd=tmp_path)
    assert STASH_YOUR_CHANGES.check(tmp_path, _blank()).passed is True


def test_list_the_stashes_pass(tmp_path):
    LIST_THE_STASHES.seed(tmp_path)
    assert LIST_THE_STASHES.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "stash", "list"),
        all_argv=[("git", "stash", "list")],
    )
    assert LIST_THE_STASHES.check(tmp_path, state).passed is True


def test_pop_a_stash_pass(tmp_path):
    POP_A_STASH.seed(tmp_path)
    assert POP_A_STASH.check(tmp_path, _blank()).passed is False
    run_git(["git", "stash", "pop"], cwd=tmp_path)
    assert POP_A_STASH.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level7.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `level7.py`**

Create `gameofgit/quests/level7.py`:

```python
"""Level 7 — STEALTH MODE. Stash, list, pop."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_file,
    run_git,
    set_identity,
    working_tree_clean,
)

_ALLOWED = frozenset({"stash", "status", "log", "diff"})


def _stash_count(sandbox: Path) -> int:
    out = run_git(["git", "stash", "list"], cwd=sandbox, capture=True).stdout
    return len([line for line in out.splitlines() if line.strip()])


def _seed_dirty_tree(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "scroll.txt", "a\n", "first scroll")
    (sandbox / "scroll.txt").write_text("a\nb\n")


def _check_stash_your_changes(sandbox: Path, _state: SessionState) -> CheckResult:
    if not working_tree_clean(sandbox):
        return CheckResult(False, "Working tree still dirty — stash the changes.")
    if _stash_count(sandbox) < 1:
        return CheckResult(False, "No stash exists — `git stash` to hide your work.")
    return CheckResult(True)


STASH_YOUR_CHANGES = Quest(
    slug="stash-your-changes",
    title="Melt into the shadows.",
    brief=(
        "You have unsaved changes to a tracked file, but someone needs you "
        "to look clean for a moment. Hide your changes without committing "
        "them."
    ),
    hints=(
        "`git stash` saves your modifications to a hidden stack.",
        "After stashing, `git status` should show a clean tree.",
    ),
    allowed=_ALLOWED,
    check=_check_stash_your_changes,
    xp=100,
    level=7,
    seed=_seed_dirty_tree,
)


def _seed_one_stash_clean_tree(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "scroll.txt", "a\n", "first scroll")
    (sandbox / "scroll.txt").write_text("a\nb\n")
    run_git(["git", "stash"], cwd=sandbox)


def _check_list_the_stashes(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 3 and argv[:3] == ("git", "stash", "list"):
            return CheckResult(True)
    return CheckResult(False, "`git stash list` to see what's hidden.")


LIST_THE_STASHES = Quest(
    slug="list-the-stashes",
    title="Count your secret scrolls.",
    brief=(
        "You've stashed changes before. Ask git to list what's still hidden "
        "in the shadow library."
    ),
    hints=(
        "`git stash list` prints every stash with an index and short message.",
        "Each stash is `stash@{0}`, `stash@{1}`, and so on.",
    ),
    allowed=_ALLOWED,
    check=_check_list_the_stashes,
    xp=75,
    level=7,
    seed=_seed_one_stash_clean_tree,
)


def _check_pop_a_stash(sandbox: Path, _state: SessionState) -> CheckResult:
    if _stash_count(sandbox) != 0:
        return CheckResult(False, "The stash is still there — pop it.")
    if working_tree_clean(sandbox):
        return CheckResult(False, "Working tree clean — the stash's changes aren't back yet.")
    return CheckResult(True)


POP_A_STASH = Quest(
    slug="pop-a-stash",
    title="Return the stolen memory.",
    brief=(
        "Your stash contains changes you hid earlier. Bring them back to "
        "your working tree AND remove them from the stash in one move."
    ),
    hints=(
        "`git stash pop` applies the most recent stash and drops it.",
        "If you wanted to apply without dropping, you'd use `git stash apply`.",
    ),
    allowed=_ALLOWED,
    check=_check_pop_a_stash,
    xp=150,
    level=7,
    seed=_seed_one_stash_clean_tree,
)
```

- [ ] **Step 4: Register Level 7**

```python
from gameofgit.quests.level7 import (
    LIST_THE_STASHES,
    POP_A_STASH,
    STASH_YOUR_CHANGES,
)
_LEVEL7 = (STASH_YOUR_CHANGES, LIST_THE_STASHES, POP_A_STASH)
# update all_quests()
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level7.py gameofgit/quests/__init__.py tests/quests/test_level7.py
git commit -m "quests(level7): STEALTH MODE — stash, list, pop

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 19: Level 8 — CLEANUP CREW

**Files:**
- Create: `gameofgit/quests/level8.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level8.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level8.py`:

```python
"""Level 8 — CLEANUP CREW quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level8 import (
    AMEND_YOUR_LAST_COMMIT,
    REMOVE_A_TRACKED_FILE,
    RENAME_A_FILE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_remove_a_tracked_file_pass(tmp_path):
    REMOVE_A_TRACKED_FILE.seed(tmp_path)
    assert REMOVE_A_TRACKED_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "rm", "scroll.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "-m", "drop scroll"], cwd=tmp_path)
    assert REMOVE_A_TRACKED_FILE.check(tmp_path, _blank()).passed is True


def test_rename_a_file_pass(tmp_path):
    RENAME_A_FILE.seed(tmp_path)
    assert RENAME_A_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "mv", "oldname.txt", "newname.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "-m", "rename"], cwd=tmp_path)
    assert RENAME_A_FILE.check(tmp_path, _blank()).passed is True


def test_amend_your_last_commit_pass(tmp_path):
    AMEND_YOUR_LAST_COMMIT.seed(tmp_path)
    assert AMEND_YOUR_LAST_COMMIT.check(tmp_path, _blank()).passed is False
    run_git(["git", "commit", "--amend", "-q", "-m", "Properly describe the work"], cwd=tmp_path)
    assert AMEND_YOUR_LAST_COMMIT.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level8.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `level8.py`**

Create `gameofgit/quests/level8.py`:

```python
"""Level 8 — CLEANUP CREW. rm, mv, commit --amend."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_file,
    head_message,
    run_git,
    set_identity,
    working_tree_clean,
)

_ALLOWED = frozenset({"clean", "rm", "mv", "commit", "add", "status", "log"})


def _seed_tracked_file(sandbox: Path, name: str = "scroll.txt") -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, name, "a\n", f"add {name}")


def _check_remove_a_tracked_file(sandbox: Path, _state: SessionState) -> CheckResult:
    tree = run_git(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True
    ).stdout.split()
    if "scroll.txt" in tree:
        return CheckResult(False, "scroll.txt still tracked in HEAD.")
    if not working_tree_clean(sandbox):
        return CheckResult(False, "Working tree not clean — finish the commit.")
    return CheckResult(True)


REMOVE_A_TRACKED_FILE = Quest(
    slug="remove-a-tracked-file",
    title="Burn a scroll.",
    brief=(
        "`scroll.txt` is tracked and committed. Remove it from the repository "
        "and record the deletion as a commit."
    ),
    hints=(
        "`git rm scroll.txt` removes it from the working tree AND stages the deletion.",
        "Then `git commit -m \"drop scroll\"` to record it.",
    ),
    allowed=_ALLOWED,
    check=_check_remove_a_tracked_file,
    xp=100,
    level=8,
    seed=lambda p: _seed_tracked_file(p, "scroll.txt"),
)


def _seed_for_rename(sandbox: Path) -> None:
    _seed_tracked_file(sandbox, "oldname.txt")


def _check_rename_a_file(sandbox: Path, _state: SessionState) -> CheckResult:
    tree = run_git(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True
    ).stdout.split()
    if "oldname.txt" in tree:
        return CheckResult(False, "oldname.txt is still tracked.")
    if "newname.txt" not in tree:
        return CheckResult(False, "newname.txt isn't in the tree yet.")
    if not working_tree_clean(sandbox):
        return CheckResult(False, "Working tree not clean — finish the commit.")
    return CheckResult(True)


RENAME_A_FILE = Quest(
    slug="rename-a-file",
    title="Re-scroll under a new title.",
    brief=(
        "`oldname.txt` deserves a better name. Rename it to `newname.txt` "
        "and record the rename."
    ),
    hints=(
        "`git mv oldname.txt newname.txt` renames AND stages in one step.",
        "Then `git commit` to record the change.",
    ),
    allowed=_ALLOWED,
    check=_check_rename_a_file,
    xp=100,
    level=8,
    seed=_seed_for_rename,
)


def _seed_wip_commit(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    # first commit
    commit_file(sandbox, "work.txt", "in progress\n", "wip")


def _check_amend_your_last_commit(sandbox: Path, _state: SessionState) -> CheckResult:
    msg = head_message(sandbox)
    if msg == "wip" or len(msg) < 10:
        return CheckResult(
            False,
            f'Message is still "{msg}" — amend with something ≥ 10 chars.',
        )
    return CheckResult(True)


AMEND_YOUR_LAST_COMMIT = Quest(
    slug="amend-your-last-commit",
    title="Speak more clearly.",
    brief=(
        "Your last commit has a useless message (`wip`). Rewrite that message "
        "to something at least 10 characters long that actually describes the work."
    ),
    hints=(
        "`git commit --amend -m \"<new message>\"` replaces the last commit's message.",
        "The tree stays the same; only the message changes.",
    ),
    allowed=_ALLOWED,
    check=_check_amend_your_last_commit,
    xp=150,
    level=8,
    seed=_seed_wip_commit,
)
```

- [ ] **Step 4: Register Level 8**

```python
from gameofgit.quests.level8 import (
    AMEND_YOUR_LAST_COMMIT,
    REMOVE_A_TRACKED_FILE,
    RENAME_A_FILE,
)
_LEVEL8 = (REMOVE_A_TRACKED_FILE, RENAME_A_FILE, AMEND_YOUR_LAST_COMMIT)
# update all_quests()
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level8.py gameofgit/quests/__init__.py tests/quests/test_level8.py
git commit -m "quests(level8): CLEANUP CREW — rm, mv, commit --amend

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 20: Level 9 — CONFIG GOD

**Files:**
- Create: `gameofgit/quests/level9.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level9.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level9.py`:

```python
"""Level 9 — CONFIG GOD quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level9 import LIST_THE_CONFIG, SET_YOUR_EMAIL, SET_YOUR_NAME


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_set_your_name_pass(tmp_path):
    SET_YOUR_NAME.seed(tmp_path)
    assert SET_YOUR_NAME.check(tmp_path, _blank()).passed is False
    run_git(["git", "config", "user.name", "Robb Stark"], cwd=tmp_path)
    assert SET_YOUR_NAME.check(tmp_path, _blank()).passed is True


def test_set_your_email_pass(tmp_path):
    SET_YOUR_EMAIL.seed(tmp_path)
    assert SET_YOUR_EMAIL.check(tmp_path, _blank()).passed is False
    run_git(["git", "config", "user.email", "robb@winterfell.north"], cwd=tmp_path)
    assert SET_YOUR_EMAIL.check(tmp_path, _blank()).passed is True


def test_list_the_config_pass(tmp_path):
    LIST_THE_CONFIG.seed(tmp_path)
    assert LIST_THE_CONFIG.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "config", "--list"),
        all_argv=[("git", "config", "--list")],
    )
    assert LIST_THE_CONFIG.check(tmp_path, state).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level9.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `level9.py`**

Create `gameofgit/quests/level9.py`:

```python
"""Level 9 — CONFIG GOD. user.name, user.email, --list."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import run_git

_ALLOWED = frozenset({"config", "status"})

_SEED_NAME = "Anon"
_SEED_EMAIL = "seed@gameofgit.local"


def _seed_with_default_identity(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    run_git(["git", "config", "user.name", _SEED_NAME], cwd=sandbox)
    run_git(["git", "config", "user.email", _SEED_EMAIL], cwd=sandbox)


def _config_value(sandbox: Path, key: str) -> str:
    return run_git(
        ["git", "config", key], cwd=sandbox, capture=True, check=False
    ).stdout.strip()


def _check_set_your_name(sandbox: Path, _state: SessionState) -> CheckResult:
    name = _config_value(sandbox, "user.name")
    if not name:
        return CheckResult(False, "user.name is empty.")
    if name == _SEED_NAME:
        return CheckResult(False, "Still the default — change user.name.")
    return CheckResult(True)


SET_YOUR_NAME = Quest(
    slug="set-your-name",
    title="Claim your true name.",
    brief=(
        "The repo's current `user.name` is `Anon`. Replace it with your real "
        "name (or whatever name you wish to sign commits with)."
    ),
    hints=(
        "`git config user.name \"Your Name\"`",
        "Add `--global` to set it for all your repositories — but the quest only needs the local config.",
    ),
    allowed=_ALLOWED,
    check=_check_set_your_name,
    xp=50,
    level=9,
    seed=_seed_with_default_identity,
)


def _check_set_your_email(sandbox: Path, _state: SessionState) -> CheckResult:
    email = _config_value(sandbox, "user.email")
    if not email:
        return CheckResult(False, "user.email is empty.")
    if email == _SEED_EMAIL:
        return CheckResult(False, "Still the seeded email — change user.email.")
    if "@" not in email:
        return CheckResult(False, "That doesn't look like an email (no @).")
    return CheckResult(True)


SET_YOUR_EMAIL = Quest(
    slug="set-your-email",
    title="Seal your correspondence.",
    brief=(
        "Set `user.email` to a real email address. Anything with `@` in it "
        "will do — this is a sandbox."
    ),
    hints=(
        "`git config user.email \"you@example.com\"`",
        "Git doesn't verify the address — any `@`-containing string works.",
    ),
    allowed=_ALLOWED,
    check=_check_set_your_email,
    xp=50,
    level=9,
    seed=_seed_with_default_identity,
)


def _check_list_the_config(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "config" and argv[2] in ("--list", "-l"):
            return CheckResult(True)
    return CheckResult(False, "Try `git config --list`.")


LIST_THE_CONFIG = Quest(
    slug="list-the-config",
    title="Read the laws of your realm.",
    brief="Ask git to print every configured setting it can see, from every level.",
    hints=(
        "`git config --list` prints everything.",
        "Add `--show-origin` to see which file each setting came from.",
    ),
    allowed=_ALLOWED,
    check=_check_list_the_config,
    xp=100,
    level=9,
    seed=_seed_with_default_identity,
)
```

- [ ] **Step 4: Register Level 9**

```python
from gameofgit.quests.level9 import LIST_THE_CONFIG, SET_YOUR_EMAIL, SET_YOUR_NAME
_LEVEL9 = (SET_YOUR_NAME, SET_YOUR_EMAIL, LIST_THE_CONFIG)
# update all_quests()
```

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level9.py gameofgit/quests/__init__.py tests/quests/test_level9.py
git commit -m "quests(level9): CONFIG GOD — user.name, user.email, config --list

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 21: Level 10 — GIT NINJA (final boss)

**Files:**
- Create: `gameofgit/quests/level10.py`
- Modify: `gameofgit/quests/__init__.py`
- Test: `tests/quests/test_level10.py`

- [ ] **Step 1: Write failing tests**

Create `tests/quests/test_level10.py`:

```python
"""Level 10 — GIT NINJA quest tests (final boss)."""
import os
import stat

from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level10 import (
    BLAME_A_LINE,
    FIND_THE_BUG,
    READ_THE_REFLOG,
    TAG_A_RELEASE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_read_the_reflog_pass(tmp_path):
    READ_THE_REFLOG.seed(tmp_path)
    assert READ_THE_REFLOG.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "reflog"),
        all_argv=[("git", "reflog")],
    )
    assert READ_THE_REFLOG.check(tmp_path, state).passed is True


def test_blame_a_line_pass(tmp_path):
    BLAME_A_LINE.seed(tmp_path)
    assert BLAME_A_LINE.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "blame", "chronicle.txt"),
        all_argv=[("git", "blame", "chronicle.txt")],
    )
    assert BLAME_A_LINE.check(tmp_path, state).passed is True


def test_tag_a_release_pass(tmp_path):
    TAG_A_RELEASE.seed(tmp_path)
    assert TAG_A_RELEASE.check(tmp_path, _blank()).passed is False
    run_git(["git", "tag", "-a", "v1.0", "-m", "first release"], cwd=tmp_path)
    assert TAG_A_RELEASE.check(tmp_path, _blank()).passed is True


def test_find_the_bug_pass_via_bisect_run(tmp_path):
    FIND_THE_BUG.seed(tmp_path)
    assert FIND_THE_BUG.check(tmp_path, _blank()).passed is False
    # Kick off bisect, mark endpoints, run
    run_git(["git", "bisect", "start"], cwd=tmp_path)
    run_git(["git", "bisect", "bad", "HEAD"], cwd=tmp_path)
    # good = commit #1 (oldest)
    first = run_git(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=tmp_path, capture=True,
    ).stdout.strip()
    run_git(["git", "bisect", "good", first], cwd=tmp_path)
    run_git(
        ["git", "bisect", "run", "./bisect_test.sh"],
        cwd=tmp_path, check=False,
    )
    assert FIND_THE_BUG.check(tmp_path, _blank()).passed is True
```

- [ ] **Step 2: Observe fail**

Run: `pytest tests/quests/test_level10.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `level10.py`**

Create `gameofgit/quests/level10.py`:

```python
"""Level 10 — GIT NINJA (final boss). reflog, blame, tag, bisect."""
import os
import stat
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity

_ALLOWED = frozenset({
    "reflog", "blame", "tag", "bisect", "log", "show", "status", "checkout",
})


def _seed_reflog_history(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    for i in range(5):
        commit_file(sandbox, f"page_{i}.txt", f"page {i}\n", f"page {i}")
    run_git(["git", "checkout", "-q", "-b", "side"], cwd=sandbox)
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_read_the_reflog(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "reflog":
            return CheckResult(True)
    return CheckResult(False, "Try `git reflog`.")


READ_THE_REFLOG = Quest(
    slug="read-the-reflog",
    title="Consult the book of everything.",
    brief=(
        "The reflog remembers every move HEAD has ever made — even ones "
        "git log won't show you. Call it up."
    ),
    hints=(
        "`git reflog` prints the HEAD history.",
        "Useful for finding commits that seem lost after a reset.",
    ),
    allowed=_ALLOWED,
    check=_check_read_the_reflog,
    xp=125,
    level=10,
    seed=_seed_reflog_history,
)


def _seed_multi_author_chronicle(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    # Simulate "different authors" by changing identity per commit
    for i, name in enumerate(["Stark", "Lannister", "Targaryen", "Baratheon", "Tyrell"]):
        run_git(["git", "config", "user.name", name], cwd=sandbox)
        run_git(
            ["git", "config", "user.email", f"{name.lower()}@westeros"],
            cwd=sandbox,
        )
        existing = ""
        if (sandbox / "chronicle.txt").exists():
            existing = (sandbox / "chronicle.txt").read_text()
        (sandbox / "chronicle.txt").write_text(existing + f"line from {name}\n")
        run_git(["git", "add", "chronicle.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"entry by {name}"], cwd=sandbox)


def _check_blame_a_line(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "blame":
            return CheckResult(True)
    return CheckResult(False, "Try `git blame chronicle.txt`.")


BLAME_A_LINE = Quest(
    slug="blame-a-line",
    title="Name the hand that wrote this.",
    brief=(
        "`chronicle.txt` has five lines, each written by a different author. "
        "Ask git to annotate every line with who last touched it."
    ),
    hints=(
        "`git blame <file>` prints line-by-line attribution.",
        "`git blame` doesn't mean accusation — it's just the name of the tool.",
    ),
    allowed=_ALLOWED,
    check=_check_blame_a_line,
    xp=175,
    level=10,
    seed=_seed_multi_author_chronicle,
)


def _seed_for_tagging(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "release.txt", "alpha\n", "alpha")
    commit_file(sandbox, "release.txt", "alpha\nbeta\n", "beta")


def _check_tag_a_release(sandbox: Path, _state: SessionState) -> CheckResult:
    out = run_git(
        ["git", "for-each-ref", "--format=%(objecttype) %(refname:short)", "refs/tags"],
        cwd=sandbox, capture=True,
    ).stdout.splitlines()
    annotated = [line for line in out if line.startswith("tag ")]
    if not annotated:
        return CheckResult(False, "Create an annotated tag (`git tag -a`).")
    # Check the first tag has a non-empty message
    tag_name = annotated[0].split(" ", 1)[1]
    msg = run_git(
        ["git", "tag", "-n99", "-l", tag_name], cwd=sandbox, capture=True
    ).stdout.strip()
    # Output looks like: "v1.0            the message here"
    parts = msg.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return CheckResult(False, "Your tag has no message — add `-m \"...\"`.")
    return CheckResult(True)


TAG_A_RELEASE = Quest(
    slug="tag-a-release",
    title="Name a version for the bards.",
    brief=(
        "Cut an annotated tag (like `v1.0`) on the current commit, with a "
        "message describing the release. Lightweight tags don't count — "
        "an annotated tag carries a message."
    ),
    hints=(
        "`git tag -a v1.0 -m \"first release\"` creates an annotated tag.",
        "`git tag` (no args) lists every tag.",
    ),
    allowed=_ALLOWED,
    check=_check_tag_a_release,
    xp=200,
    level=10,
    seed=_seed_for_tagging,
)


# -------------------- FINAL BOSS: bisect --------------------

_BISECT_TEST_OK = "#!/bin/sh\nexit 0\n"
_BISECT_TEST_FAIL = "#!/bin/sh\nexit 1\n"

_PLANTED_MARKER = "[PLANTED_BUG]"


def _seed_planted_bug(sandbox: Path) -> None:
    """Seed 15 commits. Commits 1-8 pass ./bisect_test.sh; 9-15 fail.

    Commit #9's message contains the PLANTED_MARKER. The bisect_test.sh
    file itself IS the bug — its content changes at commit #9.
    """
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)

    def _write_test(content: str) -> None:
        path = sandbox / "bisect_test.sh"
        path.write_text(content)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Commits 1..8: test passes
    _write_test(_BISECT_TEST_OK)
    run_git(["git", "add", "bisect_test.sh"], cwd=sandbox)
    run_git(["git", "commit", "-q", "-m", "commit 1: seed"], cwd=sandbox)
    for i in range(2, 9):
        (sandbox / f"chapter_{i}.txt").write_text(f"chapter {i}\n")
        run_git(["git", "add", f"chapter_{i}.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"commit {i}: clean"], cwd=sandbox)

    # Commit 9: the planted bug — test now fails
    _write_test(_BISECT_TEST_FAIL)
    run_git(["git", "add", "bisect_test.sh"], cwd=sandbox)
    run_git(
        ["git", "commit", "-q", "-m", f"commit 9: {_PLANTED_MARKER} broke the test"],
        cwd=sandbox,
    )

    # Commits 10..15: test still fails
    for i in range(10, 16):
        (sandbox / f"chapter_{i}.txt").write_text(f"chapter {i}\n")
        run_git(["git", "add", f"chapter_{i}.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"commit {i}: ignored"], cwd=sandbox)


def _check_find_the_bug(sandbox: Path, _state: SessionState) -> CheckResult:
    bisect_bad = sandbox / ".git" / "refs" / "bisect" / "bad"
    if not bisect_bad.exists():
        return CheckResult(
            False,
            "No bisect/bad ref yet — `git bisect start` and mark endpoints.",
        )
    sha = bisect_bad.read_text().strip()
    msg = run_git(
        ["git", "log", "-1", "--pretty=%s", sha], cwd=sandbox, capture=True
    ).stdout.strip()
    if _PLANTED_MARKER not in msg:
        return CheckResult(
            False,
            f"bisect/bad points at a commit without the {_PLANTED_MARKER} marker.",
        )
    return CheckResult(True)


FIND_THE_BUG = Quest(
    slug="find-the-bug",
    title="FINAL BOSS: Find the commit that broke the realm.",
    brief=(
        "There are 15 commits. One of them broke `./bisect_test.sh` — in early "
        "commits it exits 0, but somewhere along the way it started exiting 1. "
        "Use bisect to find the exact commit that introduced the bug.\n\n"
        "The `./bisect_test.sh` file is executable — `git bisect run` can "
        "automate the whole thing for you."
    ),
    hints=(
        "`git bisect start`, then `git bisect bad HEAD`, then `git bisect good <earliest-sha>` (find it with `git log --max-parents=0 --pretty=%H`).",
        "Then let git drive: `git bisect run ./bisect_test.sh`.",
    ),
    allowed=_ALLOWED,
    check=_check_find_the_bug,
    xp=500,
    level=10,
    seed=_seed_planted_bug,
)
```

- [ ] **Step 4: Register Level 10**

Full `gameofgit/quests/__init__.py`:

```python
from collections.abc import Iterable

from gameofgit.engine.quest import Quest
from gameofgit.quests.level1 import (
    FIRST_COMMIT,
    INIT_REPO,
    MEANINGFUL_MESSAGE,
    STAGE_A_FILE,
)
from gameofgit.quests.level2 import INSPECT_A_COMMIT, READ_THE_LOG, SPOT_THE_DIFF
from gameofgit.quests.level3 import (
    LIST_THE_BRANCHES,
    MAKE_A_BRANCH,
    SWITCH_AND_RETURN,
)
from gameofgit.quests.level4 import (
    CHERRY_PICK_ONE,
    FAST_FORWARD_MERGE,
    REBASE_A_BRANCH,
    RESOLVE_THE_CONFLICT,
)
from gameofgit.quests.level5 import FETCH_THE_NEWS, INSPECT_REMOTES, PUSH_YOUR_WORK
from gameofgit.quests.level6 import (
    REVERT_A_PUBLIC_COMMIT,
    UNDO_A_COMMIT_KEEP_WORK,
    UNSTAGE_A_FILE,
)
from gameofgit.quests.level7 import LIST_THE_STASHES, POP_A_STASH, STASH_YOUR_CHANGES
from gameofgit.quests.level8 import (
    AMEND_YOUR_LAST_COMMIT,
    REMOVE_A_TRACKED_FILE,
    RENAME_A_FILE,
)
from gameofgit.quests.level9 import LIST_THE_CONFIG, SET_YOUR_EMAIL, SET_YOUR_NAME
from gameofgit.quests.level10 import (
    BLAME_A_LINE,
    FIND_THE_BUG,
    READ_THE_REFLOG,
    TAG_A_RELEASE,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)
_LEVEL2 = (READ_THE_LOG, SPOT_THE_DIFF, INSPECT_A_COMMIT)
_LEVEL3 = (LIST_THE_BRANCHES, MAKE_A_BRANCH, SWITCH_AND_RETURN)
_LEVEL4 = (FAST_FORWARD_MERGE, REBASE_A_BRANCH, CHERRY_PICK_ONE, RESOLVE_THE_CONFLICT)
_LEVEL5 = (INSPECT_REMOTES, FETCH_THE_NEWS, PUSH_YOUR_WORK)
_LEVEL6 = (UNSTAGE_A_FILE, UNDO_A_COMMIT_KEEP_WORK, REVERT_A_PUBLIC_COMMIT)
_LEVEL7 = (STASH_YOUR_CHANGES, LIST_THE_STASHES, POP_A_STASH)
_LEVEL8 = (REMOVE_A_TRACKED_FILE, RENAME_A_FILE, AMEND_YOUR_LAST_COMMIT)
_LEVEL9 = (SET_YOUR_NAME, SET_YOUR_EMAIL, LIST_THE_CONFIG)
_LEVEL10 = (READ_THE_REFLOG, BLAME_A_LINE, TAG_A_RELEASE, FIND_THE_BUG)


def all_quests() -> Iterable[Quest]:
    return (
        _LEVEL1 + _LEVEL2 + _LEVEL3 + _LEVEL4 + _LEVEL5 +
        _LEVEL6 + _LEVEL7 + _LEVEL8 + _LEVEL9 + _LEVEL10
    )


__all__ = ["all_quests"]
```

- [ ] **Step 5: Run the full test suite**

Run: `pytest -q`
Expected: PASS (all tests, every level).

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/level10.py gameofgit/quests/__init__.py tests/quests/test_level10.py
git commit -m "quests(level10): GIT NINJA — reflog, blame, tag, and the bisect boss

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 6 — Final integration + documentation

### Task 22: Manual smoke test + README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run the full suite one more time**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 2: Manual smoke test**

```bash
rm -rf ~/.gameofgit/players/*  # clean slate for the test
./venv/bin/python -m gameofgit &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8000/ | grep -q "Enter your name" || echo FAIL_HOME
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"name":"Smoke"}' http://127.0.0.1:8000/api/player | grep -q '"tier":"Junior"' || echo FAIL_PLAYER
kill $SERVER_PID
ls ~/.gameofgit/players/smoke.json || echo FAIL_FILE
```
Expected: no `FAIL_*` output.

- [ ] **Step 3: Update the README status section**

In `README.md`, replace the "## Status" section with:

```markdown
## Status

Playable: **all 10 levels, 33 quests**. Named player profiles with XP-tracked
tier progression: **Junior → Senior → Expert** (Expert requires completing
every quest). Profiles persist to `~/.gameofgit/players/<slug>.json`.

Level roster:
- L1 INIT NOOB · L2 TIME TRAVELER · L3 BRANCH MASTER · L4 MERGE WARRIOR (boss)
- L5 REMOTE HACKER · L6 DAMAGE CONTROL · L7 STEALTH MODE · L8 CLEANUP CREW
- L9 CONFIG GOD · L10 GIT NINJA (final boss: bisect a planted bug)
```

Also update the "### How to play" section by adding at the top:

```markdown
- On the home page, enter a player name before clicking **PLAY**. Your XP and completed quests persist under that name across browser sessions and across devices on the same machine.
- The status bar shows your current **Tier** (Junior / Senior / Expert), total **XP**, and a progress bar to the next tier.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README reflects all-levels + gamification

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 5: Final verification**

Run: `pytest -q && echo "--- ALL GREEN ---"`
Expected: `--- ALL GREEN ---`.

---

## Appendix — File manifest summary

**Created:**
- `gameofgit/player/__init__.py`
- `gameofgit/player/model.py`
- `gameofgit/player/store.py`
- `gameofgit/player/tiers.py`
- `gameofgit/quests/_helpers.py`
- `gameofgit/quests/level2.py` through `level10.py`
- `tests/player/__init__.py`, `test_model.py`, `test_tiers.py`, `test_store.py`
- `tests/quests/__init__.py`, `test_helpers.py`, `test_level2.py` through `test_level10.py`
- `tests/test_web_schemas.py`
- `tests/test_web_player_routes.py`

**Modified:**
- `gameofgit/engine/quest.py` — `Quest.xp/level`, `SessionState`, new `check` signature
- `gameofgit/engine/session.py` — argv tracking
- `gameofgit/quests/level1.py` — xp/level tags, updated check signatures
- `gameofgit/quests/__init__.py` — registers all 10 levels
- `gameofgit/web/games.py` — `Game` carries a `Player`; `new_game(player_slug)`
- `gameofgit/web/schemas.py` — `PlayerView`, xp/level on `QuestView`, xp_awarded on `RunResponse`
- `gameofgit/web/server.py` — player routes; game creation requires `player_slug`
- `gameofgit/web/static/index.html` — name input + PLAY gate
- `gameofgit/web/static/play.html` — status-bar header, level-complete XP line
- `gameofgit/web/static/app.js` — player state, XP accrual UI, tier-up toast, exit summary
- `gameofgit/web/static/style.css` — name-gate + status-bar styling
- `tests/test_web_api.py` — pass `player_slug`, assert xp_awarded
- `tests/test_quest.py` — new Quest shape + SessionState
- `tests/test_session.py` — argv-tracking tests + Quest updates
- `tests/test_level1_quests.py` — SessionState arg in direct `check` calls
- `README.md` — status + How-to-play updates
