"""In-memory game registry.

Thread-safety is not required — FastAPI runs single-process for this local game.
"""

import uuid
from dataclasses import dataclass, field

from gameofgit.engine import QuestSession
from gameofgit.quests import all_quests

_QUESTS = list(all_quests())


@dataclass
class Game:
    id: str
    quest_index: int
    session: QuestSession
    hints_revealed: int = 0

    @property
    def quest(self):
        return _QUESTS[self.quest_index]

    @property
    def is_last_quest(self) -> bool:
        return self.quest_index >= len(_QUESTS) - 1

    def advance(self) -> None:
        """Tear down current session, open a session for the next quest."""
        self.session.close()
        self.quest_index += 1
        self.session = QuestSession(self.quest)
        self.hints_revealed = 0

    def close(self) -> None:
        self.session.close()


_GAMES: dict[str, Game] = {}


def new_game() -> Game:
    gid = uuid.uuid4().hex
    quest = _QUESTS[0]
    g = Game(id=gid, quest_index=0, session=QuestSession(quest))
    _GAMES[gid] = g
    return g


def get_game(gid: str) -> Game | None:
    return _GAMES.get(gid)


def close_game(gid: str) -> None:
    g = _GAMES.pop(gid, None)
    if g is not None:
        g.close()


def total_quests() -> int:
    return len(_QUESTS)
