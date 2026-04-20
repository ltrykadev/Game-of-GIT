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
