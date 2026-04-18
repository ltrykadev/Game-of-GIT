import dataclasses

import pytest

from gameofgit.engine.quest import Quest, CheckResult


def test_check_result_defaults_to_no_detail():
    r = CheckResult(True)
    assert r.passed is True
    assert r.detail is None


def test_check_result_with_detail():
    r = CheckResult(False, "not yet")
    assert r.passed is False
    assert r.detail == "not yet"


def test_check_result_is_frozen():
    r = CheckResult(True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def _noop_check(_path):
    return CheckResult(False)


def test_quest_is_frozen():
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.slug = "y"  # type: ignore[misc]


def test_quest_seed_defaults_to_none():
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    assert q.seed is None


def test_quest_is_hashable_via_slug():
    # frozen dataclasses are hashable by default (all fields hash); a frozenset
    # of quest slugs would be the natural way to dedupe quests. We don't assert
    # equality semantics, only that __hash__ doesn't raise.
    q = Quest(
        slug="x",
        title="t",
        brief="b",
        hints=(),
        allowed=frozenset({"init"}),
        check=_noop_check,
    )
    hash(q)
