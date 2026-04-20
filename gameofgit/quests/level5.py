"""Level 5 — REMOTE HACKER. Bare-repo origin, fetch, push."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity

_ALLOWED = frozenset({
    "remote", "fetch", "pull", "push", "log", "branch", "status",
})


def _bare_repo_for(sandbox: Path) -> Path:
    """Sibling dir to `sandbox` that serves as origin."""
    return sandbox.parent / (sandbox.name + ".origin.git")


def _seed_with_origin(sandbox: Path) -> None:
    bare = _bare_repo_for(sandbox)
    bare.mkdir(parents=True, exist_ok=True)
    run_git(["git", "init", "--bare", "-q", "-b", "main"], cwd=bare)

    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "readme.txt", "raven post\n", "first raven")
    run_git(["git", "remote", "add", "origin", str(bare)], cwd=sandbox)
    run_git(["git", "push", "-q", "-u", "origin", "main"], cwd=sandbox)


def _seed_remote_ahead(sandbox: Path) -> None:
    """Origin has a commit local doesn't yet have. Player must fetch to learn of it."""
    _seed_with_origin(sandbox)
    bare = _bare_repo_for(sandbox)
    # Spawn a helper clone, add a commit, push back to bare
    helper = sandbox.parent / (sandbox.name + ".helper")
    helper.mkdir(parents=True, exist_ok=True)
    run_git(["git", "clone", "-q", str(bare), "."], cwd=helper)
    set_identity(helper)
    commit_file(helper, "raven2.txt", "second raven\n", "raven from the Wall")
    run_git(["git", "push", "-q", "origin", "main"], cwd=helper)


def _seed_local_ahead(sandbox: Path) -> None:
    """Local is one commit ahead of origin. Player must push."""
    _seed_with_origin(sandbox)
    commit_file(sandbox, "raven_local.txt", "local raven\n", "from the keep")


def _check_inspect_remotes(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "remote":
            return CheckResult(True)
    return CheckResult(False, "Check who your remotes are with `git remote -v`.")


INSPECT_REMOTES = Quest(
    slug="inspect-remotes",
    title="Know the ravens.",
    brief="An `origin` remote is already configured. Ask git to list your remotes and their URLs.",
    hints=(
        "`git remote` alone just prints names. Add `-v` for verbose (URLs too).",
        "Try `git remote -v`.",
    ),
    allowed=_ALLOWED,
    check=_check_inspect_remotes,
    xp=75,
    level=5,
    seed=_seed_with_origin,
)


def _check_fetch_the_news(sandbox: Path, _state: SessionState) -> CheckResult:
    bare = _bare_repo_for(sandbox)
    bare_sha = run_git(
        ["git", "rev-parse", "main"], cwd=bare, capture=True
    ).stdout.strip()
    result = run_git(
        ["git", "rev-parse", "refs/remotes/origin/main"],
        cwd=sandbox,
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return CheckResult(False, "origin/main isn't known yet — try `git fetch`.")
    if result.stdout.strip() == bare_sha:
        return CheckResult(True)
    return CheckResult(False, "origin/main is still out of date — `git fetch` to catch up.")


FETCH_THE_NEWS = Quest(
    slug="fetch-the-news",
    title="Gather the ravens from the Wall.",
    brief=(
        "A scout at the Wall has posted a new commit to `origin`. "
        "Pull the news down — without touching your working branch."
    ),
    hints=(
        "`git fetch` updates `origin/main` without merging.",
        "After fetching, `git log origin/main` shows what the remote has.",
    ),
    allowed=_ALLOWED,
    check=_check_fetch_the_news,
    xp=125,
    level=5,
    seed=_seed_remote_ahead,
)


def _check_push_your_work(sandbox: Path, _state: SessionState) -> CheckResult:
    bare = _bare_repo_for(sandbox)
    bare_sha = run_git(
        ["git", "rev-parse", "main"], cwd=bare, capture=True
    ).stdout.strip()
    local_sha = run_git(
        ["git", "rev-parse", "main"], cwd=sandbox, capture=True
    ).stdout.strip()
    if local_sha == bare_sha:
        return CheckResult(True)
    return CheckResult(False, "Origin's main still trails your local — push it.")


PUSH_YOUR_WORK = Quest(
    slug="push-your-work",
    title="Send your decree across the realm.",
    brief=(
        "You have one local commit that `origin` hasn't yet seen. "
        "Push it so the whole realm shares the same history."
    ),
    hints=(
        "`git push` with no args pushes the current branch to its tracked upstream.",
        "`git push origin main` is the explicit form.",
    ),
    allowed=_ALLOWED,
    check=_check_push_your_work,
    xp=150,
    level=5,
    seed=_seed_local_ahead,
)
