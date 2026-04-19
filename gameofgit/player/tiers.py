"""Tier constants and boundary logic.

A tier is a function of *levels completed* — not raw XP — so the player
always knows what milestone stands between them and the next title.
"""
from typing import Literal

TierName = Literal["Junior", "Senior", "Expert"]
TIERS: tuple[TierName, ...] = ("Junior", "Senior", "Expert")

_JUNIOR_MAX = 4   # 0..4 levels => Junior
_SENIOR_MAX = 9   # 5..9 levels => Senior
# 10 => Expert


def tier_for_levels_completed(n: int) -> TierName:
    if n <= _JUNIOR_MAX:
        return "Junior"
    if n <= _SENIOR_MAX:
        return "Senior"
    return "Expert"


def xp_required_for(tier: TierName) -> int:
    """Minimum cumulative XP needed to be *eligible* to first reach `tier`.

    This is informational — the actual gate is levels-complete. Returns 0 for
    Junior (everyone starts there).

    Concrete numbers are wired up in `model.xp_to_next_tier` using the
    current catalog. This function is a stable constant surface for tests
    that don't need catalog access.
    """
    if tier == "Junior":
        return 0
    if tier == "Senior":
        return 0  # level-gated, not XP-gated
    return 0      # level-gated, not XP-gated
