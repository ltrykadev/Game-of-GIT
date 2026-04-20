"""Level 10 — GIT NINJA (final boss). reflog, blame, tag, bisect."""
import os
import stat
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity

_ALLOWED = frozenset({
    "reflog", "blame", "tag", "bisect", "log", "show", "status", "checkout",
})


def _seed_reflog_history(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    for i in range(5):
        commit_file(sandbox, f"page_{i}.txt", f"page {i}\n", f"page {i}")
    run_git(["git", "checkout", "-q", "-b", "side"], cwd=sandbox)
    run_git(["git", "checkout", "-q", "main"], cwd=sandbox)


def _check_read_the_reflog(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "reflog":
            return CheckResult(True)
    return CheckResult(False, "Try `git reflog`.")


READ_THE_REFLOG = Quest(
    slug="read-the-reflog",
    title="Consult the book of everything.",
    brief=(
        "The reflog remembers every move HEAD has ever made — even ones "
        "git log won't show you. Call it up."
    ),
    hints=(
        "`git reflog` prints the HEAD history.",
        "Useful for finding commits that seem lost after a reset.",
    ),
    allowed=_ALLOWED,
    check=_check_read_the_reflog,
    xp=125,
    level=10,
    seed=_seed_reflog_history,
)


def _seed_multi_author_chronicle(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    # Simulate "different authors" by changing identity per commit
    for i, name in enumerate(["Stark", "Lannister", "Targaryen", "Baratheon", "Tyrell"]):
        run_git(["git", "config", "user.name", name], cwd=sandbox)
        run_git(
            ["git", "config", "user.email", f"{name.lower()}@westeros"],
            cwd=sandbox,
        )
        existing = ""
        if (sandbox / "chronicle.txt").exists():
            existing = (sandbox / "chronicle.txt").read_text()
        (sandbox / "chronicle.txt").write_text(existing + f"line from {name}\n")
        run_git(["git", "add", "chronicle.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"entry by {name}"], cwd=sandbox)


def _check_blame_a_line(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "blame":
            return CheckResult(True)
    return CheckResult(False, "Try `git blame chronicle.txt`.")


BLAME_A_LINE = Quest(
    slug="blame-a-line",
    title="Name the hand that wrote this.",
    brief=(
        "`chronicle.txt` has five lines, each written by a different author. "
        "Ask git to annotate every line with who last touched it."
    ),
    hints=(
        "`git blame <file>` prints line-by-line attribution.",
        "`git blame` doesn't mean accusation — it's just the name of the tool.",
    ),
    allowed=_ALLOWED,
    check=_check_blame_a_line,
    xp=175,
    level=10,
    seed=_seed_multi_author_chronicle,
)


def _seed_for_tagging(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)
    commit_file(sandbox, "release.txt", "alpha\n", "alpha")
    commit_file(sandbox, "release.txt", "alpha\nbeta\n", "beta")


def _check_tag_a_release(sandbox: Path, _state: SessionState) -> CheckResult:
    out = run_git(
        ["git", "for-each-ref", "--format=%(objecttype) %(refname:short)", "refs/tags"],
        cwd=sandbox, capture=True,
    ).stdout.splitlines()
    annotated = [line for line in out if line.startswith("tag ")]
    if not annotated:
        return CheckResult(False, "Create an annotated tag (`git tag -a`).")
    # Check the first tag has a non-empty message
    tag_name = annotated[0].split(" ", 1)[1]
    msg = run_git(
        ["git", "tag", "-n99", "-l", tag_name], cwd=sandbox, capture=True
    ).stdout.strip()
    # Output looks like: "v1.0            the message here"
    parts = msg.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return CheckResult(False, "Your tag has no message — add `-m \"...\"`.")
    return CheckResult(True)


TAG_A_RELEASE = Quest(
    slug="tag-a-release",
    title="Name a version for the bards.",
    brief=(
        "Cut an annotated tag (like `v1.0`) on the current commit, with a "
        "message describing the release. Lightweight tags don't count — "
        "an annotated tag carries a message."
    ),
    hints=(
        "`git tag -a v1.0 -m \"first release\"` creates an annotated tag.",
        "`git tag` (no args) lists every tag.",
    ),
    allowed=_ALLOWED,
    check=_check_tag_a_release,
    xp=200,
    level=10,
    seed=_seed_for_tagging,
)


# -------------------- FINAL BOSS: bisect --------------------

_BISECT_TEST_OK = "#!/bin/sh\nexit 0\n"
_BISECT_TEST_FAIL = "#!/bin/sh\nexit 1\n"

_PLANTED_MARKER = "[PLANTED_BUG]"


def _seed_planted_bug(sandbox: Path) -> None:
    """Seed 15 commits. Commits 1-8 pass ./bisect_test.sh; 9-15 fail.

    Commit #9's message contains the PLANTED_MARKER. The bisect_test.sh
    file itself IS the bug — its content changes at commit #9.
    """
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    set_identity(sandbox)

    def _write_test(content: str) -> None:
        path = sandbox / "bisect_test.sh"
        path.write_text(content)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Commits 1..8: test passes
    _write_test(_BISECT_TEST_OK)
    run_git(["git", "add", "bisect_test.sh"], cwd=sandbox)
    run_git(["git", "commit", "-q", "-m", "commit 1: seed"], cwd=sandbox)
    for i in range(2, 9):
        (sandbox / f"chapter_{i}.txt").write_text(f"chapter {i}\n")
        run_git(["git", "add", f"chapter_{i}.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"commit {i}: clean"], cwd=sandbox)

    # Commit 9: the planted bug — test now fails
    _write_test(_BISECT_TEST_FAIL)
    run_git(["git", "add", "bisect_test.sh"], cwd=sandbox)
    run_git(
        ["git", "commit", "-q", "-m", f"commit 9: {_PLANTED_MARKER} broke the test"],
        cwd=sandbox,
    )

    # Commits 10..15: test still fails
    for i in range(10, 16):
        (sandbox / f"chapter_{i}.txt").write_text(f"chapter {i}\n")
        run_git(["git", "add", f"chapter_{i}.txt"], cwd=sandbox)
        run_git(["git", "commit", "-q", "-m", f"commit {i}: ignored"], cwd=sandbox)


def _check_find_the_bug(sandbox: Path, _state: SessionState) -> CheckResult:
    bisect_bad = sandbox / ".git" / "refs" / "bisect" / "bad"
    if not bisect_bad.exists():
        return CheckResult(
            False,
            "No bisect/bad ref yet — `git bisect start` and mark endpoints.",
        )
    sha = bisect_bad.read_text().strip()
    msg = run_git(
        ["git", "log", "-1", "--pretty=%s", sha], cwd=sandbox, capture=True
    ).stdout.strip()
    if _PLANTED_MARKER not in msg:
        return CheckResult(
            False,
            f"bisect/bad points at a commit without the {_PLANTED_MARKER} marker.",
        )
    return CheckResult(True)


FIND_THE_BUG = Quest(
    slug="find-the-bug",
    title="FINAL BOSS: Find the commit that broke the realm.",
    brief=(
        "There are 15 commits. One of them broke `./bisect_test.sh` — in early "
        "commits it exits 0, but somewhere along the way it started exiting 1. "
        "Use bisect to find the exact commit that introduced the bug.\n\n"
        "The `./bisect_test.sh` file is executable — `git bisect run` can "
        "automate the whole thing for you."
    ),
    hints=(
        "`git bisect start`, then `git bisect bad HEAD`, then `git bisect good <earliest-sha>` (find it with `git log --max-parents=0 --pretty=%H`).",
        "Then let git drive: `git bisect run ./bisect_test.sh`.",
    ),
    allowed=_ALLOWED,
    check=_check_find_the_bug,
    xp=500,
    level=10,
    seed=_seed_planted_bug,
)
