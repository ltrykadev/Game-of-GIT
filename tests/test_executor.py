from gameofgit.engine.executor import ExecResult, execute


def test_execute_git_init_succeeds(tmp_path):
    result = execute(["git", "init"], cwd=tmp_path)
    assert isinstance(result, ExecResult)
    assert result.exit_code == 0
    assert (tmp_path / ".git").is_dir()


def test_execute_git_status_fails_outside_repo(tmp_path):
    result = execute(["git", "status"], cwd=tmp_path)
    assert result.exit_code != 0
    # With LANG=C pinned, the phrase is stable:
    assert "not a git repository" in result.stderr.lower()


def test_execute_captures_stdout(tmp_path):
    # 'git --version' always works, even outside a repo, and prints to stdout.
    result = execute(["git", "--version"], cwd=tmp_path)
    assert result.exit_code == 0
    assert result.stdout.startswith("git version")
    assert result.stderr == ""


def test_execute_timeout_returns_124(tmp_path):
    # Use 'sh -c sleep 2' with timeout 0.1 to force a TimeoutExpired.
    result = execute(["sh", "-c", "sleep 2"], cwd=tmp_path, timeout_s=0.1)
    assert result.exit_code == 124
    assert "timed out" in result.stderr.lower()
    assert result.stdout == ""


def test_execute_respects_cwd(tmp_path):
    # 'git init' only creates .git/ inside cwd; a second call in a subdir should
    # create a nested repo, not touch the parent.
    sub = tmp_path / "nested"
    sub.mkdir()
    execute(["git", "init"], cwd=sub)
    assert (sub / ".git").is_dir()
    assert not (tmp_path / ".git").exists()


def test_locale_pinned_despite_inherited_lc_all(tmp_path, monkeypatch):
    # Even if the caller's environment has a non-English locale, git error
    # messages must come back in English so downstream predicates can match them.
    monkeypatch.setenv("LC_ALL", "pl_PL.UTF-8")
    result = execute(["git", "status"], cwd=tmp_path)
    assert result.exit_code != 0
    assert "not a git repository" in result.stderr.lower()


def test_git_env_vars_scrubbed(tmp_path, monkeypatch):
    # A bogus GIT_DIR in the inherited env must not redirect git init away from
    # cwd — the executor should strip all GIT_* variables before running.
    bogus = str(tmp_path / "bogus_git_dir")
    monkeypatch.setenv("GIT_DIR", bogus)
    result = execute(["git", "init"], cwd=tmp_path)
    assert result.exit_code == 0
    assert (tmp_path / ".git").is_dir()
