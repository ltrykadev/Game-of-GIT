from gameofgit.web.schemas import PlayerView, QuestView, RunResponse


def test_player_view_expert_has_null_xp_to_next():
    v = PlayerView(
        name="n",
        tier="Expert",
        xp=4175,
        xp_to_next_tier=None,
        levels_completed=10,
        total_levels=10,
    )
    assert v.xp_to_next_tier is None


def test_quest_view_has_xp_and_level():
    v = QuestView(
        slug="s", title="t", brief="b",
        allowed=["init"], quest_index=0, total=1,
        hints_revealed=[], total_hints=0,
        check_passed=False, check_detail=None,
        xp=50, level=1,
    )
    assert v.xp == 50
    assert v.level == 1


def test_run_response_has_xp_awarded_and_player():
    qv = QuestView(
        slug="s", title="t", brief="b",
        allowed=["init"], quest_index=0, total=1,
        hints_revealed=[], total_hints=0,
        check_passed=False, check_detail=None,
        xp=50, level=1,
    )
    pv = PlayerView(
        name="n", tier="Junior", xp=0,
        xp_to_next_tier=1000, levels_completed=0, total_levels=10,
    )
    r = RunResponse(
        stdout="", stderr="", exit_code=0,
        quest=qv, advanced=False, level_complete=False,
        xp_awarded=50, player=pv,
    )
    assert r.xp_awarded == 50
    assert r.player.tier == "Junior"
