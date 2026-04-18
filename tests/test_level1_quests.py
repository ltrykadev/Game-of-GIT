import subprocess

from gameofgit.quests.level1 import INIT_REPO


def test_init_repo_predicate_false_on_empty_dir(tmp_path):
    r = INIT_REPO.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert ".git" in r.detail


def test_init_repo_predicate_true_after_git_init(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    r = INIT_REPO.check(tmp_path)
    assert r.passed is True
    assert r.detail is None


def test_init_repo_quest_metadata():
    assert INIT_REPO.slug == "init-repo"
    assert INIT_REPO.seed is None
    assert INIT_REPO.allowed == frozenset({"init", "status", "add", "commit"})
    assert len(INIT_REPO.hints) >= 1
