from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from player import Player


@dataclass
class Quest:
    id: str
    name: str
    description: str
    steps: List[str]
    current_step: int = 0
    reward_spheres: int = 0
    is_completed: bool = False

    def advance(self) -> None:
        if self.is_completed:
            return
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
        else:
            self.complete()

    def complete(self) -> None:
        self.is_completed = True
        if self.steps:
            self.current_step = min(self.current_step, len(self.steps) - 1)


@dataclass
class QuestLog:
    active_quests: Dict[str, Quest] = field(default_factory=dict)
    completed_quests: Dict[str, Quest] = field(default_factory=dict)

    def add(self, quest: Quest) -> str:
        if quest.id in self.active_quests:
            return f"You already track the quest '{quest.name}'."
        if quest.id in self.completed_quests:
            return f"You have already completed '{quest.name}'."
        self.active_quests[quest.id] = quest
        return f"Quest '{quest.name}' added to your log."

    def complete(self, quest_id: str) -> Optional[Quest]:
        quest = self.active_quests.pop(quest_id, None)
        if not quest:
            return None
        quest.complete()
        self.completed_quests[quest_id] = quest
        return quest

    def list_active(self) -> str:
        if not self.active_quests:
            return "No active quests."
        lines = ["Active quests:"]
        for quest in self.active_quests.values():
            total = len(quest.steps)
            lines.append(f"- {quest.name} ({quest.current_step + 1}/{total})")
        return "\n".join(lines)

    def list_completed(self) -> str:
        if not self.completed_quests:
            return "No completed quests yet."
        lines = ["Completed quests:"]
        for quest in self.completed_quests.values():
            lines.append(f"- {quest.name} (Reward: {quest.reward_spheres} mark(s))")
        return "\n".join(lines)

    def describe(self, quest_id: str) -> Optional[str]:
        quest = self.active_quests.get(quest_id) or self.completed_quests.get(quest_id)
        if not quest:
            return None
        lines = [
            f"{quest.name}",
            quest.description,
            f"Reward: {quest.reward_spheres} mark(s)",
        ]
        for idx, step in enumerate(quest.steps):
            marker = "[x]" if idx < quest.current_step or quest.is_completed else "[ ]"
            if idx == quest.current_step and not quest.is_completed:
                marker = "[>]"
            lines.append(f"{marker} {step}")
        if quest.is_completed:
            lines.append("Status: Completed")
        else:
            lines.append(f"Current step: {quest.current_step + 1}/{len(quest.steps)}")
        return "\n".join(lines)


QUEST_TEMPLATES: Dict[str, Dict[str, object]] = {
    "first_errand": {
        "name": "First Errand",
        "description": "Prove your reliability by helping the quartermaster and handling basic supplies.",
        "steps": [
            "Speak to the quartermaster at the warcamp plateau.",
            "Retrieve a training_spear from the storage bay.",
            "Return to the barracks.",
        ],
        "reward_spheres": 2,
    },
    "chasm_scouting": {
        "name": "Chasm Scouting",
        "description": "Scout the chasm rim for Parshendi scouts and bring back proof of any encounter.",
        "steps": [
            "Travel to the chasm rim.",
            "Defeat any enemy present.",
            "Bring back proof to the barracks.",
        ],
        "reward_spheres": 3,
    },
}


def create_quest(quest_id: str) -> Optional[Quest]:
    template = QUEST_TEMPLATES.get(quest_id)
    if not template:
        return None
    return Quest(
        id=quest_id,
        name=template["name"],
        description=template["description"],
        steps=list(template["steps"]),
        reward_spheres=template["reward_spheres"],
    )


def _reward_player(player: "Player", quest: Quest) -> str:
    player.add_spheres(quest.reward_spheres)
    return f"Quest complete! You gain {quest.reward_spheres} infused mark(s)."


def process_room_entry(player: "Player", room_id: str) -> List[str]:
    messages: List[str] = []
    log = player.quest_log

    errand = log.active_quests.get("first_errand")
    if errand:
        if errand.current_step == 0 and room_id == "warcamp_plateau":
            errand.advance()
            messages.append("The quartermaster grunts their approval as you report in.")
        elif errand.current_step == 2 and room_id == "bridgeman_barracks":
            errand.advance()
            completed = log.complete("first_errand")
            if completed:
                messages.append("You deliver the supplies and the sergeant marks you present.")
                messages.append(_reward_player(player, completed))

    scouting = log.active_quests.get("chasm_scouting")
    if scouting:
        if scouting.current_step == 0 and room_id == "chasm_rim":
            scouting.advance()
            messages.append("Wind howls across the chasm as you begin the scouting run.")
        elif (
            scouting.current_step == 2
            and room_id == "bridgeman_barracks"
            and player.last_defeated_enemy_id
        ):
            scouting.advance()
            completed = log.complete("chasm_scouting")
            if completed:
                messages.append("You report the encounter to the duty officers.")
                messages.append(_reward_player(player, completed))
                player.last_defeated_enemy_id = None

    return messages


def process_item_pickup(player: "Player", item_id: str) -> List[str]:
    messages: List[str] = []
    errand = player.quest_log.active_quests.get("first_errand")
    if errand and errand.current_step == 1 and item_id == "training_spear":
        errand.advance()
        messages.append("You secure the requested spear and sling it over your shoulder.")
    return messages


def process_enemy_defeat(player: "Player", enemy_id: str) -> List[str]:
    messages: List[str] = []
    scouting = player.quest_log.active_quests.get("chasm_scouting")
    if scouting and scouting.current_step == 1:
        scouting.advance()
        player.last_defeated_enemy_id = enemy_id
        messages.append("You take a moment to collect proof of your victory.")
    return messages

