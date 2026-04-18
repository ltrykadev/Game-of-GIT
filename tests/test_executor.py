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
