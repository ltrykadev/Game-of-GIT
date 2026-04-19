from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from gameofgit.engine.quest import CheckResult, Quest, SessionState


def _always_pass(_: Path, __: SessionState) -> CheckResult:
    return CheckResult(passed=True)


def test_check_result_defaults_to_no_detail():
    r = CheckResult(passed=True)
    assert r.passed is True
    assert r.detail is None


def test_check_result_with_detail():
    r = CheckResult(passed=False, detail="nope")
    assert r.detail == "nope"


def test_check_result_is_frozen():
    r = CheckResult(passed=True)
    with pytest.raises(FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def test_session_state_empty():
    s = SessionState(last_argv=None, all_argv=[])
    assert s.last_argv is None
    assert s.all_argv == []


def test_quest_is_frozen():
    q = Quest(
        slug="demo",
        title="Demo",
        brief="a demo",
        hints=("hint",),
        allowed=frozenset({"status"}),
        check=_always_pass,
        xp=100,
        level=1,
    )
    with pytest.raises(FrozenInstanceError):
        q.title = "Other"  # type: ignore[misc]


def test_quest_seed_defaults_to_none():
    q = Quest(
        slug="demo",
        title="Demo",
        brief="a demo",
        hints=(),
        allowed=frozenset(),
        check=_always_pass,
        xp=50,
        level=1,
    )
    assert q.seed is None


def test_quest_requires_xp_and_level():
    with pytest.raises(TypeError):
        Quest(  # type: ignore[call-arg]
            slug="no-xp",
            title="",
            brief="",
            hints=(),
            allowed=frozenset(),
            check=_always_pass,
        )


def test_quest_is_hashable_via_slug():
    q1 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass, xp=1, level=1)
    q2 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass, xp=1, level=1)
    assert q1 == q2
    assert hash(q1) == hash(q2)
