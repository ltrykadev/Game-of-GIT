# Quest-Runner Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend engine that takes a Quest, runs real `git` against a throwaway sandbox, and reports quest completion — plus the four Level 1 quests as its first end-to-end exercise.

**Architecture:** One `QuestSession` per quest owns a temp-dir sandbox, a command parser with a per-quest subcommand whitelist, a subprocess executor (real `git`), and a re-runnable predicate that fires after every subprocess invocation. Every `run()` returns an `Outcome` carrying stdout, stderr, exit code, and a `CheckResult`.

**Tech Stack:** Python 3.12, stdlib only for the engine (`subprocess`, `shlex`, `tempfile`, `shutil`, `pathlib`, `dataclasses`). `pytest ≥ 8.0` for tests. No other dependencies.

**Spec:** `docs/superpowers/specs/2026-04-18-quest-runner-core-design.md` (approved, committed).

**Tooling note:** The user explicitly deferred the dependency-manager choice in CLAUDE.md. This plan commits only to a minimal `pyproject.toml` + plain `pip` install into the existing `./venv/`. No lockfile, no editable install, no `uv`/`poetry`. If the user later picks a different manager, the only migration is regenerating the project metadata.

**File map:**

```
pyproject.toml                                                 (Task 1)
gameofgit/__init__.py                                          (Task 1)
gameofgit/engine/__init__.py                                   (Task 7)
gameofgit/engine/quest.py         — Quest, CheckResult         (Task 2)
gameofgit/engine/sandbox.py       — Sandbox                    (Task 3)
gameofgit/engine/parser.py        — parse(), error classes     (Task 4)
gameofgit/engine/executor.py      — execute(), ExecResult      (Task 5)
gameofgit/engine/session.py       — QuestSession, Outcome      (Task 6)
gameofgit/quests/__init__.py      — all_quests() helper        (Task 12)
gameofgit/quests/level1.py        — 4 Quest instances          (Tasks 8-11)
tests/conftest.py                                              (Task 12)
tests/test_quest.py                                            (Task 2)
tests/test_sandbox.py                                          (Task 3)
tests/test_parser.py                                           (Task 4)
tests/test_executor.py                                         (Task 5)
tests/test_session.py                                          (Task 6)
tests/test_engine_exports.py                                   (Task 7)
tests/test_level1_quests.py                                    (Tasks 8-11)
tests/test_session_e2e.py                                      (Task 13)
```

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `gameofgit/__init__.py`
- Create: `gameofgit/engine/__init__.py` (empty placeholder, filled in Task 7)
- Create: `gameofgit/quests/__init__.py` (empty placeholder, filled in Task 12)
- Create: `tests/__init__.py` (empty — pytest uses rootdir discovery, but the file keeps `tests/` from being treated as implicit namespace noise)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "gameofgit"
version = "0.0.1"
description = "Learn Git by playing."
requires-python = ">=3.12"
license = { text = "MIT" }

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["gameofgit*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create empty package files**

```bash
mkdir -p gameofgit/engine gameofgit/quests tests
: > gameofgit/__init__.py
: > gameofgit/engine/__init__.py
: > gameofgit/quests/__init__.py
: > tests/__init__.py
```

- [ ] **Step 3: Install pytest into the existing venv**

```bash
./venv/bin/pip install 'pytest>=8.0'
```

Expected: pytest installs successfully. (Plus its transitive deps: `iniconfig`, `packaging`, `pluggy`.)

- [ ] **Step 4: Smoke-test pytest**

```bash
./venv/bin/python -m pytest --version
./venv/bin/python -m pytest
```

Expected from `--version`: something like `pytest 8.x.x`.
Expected from `pytest`: `no tests ran` (or a "no tests collected" message — zero tests, zero failures, zero errors, exit 0 or 5).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml gameofgit/ tests/
git commit -m "chore: project scaffold — pyproject.toml, package skeleton, pytest"
```

---

## Task 2: Quest and CheckResult dataclasses

**Files:**
- Create: `gameofgit/engine/quest.py`
- Test: `tests/test_quest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_quest.py`:

```python
import dataclasses

import pytest

from gameofgit.engine.quest import Quest, CheckResult


def test_check_result_defaults_to_no_detail():
    r = CheckResult(True)
    assert r.passed is True
    assert r.detail is None


def test_check_result_with_detail():
    r = CheckResult(False, "not yet")
    assert r.passed is False
    assert r.detail == "not yet"


def test_check_result_is_frozen():
    r = CheckResult(True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def _noop_check(_path):
    return CheckResult(False)


def test_quest_is_frozen():
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.slug = "y"  # type: ignore[misc]


def test_quest_seed_defaults_to_none():
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    assert q.seed is None


def test_quest_is_hashable_via_slug():
    # frozen dataclasses are hashable by default (all fields hash); a frozenset
    # of quest slugs would be the natural way to dedupe quests. We don't assert
    # equality semantics, only that __hash__ doesn't raise.
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    hash(q)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_quest.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.engine.quest'`.

- [ ] **Step 3: Implement `gameofgit/engine/quest.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_quest.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/quest.py tests/test_quest.py
git commit -m "feat(engine): Quest and CheckResult dataclasses"
```

---

## Task 3: Sandbox (temp-dir lifecycle)

**Files:**
- Create: `gameofgit/engine/sandbox.py`
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sandbox.py`:

```python
from gameofgit.engine.sandbox import Sandbox


def test_sandbox_path_exists_inside_with():
    with Sandbox() as s:
        assert s.path.is_dir()


def test_sandbox_path_removed_after_with():
    with Sandbox() as s:
        p = s.path
    assert not p.exists()


def test_sandbox_close_is_idempotent():
    s = Sandbox()
    s.close()
    s.close()  # second call must not raise


def test_sandbox_cleans_up_on_exception_inside_with():
    p = None
    try:
        with Sandbox() as s:
            p = s.path
            assert p.is_dir()
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert p is not None
    assert not p.exists()


def test_sandbox_path_is_unique_per_instance():
    with Sandbox() as a, Sandbox() as b:
        assert a.path != b.path


def test_sandbox_prefix_is_gog():
    with Sandbox() as s:
        assert s.path.name.startswith("gog-")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_sandbox.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.engine.sandbox'`.

- [ ] **Step 3: Implement `gameofgit/engine/sandbox.py`**

```python
import shutil
import tempfile
from pathlib import Path


class Sandbox:
    """Owns one throwaway directory. Context manager. No git knowledge."""

    def __init__(self) -> None:
        self.path: Path = Path(tempfile.mkdtemp(prefix="gog-"))
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        shutil.rmtree(self.path, ignore_errors=False)
        self._closed = True

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_sandbox.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/sandbox.py tests/test_sandbox.py
git commit -m "feat(engine): Sandbox temp-dir lifecycle"
```

---

## Task 4: Parser and engine error classes

**Files:**
- Create: `gameofgit/engine/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_parser.py`:

```python
import pytest

from gameofgit.engine.parser import (
    DisallowedSubcommand,
    EmptyCommand,
    EngineError,
    NotAGitCommand,
    parse,
)

ALLOWED = frozenset({"init", "status", "add", "commit"})


def test_parse_simple_valid():
    assert parse("git init", ALLOWED) == ["git", "init"]


def test_parse_valid_with_arg():
    assert parse("git add README.md", ALLOWED) == ["git", "add", "README.md"]


def test_parse_valid_with_quoted_message():
    assert parse('git commit -m "hello world"', ALLOWED) == [
        "git",
        "commit",
        "-m",
        "hello world",
    ]


@pytest.mark.parametrize("cmdline", ["", "   ", "\t", "\n"])
def test_parse_empty_or_whitespace_raises(cmdline):
    with pytest.raises(EmptyCommand):
        parse(cmdline, ALLOWED)


def test_parse_non_git_raises():
    with pytest.raises(NotAGitCommand) as exc:
        parse("rm -rf /", ALLOWED)
    assert exc.value.argv0 == "rm"


def test_parse_disallowed_subcommand_raises():
    with pytest.raises(DisallowedSubcommand) as exc:
        parse("git rebase main", ALLOWED)
    assert exc.value.sub == "rebase"
    assert exc.value.allowed == ALLOWED


def test_parse_bare_git_raises_disallowed():
    with pytest.raises(DisallowedSubcommand) as exc:
        parse("git", ALLOWED)
    assert exc.value.sub == ""


def test_all_engine_errors_share_base():
    # Useful when the Session wants a single except EngineError: clause.
    assert issubclass(EmptyCommand, EngineError)
    assert issubclass(NotAGitCommand, EngineError)
    assert issubclass(DisallowedSubcommand, EngineError)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_parser.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.engine.parser'`.

- [ ] **Step 3: Implement `gameofgit/engine/parser.py`**

```python
import shlex


class EngineError(Exception):
    """Base class for engine-level command rejections."""


class EmptyCommand(EngineError):
    """The command line parsed to an empty argv (empty string or whitespace)."""


class NotAGitCommand(EngineError):
    """argv[0] is not 'git'."""

    def __init__(self, argv0: str) -> None:
        super().__init__(argv0)
        self.argv0 = argv0


class DisallowedSubcommand(EngineError):
    """argv[1] is missing or not in the quest's allowed set."""

    def __init__(self, sub: str, allowed: frozenset[str]) -> None:
        super().__init__(sub)
        self.sub = sub
        self.allowed = allowed


def parse(cmdline: str, allowed: frozenset[str]) -> list[str]:
    argv = shlex.split(cmdline)
    if not argv:
        raise EmptyCommand()
    if argv[0] != "git":
        raise NotAGitCommand(argv[0])
    sub = argv[1] if len(argv) >= 2 else ""
    if sub not in allowed:
        raise DisallowedSubcommand(sub, allowed)
    return argv
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_parser.py -v
```

Expected: all parameterized cases PASS (11 test cases total across the 8 functions).

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/parser.py tests/test_parser.py
git commit -m "feat(engine): parser with engine error classes"
```

---

## Task 5: Executor and ExecResult

**Files:**
- Create: `gameofgit/engine/executor.py`
- Test: `tests/test_executor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_executor.py`:

```python
from gameofgit.engine.executor import ExecResult, execute


def test_execute_git_init_succeeds(tmp_path):
    result = execute(["git", "init"], cwd=tmp_path)
    assert isinstance(result, ExecResult)
    assert result.exit_code == 0
    assert (tmp_path / ".git").is_dir()


def test_execute_git_status_fails_outside_repo(tmp_path):
    result = execute(["git", "status"], cwd=tmp_path)
    assert result.exit_code != 0
    # With LANG=C pinned, the phrase is stable:
    assert "not a git repository" in result.stderr.lower()


def test_execute_captures_stdout(tmp_path):
    # 'git --version' always works, even outside a repo, and prints to stdout.
    result = execute(["git", "--version"], cwd=tmp_path)
    assert result.exit_code == 0
    assert result.stdout.startswith("git version")
    assert result.stderr == ""


def test_execute_timeout_returns_124(tmp_path):
    # Use 'sh -c sleep 2' with timeout 0.1 to force a TimeoutExpired.
    result = execute(["sh", "-c", "sleep 2"], cwd=tmp_path, timeout_s=0.1)
    assert result.exit_code == 124
    assert "timed out" in result.stderr.lower()
    assert result.stdout == ""


def test_execute_respects_cwd(tmp_path):
    # 'git init' only creates .git/ inside cwd; a second call in a subdir should
    # create a nested repo, not touch the parent.
    sub = tmp_path / "nested"
    sub.mkdir()
    execute(["git", "init"], cwd=sub)
    assert (sub / ".git").is_dir()
    assert not (tmp_path / ".git").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_executor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.engine.executor'`.

- [ ] **Step 3: Implement `gameofgit/engine/executor.py`**

```python
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def execute(argv: list[str], cwd: Path, timeout_s: float = 5.0) -> ExecResult:
    """Run a validated argv against `cwd`. No quest logic, no validation.

    Returns ExecResult. Translates TimeoutExpired into exit_code=124 (GNU
    timeout convention). Never raises for ordinary subprocess failures —
    those just show up as non-zero exit codes.
    """
    env = {**os.environ, "LANG": "C"}
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ExecResult(completed.stdout, completed.stderr, completed.returncode)
    except subprocess.TimeoutExpired:
        return ExecResult(
            stdout="",
            stderr=f"Command timed out after {timeout_s}s and was killed.",
            exit_code=124,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_executor.py -v
```

Expected: all 5 tests PASS. (If `test_execute_git_status_fails_outside_repo` fails because of locale, that means `LANG=C` isn't taking effect — re-check the `env=` argument.)

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/executor.py tests/test_executor.py
git commit -m "feat(engine): executor with LANG=C pinning and timeout handling"
```

---

## Task 6: QuestSession and Outcome

**Files:**
- Create: `gameofgit/engine/session.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_session.py`:

```python
from pathlib import Path

import pytest

from gameofgit.engine.quest import CheckResult, Quest
from gameofgit.engine.session import Outcome, QuestSession


def _quest(
    slug: str = "t",
    allowed: frozenset[str] = frozenset({"init", "status"}),
    check=lambda _p: CheckResult(False),
    seed=None,
) -> Quest:
    return Quest(
        slug=slug,
        title="T",
        brief="b",
        hints=(),
        allowed=allowed,
        check=check,
        seed=seed,
    )


def test_session_creates_and_destroys_sandbox():
    q = _quest()
    with QuestSession(q) as s:
        assert s._sandbox.path.is_dir()
        p = s._sandbox.path
    assert not p.exists()


def test_session_runs_initial_check_and_stores_it():
    calls = []

    def check(path):
        calls.append(path)
        return CheckResult(False, "initial")

    q = _quest(check=check)
    with QuestSession(q) as s:
        # __init__ must have run the predicate once.
        assert len(calls) == 1
        assert s._last_check == CheckResult(False, "initial")


def test_session_seed_runs_and_receives_path():
    recorded: dict[str, Path] = {}

    def seed(path: Path) -> None:
        recorded["path"] = path
        (path / "marker").write_text("seeded\n")

    q = _quest(seed=seed)
    with QuestSession(q) as s:
        assert recorded["path"] == s._sandbox.path
        assert (s._sandbox.path / "marker").read_text() == "seeded\n"


def test_session_seed_failure_cleans_up_and_reraises():
    captured: dict[str, Path] = {}

    def seed(path: Path) -> None:
        captured["path"] = path
        raise RuntimeError("bad seed")

    q = _quest(seed=seed)
    with pytest.raises(RuntimeError, match="bad seed"):
        QuestSession(q)
    assert not captured["path"].exists()


def test_session_empty_command_is_noop():
    q = _quest(check=lambda _p: CheckResult(True, "already done"))
    with QuestSession(q) as s:
        out = s.run("")
        assert isinstance(out, Outcome)
        assert out.exit_code == 0
        assert out.stdout == ""
        assert out.stderr == ""
        # Empty command re-uses the stored _last_check.
        assert out.check.passed is True
        assert out.check.detail == "already done"


def test_session_non_git_command_returns_127():
    q = _quest()
    with QuestSession(q) as s:
        out = s.run("rm -rf /")
        assert out.exit_code == 127
        assert "rm:" in out.stderr
        assert "not available" in out.stderr


def test_session_disallowed_subcommand_returns_127():
    q = _quest(allowed=frozenset({"init"}))
    with QuestSession(q) as s:
        out = s.run("git rebase main")
        assert out.exit_code == 127
        assert "rebase" in out.stderr


def test_session_parser_reject_does_not_rerun_check():
    calls = 0

    def check(_p):
        nonlocal calls
        calls += 1
        return CheckResult(False)

    q = _quest(check=check)
    with QuestSession(q) as s:
        assert calls == 1  # initial
        s.run("rm -rf /")
        assert calls == 1  # parser reject: check NOT re-run
        s.run("")  # empty command: also no re-run
        assert calls == 1


def test_session_successful_git_reruns_check_and_can_complete_quest():
    calls = 0

    def check(path):
        nonlocal calls
        calls += 1
        return CheckResult((path / ".git").is_dir())

    q = _quest(check=check, allowed=frozenset({"init", "status"}))
    with QuestSession(q) as s:
        assert calls == 1
        out = s.run("git init")
        assert calls == 2
        assert out.exit_code == 0
        assert out.check.passed is True


def test_session_failing_git_still_reruns_check():
    # `git status` with no repo fails, but we still re-evaluate the predicate
    # afterward — the spec says "every real subprocess" triggers a re-check.
    calls = 0

    def check(_p):
        nonlocal calls
        calls += 1
        return CheckResult(False)

    q = _quest(check=check, allowed=frozenset({"status"}))
    with QuestSession(q) as s:
        assert calls == 1
        out = s.run("git status")
        assert out.exit_code != 0  # git itself failed
        assert calls == 2  # but we still re-checked


def test_session_close_is_idempotent():
    q = _quest()
    s = QuestSession(q)
    s.close()
    s.close()  # second call must not raise
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_session.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.engine.session'`.

- [ ] **Step 3: Implement `gameofgit/engine/session.py`**

```python
from dataclasses import dataclass
from pathlib import Path

from .executor import execute
from .parser import (
    DisallowedSubcommand,
    EmptyCommand,
    NotAGitCommand,
    parse,
)
from .quest import CheckResult, Quest
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
        try:
            if quest.seed is not None:
                quest.seed(self._sandbox.path)
            self._last_check: CheckResult = quest.check(self._sandbox.path)
        except Exception:
            self._sandbox.close()
            raise

    def run(self, cmdline: str) -> Outcome:
        try:
            argv = parse(cmdline, self._quest.allowed)
        except EmptyCommand:
            return Outcome("", "", 0, self._last_check)
        except NotAGitCommand as e:
            return Outcome(
                stdout="",
                stderr=f"{e.argv0}: command not available in this quest",
                exit_code=127,
                check=self._last_check,
            )
        except DisallowedSubcommand as e:
            return Outcome(
                stdout="",
                stderr=f"git: '{e.sub}' is not available in this level yet",
                exit_code=127,
                check=self._last_check,
            )

        result = execute(argv, cwd=self._sandbox.path)
        # Re-evaluate the predicate after every real subprocess invocation,
        # whether git succeeded or failed.
        self._last_check = self._quest.check(self._sandbox.path)
        return Outcome(result.stdout, result.stderr, result.exit_code, self._last_check)

    def close(self) -> None:
        self._sandbox.close()

    def __enter__(self) -> "QuestSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_session.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/session.py tests/test_session.py
git commit -m "feat(engine): QuestSession orchestrating sandbox, parser, executor, check"
```

---

## Task 7: Engine package re-exports

**Files:**
- Modify: `gameofgit/engine/__init__.py`
- Test: `tests/test_engine_exports.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_engine_exports.py`:

```python
def test_engine_public_api_reexports():
    from gameofgit.engine import CheckResult, Outcome, Quest, QuestSession

    # Sanity: each import resolved to the real class, not a stub.
    assert Quest.__module__ == "gameofgit.engine.quest"
    assert CheckResult.__module__ == "gameofgit.engine.quest"
    assert Outcome.__module__ == "gameofgit.engine.session"
    assert QuestSession.__module__ == "gameofgit.engine.session"


def test_engine_all_declares_public_api():
    import gameofgit.engine as eng

    assert set(eng.__all__) == {"Quest", "CheckResult", "Outcome", "QuestSession"}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_engine_exports.py -v
```

Expected: FAIL — either `ImportError` for the names, or `AttributeError: module 'gameofgit.engine' has no attribute '__all__'`.

- [ ] **Step 3: Fill in `gameofgit/engine/__init__.py`**

```python
from .quest import CheckResult, Quest
from .session import Outcome, QuestSession

__all__ = ["Quest", "CheckResult", "Outcome", "QuestSession"]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_engine_exports.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/engine/__init__.py tests/test_engine_exports.py
git commit -m "feat(engine): public API re-exports"
```

---

## Task 8: Level 1 Quest 1 — `init-repo`

**Files:**
- Create: `gameofgit/quests/level1.py` (new file with Quest 1 only; Quests 2–4 added in later tasks)
- Test: `tests/test_level1_quests.py` (new file)

**Why this quest first:** no seed, single-line predicate. Confirms the Quest dataclass machinery works end-to-end before the seeded quests pile on complexity.

- [ ] **Step 1: Write the failing test**

Create `tests/test_level1_quests.py`:

```python
import subprocess

from gameofgit.quests.level1 import INIT_REPO


def test_init_repo_predicate_false_on_empty_dir(tmp_path):
    r = INIT_REPO.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert ".git" in r.detail


def test_init_repo_predicate_true_after_git_init(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    r = INIT_REPO.check(tmp_path)
    assert r.passed is True
    assert r.detail is None


def test_init_repo_quest_metadata():
    assert INIT_REPO.slug == "init-repo"
    assert INIT_REPO.seed is None
    assert INIT_REPO.allowed == frozenset({"init", "status", "add", "commit"})
    assert len(INIT_REPO.hints) >= 1
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'gameofgit.quests.level1'`.

- [ ] **Step 3: Implement `gameofgit/quests/level1.py`**

```python
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest

_ALLOWED = frozenset({"init", "status", "add", "commit"})


def _check_init_repo(sandbox: Path) -> CheckResult:
    if (sandbox / ".git").is_dir():
        return CheckResult(True)
    return CheckResult(
        False,
        "No .git/ directory found yet — the workspace isn't a repo.",
    )


INIT_REPO = Quest(
    slug="init-repo",
    title="Turn this place into a git repository.",
    brief=(
        "You've arrived in an empty workspace. Before you can save anything, "
        "you need to make it a git repository. One command is all it takes."
    ),
    hints=(
        "There's a git command whose whole job is to create a new repo.",
        "Try `git init`.",
    ),
    allowed=_ALLOWED,
    check=_check_init_repo,
    seed=None,
)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gameofgit/quests/level1.py tests/test_level1_quests.py
git commit -m "feat(quests): Level 1 quest 1 — init-repo"
```

---

## Task 9: Level 1 Quest 2 — `stage-a-file`

**Files:**
- Modify: `gameofgit/quests/level1.py` (append Quest 2)
- Modify: `tests/test_level1_quests.py` (append Quest 2 tests)

**Why seeds set a local git identity:** `git commit` refuses to run without `user.email` / `user.name` configured. The player may or may not have a global identity set; we don't want the engine to leak player identity into throwaway repos anyway. Every seed that initializes a repo also sets a local identity (`player@gameofgit.local` / `Player`). This is pragmatic robustness, not in the spec — document the choice in the seed helper's docstring.

- [ ] **Step 1: Add the failing test**

Append to `tests/test_level1_quests.py`:

```python
from gameofgit.quests.level1 import STAGE_A_FILE


def test_stage_a_file_seed_initializes_repo(tmp_path):
    assert STAGE_A_FILE.seed is not None
    STAGE_A_FILE.seed(tmp_path)
    assert (tmp_path / ".git").is_dir()


def test_stage_a_file_predicate_false_after_seed_only(tmp_path):
    STAGE_A_FILE.seed(tmp_path)
    r = STAGE_A_FILE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "staged" in r.detail.lower()


def test_stage_a_file_predicate_true_after_add(tmp_path):
    STAGE_A_FILE.seed(tmp_path)
    (tmp_path / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    r = STAGE_A_FILE.check(tmp_path)
    assert r.passed is True


def test_stage_a_file_quest_metadata():
    assert STAGE_A_FILE.slug == "stage-a-file"
    assert STAGE_A_FILE.allowed == frozenset({"init", "status", "add", "commit"})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: FAIL with `ImportError: cannot import name 'STAGE_A_FILE'`.

- [ ] **Step 3: Add to `gameofgit/quests/level1.py`**

Insert above `INIT_REPO` (or after — order doesn't matter; keep sections grouped by quest) a helper, then the new quest. Full module additions below:

```python
import subprocess

# ... (existing imports and INIT_REPO remain above) ...


def _seed_initialized_repo(sandbox: Path) -> None:
    """Initialize a git repo in `sandbox` and set a local identity.

    A local identity is required because `git commit` refuses to run without
    one, and we don't want the engine depending on whatever identity the
    player happens to have in their global ~/.gitconfig.
    """
    subprocess.run(["git", "init", "-q"], cwd=sandbox, check=True)
    subprocess.run(
        ["git", "config", "user.email", "player@gameofgit.local"],
        cwd=sandbox,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Player"], cwd=sandbox, check=True)


def _check_stage_a_file(sandbox: Path) -> CheckResult:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip():
        return CheckResult(True)
    return CheckResult(
        False,
        "Nothing is staged yet. Create a file and `git add` it.",
    )


STAGE_A_FILE = Quest(
    slug="stage-a-file",
    title="Stage your first change.",
    brief=(
        "Good — the repo exists. Now create a file (any file, any content) "
        "and stage it so git knows you want to include it in your next commit."
    ),
    hints=(
        "Git doesn't track files automatically — you have to tell it which ones.",
        "`git add <filename>` adds a specific file; `git status` shows what's staged.",
    ),
    allowed=_ALLOWED,
    check=_check_stage_a_file,
    seed=_seed_initialized_repo,
)
```

(Remember to add `import subprocess` at the top of the file if it isn't there yet.)

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: all 7 tests PASS (3 from Task 8 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add gameofgit/quests/level1.py tests/test_level1_quests.py
git commit -m "feat(quests): Level 1 quest 2 — stage-a-file (adds seed helper)"
```

---

## Task 10: Level 1 Quest 3 — `first-commit`

**Files:**
- Modify: `gameofgit/quests/level1.py` (append Quest 3)
- Modify: `tests/test_level1_quests.py` (append Quest 3 tests)

- [ ] **Step 1: Add the failing test**

Append to `tests/test_level1_quests.py`:

```python
from gameofgit.quests.level1 import FIRST_COMMIT


def test_first_commit_seed_stages_a_file(tmp_path):
    assert FIRST_COMMIT.seed is not None
    FIRST_COMMIT.seed(tmp_path)
    # After seed: repo exists, at least one file is staged.
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert r.stdout.strip() != ""


def test_first_commit_predicate_false_after_seed_only(tmp_path):
    FIRST_COMMIT.seed(tmp_path)
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "HEAD" in r.detail


def test_first_commit_predicate_true_after_commit(tmp_path):
    FIRST_COMMIT.seed(tmp_path)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial commit"],
        cwd=tmp_path,
        check=True,
    )
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is True


def test_first_commit_predicate_false_if_empty_commit(tmp_path):
    # Edge case: a commit with no files (allow-empty) must not satisfy the quest.
    FIRST_COMMIT.seed(tmp_path)
    subprocess.run(["git", "reset"], cwd=tmp_path, check=True)  # unstage
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "nothing"],
        cwd=tmp_path,
        check=True,
    )
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "no files" in r.detail.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: FAIL with `ImportError: cannot import name 'FIRST_COMMIT'`.

- [ ] **Step 3: Add to `gameofgit/quests/level1.py`**

```python
def _seed_repo_with_staged_file(sandbox: Path) -> None:
    _seed_initialized_repo(sandbox)
    (sandbox / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=sandbox, check=True)


def _check_first_commit(sandbox: Path) -> CheckResult:
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
    )
    if head.returncode != 0:
        return CheckResult(False, "HEAD doesn't point at any commit yet.")
    files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    )
    if not files.stdout.strip():
        return CheckResult(False, "You committed, but the commit contains no files.")
    return CheckResult(True)


FIRST_COMMIT = Quest(
    slug="first-commit",
    title="Record your first commit.",
    brief=(
        "Staging is a promise; committing keeps it. Turn your staged changes "
        "into a permanent snapshot."
    ),
    hints=(
        "A commit needs a message — without one, git will open an editor.",
        '`git commit -m "your message here"` keeps it on one line.',
    ),
    allowed=_ALLOWED,
    check=_check_first_commit,
    seed=_seed_repo_with_staged_file,
)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: all 11 tests PASS (7 previous + 4 new).

- [ ] **Step 5: Commit**

```bash
git add gameofgit/quests/level1.py tests/test_level1_quests.py
git commit -m "feat(quests): Level 1 quest 3 — first-commit"
```

---

## Task 11: Level 1 Quest 4 — `meaningful-message`

**Files:**
- Modify: `gameofgit/quests/level1.py` (append Quest 4)
- Modify: `tests/test_level1_quests.py` (append Quest 4 tests)

- [ ] **Step 1: Add the failing test**

Append to `tests/test_level1_quests.py`:

```python
from gameofgit.quests.level1 import MEANINGFUL_MESSAGE


def test_meaningful_message_seed_has_one_commit(tmp_path):
    assert MEANINGFUL_MESSAGE.seed is not None
    MEANINGFUL_MESSAGE.seed(tmp_path)
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert count.stdout.strip() == "1"


def test_meaningful_message_predicate_false_after_seed_only(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "new commit" in r.detail.lower()


def test_meaningful_message_predicate_false_with_short_new_message(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    (tmp_path / "new.txt").write_text("new\n")
    subprocess.run(["git", "add", "new.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fix"],  # 3 chars, < 10
        cwd=tmp_path,
        check=True,
    )
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "3 chars" in r.detail


def test_meaningful_message_predicate_true_with_long_new_message(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    (tmp_path / "new.txt").write_text("new\n")
    subprocess.run(["git", "add", "new.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Add greeting to new file"],
        cwd=tmp_path,
        check=True,
    )
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is True
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: FAIL with `ImportError: cannot import name 'MEANINGFUL_MESSAGE'`.

- [ ] **Step 3: Add to `gameofgit/quests/level1.py`**

```python
def _seed_repo_with_initial_commit(sandbox: Path) -> None:
    _seed_repo_with_staged_file(sandbox)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=sandbox,
        check=True,
    )


def _check_meaningful_message(sandbox: Path) -> CheckResult:
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
    )
    if count.returncode != 0 or int(count.stdout.strip() or 0) < 2:
        return CheckResult(False, "Make a new commit on top of the starting one.")
    msg = subprocess.run(
        ["git", "log", "-1", "--pretty=%s", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if len(msg) < 10:
        return CheckResult(
            False,
            f"Your message is {len(msg)} chars — try for at least 10.",
        )
    return CheckResult(True)


MEANINGFUL_MESSAGE = Quest(
    slug="meaningful-message",
    title="Write a commit message that future-you will thank you for.",
    brief=(
        "A commit message is a note to the next person who reads this code — "
        "often yourself, six months from now. Make a new change, commit it, "
        "and give it a message at least 10 characters long."
    ),
    hints=(
        "`Fix` or `update` on their own don't tell anyone what changed.",
        "Aim for something like `Add greeting to README`.",
    ),
    allowed=_ALLOWED,
    check=_check_meaningful_message,
    seed=_seed_repo_with_initial_commit,
)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v
```

Expected: all 15 tests PASS (11 previous + 4 new).

- [ ] **Step 5: Commit**

```bash
git add gameofgit/quests/level1.py tests/test_level1_quests.py
git commit -m "feat(quests): Level 1 quest 4 — meaningful-message"
```

---

## Task 12: Quests package `all_quests()` helper and shared fixtures

**Files:**
- Modify: `gameofgit/quests/__init__.py`
- Create: `tests/conftest.py`
- Test: add one test to `tests/test_level1_quests.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_level1_quests.py`:

```python
from gameofgit.quests import all_quests


def test_all_quests_returns_all_level1_quests():
    quests = list(all_quests())
    slugs = {q.slug for q in quests}
    assert slugs == {
        "init-repo",
        "stage-a-file",
        "first-commit",
        "meaningful-message",
    }


def test_all_quests_preserves_level_order():
    # The return order determines the intended progression through the level.
    slugs = [q.slug for q in all_quests()]
    assert slugs == [
        "init-repo",
        "stage-a-file",
        "first-commit",
        "meaningful-message",
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
./venv/bin/python -m pytest tests/test_level1_quests.py -v -k all_quests
```

Expected: FAIL with `ImportError: cannot import name 'all_quests' from 'gameofgit.quests'`.

- [ ] **Step 3: Fill in `gameofgit/quests/__init__.py`**

```python
from collections.abc import Iterable

from gameofgit.engine.quest import Quest
from gameofgit.quests.level1 import (
    FIRST_COMMIT,
    INIT_REPO,
    MEANINGFUL_MESSAGE,
    STAGE_A_FILE,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)


def all_quests() -> Iterable[Quest]:
    """Every quest currently shipped, in intended play order."""
    return _LEVEL1


__all__ = ["all_quests"]
```

- [ ] **Step 4: Create `tests/conftest.py`**

This sets up the `quest` fixture that Task 13 will rely on. Put it here rather than in `test_session_e2e.py` so other modules can reuse it.

```python
import pytest

from gameofgit.quests import all_quests


@pytest.fixture(params=list(all_quests()), ids=lambda q: q.slug)
def quest(request):
    return request.param
```

- [ ] **Step 5: Run all tests**

```bash
./venv/bin/python -m pytest -v
```

Expected: all tests PASS. Count should be ~58 (17 from `test_level1_quests.py`, 41 from the rest of the engine suite).

- [ ] **Step 6: Commit**

```bash
git add gameofgit/quests/__init__.py tests/conftest.py tests/test_level1_quests.py
git commit -m "feat(quests): all_quests() helper and shared quest fixture"
```

---

## Task 13: End-to-end session test — play through every quest

**Files:**
- Create: `tests/test_session_e2e.py`

This is the capstone: drive each quest through a `QuestSession` using the same kind of command sequence the future UI will hand it. Proves all four predicates are reachable via real player input and that the session's check re-evaluation works end-to-end.

- [ ] **Step 1: Write the failing test**

Create `tests/test_session_e2e.py`:

```python
from pathlib import Path

from gameofgit.engine.quest import Quest
from gameofgit.engine.session import QuestSession


def _play_through(session: QuestSession, slug: str) -> None:
    """Drive a quest to completion using only session.run() + filesystem writes.

    File writes (outside the whitelist) mirror what a real UI would allow
    the player to do via a text-editor pane.
    """
    sandbox: Path = session._sandbox.path
    if slug == "init-repo":
        session.run("git init")
    elif slug == "stage-a-file":
        (sandbox / "README.md").write_text("hello\n")
        session.run("git add README.md")
    elif slug == "first-commit":
        # Seed has already staged a file; all that's left is committing.
        session.run('git commit -m "initial commit"')
    elif slug == "meaningful-message":
        (sandbox / "new.txt").write_text("new content\n")
        session.run("git add new.txt")
        session.run('git commit -m "Add greeting to new file"')
    else:
        raise AssertionError(f"no playthrough defined for slug: {slug}")


def test_each_quest_starts_not_completed(quest: Quest):
    with QuestSession(quest) as s:
        assert s._last_check.passed is False


def test_each_quest_can_be_completed(quest: Quest):
    with QuestSession(quest) as s:
        _play_through(s, quest.slug)
        # Final "git status" is a cheap, state-preserving command that forces
        # one more re-check and gives the UI a clean "you're done" outcome.
        out = s.run("git status")
        assert out.exit_code == 0
        assert out.check.passed is True, out.check.detail


def test_quest_rejects_non_git_commands_without_breaking_state(quest: Quest):
    # Typing junk shouldn't affect whether the quest later succeeds.
    with QuestSession(quest) as s:
        out = s.run("rm -rf /")
        assert out.exit_code == 127
        # Now the quest should still be completable the normal way.
        _play_through(s, quest.slug)
        assert s.run("git status").check.passed is True
```

- [ ] **Step 2: Run the test to verify it fails if `QuestSession` is broken**

```bash
./venv/bin/python -m pytest tests/test_session_e2e.py -v
```

Expected: all 12 tests PASS (3 test functions × 4 parametrized quests).

If any test fails, the likely suspects are:

- **`init-repo` fails after `git init`:** probably the executor didn't pass `LANG=C`, so `git`'s default-branch hint spam is confusing the predicate — re-check `executor.py`.
- **`first-commit` fails at seed:** the seed's `git config user.email` is missing — re-check `_seed_initialized_repo`.
- **`meaningful-message` fails at commit step:** the commit message length calculation is off — the predicate uses bytes-of-text, and non-ASCII characters could count differently than expected, but the scripted message is pure ASCII so this shouldn't fire.

- [ ] **Step 3: Run the full suite**

```bash
./venv/bin/python -m pytest -v
```

Expected: every test in every module PASSES. This is the real completion signal for the plan.

- [ ] **Step 4: Commit**

```bash
git add tests/test_session_e2e.py
git commit -m "test: end-to-end playthrough for every Level 1 quest"
```

---

## Done

After Task 13, the repo has:

- A working engine (`QuestSession`, `Quest`, `CheckResult`, `Outcome`, `Sandbox`, `parse()`, `execute()`).
- Four playable quests (`INIT_REPO`, `STAGE_A_FILE`, `FIRST_COMMIT`, `MEANINGFUL_MESSAGE`).
- A test suite (~70 tests) covering every public entry point and every error branch listed in the spec.
- No UI, no TUI library dependency, no typo suggestions. Those belong to later plans.

**Running the suite:**

```bash
./venv/bin/python -m pytest -v            # everything
./venv/bin/python -m pytest -k parser -v  # one module
./venv/bin/python -m pytest -x            # stop at first fail
```

**Next plans (deferred, not in scope here):**

1. Two-pane TUI (left: simulated shell; right: task + reveal-on-demand hints). Will wrap `QuestSession`.
2. Typo detection / "did you mean?" on keystroke input. UI-layer concern.
3. Seeding framework for Level 2+ (broken repos, merge conflicts) — bigger than a "seed function", likely fixture tarballs or a small DSL.
