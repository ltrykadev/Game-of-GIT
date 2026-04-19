from dataclasses import dataclass

from gameofgit.player.model import Player


def _all_slugs_for_levels(n: int) -> set[str]:
    """Return every quest slug in Levels 1..n from the current catalog."""
    from gameofgit.quests import all_quests
    return {q.slug for q in all_quests() if q.level <= n}


@dataclass
class _StubQuest:
    """Minimal stand-in for Quest that exposes only the fields Player reads."""
    slug: str
    xp: int
    level: int


def _stub_catalog(levels: range, quests_per_level: int = 2):
    """Build a tuple of StubQuests spanning the given levels."""
    return tuple(
        _StubQuest(slug=f"L{lvl}-q{i}", xp=100, level=lvl)
        for lvl in levels
        for i in range(quests_per_level)
    )


def test_empty_player_is_junior():
    p = Player(name="Robb Stark", slug="robb_stark", xp=0, completed_quests=set())
    assert p.tier == "Junior"
    assert p.levels_completed == 0


def test_player_with_level_1_complete():
    p = Player(name="a", slug="a", xp=250, completed_quests=_all_slugs_for_levels(1))
    assert p.levels_completed == 1
    assert p.tier == "Junior"


def test_player_with_5_levels_is_senior(monkeypatch):
    """All quests in Levels 1-5 complete => Senior tier.

    Uses a stub catalog spanning 5 levels since Levels 2-10 aren't populated yet.
    """
    stubs = _stub_catalog(range(1, 6))
    monkeypatch.setattr("gameofgit.quests.all_quests", lambda: stubs)
    p = Player(name="a", slug="a", xp=0, completed_quests={q.slug for q in stubs})
    assert p.levels_completed == 5
    assert p.tier == "Senior"


def test_player_with_all_10_levels_is_expert(monkeypatch):
    """All 10 levels complete => Expert. Uses a 10-level stub catalog."""
    stubs = _stub_catalog(range(1, 11))
    monkeypatch.setattr("gameofgit.quests.all_quests", lambda: stubs)
    p = Player(name="a", slug="a", xp=0, completed_quests={q.slug for q in stubs})
    assert p.levels_completed == 10
    assert p.tier == "Expert"


def test_partial_level_does_not_count():
    # All of Level 1 except the last slug -> level is not counted complete
    slugs = _all_slugs_for_levels(1)
    slugs.pop()  # drop one slug
    p = Player(name="a", slug="a", xp=0, completed_quests=slugs)
    assert p.levels_completed == 0


def test_xp_to_next_tier_is_none_for_expert(monkeypatch):
    """Expert => no further tier => xp_to_next_tier is None."""
    stubs = _stub_catalog(range(1, 11))
    monkeypatch.setattr("gameofgit.quests.all_quests", lambda: stubs)
    p = Player(name="a", slug="a", xp=0, completed_quests={q.slug for q in stubs})
    assert p.xp_to_next_tier is None


def test_xp_to_next_tier_positive_for_junior():
    # With only Level 1 in the real catalog (250 XP total), a player at 0 XP has
    # 250 XP to go before the Junior->Senior gate. Not mocked -- relies on real catalog.
    p = Player(name="a", slug="a", xp=0, completed_quests=set())
    assert p.xp_to_next_tier is not None
    assert p.xp_to_next_tier > 0
