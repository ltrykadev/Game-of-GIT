"""Level 10 — GIT NINJA quest tests (final boss)."""
import os
import stat

from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level10 import (
    BLAME_A_LINE,
    FIND_THE_BUG,
    READ_THE_REFLOG,
    TAG_A_RELEASE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_read_the_reflog_pass(tmp_path):
    READ_THE_REFLOG.seed(tmp_path)
    assert READ_THE_REFLOG.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "reflog"),
        all_argv=[("git", "reflog")],
    )
    assert READ_THE_REFLOG.check(tmp_path, state).passed is True


def test_blame_a_line_pass(tmp_path):
    BLAME_A_LINE.seed(tmp_path)
    assert BLAME_A_LINE.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "blame", "chronicle.txt"),
        all_argv=[("git", "blame", "chronicle.txt")],
    )
    assert BLAME_A_LINE.check(tmp_path, state).passed is True


def test_tag_a_release_pass(tmp_path):
    TAG_A_RELEASE.seed(tmp_path)
    assert TAG_A_RELEASE.check(tmp_path, _blank()).passed is False
    run_git(["git", "tag", "-a", "v1.0", "-m", "first release"], cwd=tmp_path)
    assert TAG_A_RELEASE.check(tmp_path, _blank()).passed is True


def test_find_the_bug_pass_via_bisect_run(tmp_path):
    FIND_THE_BUG.seed(tmp_path)
    assert FIND_THE_BUG.check(tmp_path, _blank()).passed is False
    # Kick off bisect, mark endpoints, run
    run_git(["git", "bisect", "start"], cwd=tmp_path)
    run_git(["git", "bisect", "bad", "HEAD"], cwd=tmp_path)
    # good = commit #1 (oldest)
    first = run_git(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=tmp_path, capture=True,
    ).stdout.strip()
    run_git(["git", "bisect", "good", first], cwd=tmp_path)
    run_git(
        ["git", "bisect", "run", "./bisect_test.sh"],
        cwd=tmp_path, check=False,
    )
    assert FIND_THE_BUG.check(tmp_path, _blank()).passed is True
