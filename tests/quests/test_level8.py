"""Level 8 — CLEANUP CREW quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level8 import (
    AMEND_YOUR_LAST_COMMIT,
    REMOVE_A_TRACKED_FILE,
    RENAME_A_FILE,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_remove_a_tracked_file_pass(tmp_path):
    REMOVE_A_TRACKED_FILE.seed(tmp_path)
    assert REMOVE_A_TRACKED_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "rm", "scroll.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "-m", "drop scroll"], cwd=tmp_path)
    assert REMOVE_A_TRACKED_FILE.check(tmp_path, _blank()).passed is True


def test_rename_a_file_pass(tmp_path):
    RENAME_A_FILE.seed(tmp_path)
    assert RENAME_A_FILE.check(tmp_path, _blank()).passed is False
    run_git(["git", "mv", "oldname.txt", "newname.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "-m", "rename"], cwd=tmp_path)
    assert RENAME_A_FILE.check(tmp_path, _blank()).passed is True


def test_amend_your_last_commit_pass(tmp_path):
    AMEND_YOUR_LAST_COMMIT.seed(tmp_path)
    assert AMEND_YOUR_LAST_COMMIT.check(tmp_path, _blank()).passed is False
    run_git(["git", "commit", "--amend", "-q", "-m", "Properly describe the work"], cwd=tmp_path)
    assert AMEND_YOUR_LAST_COMMIT.check(tmp_path, _blank()).passed is True


def test_amend_rejects_extra_commit(tmp_path):
    """Stacking a new commit with a good message must NOT pass — amend is verb-specific."""
    AMEND_YOUR_LAST_COMMIT.seed(tmp_path)
    run_git(
        ["git", "commit", "--allow-empty", "-q", "-m", "Reworked the WIP file"],
        cwd=tmp_path,
    )
    result = AMEND_YOUR_LAST_COMMIT.check(tmp_path, _blank())
    assert result.passed is False
    assert "more than one commit" in result.detail.lower()
