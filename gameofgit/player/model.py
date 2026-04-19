"""Player profile + tier derivation.

`completed_quests` is the source of truth. `xp` is denormalized for display
but is always recomputable from the quest catalog.
"""
from dataclasses import dataclass, field
from typing import Optional

from gameofgit.player.tiers import TierName, tier_for_levels_completed


@dataclass
class Player:
    name: str
    slug: str
    xp: int = 0
    completed_quests: set[str] = field(default_factory=set)

    @property
    def levels_completed(self) -> int:
        """Number of levels where every quest slug has been completed."""
        from gameofgit.quests import all_quests
        quests = list(all_quests())
        by_level: dict[int, set[str]] = {}
        for q in quests:
            by_level.setdefault(q.level, set()).add(q.slug)
        count = 0
        for level_slugs in by_level.values():
            if level_slugs.issubset(self.completed_quests):
                count += 1
        return count

    @property
    def tier(self) -> TierName:
        return tier_for_levels_completed(self.levels_completed)

    @property
    def xp_to_next_tier(self) -> Optional[int]:
        """XP remaining to the *next* tier title, or None if already Expert.

        Computed as: sum of XP for all quests in levels 1..N (where N is the
        first level count that promotes the player) minus current xp, clamped
        at 0.
        """
        from gameofgit.quests import all_quests
        current_tier = self.tier
        if current_tier == "Expert":
            return None
        target_levels_completed = 5 if current_tier == "Junior" else 10
        target_xp = sum(
            q.xp for q in all_quests() if q.level <= target_levels_completed
        )
        remaining = target_xp - self.xp
        return max(remaining, 0)
