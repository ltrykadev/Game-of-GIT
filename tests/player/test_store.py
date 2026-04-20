import json

import pytest

from gameofgit.player.store import (
    InvalidName,
    load_or_create,
    save,
    slugify,
)


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def test_slugify_lowercases_and_strips():
    assert slugify("Robb Stark") == "robb_stark"
    assert slugify("ROBB STARK") == "robb_stark"
    assert slugify("  robb   stark  ") == "robb_stark"


def test_slugify_handles_polish_and_other_latin_diacritics():
    # Combining diacritics (NFKD decomposes these cleanly).
    assert slugify("Kraków") == "krakow"
    assert slugify("Héloïse") == "heloise"
    assert slugify("François") == "francois"
    assert slugify("Zażółć") == "zazolc"
    # Stroked letters need a manual map — NFKD alone leaves them alone.
    assert slugify("Łukasz") == "lukasz"
    assert slugify("Łódź") == "lodz"
    # Ligatures / eszett.
    assert slugify("Straße") == "strasse"
    assert slugify("Æther") == "aether"


def test_slugify_rejects_empty_after_normalization():
    with pytest.raises(InvalidName):
        slugify("   ")
    with pytest.raises(InvalidName):
        slugify("!!!")
    with pytest.raises(InvalidName):
        slugify("")


def test_load_or_create_creates_new_profile(_profiles_dir):
    p = load_or_create("Robb Stark")
    assert p.name == "Robb Stark"
    assert p.slug == "robb_stark"
    assert p.xp == 0
    assert p.completed_quests == set()
    # File was NOT written yet — creation without explicit save is in-memory only.
    assert not (_profiles_dir / "robb_stark.json").exists()


def test_save_then_load_roundtrip(_profiles_dir):
    p = load_or_create("Robb Stark")
    p.completed_quests = {"init-repo", "stage-a-file"}
    p.xp = 999  # wrong on purpose — should be recomputed on load
    save(p)

    # File exists
    data = json.loads((_profiles_dir / "robb_stark.json").read_text())
    assert data["slug"] == "robb_stark"
    assert set(data["completed_quests"]) == {"init-repo", "stage-a-file"}

    # Reload: xp is recomputed from catalog (not the stale 999)
    reloaded = load_or_create("Robb Stark")
    assert reloaded.completed_quests == {"init-repo", "stage-a-file"}
    assert reloaded.xp == 100  # 50 + 50 from Level 1


def test_slug_collision_shares_profile(_profiles_dir):
    a = load_or_create("Robb Stark")
    a.completed_quests = {"init-repo"}
    save(a)
    b = load_or_create("ROBB STARK")
    assert b.slug == "robb_stark"
    assert b.completed_quests == {"init-repo"}


def test_corrupt_json_falls_back_to_fresh(_profiles_dir):
    path = _profiles_dir / "corrupt.json"
    path.write_text("not json at all {{{")
    # Directly write a file under a slug the caller expects to exist
    p = load_or_create("corrupt")
    assert p.xp == 0
    assert p.completed_quests == set()


def test_invalid_name_raises(_profiles_dir):
    with pytest.raises(InvalidName):
        load_or_create("   ")
