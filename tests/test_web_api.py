"""Tests for the FastAPI web API layer."""

from fastapi.testclient import TestClient

from gameofgit.web.server import app


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
        assert "app.js" in r.text  # script reference present


def test_create_game_and_run_init():
    with TestClient(app) as client:
        r = client.post("/api/game")
        assert r.status_code == 200
        game_id = r.json()["game_id"]
        quest = r.json()["quest"]
        assert quest["slug"] == "init-repo"
        assert quest["check_passed"] is False

        # Run git init
        r = client.post(f"/api/game/{game_id}/run", json={"cmdline": "git init"})
        assert r.status_code == 200
        body = r.json()
        assert body["exit_code"] == 0
        # Auto-advanced to the next quest
        assert body["advanced"] is True
        assert body["quest"]["slug"] == "stage-a-file"

        # Cleanup
        client.delete(f"/api/game/{game_id}")


def test_hint_reveals_one_at_a_time():
    with TestClient(app) as client:
        r = client.post("/api/game")
        gid = r.json()["game_id"]
        assert r.json()["quest"]["hints_revealed"] == []

        r = client.post(f"/api/game/{gid}/hint")
        assert len(r.json()["hints_revealed"]) == 1

        r = client.post(f"/api/game/{gid}/hint")
        assert len(r.json()["hints_revealed"]) == 2

        client.delete(f"/api/game/{gid}")


def test_suggest_endpoint_returns_correction_for_typo():
    with TestClient(app) as client:
        r = client.post("/api/game")
        gid = r.json()["game_id"]

        r = client.post(f"/api/game/{gid}/suggest", json={"cmdline": "gti init"})
        assert r.status_code == 200
        assert r.json()["suggestion"] == "git init"

        r = client.post(f"/api/game/{gid}/suggest", json={"cmdline": "git init"})
        assert r.json()["suggestion"] is None

        client.delete(f"/api/game/{gid}")


def test_rejected_command_does_not_advance():
    with TestClient(app) as client:
        r = client.post("/api/game")
        gid = r.json()["game_id"]
        orig_slug = r.json()["quest"]["slug"]

        r = client.post(f"/api/game/{gid}/run", json={"cmdline": "rm -rf /"})
        assert r.status_code == 200
        body = r.json()
        assert body["exit_code"] == 127
        assert body["advanced"] is False
        assert body["quest"]["slug"] == orig_slug

        client.delete(f"/api/game/{gid}")


def test_full_level1_playthrough():
    """Drive all 4 quests to level complete via the HTTP API."""
    with TestClient(app) as client:
        r = client.post("/api/game")
        gid = r.json()["game_id"]

        # Quest 1: git init
        r = client.post(f"/api/game/{gid}/run", json={"cmdline": "git init"})
        assert r.json()["advanced"] is True

        # Quest 2: stage a file. The API doesn't expose file writes, so we
        # reach into the sandbox via the games module (same approach used in
        # the engine's own session e2e tests).
        from gameofgit.web.games import get_game
        g = get_game(gid)
        (g.session._sandbox.path / "README.md").write_text("hello\n")

        r = client.post(f"/api/game/{gid}/run", json={"cmdline": "git add README.md"})
        assert r.json()["advanced"] is True

        # Quest 3: first-commit (file already staged by the seed)
        r = client.post(f"/api/game/{gid}/run", json={"cmdline": 'git commit -m "initial"'})
        assert r.json()["advanced"] is True

        # Quest 4: meaningful-message (need ≥10-char message on a new commit)
        g = get_game(gid)
        (g.session._sandbox.path / "new.txt").write_text("new\n")
        client.post(f"/api/game/{gid}/run", json={"cmdline": "git add new.txt"})
        r = client.post(
            f"/api/game/{gid}/run",
            json={"cmdline": 'git commit -m "Add greeting to new file"'},
        )
        body = r.json()
        assert body["advanced"] is False
        assert body["level_complete"] is True

        client.delete(f"/api/game/{gid}")
