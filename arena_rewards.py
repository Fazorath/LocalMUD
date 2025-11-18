from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

import ui
from items import Item

RANKS = ["bronze", "silver", "gold", "champion"]

RANK_THRESHOLDS: Dict[str, int] = {
    "bronze": 0,
    "silver": 20,
    "gold": 40,
    "champion": 75,
}

FAME_REWARDS: Dict[str, int] = {
    "bronze": 4,
    "silver": 6,
    "gold": 10,
    "champion": 20,
}

MARK_REWARD_RANGE: Dict[str, Tuple[int, int]] = {
    "bronze": (2, 4),
    "silver": (4, 7),
    "gold": (8, 12),
    "champion": (15, 25),
}

ITEM_REWARD_POOL: Dict[str, List[Tuple[str, str]]] = {
    "bronze": [
        ("leather_kit", "Leather Armor Kit"),
    ],
    "silver": [
        ("reinforced_spear", "Reinforced Practice Spear"),
        ("chipped_sapphire", "Chipped Sapphire"),
    ],
    "gold": [
        ("balanced_halberd", "Balanced Halberd"),
        ("chipped_ruby", "Chipped Ruby"),
    ],
    "champion": [
        ("honor_blade_replica", "Honor Guard Spear"),
        ("chipped_topaz", "Chipped Topaz"),
    ],
}


def fame_required_for(rank: str) -> int:
    return RANK_THRESHOLDS[rank]


def fame_reward(rank: str) -> int:
    return FAME_REWARDS.get(rank, 0)


def roll_mark_reward(rank: str) -> int:
    low, high = MARK_REWARD_RANGE.get(rank, (1, 2))
    return random.randint(low, high)


def maybe_roll_item(rank: str) -> Optional[Item]:
    pool = ITEM_REWARD_POOL.get(rank, [])
    if not pool:
        return None
    chance = 0.25 if rank != "champion" else 0.5
    if random.random() > chance:
        return None
    item_id, name = random.choice(pool)
    return Item(
        id=item_id,
        name=name,
        description=f"An award from the {rank.title()} tier of the arena.",
        type="reward",
        value=0,
    )


def format_arena_panel(player) -> str:
    lines = [ui.help_heading("Grand Arena Status")]
    lines.append(ui.section("Rank", player.arena_rank))
    lines.append(ui.section("Fame", str(player.fame)))
    next_rank = next((r for r in RANKS if fame_required_for(r) > player.fame), None)
    if next_rank:
        needed = fame_required_for(next_rank) - player.fame
        lines.append(ui.hint(f"{needed} fame to reach {next_rank.title()}."))
    lines.append(ui.section("Available tiers", describe_available_ranks(player)))
    lines.append(ui.section("Uncollected winnings", str(player.arena_winnings)))
    return "\n".join(lines)


def describe_available_ranks(player) -> str:
    unlocked = []
    for rank in RANKS:
        if can_access_rank(player, rank):
            unlocked.append(rank.title())
    return ", ".join(unlocked) if unlocked else "Bronze"


def can_access_rank(player, rank: str) -> bool:
    required = fame_required_for(rank)
    return player.fame >= required


def upgrade_rank_if_needed(player) -> None:
    for rank in reversed(RANKS):
        if player.fame >= fame_required_for(rank):
            player.arena_rank = rank.title()
            break

