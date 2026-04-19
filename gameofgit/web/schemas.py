"""Pydantic models for the Game of GIT web API request/response payloads."""

from typing import Literal

from pydantic import BaseModel

from gameofgit.player.model import Player
from gameofgit.web.games import Game, total_quests


class QuestView(BaseModel):
    slug: str
    title: str
    brief: str
    allowed: list[str]
    quest_index: int
    total: int
    hints_revealed: list[str]
    total_hints: int
    check_passed: bool
    check_detail: str | None
    xp: int
    level: int


class PlayerView(BaseModel):
    name: str
    tier: Literal["Junior", "Senior", "Expert"]
    xp: int
    xp_to_next_tier: int | None
    levels_completed: int
    total_levels: int


class RunRequest(BaseModel):
    cmdline: str


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    quest: QuestView
    advanced: bool
    level_complete: bool
    xp_awarded: int
    player: "PlayerView"


class SuggestRequest(BaseModel):
    cmdline: str


class SuggestResponse(BaseModel):
    suggestion: str | None


class CreatePlayerRequest(BaseModel):
    name: str


class CreateGameRequest(BaseModel):
    player_slug: str


class GameCreatedResponse(BaseModel):
    game_id: str
    quest: QuestView
    player: "PlayerView"


def player_view(player: Player) -> PlayerView:
    return PlayerView(
        name=player.name,
        tier=player.tier,
        xp=player.xp,
        xp_to_next_tier=player.xp_to_next_tier,
        levels_completed=player.levels_completed,
        total_levels=10,
    )


def quest_view(g: Game) -> QuestView:
    q = g.quest
    check = g.session._last_check
    return QuestView(
        slug=q.slug,
        title=q.title,
        brief=q.brief,
        allowed=sorted(q.allowed),
        quest_index=g.quest_index,
        total=total_quests(),
        hints_revealed=list(q.hints[: g.hints_revealed]),
        total_hints=len(q.hints),
        check_passed=check.passed,
        check_detail=check.detail,
        xp=q.xp,
        level=q.level,
    )
