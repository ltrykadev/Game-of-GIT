"""Level 3 — BRANCH MASTER quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level3 import (
    LIST_THE_BRANCHES,
    MAKE_A_BRANCH,
    SWITCH_AND_RETURN,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_list_the_branches_pass_after_branch(tmp_path):
    LIST_THE_BRANCHES.seed(tmp_path)
    assert LIST_THE_BRANCHES.check(tmp_path, _blank()).passed is False
    state = SessionState(last_argv=("git", "branch"), all_argv=[("git", "branch")])
    assert LIST_THE_BRANCHES.check(tmp_path, state).passed is True


def test_make_a_branch_pass_after_creating_one(tmp_path):
    MAKE_A_BRANCH.seed(tmp_path)
    assert MAKE_A_BRANCH.check(tmp_path, _blank()).passed is False
    run_git(["git", "branch", "kingsguard"], cwd=tmp_path)
    assert MAKE_A_BRANCH.check(tmp_path, _blank()).passed is True


def test_switch_and_return_pass_after_round_trip(tmp_path):
    SWITCH_AND_RETURN.seed(tmp_path)
    assert SWITCH_AND_RETURN.check(tmp_path, _blank()).passed is False
    run_git(["git", "checkout", "dragonstone"], cwd=tmp_path)
    run_git(["git", "checkout", "main"], cwd=tmp_path)
    assert SWITCH_AND_RETURN.check(tmp_path, _blank()).passed is True
