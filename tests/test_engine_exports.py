def test_engine_public_api_reexports():
    from gameofgit.engine import CheckResult, Outcome, Quest, QuestSession

    # Sanity: each import resolved to the real class, not a stub.
    assert Quest.__module__ == "gameofgit.engine.quest"
    assert CheckResult.__module__ == "gameofgit.engine.quest"
    assert Outcome.__module__ == "gameofgit.engine.session"
    assert QuestSession.__module__ == "gameofgit.engine.session"


def test_engine_all_declares_public_api():
    import gameofgit.engine as eng

    assert set(eng.__all__) == {"Quest", "CheckResult", "Outcome", "QuestSession"}
