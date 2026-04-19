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
from gameofgit.quests.level4 import (
    CHERRY_PICK_ONE,
    FAST_FORWARD_MERGE,
    REBASE_A_BRANCH,
    RESOLVE_THE_CONFLICT,
)
from gameofgit.quests.level5 import (
    FETCH_THE_NEWS,
    INSPECT_REMOTES,
    PUSH_YOUR_WORK,
)
from gameofgit.quests.level6 import (
    REVERT_A_PUBLIC_COMMIT,
    UNDO_A_COMMIT_KEEP_WORK,
    UNSTAGE_A_FILE,
)

_LEVEL1 = (INIT_REPO, STAGE_A_FILE, FIRST_COMMIT, MEANINGFUL_MESSAGE)
_LEVEL2 = (READ_THE_LOG, SPOT_THE_DIFF, INSPECT_A_COMMIT)
_LEVEL3 = (LIST_THE_BRANCHES, MAKE_A_BRANCH, SWITCH_AND_RETURN)
_LEVEL4 = (FAST_FORWARD_MERGE, REBASE_A_BRANCH, CHERRY_PICK_ONE, RESOLVE_THE_CONFLICT)
_LEVEL5 = (INSPECT_REMOTES, FETCH_THE_NEWS, PUSH_YOUR_WORK)
_LEVEL6 = (UNSTAGE_A_FILE, UNDO_A_COMMIT_KEEP_WORK, REVERT_A_PUBLIC_COMMIT)


def all_quests() -> Iterable[Quest]:
    return _LEVEL1 + _LEVEL2 + _LEVEL3 + _LEVEL4 + _LEVEL5 + _LEVEL6


__all__ = ["all_quests"]
