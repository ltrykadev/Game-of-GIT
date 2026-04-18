import subprocess

from gameofgit.quests import all_quests
from gameofgit.quests.level1 import FIRST_COMMIT, INIT_REPO, MEANINGFUL_MESSAGE, STAGE_A_FILE


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


def test_first_commit_seed_stages_a_file(tmp_path):
    assert FIRST_COMMIT.seed is not None
    FIRST_COMMIT.seed(tmp_path)
    # After seed: repo exists, at least one file is staged.
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert r.stdout.strip() != ""


def test_first_commit_predicate_false_after_seed_only(tmp_path):
    FIRST_COMMIT.seed(tmp_path)
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "HEAD" in r.detail


def test_first_commit_predicate_true_after_commit(tmp_path):
    FIRST_COMMIT.seed(tmp_path)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial commit"],
        cwd=tmp_path,
        check=True,
    )
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is True


def test_first_commit_predicate_false_if_empty_commit(tmp_path):
    # Edge case: a commit with no files (allow-empty) must not satisfy the quest.
    FIRST_COMMIT.seed(tmp_path)
    subprocess.run(["git", "reset"], cwd=tmp_path, check=True)  # unstage
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "nothing"],
        cwd=tmp_path,
        check=True,
    )
    r = FIRST_COMMIT.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "no files" in r.detail.lower()


def test_meaningful_message_seed_has_one_commit(tmp_path):
    assert MEANINGFUL_MESSAGE.seed is not None
    MEANINGFUL_MESSAGE.seed(tmp_path)
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert count.stdout.strip() == "1"


def test_meaningful_message_predicate_false_after_seed_only(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "new commit" in r.detail.lower()


def test_meaningful_message_predicate_false_with_short_new_message(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    (tmp_path / "new.txt").write_text("new\n")
    subprocess.run(["git", "add", "new.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fix"],  # 3 chars, < 10
        cwd=tmp_path,
        check=True,
    )
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is False
    assert r.detail is not None
    assert "3 chars" in r.detail


def test_meaningful_message_predicate_true_with_long_new_message(tmp_path):
    MEANINGFUL_MESSAGE.seed(tmp_path)
    (tmp_path / "new.txt").write_text("new\n")
    subprocess.run(["git", "add", "new.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Add greeting to new file"],
        cwd=tmp_path,
        check=True,
    )
    r = MEANINGFUL_MESSAGE.check(tmp_path)
    assert r.passed is True


def test_all_quests_returns_all_level1_quests():
    quests = list(all_quests())
    slugs = {q.slug for q in quests}
    assert slugs == {
        "init-repo",
        "stage-a-file",
        "first-commit",
        "meaningful-message",
    }


def test_all_quests_preserves_level_order():
    # The return order determines the intended progression through the level.
    slugs = [q.slug for q in all_quests()]
    assert slugs == [
        "init-repo",
        "stage-a-file",
        "first-commit",
        "meaningful-message",
    ]
