"""Level 4 — MERGE WARRIOR quest tests."""
from gameofgit.engine.quest import SessionState
from gameofgit.quests._helpers import commit_file, run_git, set_identity
from gameofgit.quests.level4 import (
    CHERRY_PICK_ONE,
    FAST_FORWARD_MERGE,
    REBASE_A_BRANCH,
    RESOLVE_THE_CONFLICT,
)


def _blank():
    return SessionState(last_argv=None, all_argv=[])


def test_fast_forward_merge_pass(tmp_path):
    FAST_FORWARD_MERGE.seed(tmp_path)
    assert FAST_FORWARD_MERGE.check(tmp_path, _blank()).passed is False
    run_git(["git", "merge", "feature", "-q"], cwd=tmp_path)
    assert FAST_FORWARD_MERGE.check(tmp_path, _blank()).passed is True


def test_rebase_a_branch_pass(tmp_path):
    REBASE_A_BRANCH.seed(tmp_path)
    assert REBASE_A_BRANCH.check(tmp_path, _blank()).passed is False
    run_git(["git", "checkout", "feature", "-q"], cwd=tmp_path)
    run_git(["git", "rebase", "main", "-q"], cwd=tmp_path)
    assert REBASE_A_BRANCH.check(tmp_path, _blank()).passed is True


def test_cherry_pick_one_pass(tmp_path):
    CHERRY_PICK_ONE.seed(tmp_path)
    assert CHERRY_PICK_ONE.check(tmp_path, _blank()).passed is False
    middle_sha = run_git(
        ["git", "log", "experiment", "--pretty=%H"], cwd=tmp_path, capture=True
    ).stdout.splitlines()[1]
    run_git(["git", "cherry-pick", middle_sha], cwd=tmp_path, capture=True)
    assert CHERRY_PICK_ONE.check(tmp_path, _blank()).passed is True


def test_resolve_the_conflict_pass(tmp_path):
    RESOLVE_THE_CONFLICT.seed(tmp_path)
    assert RESOLVE_THE_CONFLICT.check(tmp_path, _blank()).passed is False
    # Trigger the conflict
    merge = run_git(
        ["git", "merge", "rebellion"], cwd=tmp_path, capture=True, check=False
    )
    assert merge.returncode != 0  # conflict expected
    # Resolve: pick our content, remove markers
    (tmp_path / "throne.txt").write_text("The Iron Throne stands resolute.\n")
    run_git(["git", "add", "throne.txt"], cwd=tmp_path)
    run_git(["git", "commit", "-q", "--no-edit"], cwd=tmp_path)
    assert RESOLVE_THE_CONFLICT.check(tmp_path, _blank()).passed is True
