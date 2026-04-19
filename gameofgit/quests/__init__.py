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
from gameofgit.quests.level3 import (
    LIST_THE_BRANCHES,
    MAKE_A_BRANCH,
    SWITCH_AND_RETURN,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)
_LEVEL2 = (READ_THE_LOG, SPOT_THE_DIFF, INSPECT_A_COMMIT)
_LEVEL3 = (LIST_THE_BRANCHES, MAKE_A_BRANCH, SWITCH_AND_RETURN)


def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2 + _LEVEL3


__all__ = ["all_quests"]
