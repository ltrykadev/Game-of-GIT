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
