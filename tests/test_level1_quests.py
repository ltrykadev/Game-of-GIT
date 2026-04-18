import subprocess

from gameofgit.quests.level1 import INIT_REPO, STAGE_A_FILE


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


def test_stage_a_file_seed_initializes_repo(tmp_path):
    assert STAGE_A_FILE.seed is not None
    STAGE_A_FILE.seed(tmp_path)
    assert (tmp_path / ".git").is_dir()


def test_stage_a_file_predicate_false_after_seed_only(tmp_path):
    STAGE_A_FILE.seed(tmp_path)
    r = STAGE_A_FILE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "staged" in r.detail.lower()


def test_stage_a_file_predicate_true_after_add(tmp_path):
    STAGE_A_FILE.seed(tmp_path)
    (tmp_path / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    r = STAGE_A_FILE.check(tmp_path)
    assert r.passed is True


def test_stage_a_file_quest_metadata():
    assert STAGE_A_FILE.slug == "stage-a-file"
    assert STAGE_A_FILE.allowed == frozenset({"init", "status", "add", "commit"})


def test_stage_a_file_seed_is_immune_to_ambient_git_dir(tmp_path, monkeypatch):
    # If seed respected an inherited GIT_DIR, `git init` would place .git
    # somewhere else (or fail). Hardened env must override it.
    bogus = tmp_path / "bogus-git"
    monkeypatch.setenv("GIT_DIR", str(bogus))
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    STAGE_A_FILE.seed(sandbox)
    assert (sandbox / ".git").is_dir()
    assert not bogus.exists()
