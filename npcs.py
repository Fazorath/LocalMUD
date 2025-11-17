from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

import quests

if TYPE_CHECKING:
    from player import Player
    from game_state import GameState

DialogueHandler = Callable[["Player", "GameState"], List[str]]


@dataclass
class CombatProfile:
    hp: int
    weapon_id: str
    weapon_skill: Dict[str, int]
    preferred_stances: List[str]
    aggression: int
    awareness: int

    @classmethod
    def from_template(cls, data: dict) -> "CombatProfile":
        return cls(
            hp=int(data.get("hp", 20)),
            weapon_id=data.get("weapon", "training_spear"),
            weapon_skill={weapon: int(value) for weapon, value in data.get("weapon_skill", {}).items()},
            preferred_stances=data.get("preferred_stances", ["balanced"]),
            aggression=int(data.get("aggression", 50)),
            awareness=int(data.get("awareness", 50)),
        )


@dataclass
class NPC:
    id: str
    name: str
    role: str
    room_id: str
    lines: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    dialogue_id: Optional[str] = None
    on_talk: Optional[DialogueHandler] = None
    combat_profile: Optional[CombatProfile] = None

    @classmethod
    def from_template(cls, data: dict) -> "NPC":
        combat_profile = None
        if data.get("combat_profile"):
            combat_profile = CombatProfile.from_template(data["combat_profile"])
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            role=data.get("role", ""),
            room_id=data.get("room_id", ""),
            lines=list(data.get("lines", [])),
            interactions=list(data.get("interactions", [])),
            dialogue_id=data.get("dialogue_id"),
            combat_profile=combat_profile,
        )

def quartermaster_on_talk(player: "Player", game_state: "GameState") -> List[str]:
    messages: List[str] = ["The quartermaster looks you over, then nods slowly."]
    log = player.quest_log
    errand = log.active_quests.get("first_errand")
    completed = log.completed_quests.get("first_errand")

    if not errand and not completed:
        quest_message = quests.give_quest_if_available(player, "first_errand")
        if quest_message:
            messages.append(quest_message)
            errand = log.active_quests.get("first_errand")
            if errand and errand.current_step == 0:
                errand.advance()
                messages.append("The quartermaster grunts their approval as you report in.")
            messages.append("Bring me a training spear from storage, then report back.")
        else:
            messages.append("Supplies are handled for now. Check back later.")
        return messages

    if errand and not errand.is_completed:
        if errand.current_step == 0:
            errand.advance()
            messages.append("Don't dawdle—head to storage and fetch that spear.")
        elif errand.current_step == 1:
            messages.append("Once you've got it, see the sergeant in the barracks.")
        else:
            messages.append("Deliver the gear to the barracks and get signed off.")
        return messages

    messages.append("Good work on the errand. Stay sharp for the next assignment.")
    return messages

