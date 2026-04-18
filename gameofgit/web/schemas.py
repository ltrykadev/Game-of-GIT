"""Pydantic models for the Game of GIT web API request/response payloads."""

from pydantic import BaseModel

from gameofgit.web.games import Game, total_quests


class QuestView(BaseModel):
    slug: str
    title: str
    brief: str
    allowed: list[str]
    quest_index: int
    total: int
    hints_revealed: list[str]   # text of hints already revealed
    total_hints: int
    check_passed: bool
    check_detail: str | None


class RunRequest(BaseModel):
    cmdline: str


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    quest: QuestView
    advanced: bool
    level_complete: bool


class SuggestRequest(BaseModel):
    cmdline: str


class SuggestResponse(BaseModel):
    suggestion: str | None


class GameCreatedResponse(BaseModel):
    game_id: str
    quest: QuestView


def quest_view(g: Game) -> QuestView:
    """Build a QuestView from the current game state."""
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
    )
