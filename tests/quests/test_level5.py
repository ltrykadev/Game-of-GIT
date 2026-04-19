"""Level 5 — REMOTE HACKER quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity
from gameofgit.quests.level5 import FETCH_THE_NEWS, INSPECT_REMOTES, PUSH_YOUR_WORK


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_inspect_remotes_pass_after_remote_v(tmp_path):
    INSPECT_REMOTES.seed(tmp_path)
    assert INSPECT_REMOTES.check(tmp_path, _blank()).passed is False
    state = SessionState(last_argv=("git", "remote", "-v"), all_argv=[("git", "remote", "-v")])
    assert INSPECT_REMOTES.check(tmp_path, state).passed is True


def test_fetch_the_news_pass_after_fetch(tmp_path):
    FETCH_THE_NEWS.seed(tmp_path)
    assert FETCH_THE_NEWS.check(tmp_path, _blank()).passed is False
    run_git(["git", "fetch", "origin"], cwd=tmp_path)
    assert FETCH_THE_NEWS.check(tmp_path, _blank()).passed is True


def test_push_your_work_pass_after_push(tmp_path):
    PUSH_YOUR_WORK.seed(tmp_path)
    assert PUSH_YOUR_WORK.check(tmp_path, _blank()).passed is False
    run_git(["git", "push", "origin", "main"], cwd=tmp_path)
    assert PUSH_YOUR_WORK.check(tmp_path, _blank()).passed is True
