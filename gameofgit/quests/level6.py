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
