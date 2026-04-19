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
        if (
            len(argv) == 3
            and argv[0] == "git"
            and argv[1] == "branch"
            and argv[2] in ("-l", "--list")
        ):
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
    target = f" to {name}"
    return any(line.rstrip().endswith(target) for line in out.splitlines())


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
