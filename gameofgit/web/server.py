"""FastAPI application — routes, static file serving, game API."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gameofgit.engine import suggest
from gameofgit.player.store import InvalidName, load_or_create, save
from gameofgit.web.games import close_game, get_game, new_game
from gameofgit.web.schemas import (
    CreateGameRequest,
    CreatePlayerRequest,
    GameCreatedResponse,
    PlayerView,
    QuestView,
    RunRequest,
    RunResponse,
    SuggestRequest,
    SuggestResponse,
    player_view,
    quest_view,
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Game of GIT")

app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.middleware("http")
async def _no_cache_assets(request: Request, call_next):
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
# Player API
# ---------------------------------------------------------------------------


@app.post("/api/player", response_model=PlayerView)
async def create_or_load_player(req: CreatePlayerRequest) -> PlayerView:
    try:
        player = load_or_create(req.name)
    except InvalidName as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Persist at least the name so /api/player/{slug} works on later requests.
    save(player)
    return player_view(player)


@app.get("/api/player/{slug}", response_model=PlayerView)
async def get_player(slug: str) -> PlayerView:
    # A slug here maps back to a real file if-and-only-if a profile exists.
    from pathlib import Path as _P
    from gameofgit.player.store import _path_for  # type: ignore[attr-defined]
    if not _path_for(slug).exists():
        raise HTTPException(status_code=404, detail="No such player.")
    player = load_or_create(slug)
    return player_view(player)


# ---------------------------------------------------------------------------
# Game API
# ---------------------------------------------------------------------------


@app.post("/api/game", response_model=GameCreatedResponse)
async def create_game(req: CreateGameRequest) -> GameCreatedResponse:
    from gameofgit.player.store import _path_for  # type: ignore[attr-defined]
    if not _path_for(req.player_slug).exists():
        raise HTTPException(
            status_code=400,
            detail="Unknown player. Create a profile first via POST /api/player.",
        )
    game = new_game(req.player_slug)
    return GameCreatedResponse(
        game_id=game.id,
        quest=quest_view(game),
        player=player_view(game.player),
    )


@app.post("/api/game/{gid}/run", response_model=RunResponse)
async def run_command(gid: str, req: RunRequest) -> RunResponse:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    prev_passed = game.session._last_check.passed
    outcome = game.session.run(req.cmdline)
    slug = game.quest.slug

    advanced = False
    level_complete = False
    xp_awarded = 0

    # XP: gated on player lifetime state — award once ever, per player.
    if outcome.check.passed and slug not in game.player.completed_quests:
        game.player.completed_quests.add(slug)
        game.player.xp += game.quest.xp
        xp_awarded = game.quest.xp
        save(game.player)

    # Advance: gated on session edge — only when this command flipped the check.
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
        xp_awarded=xp_awarded,
        player=player_view(game.player),
    )


@app.post("/api/game/{gid}/hint", response_model=QuestView)
async def reveal_hint(gid: str) -> QuestView:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    quest = game.quest
    if game.hints_revealed < len(quest.hints):
        game.hints_revealed += 1

    return quest_view(game)


@app.post("/api/game/{gid}/suggest", response_model=SuggestResponse)
async def get_suggestion(gid: str, req: SuggestRequest) -> SuggestResponse:
    game = get_game(gid)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    correction = suggest(req.cmdline, game.quest.allowed)
    return SuggestResponse(suggestion=correction)


@app.delete("/api/game/{gid}", status_code=204)
async def delete_game(gid: str) -> None:
    close_game(gid)
