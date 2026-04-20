"""Level 9 — CONFIG GOD quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level9 import LIST_THE_CONFIG, SET_YOUR_EMAIL, SET_YOUR_NAME


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_set_your_name_pass(tmp_path):
    SET_YOUR_NAME.seed(tmp_path)
    assert SET_YOUR_NAME.check(tmp_path, _blank()).passed is False
    run_git(["git", "config", "user.name", "Robb Stark"], cwd=tmp_path)
    assert SET_YOUR_NAME.check(tmp_path, _blank()).passed is True


def test_set_your_email_pass(tmp_path):
    SET_YOUR_EMAIL.seed(tmp_path)
    assert SET_YOUR_EMAIL.check(tmp_path, _blank()).passed is False
    run_git(["git", "config", "user.email", "robb@winterfell.north"], cwd=tmp_path)
    assert SET_YOUR_EMAIL.check(tmp_path, _blank()).passed is True


def test_list_the_config_pass(tmp_path):
    LIST_THE_CONFIG.seed(tmp_path)
    assert LIST_THE_CONFIG.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "config", "--list"),
        all_argv=[("git", "config", "--list")],
    )
    assert LIST_THE_CONFIG.check(tmp_path, state).passed is True
