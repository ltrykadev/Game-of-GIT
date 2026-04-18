import subprocess
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
