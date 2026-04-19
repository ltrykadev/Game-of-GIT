"""FastAPI application — routes, static file serving, game API."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gameofgit.engine import suggest
from gameofgit.web.games import close_game, get_game, new_game
from gameofgit.web.schemas import (
    GameCreatedResponse,
    QuestView,
    RunRequest,
    RunResponse,
    SuggestRequest,
    SuggestResponse,
    quest_view,
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Game of GIT")

# Mount static assets (CSS, JS, etc.) — must be mounted before the catch-all routes.
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.middleware("http")
async def _no_cache_assets(request: Request, call_next):
    """Disable browser caching for HTML/JS/CSS so dev edits propagate.

    Without this, a stale `app.js` cached in the browser will keep running
    even after the file changes — symptom: newly added commands behave as
    though they don't exist. Targets the game pages and /static/, not API
    responses (which aren't cached anyway).
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path in ("/", "/play"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def index_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")


@app.get("/play", response_class=FileResponse, include_in_schema=False)
async def play_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "play.html", media_type="text/html")


# ---------------------------------------------------------------------------
# Game API
# ---------------------------------------------------------------------------


@app.post("/api/game", response_model=GameCreatedResponse)
async def create_game() -> GameCreatedResponse:
    """Create a new game, return the game_id and first quest view."""
    game = new_game()
    return GameCreatedResponse(game_id=game.id, quest=quest_view(game))


@app.post("/api/game/{gid}/run", response_model=RunResponse)
async def run_command(gid: str, req: RunRequest) -> RunResponse:
    """Run a git command in the game's sandbox. Auto-advances on quest pass."""
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    prev_passed = game.session._last_check.passed
    outcome = game.session.run(req.cmdline)

    advanced = False
    level_complete = False
    if outcome.check.passed and not prev_passed:
        if game.is_last_quest:
            level_complete = True
        else:
            game.advance()
            advanced = True

    return RunResponse(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        exit_code=outcome.exit_code,
        quest=quest_view(game),
        advanced=advanced,
        level_complete=level_complete,
    )


@app.post("/api/game/{gid}/hint", response_model=QuestView)
async def reveal_hint(gid: str) -> QuestView:
    """Reveal the next hint for the current quest (bumps hints_revealed by one)."""
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    quest = game.quest
    if game.hints_revealed < len(quest.hints):
        game.hints_revealed += 1

    return quest_view(game)


@app.post("/api/game/{gid}/suggest", response_model=SuggestResponse)
async def get_suggestion(gid: str, req: SuggestRequest) -> SuggestResponse:
    """Return a typo-corrected command line, or null if none needed."""
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    correction = suggest(req.cmdline, game.quest.allowed)
    return SuggestResponse(suggestion=correction)


@app.delete("/api/game/{gid}", status_code=204)
async def delete_game(gid: str) -> None:
    """Close the game's sandbox and remove it from the registry."""
    close_game(gid)
