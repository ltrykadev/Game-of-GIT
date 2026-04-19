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


def test_unstage_rejects_file_deletion(tmp_path):
    UNSTAGE_A_FILE.seed(tmp_path)
    # Deleting the file + staging the deletion empties the index of oath.txt,
    # which the old check accepted. The new check must reject.
    (tmp_path / "oath.txt").unlink()
    run_git(["git", "add", "-A"], cwd=tmp_path)
    assert UNSTAGE_A_FILE.check(tmp_path, _blank()).passed is False


def test_revert_rejects_manual_delete_commit(tmp_path):
    REVERT_A_PUBLIC_COMMIT.seed(tmp_path)
    # Non-revert solution: manually rm the file and commit. Old check accepted
    # this; new check should reject (HEAD message must start with `Revert "`).
    (tmp_path / "bug.txt").unlink()
    run_git(["git", "add", "-A"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "-m", "goodbye bug"], cwd=tmp_path)
    assert REVERT_A_PUBLIC_COMMIT.check(tmp_path, _blank()).passed is False
