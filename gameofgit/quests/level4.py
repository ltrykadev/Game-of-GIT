"""Level 4 — MERGE WARRIOR. Boss-fight level. Merges, rebases, cherry-picks,
and the sacred art of resolving conflicts.
"""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import (
    commit_file,
    run_git,
    set_identity,
    working_tree_clean,
)

_ALLOWED = frozenset({
    "merge", "rebase", "cherry-pick", "branch", "checkout", "switch",
    "status", "log", "add", "commit", "diff",
})


# -------------------- fast-forward merge --------------------

def _seed_ff_branches(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "chronicle.txt", "chapter 1\n", "the realm")
    run_git(["git", "checkout", "-q", "-b", "feature"], cwd=sandbox)
    commit_file(sandbox, "chronicle.txt", "chapter 1\nchapter 2\n", "added ch2")
    commit_file(sandbox, "chronicle.txt", "chapter 1\nchapter 2\nchapter 3\n", "added ch3")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_fast_forward_merge(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "You must be on main to take the banners home.")
    main_sha = run_git(["git", "rev-parse", "main"], cwd=sandbox, capture=True).stdout.strip()
    feature_sha = run_git(
        ["git", "rev-parse", "feature"], cwd=sandbox, capture=True
    ).stdout.strip()
    if main_sha == feature_sha:
        return CheckResult(True)
    return CheckResult(False, "`main` has not caught up to `feature` yet.")


FAST_FORWARD_MERGE = Quest(
    slug="fast-forward-merge",
    title="Bring the banner home.",
    brief=(
        "The `feature` branch has two commits `main` hasn't seen yet, and "
        "`main` has no commits of its own since they diverged. Merge cleanly — "
        "no new commit needed."
    ),
    hints=(
        "Make sure you're on `main` before merging.",
        "`git merge feature` will fast-forward when there's no divergence.",
    ),
    allowed=_ALLOWED,
    check=_check_fast_forward_merge,
    xp=150,
    level=4,
    seed=_seed_ff_branches,
)


# -------------------- rebase --------------------

def _seed_rebase_repo(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "base.txt", "base\n", "base")
    run_git(["git", "checkout", "-q", "-b", "feature"], cwd=sandbox)
    commit_file(sandbox, "feature.txt", "f1\n", "feature: f1")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)
    commit_file(sandbox, "main.txt", "m1\n", "main: m1")
    commit_file(sandbox, "main.txt", "m1\nm2\n", "main: m2")


def _check_rebase_a_branch(sandbox: Path, _state: SessionState) -> CheckResult:
    # main must be ancestor of feature
    r = run_git(
        ["git", "merge-base", "--is-ancestor", "main", "feature"],
        cwd=sandbox,
        check=False,
    )
    if r.returncode != 0:
        return CheckResult(False, "`main` is not yet an ancestor of `feature`.")
    # No merge commits on feature
    out = run_git(
        ["git", "log", "--merges", "main..feature", "--pretty=%H"],
        cwd=sandbox,
        capture=True,
    ).stdout.strip()
    if out:
        return CheckResult(False, "`feature` has merge commits — a true rebase is linear.")
    return CheckResult(True)


REBASE_A_BRANCH = Quest(
    slug="rebase-a-branch",
    title="Rewrite the feature's lineage.",
    brief=(
        "`main` has moved on while `feature` waited. Rebase `feature` onto "
        "the new tip of `main` so its commits descend cleanly from today's main."
    ),
    hints=(
        "Switch to `feature`, then run `git rebase main`.",
        "After rebasing, `git log feature` should show main's commits before feature's.",
    ),
    allowed=_ALLOWED,
    check=_check_rebase_a_branch,
    xp=175,
    level=4,
    seed=_seed_rebase_repo,
)


# -------------------- cherry-pick --------------------

def _seed_experiment(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "realm.txt", "realm\n", "found")
    run_git(["git", "checkout", "-q", "-b", "experiment"], cwd=sandbox)
    commit_file(sandbox, "potion_1.txt", "wolfsbane\n", "exp: first potion")
    commit_file(sandbox, "potion_2.txt", "nightshade\n", "exp: the chosen one")
    commit_file(sandbox, "potion_3.txt", "moonflower\n", "exp: third potion")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_cherry_pick_one(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "You must be on main.")
    # potion_2.txt must exist on main; potion_1 / potion_3 must NOT
    out = run_git(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=sandbox, capture=True
    ).stdout.split()
    has_2 = "potion_2.txt" in out
    has_1 = "potion_1.txt" in out
    has_3 = "potion_3.txt" in out
    if has_2 and not has_1 and not has_3:
        return CheckResult(True)
    return CheckResult(
        False,
        "You need exactly the middle potion on main — not the first or third.",
    )


CHERRY_PICK_ONE = Quest(
    slug="cherry-pick-one",
    title="Pick the chosen one.",
    brief=(
        "The `experiment` branch has three commits. Bring only the middle one "
        "over to `main` — no first, no third."
    ),
    hints=(
        "`git log experiment` shows all three in reverse order. The middle is second from the top.",
        "`git cherry-pick <hash>` copies one commit onto your current branch.",
    ),
    allowed=_ALLOWED,
    check=_check_cherry_pick_one,
    xp=175,
    level=4,
    seed=_seed_experiment,
)


# -------------------- conflict resolution (boss) --------------------

def _seed_conflict_repo(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne is empty.\n", "empty throne")
    run_git(["git", "checkout", "-q", "-b", "rebellion"], cwd=sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne belongs to the rebels.\n", "rebels")
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)
    commit_file(sandbox, "throne.txt", "The Iron Throne stands resolute.\n", "loyalist")


def _check_resolve_the_conflict(sandbox: Path, _state: SessionState) -> CheckResult:
    current = run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=sandbox, capture=True
    ).stdout.strip()
    if current != "main":
        return CheckResult(False, "Finish the fight on main.")
    # HEAD must be a merge commit
    parents = run_git(
        ["git", "log", "-1", "--pretty=%P"], cwd=sandbox, capture=True
    ).stdout.split()
    if len(parents) < 2:
        return CheckResult(False, "HEAD is not a merge commit — combine the branches.")
    # throne.txt must not contain conflict markers
    content = (sandbox / "throne.txt").read_text()
    if "<<<<<<<" in content or ">>>>>>>" in content or "=======" in content:
        return CheckResult(False, "Conflict markers remain in throne.txt.")
    if not working_tree_clean(sandbox):
        return CheckResult(False, "Working tree not clean — finish the commit.")
    return CheckResult(True)


RESOLVE_THE_CONFLICT = Quest(
    slug="resolve-the-conflict",
    title="BOSS: Settle the war of the throne.",
    brief=(
        "Both `main` and `rebellion` have rewritten `throne.txt` in ways that "
        "cannot both be true. Merge `rebellion` into `main`, resolve the "
        "conflict by hand (edit the file so no markers remain), stage it, "
        "and commit."
    ),
    hints=(
        "`git merge rebellion` — it will stop at the conflict.",
        "Open `throne.txt`, remove `<<<<<<<` / `=======` / `>>>>>>>` lines, keep the text you want. Then `git add throne.txt` and `git commit`.",
    ),
    allowed=_ALLOWED,
    check=_check_resolve_the_conflict,
    xp=250,
    level=4,
    seed=_seed_conflict_repo,
)
