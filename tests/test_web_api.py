"""Tests for the FastAPI web API layer."""

import pytest
from fastapi.testclient import TestClient

from gameofgit.web.server import app


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def _start_game(client: TestClient, name: str = "Tester") -> str:
    client.post("/api/player", json={"name": name})
    r = client.post("/api/game", json={"player_slug": name.lower()})
    assert r.status_code == 200
    return r.json()["game_id"]


def test_index_page_loads():
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "GAME OF GIT" in r.text or "Game of GIT" in r.text
        assert "PLAY" in r.text.upper()


def test_play_page_loads():
    with TestClient(app) as client:
        r = client.get("/play")
        assert r.status_code == 200
        assert "app.js" in r.text


def test_create_game_requires_known_player():
    with TestClient(app) as client:
        r = client.post("/api/game", json={"player_slug": "ghost"})
        assert r.status_code == 400


def test_create_game_and_run_init():
    with TestClient(app) as client:
        game_id = _start_game(client)
        r = client.post(f"/api/game/{game_id}/run", json={"cmdline": "git init"})
        assert r.status_code == 200
        body = r.json()
        assert body["exit_code"] == 0
        assert body["advanced"] is True
        assert body["xp_awarded"] == 50
        assert body["player"]["xp"] == 50
        assert body["quest"]["slug"] == "stage-a-file"
        client.delete(f"/api/game/{game_id}")


def test_xp_not_double_awarded_across_games():
    with TestClient(app) as client:
        # Game 1 — pass init-repo
        g1 = _start_game(client, "Dup")
        client.post(f"/api/game/{g1}/run", json={"cmdline": "git init"})
        client.delete(f"/api/game/{g1}")
        # Game 2 — same player, pass init-repo again
        g2 = _start_game(client, "Dup")
        r = client.post(f"/api/game/{g2}/run", json={"cmdline": "git init"})
        assert r.json()["xp_awarded"] == 0
        assert r.json()["player"]["xp"] == 50
        client.delete(f"/api/game/{g2}")


def test_hint_reveals_one_at_a_time():
    with TestClient(app) as client:
        gid = _start_game(client)
        assert client.post(f"/api/game/{gid}/hint").json()["hints_revealed"] != []
        client.delete(f"/api/game/{gid}")


def test_suggest_endpoint_returns_correction_for_typo():
    with TestClient(app) as client:
        gid = _start_game(client)
        r = client.post(f"/api/game/{gid}/suggest", json={"cmdline": "git innit"})
        assert r.status_code == 200
        assert r.json().get("suggestion")
        client.delete(f"/api/game/{gid}")
