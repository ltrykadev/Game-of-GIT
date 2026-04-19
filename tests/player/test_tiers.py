from gameofgit.player.tiers import TIERS, tier_for_levels_completed, xp_required_for


def test_tier_names_are_three():
    assert TIERS == ("Junior", "Senior", "Expert")


def test_tier_boundaries():
    assert tier_for_levels_completed(0) == "Junior"
    assert tier_for_levels_completed(4) == "Junior"
    assert tier_for_levels_completed(5) == "Senior"
    assert tier_for_levels_completed(9) == "Senior"
    assert tier_for_levels_completed(10) == "Expert"


def test_tier_clamps_above_10():
    assert tier_for_levels_completed(11) == "Expert"
    assert tier_for_levels_completed(99) == "Expert"


def test_xp_required_for_milestones():
    # Placeholder: will be refined in model tests. Here we just check the API shape.
    assert xp_required_for("Junior") == 0
    assert xp_required_for("Senior") >= 0
    assert xp_required_for("Expert") >= xp_required_for("Senior")
