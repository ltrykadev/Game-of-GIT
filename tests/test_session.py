from pathlib import Path

import pytest

from gameofgit.engine.quest import CheckResult, Quest
from gameofgit.engine.session import Outcome, QuestSession


def _quest(
    slug: str = "t",
    allowed: frozenset[str] = frozenset({"init", "status"}),
    check=lambda _p, _s: CheckResult(False),
    seed=None,
) -> Quest:
    return Quest(
        slug=slug,
        title="T",
        brief="b",
        hints=(),
        allowed=allowed,
        check=check,
        xp=1,
        level=1,
        seed=seed,
    )


def test_session_creates_and_destroys_sandbox():
    q = _quest()
    with QuestSession(q) as s:
        assert s._sandbox.path.is_dir()
        p = s._sandbox.path
    assert not p.exists()


def test_session_runs_initial_check_and_stores_it():
    calls = []

    def check(path, state):
        calls.append(path)
        return CheckResult(False, "initial")

    q = _quest(check=check)
    with QuestSession(q) as s:
        # __init__ must have run the predicate once.
        assert len(calls) == 1
        assert s._last_check == CheckResult(False, "initial")


def test_session_seed_runs_and_receives_path():
    recorded: dict[str, Path] = {}

    def seed(path: Path) -> None:
        recorded["path"] = path
        (path / "marker").write_text("seeded\n")

    q = _quest(seed=seed)
    with QuestSession(q) as s:
        assert recorded["path"] == s._sandbox.path
        assert (s._sandbox.path / "marker").read_text() == "seeded\n"


def test_session_seed_failure_cleans_up_and_reraises():
    captured: dict[str, Path] = {}

    def seed(path: Path) -> None:
        captured["path"] = path
        raise RuntimeError("bad seed")

    q = _quest(seed=seed)
    with pytest.raises(RuntimeError, match="bad seed"):
        QuestSession(q)
    assert not captured["path"].exists()


def test_session_empty_command_is_noop():
    q = _quest(check=lambda _p, _s: CheckResult(True, "already done"))
    with QuestSession(q) as s:
        out = s.run("")
        assert isinstance(out, Outcome)
        assert out.exit_code == 0
        assert out.stdout == ""
        assert out.stderr == ""
        # Empty command re-uses the stored _last_check.
        assert out.check.passed is True
        assert out.check.detail == "already done"


def test_session_non_git_command_returns_127():
    q = _quest()
    with QuestSession(q) as s:
        out = s.run("rm -rf /")
        assert out.exit_code == 127
        assert "rm:" in out.stderr
        assert "not available" in out.stderr


def test_session_disallowed_subcommand_returns_127():
    q = _quest(allowed=frozenset({"init"}))
    with QuestSession(q) as s:
        out = s.run("git rebase main")
        assert out.exit_code == 127
        assert "rebase" in out.stderr


def test_session_parser_reject_does_not_rerun_check():
    calls = 0

    def check(_p, _s):
        nonlocal calls
        calls += 1
        return CheckResult(False)

    q = _quest(check=check)
    with QuestSession(q) as s:
        assert calls == 1  # initial
        s.run("rm -rf /")
        assert calls == 1  # parser reject: check NOT re-run
        s.run("")  # empty command: also no re-run
        assert calls == 1


def test_session_successful_git_reruns_check_and_can_complete_quest():
    calls = 0

    def check(path, _s):
        nonlocal calls
        calls += 1
        return CheckResult((path / ".git").is_dir())

    q = _quest(check=check, allowed=frozenset({"init", "status"}))
    with QuestSession(q) as s:
        assert calls == 1
        out = s.run("git init")
        assert calls == 2
        assert out.exit_code == 0
        assert out.check.passed is True


def test_session_failing_git_still_reruns_check():
    # `git status` with no repo fails, but we still re-evaluate the predicate
    # afterward — the spec says "every real subprocess" triggers a re-check.
    calls = 0

    def check(_p, _s):
        nonlocal calls
        calls += 1
        return CheckResult(False)

    q = _quest(check=check, allowed=frozenset({"status"}))
    with QuestSession(q) as s:
        assert calls == 1
        out = s.run("git status")
        assert out.exit_code != 0  # git itself failed
        assert calls == 2  # but we still re-checked


def test_session_close_is_idempotent():
    q = _quest()
    s = QuestSession(q)
    s.close()
    s.close()  # second call must not raise


def test_session_malformed_command_returns_127_and_reuses_check():
    calls = {"n": 0}

    def check(_, _s):
        calls["n"] += 1
        return CheckResult(False, "not done")

    q = Quest(
        slug="x",
        title="x",
        brief="x",
        hints=(),
        allowed=frozenset({"status"}),
        check=check,
        xp=1,
        level=1,
        seed=None,
    )
    with QuestSession(q) as s:
        before = calls["n"]
        out = s.run('git commit -m "unterminated')
        assert out.exit_code == 127
        assert calls["n"] == before  # check NOT re-run
        assert out.check.passed is False


def test_session_tracks_last_argv_on_success(tmp_path, monkeypatch):
    """Successful commands are recorded in SessionState passed to the check."""
    from pathlib import Path
    from gameofgit.engine.quest import CheckResult, Quest, SessionState
    from gameofgit.engine.session import QuestSession

    captured: list[SessionState] = []

    def check(_: Path, state: SessionState) -> CheckResult:
        captured.append(state)
        return CheckResult(passed=False)

    q = Quest(
        slug="t", title="", brief="", hints=(),
        allowed=frozenset({"init", "status"}),
        check=check, xp=1, level=1, seed=None,
    )
    s = QuestSession(q)
    try:
        s.run("git init")
        s.run("git status")
    finally:
        s.close()

    # First capture is the initial post-seed check (no commands run yet)
    assert captured[0].last_argv is None
    assert captured[0].all_argv == []
    # After git init
    assert captured[1].last_argv == ("git", "init")
    # After git status — all_argv has both
    assert captured[-1].last_argv == ("git", "status")
    assert captured[-1].all_argv == [("git", "init"), ("git", "status")]


def test_session_does_not_record_failed_commands(tmp_path):
    """Commands that exit non-zero are not added to all_argv."""
    from pathlib import Path
    from gameofgit.engine.quest import CheckResult, Quest, SessionState
    from gameofgit.engine.session import QuestSession

    captured: list[SessionState] = []

    def check(_: Path, state: SessionState) -> CheckResult:
        captured.append(state)
        return CheckResult(passed=False)

    q = Quest(
        slug="t", title="", brief="", hints=(),
        allowed=frozenset({"status", "log"}),
        check=check, xp=1, level=1, seed=None,
    )
    s = QuestSession(q)
    try:
        # git log in an empty (non-initialized) dir fails
        s.run("git log")
    finally:
        s.close()

    # Only the initial pre-command capture exists; the failed log was not added
    assert all(c.all_argv == [] for c in captured)
