# Quest-runner core — design

**Date:** 2026-04-18
**Status:** Approved
**Scope:** The backend engine for Game of GIT. A Python library that takes a `Quest` definition, runs real `git` against an isolated sandbox in response to player commands, and reports whether the quest is complete. The UI (two-pane TUI) is out of scope.

## Goals

- Give a future UI one object (`QuestSession`) to drive a quest.
- Run the player's real `git` commands against a real, throwaway repo.
- Evaluate quest completion automatically after every command.
- Ship with Level 1's four quests as the first end-to-end exercise of the engine.
- Never touch the player's real working tree or anything outside a per-session temp dir.

## Non-goals

- The UI (two-pane window, live typing suggestions, hint reveal interaction).
- Levels 2–10 and any quest requiring a non-empty seeded repo.
- Typo detection while the player is typing. The engine only sees completed command lines.
- Persistence / save state. Sessions are ephemeral.
- Cross-platform support. Linux/macOS only for v1.
- Concurrency. One session at a time.

## Locked-in decisions (from brainstorming)

| # | Decision | Rationale |
|---|---|---|
| 1 | One sandbox per quest, fresh each time | Known starting state → known success state; quests are independent; restarting is clean. |
| 2 | Real `git` as a subprocess, with a per-level subcommand whitelist | Authentic output (the player sees the same errors a real developer sees), plus a cheap safety layer. |
| 3 | Check predicate runs after every successful command, silently; UI surfaces result only on success | Simple code path; no nagging on intermediate failures; no accidental "you won by chance" surprises. |
| 4 | v1 ships 4 Level 1 mini-quests | Enough distinct predicate shapes to shake out the API; trivial seeding (empty dir). |
| 5 | Quest is a frozen dataclass; predicate is a callable returning `CheckResult(passed, detail)` | Smallest viable shape; `detail` pays off immediately for "why not yet?" diagnostics. |
| 6 | Session-based architecture (`QuestSession` holds the sandbox) | Matches real usage: one quest in flight, one object to talk to, context-manager cleanup. |
| 7 | pytest as the test framework | `tmp_path` fixture is purpose-built for this; parametrize across quests trivially. |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  UI (future two-pane TUI — NOT in this spec)        │
└──────────────────┬──────────────────────────────────┘
                   │ session = QuestSession(quest)
                   │ outcome = session.run("git init")
                   │ session.close()
                   ▼
┌─────────────────────────────────────────────────────┐
│  QuestSession                                       │
│  ─ owns: one temp dir (the sandbox)                 │
│  ─ knows: which Quest it's running                  │
│  ─ does: parse → whitelist → execute → check        │
└──────────────────┬──────────────────────────────────┘
         ┌─────────┼─────────┬────────────┐
         ▼         ▼         ▼            ▼
    ┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────────┐
    │Sandbox │ │Parser│ │Executor │ │Quest.check() │
    │(tmpdir)│ │+whtl │ │(git sub)│ │→ CheckResult │
    └────────┘ └──────┘ └─────────┘ └──────────────┘
```

**Invariants the engine guarantees:**

- Every `git` invocation runs with `cwd=sandbox.path`. The engine never touches anything outside the sandbox.
- The sandbox is created fresh when the session opens, seeded once, and destroyed when the session closes (or on `__exit__`).
- `session.run(cmdline)` is synchronous and returns one `Outcome`. No async, no streaming in v1.
- The predicate runs after every real git subprocess invocation (whether git's exit code was zero or not), never when the parser rejects before anything touches disk. Every `Outcome` carries a `CheckResult`; on parser-reject turns the session re-uses the most recent stored result. Predicates must be side-effect-free and idempotent.

## Components

Six types under `gameofgit/engine/`. Each file small (~50–100 lines). Dependency graph is strict: `session → {sandbox, parser, executor, quest}`. No cycles, no sibling cross-talk.

### `Quest` — `engine/quest.py`

Frozen dataclass. Pure data plus one callable.

```python
@dataclass(frozen=True)
class Quest:
    slug: str                          # "init-repo" — stable id
    title: str                         # one-line task title
    brief: str                         # markdown, shown in right pane
    hints: tuple[str, ...]             # revealed one-by-one on request
    allowed: frozenset[str]            # git subcommands permitted
    check: Callable[[Path], CheckResult]
    seed: Callable[[Path], None] | None = None   # None = empty dir start
```

### `CheckResult` — `engine/quest.py`

```python
@dataclass(frozen=True)
class CheckResult:
    passed: bool
    detail: str | None = None          # optional "why not yet" for explicit checks
```

### `Sandbox` — `engine/sandbox.py`

Owns the temp directory lifecycle. Context manager. Single responsibility: make/destroy a scratch directory safely. Deliberately tiny — no git knowledge. Exists as its own class so the session can't leak temp dirs if seeding raises.

```python
class Sandbox:
    def __init__(self) -> None:
        # tempfile.mkdtemp(prefix="gog-") → stored on self.path as a Path
        self.path: Path = ...
    def close(self) -> None: ...          # shutil.rmtree, idempotent
    def __enter__(self) -> "Sandbox": ...
    def __exit__(self, *exc) -> None: self.close()
```

### `CommandParser` — `engine/parser.py`

Pure function. Turns a typed string into a validated argv, or raises a typed error.

```python
def parse(cmdline: str, allowed: frozenset[str]) -> list[str]:
    # shlex.split, verify argv[0] == "git", verify argv[1] in allowed.
    # raises: EmptyCommand | NotAGitCommand | DisallowedSubcommand
```

### `Executor` — `engine/executor.py`

Pure function. Runs validated argv against the sandbox. No quest logic.

```python
def execute(argv: list[str], cwd: Path, timeout_s: float = 5.0) -> ExecResult:
    # subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=...)
    # env includes LANG=C for stable output
    # returns ExecResult(stdout, stderr, exit_code)
    # TimeoutExpired → ExecResult(stdout="", stderr="Command timed out after Ns...", exit_code=124)
```

### `QuestSession` — `engine/session.py`

The only type the UI touches. Orchestrates everything.

```python
class QuestSession:
    def __init__(self, quest: Quest) -> None:
        # creates Sandbox, seeds it, runs an initial quest.check() and stores
        # the result as self._last_check so parser-reject turns have something
        # to return without re-running the predicate.
        ...
    def run(self, cmdline: str) -> Outcome: ...
    def close(self) -> None: ...
    def __enter__(self): ...
    def __exit__(self, *exc): self.close()

@dataclass(frozen=True)
class Outcome:
    stdout: str
    stderr: str
    exit_code: int                         # 0 success; 127 engine rejection; 124 timeout; else git
    check: CheckResult                     # evaluated after every command
```

### Module layout

```
gameofgit/
  engine/
    __init__.py        # re-exports: Quest, CheckResult, QuestSession, Outcome
    quest.py           # Quest, CheckResult
    sandbox.py         # Sandbox
    parser.py          # parse() + engine error classes
    executor.py        # execute() + ExecResult
    session.py         # QuestSession, Outcome
  quests/
    __init__.py
    level1.py          # the 4 Level 1 Quest instances
```

## Data flow

### Session creation (once per quest)

```
QuestSession(quest)
  → Sandbox() creates /tmp/gog-XXXX/
  → if quest.seed is not None: quest.seed(sandbox.path)
  → session is ready
```

### One command turn (the hot path)

```
player types:  git add README.md
      │
      ▼
session.run("git add README.md")
      │
      ├── parse("git add README.md", quest.allowed)
      │     ├── shlex.split   → ["git", "add", "README.md"]
      │     ├── verify argv[0] == "git"
      │     ├── verify argv[1] in quest.allowed
      │     └── returns argv  (or raises → caught below)
      │
      ├── execute(argv, cwd=sandbox.path, timeout=5.0)
      │     ├── subprocess.run(...)
      │     └── returns ExecResult(stdout, stderr, exit_code)
      │
      ├── check = quest.check(sandbox.path)    ← runs if subprocess actually ran
      │
      └── returns Outcome(stdout, stderr, exit_code, check)
```

### Three branches the UI sees from `run()`

| Situation | exit_code | stderr | check re-run? |
|---|---|---|---|
| Parser rejects | 127 | engine message mimicking shell tone | no — session's stored `_last_check` is re-used |
| git runs, fails | whatever git returned | real git stderr, untouched | yes — result overwrites `_last_check` |
| git runs, succeeds | 0 | real git stderr if any | yes — result overwrites `_last_check` |

**Why re-check on non-zero exit too:** In principle a failing command can't complete a quest, but re-checking whenever a real subprocess ran is cheap and removes a class of "why didn't my quest complete?" bugs. We only skip re-check when the parser rejects — nothing touched disk.

**Why exit code 127 for parser rejections:** Traditional Unix "command not found". Keeps the mental model consistent with a real shell.

### Session close

```
session.close()
  → Sandbox.close() → shutil.rmtree(sandbox.path, ignore_errors=False)
  → close is idempotent
  → __exit__ calls close automatically (recommended: with QuestSession(q) as s: ...)
```

## Error handling

### Parser rejections

Three subclasses in `engine/parser.py`, all inheriting from `EngineError`:

```python
class EngineError(Exception): ...
class EmptyCommand(EngineError): ...
class NotAGitCommand(EngineError): ...
class DisallowedSubcommand(EngineError):
    def __init__(self, sub: str, allowed: frozenset[str]):
        self.sub, self.allowed = sub, allowed
```

`QuestSession.run()` catches these internally and folds into the `Outcome` — the UI never sees raised exceptions on the hot path. Exception classes exist for tests and future log routing.

Stderr shapes:

```
NotAGitCommand       →  "rm: command not available in this quest"
DisallowedSubcommand →  "git: 'rebase' is not available in this level yet"
EmptyCommand         →  ""   (exit 0, no-op — matches shell behavior)
```

`EmptyCommand` is deliberately a no-op with exit 0. That's what a shell does when you press Enter on an empty prompt.

### Git itself fails

Passed through untouched. The README's pedagogy depends on the player seeing real git errors — mistakes are learning material. We do **not** wrap or rewrite git's output.

### Subprocess timeout

`subprocess.run(timeout=5.0)` raises `TimeoutExpired`. Caught in `execute()`:

```
Outcome(stdout="", stderr="Command timed out after 5s and was killed.",
        exit_code=124, check=<last stored>)
```

Exit code 124 matches GNU `timeout`. Shouldn't fire for Level 1 — insurance for later levels that can hang.

### Seeding fails

Session constructor cleans up and re-raises:

```python
def __init__(self, quest):
    self._sandbox = Sandbox()
    try:
        if quest.seed: quest.seed(self._sandbox.path)
    except Exception:
        self._sandbox.close()
        raise
```

Seeding failures are quest-author bugs. They crash loudly. Irrelevant for v1 (all 4 quests have `seed=None` or a trivial seed that shouldn't fail), but the pattern is in place.

### Cleanup fails

`Sandbox.close()` calls `shutil.rmtree(path, ignore_errors=False)` — errors propagate on the first call. `close()` is idempotent: repeated calls after success are no-ops; repeated calls after failure re-raise until it succeeds. Deliberately unforgiving: silent leaks would fill `/tmp` over a long session.

### Explicitly NOT handled

- Malicious subcommands. Level 1's whitelist `{init, status, add, commit}` can't escape cwd. We rely on git's own safety. Revisit when Level 5 adds `clone <url>`.
- Concurrent sessions. Not supported. Two `QuestSession`s get two independent temp dirs with no coordination.
- Process crashes. If Python dies mid-session, `/tmp/gog-XXXX/` leaks. The OS cleans `/tmp` on reboot.

## Testing

### Layout

```
tests/
  conftest.py              # shared fixtures
  test_sandbox.py          # Sandbox lifecycle
  test_parser.py           # parse() validation (parametrized)
  test_executor.py         # execute() against a real tmp git repo
  test_quest.py            # Quest/CheckResult dataclass invariants
  test_session.py          # QuestSession end-to-end per quest
  test_level1_quests.py    # 4 quests, happy + unhappy paths
```

### Fixtures

```python
@pytest.fixture
def sandbox(tmp_path):
    """Bare temp dir, no git init. For parser/executor tests."""
    return tmp_path

@pytest.fixture(params=all_quests())   # yields each Quest from gameofgit.quests.level1
def quest(request):
    return request.param
```

The parametrized `quest` fixture makes covering all 4 quests a single test:

```python
def test_each_quest_can_be_completed(quest):
    with QuestSession(quest) as s:
        for cmd in scripted_solution(quest.slug):
            outcome = s.run(cmd)
            assert outcome.exit_code == 0
        assert s.run("git status").check.passed
```

`scripted_solution()` is test data keyed by quest slug, lives in the test module (not the engine).

### What each module proves

- **test_sandbox.py** — context-manager semantics: path exists inside `with`, gone after; `close()` idempotent; cleanup still happens on exception.
- **test_parser.py** — parametrized decision table: valid cases return argv; `rm -rf /` raises `NotAGitCommand`; disallowed subcommand raises; empty/whitespace raises `EmptyCommand`.
- **test_executor.py** — `git init` against a real tmp dir gives exit 0 and `.git/` exists. Sets `LANG=C` for stable output.
- **test_quest.py** — Quest is frozen and hashable; CheckResult defaults correct.
- **test_session.py** — end-to-end happy path, parametrized over all quests.
- **test_level1_quests.py** — per-quest unhappy paths: predicate false after only `git init`, predicate false with empty commit message, etc.

### What v1 does NOT test

- Cross-platform (Windows `shutil.rmtree` quirks).
- Concurrent sessions.
- Locale-dependent output (pinned via `LANG=C` env fixture).

### Coverage

No numeric target. The test list covers every public entry point and every error branch.

### Running

```
./venv/bin/python -m pytest           # all
./venv/bin/python -m pytest -k quest  # subset by keyword
./venv/bin/python -m pytest -x -v     # stop at first fail, verbose
```

No CI config in v1.

## The four Level 1 quests

All share `allowed = frozenset({"init", "status", "add", "commit"})`. Differ by seed and predicate. Hint/brief text here is English for readability of this spec; final wording is a content decision (README is Polish).

### Quest 1 — `init-repo`

- **Title:** Turn this place into a git repository.
- **Brief:** You've arrived in an empty workspace. Before you can save anything, you need to make it a git repository. One command is all it takes.
- **Hints:** `("There's a git command whose whole job is to create a new repo.", "Try `git init`.")`
- **Seed:** `None` (empty dir).
- **Predicate:**
  ```python
  def check(sandbox: Path) -> CheckResult:
      if (sandbox / ".git").is_dir():
          return CheckResult(True)
      return CheckResult(False, "No .git/ directory found yet — the workspace isn't a repo.")
  ```

### Quest 2 — `stage-a-file`

- **Title:** Stage your first change.
- **Brief:** Good — the repo exists. Now create a file (any file, any content) and stage it so git knows you want to include it in your next commit.
- **Hints:** `("Git doesn't track files automatically — you have to tell it which ones.", "`git add <filename>` adds a specific file; `git status` shows what's staged.")`
- **Seed:** `git init -q` in the sandbox.
- **Predicate:**
  ```python
  def check(sandbox: Path) -> CheckResult:
      result = subprocess.run(
          ["git", "diff", "--cached", "--name-only"],
          cwd=sandbox, capture_output=True, text=True, check=True,
      )
      if result.stdout.strip():
          return CheckResult(True)
      return CheckResult(False, "Nothing is staged yet. Create a file and `git add` it.")
  ```

### Quest 3 — `first-commit`

- **Title:** Record your first commit.
- **Brief:** Staging is a promise; committing keeps it. Turn your staged changes into a permanent snapshot.
- **Hints:** `("A commit needs a message — without one, git will open an editor.", "`git commit -m \"your message here\"` keeps it on one line.")`
- **Seed:** init repo, create a file, stage it. Player only needs `git commit -m ...`.
- **Predicate:**
  ```python
  def check(sandbox: Path) -> CheckResult:
      head = subprocess.run(
          ["git", "rev-parse", "--verify", "HEAD"],
          cwd=sandbox, capture_output=True, text=True,
      )
      if head.returncode != 0:
          return CheckResult(False, "HEAD doesn't point at any commit yet.")
      files = subprocess.run(
          ["git", "ls-tree", "-r", "--name-only", "HEAD"],
          cwd=sandbox, capture_output=True, text=True, check=True,
      )
      if not files.stdout.strip():
          return CheckResult(False, "You committed, but the commit contains no files.")
      return CheckResult(True)
  ```

### Quest 4 — `meaningful-message`

- **Title:** Write a commit message that future-you will thank you for.
- **Brief:** A commit message is a note to the next person who reads this code — often yourself, six months from now. Make a new change, commit it, and give it a message at least 10 characters long.
- **Hints:** `("`Fix` or `update` on their own don't tell anyone what changed.", "Aim for something like `Add greeting to README`.")`
- **Seed:** init repo, create a file, stage and commit it with a minimal message (`"initial"`). Player must make a *new* commit.
- **Predicate:**
  ```python
  def check(sandbox: Path) -> CheckResult:
      count = subprocess.run(
          ["git", "rev-list", "--count", "HEAD"],
          cwd=sandbox, capture_output=True, text=True,
      )
      if count.returncode != 0 or int(count.stdout.strip() or 0) < 2:
          return CheckResult(False, "Make a new commit on top of the starting one.")
      msg = subprocess.run(
          ["git", "log", "-1", "--pretty=%s", "HEAD"],
          cwd=sandbox, capture_output=True, text=True, check=True,
      ).stdout.strip()
      if len(msg) < 10:
          return CheckResult(False, f"Your message is {len(msg)} chars — try for at least 10.")
      return CheckResult(True)
  ```

## Flexibility notes

- **Hint text is English in this spec** but final wording is Polish (to match the README). The data shape (`tuple[str, ...]`) doesn't care.
- **The 10-char commit message threshold** is arbitrary — easy to tune. The point is to force engagement with the message rather than `.`.
- **LANG=C in tests** pins locale for stable git output across dev machines. Production (when there is one) can inherit the player's locale.

## Open questions deferred to later specs

- Seeding story for non-trivial starting states (Level 2 "broken repo", Level 4 merge conflicts). v1 uses only trivial seed scripts.
- Safety hardening for `clone <url>` and other subcommands that take external input (Level 5).
- How the hint reveal interaction works from the UI side (UI spec, not engine).
- Typo-awareness while the player types. Engine only sees completed command lines; typo detection belongs to the UI.
