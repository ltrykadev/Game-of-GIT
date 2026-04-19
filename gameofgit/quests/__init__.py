from collections.abc import Iterable

from gameofgit.engine.quest import Quest
from gameofgit.quests.level1 import (
    FIRST_COMMIT,
    INIT_REPO,
    MEANINGFUL_MESSAGE,
    STAGE_A_FILE,
)
from gameofgit.quests.level2 import (
    INSPECT_A_COMMIT,
    READ_THE_LOG,
    SPOT_THE_DIFF,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)
_LEVEL2 = (READ_THE_LOG, SPOT_THE_DIFF, INSPECT_A_COMMIT)


def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2


__all__ = ["all_quests"]
