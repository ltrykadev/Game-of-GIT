"""Level 6 — DAMAGE CONTROL quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level6 import (
    REVERT_A_PUBLIC_COMMIT,
    UNDO_A_COMMIT_KEEP_WORK,
    UNSTAGE_A_FILE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_unstage_a_file_pass(tmp_path):
    UNSTAGE_A_FILE.seed(tmp_path)
    assert UNSTAGE_A_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "restore", "--staged", "oath.txt"], cwd=tmp_path)
    assert UNSTAGE_A_FILE.check(tmp_path, _blank()).passed is True


def test_undo_a_commit_keep_work_pass(tmp_path):
    UNDO_A_COMMIT_KEEP_WORK.seed(tmp_path)
    assert UNDO_A_COMMIT_KEEP_WORK.check(tmp_path, _blank()).passed is False
    run_git(["git", "reset", "--soft", "HEAD~1"], cwd=tmp_path)
    assert UNDO_A_COMMIT_KEEP_WORK.check(tmp_path, _blank()).passed is True


def test_revert_a_public_commit_pass(tmp_path):
    REVERT_A_PUBLIC_COMMIT.seed(tmp_path)
    assert REVERT_A_PUBLIC_COMMIT.check(tmp_path, _blank()).passed is False
    bad_sha = run_git(
        ["git", "log", "--pretty=%H"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[1]
    run_git(["git", "revert", "--no-edit", bad_sha], cwd=tmp_path)
    assert REVERT_A_PUBLIC_COMMIT.check(tmp_path, _blank()).passed is True
