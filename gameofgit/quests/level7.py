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
