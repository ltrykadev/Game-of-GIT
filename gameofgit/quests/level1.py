import subprocess
from pathlib import Path

from gameofgit.engine.env import hardened_env
from gameofgit.engine.quest import CheckResult, Quest, SessionState

_ALLOWED = frozenset({"init", "status", "add", "commit"})


def _run(args: list[str], cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run `args` under the hardened env, from `cwd`. Raises on non-zero exit."""
    return subprocess.run(
        args,
        cwd=cwd,
        env=hardened_env(),
        capture_output=capture,
        text=True,
        check=True,
    )


def _check_init_repo(sandbox: Path, _state: SessionState) -> CheckResult:
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
    xp=50,
    level=1,
    seed=None,
)


def _seed_initialized_repo(sandbox: Path) -> None:
    """Initialize a git repo in `sandbox` and set a local identity.

    A local identity is required because `git commit` refuses to run without
    one, and we don't want the engine depending on whatever identity the
    player happens to have in their global ~/.gitconfig. The env is also
    scrubbed of GIT_* vars and locale is pinned — same hardening the engine's
    executor applies.
    """
    _run(["git", "init", "-q"], cwd=sandbox)
    _run(["git", "config", "user.email", "player@gameofgit.local"], cwd=sandbox)
    _run(["git", "config", "user.name", "Player"], cwd=sandbox)


def _check_stage_a_file(sandbox: Path, _state: SessionState) -> CheckResult:
    result = _run(["git", "diff", "--cached", "--name-only"], cwd=sandbox, capture=True)
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
    xp=50,
    level=1,
    seed=_seed_initialized_repo,
)


def _seed_repo_with_staged_file(sandbox: Path) -> None:
    _seed_initialized_repo(sandbox)
    (sandbox / "README.md").write_text("hello\n")
    _run(["git", "add", "README.md"], cwd=sandbox)


def _check_first_commit(sandbox: Path, _state: SessionState) -> CheckResult:
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=sandbox,
        env=hardened_env(),
        capture_output=True,
        text=True,
    )
    if head.returncode != 0:
        return CheckResult(False, "HEAD doesn't point at any commit yet.")
    files = _run(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True)
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
    xp=75,
    level=1,
    seed=_seed_repo_with_staged_file,
)


def _seed_repo_with_initial_commit(sandbox: Path) -> None:
    _seed_repo_with_staged_file(sandbox)
    _run(["git", "commit", "-q", "-m", "initial"], cwd=sandbox)


def _check_meaningful_message(sandbox: Path, _state: SessionState) -> CheckResult:
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=sandbox,
        env=hardened_env(),
        capture_output=True,
        text=True,
    )
    if count.returncode != 0 or int(count.stdout.strip() or 0) < 2:
        return CheckResult(False, "Make a new commit on top of the starting one.")
    msg = _run(
        ["git", "log", "-1", "--pretty=%s", "HEAD"],
        cwd=sandbox,
        capture=True,
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
    xp=75,
    level=1,
    seed=_seed_repo_with_initial_commit,
)
