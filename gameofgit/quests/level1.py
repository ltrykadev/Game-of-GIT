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
