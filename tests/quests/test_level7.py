"""Level 7 — STEALTH MODE quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level7 import (
    LIST_THE_STASHES,
    POP_A_STASH,
    STASH_YOUR_CHANGES,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_stash_your_changes_pass(tmp_path):
    STASH_YOUR_CHANGES.seed(tmp_path)
    assert STASH_YOUR_CHANGES.check(tmp_path, _blank()).passed is False
    run_git(["git", "stash"], cwd=tmp_path)
    assert STASH_YOUR_CHANGES.check(tmp_path, _blank()).passed is True


def test_list_the_stashes_pass(tmp_path):
    LIST_THE_STASHES.seed(tmp_path)
    assert LIST_THE_STASHES.check(tmp_path, _blank()).passed is False
    state = SessionState(
        last_argv=("git", "stash", "list"),
        all_argv=[("git", "stash", "list")],
    )
    assert LIST_THE_STASHES.check(tmp_path, state).passed is True


def test_pop_a_stash_pass(tmp_path):
    POP_A_STASH.seed(tmp_path)
    assert POP_A_STASH.check(tmp_path, _blank()).passed is False
    run_git(["git", "stash", "pop"], cwd=tmp_path)
    assert POP_A_STASH.check(tmp_path, _blank()).passed is True
