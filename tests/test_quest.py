from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from gameofgit.engine.quest import CheckResult, Quest


def _always_pass(_: Path) -> CheckResult:
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


def test_quest_is_frozen():
    q = Quest(
        slug="demo",
        title="Demo",
        brief="a demo",
        hints=("hint",),
        allowed=frozenset({"status"}),
        check=_always_pass,
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
    )
    assert q.seed is None


def test_quest_is_hashable_via_slug():
    # frozen dataclass with hashable fields => hashable
    q1 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass)
    q2 = Quest(slug="a", title="", brief="", hints=(), allowed=frozenset(), check=_always_pass)
    # same field values -> equal and hashable
    assert q1 == q2
    assert hash(q1) == hash(q2)
