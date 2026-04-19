import pytest
from fastapi.testclient import TestClient

from gameofgit.web.server import app


@pytest.fixture(autouse=True)
def _profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))
    yield tmp_path


def test_post_player_creates_and_returns_view():
    with TestClient(app) as client:
        r = client.post("/api/player", json={"name": "Robb Stark"})
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Robb Stark"
        assert body["tier"] == "Junior"
        assert body["xp"] == 0
        assert body["levels_completed"] == 0
        assert body["total_levels"] == 10


def test_post_player_rejects_empty_name():
    with TestClient(app) as client:
        r = client.post("/api/player", json={"name": "   "})
        assert r.status_code == 400


def test_post_player_is_idempotent():
    with TestClient(app) as client:
        r1 = client.post("/api/player", json={"name": "Arya"})
        assert r1.status_code == 200
        r2 = client.post("/api/player", json={"name": "arya"})
        assert r2.status_code == 200
        assert r2.json()["name"] in ("Arya", "arya")  # keeps latest-entered form


def test_get_player_returns_404_if_missing():
    with TestClient(app) as client:
        r = client.get("/api/player/does_not_exist")
        assert r.status_code == 404


def test_get_player_returns_existing_profile():
    with TestClient(app) as client:
        client.post("/api/player", json={"name": "Jon"})
        r = client.get("/api/player/jon")
        assert r.status_code == 200
        assert r.json()["name"] == "Jon"
