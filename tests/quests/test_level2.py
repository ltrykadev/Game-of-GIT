"""Level 2 — TIME TRAVELER quest tests."""
from pathlib import Path

from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import run_git
from gameofgit.quests.level2 import INSPECT_A_COMMIT, READ_THE_LOG, SPOT_THE_DIFF


def _blank_state():
    return SessionState(last_argv=None, all_argv=[])


def test_read_the_log_pass_after_running_log(tmp_path):
    READ_THE_LOG.seed(tmp_path)
    assert READ_THE_LOG.check(tmp_path, _blank_state()).passed is False
    state_after_log = SessionState(
        last_argv=("git", "log"),
        all_argv=[("git", "log")],
    )
    assert READ_THE_LOG.check(tmp_path, state_after_log).passed is True


def test_spot_the_diff_pass_after_running_diff(tmp_path):
    SPOT_THE_DIFF.seed(tmp_path)
    assert SPOT_THE_DIFF.check(tmp_path, _blank_state()).passed is False
    state = SessionState(last_argv=("git", "diff"), all_argv=[("git", "diff")])
    assert SPOT_THE_DIFF.check(tmp_path, state).passed is True


def test_inspect_a_commit_pass_after_show(tmp_path):
    INSPECT_A_COMMIT.seed(tmp_path)
    assert INSPECT_A_COMMIT.check(tmp_path, _blank_state()).passed is False
    # Get any real commit sha
    sha = run_git(
        ["git", "log", "--pretty=%H", "-n", "2"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[-1]  # not HEAD
    state = SessionState(
        last_argv=("git", "show", sha),
        all_argv=[("git", "show", sha)],
    )
    assert INSPECT_A_COMMIT.check(tmp_path, state).passed is True
