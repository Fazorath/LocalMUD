from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

import quests
import ui
from content_loader import ContentManager

if TYPE_CHECKING:
    from game_state import GameState
    from npcs import NPC
    from player import Player


@dataclass
class DialogueChoice:
    id: str
    text: str

    @classmethod
    def from_template(cls, data: dict) -> "DialogueChoice":
        return cls(id=data["id"], text=data["text"])


@dataclass
class DialogueNode:
    id: str
    text: str
    choices: List[DialogueChoice] = field(default_factory=list)
    effects: List[dict] = field(default_factory=list)
    next: Optional[str] = None
    end: bool = False

    @classmethod
    def from_template(cls, node_id: str, data: dict) -> "DialogueNode":
        choices = [DialogueChoice.from_template(choice) for choice in data.get("choices", [])]
        return cls(
            id=node_id,
            text=data.get("text", ""),
            choices=choices,
            effects=list(data.get("effects", [])),
            next=data.get("next"),
            end=data.get("end", False),
        )


@dataclass
class DialogueTree:
    id: str
    nodes: Dict[str, DialogueNode]

    @classmethod
    def from_template(cls, data: dict) -> "DialogueTree":
        node_templates = data.get("nodes", {})
        nodes = {
            node_id: DialogueNode.from_template(node_id, node_data)
            for node_id, node_data in node_templates.items()
        }
        return cls(id=data["id"], nodes=nodes)

    def get_node(self, node_id: str) -> Optional[DialogueNode]:
        return self.nodes.get(node_id)


class DialogueManager:
    def __init__(self) -> None:
        self.trees: Dict[str, DialogueTree] = {}
        self._interaction_runner: Optional[
            Callable[[str, "Player", "NPC", "GameState"], List[str]]
        ] = None

    def load(self, content_manager: ContentManager) -> None:
        self.trees = {
            tree_id: DialogueTree.from_template(payload)
            for tree_id, payload in content_manager.dialogue.items()
        }

    def get_tree(self, tree_id: Optional[str]) -> Optional[DialogueTree]:
        if not tree_id:
            return None
        return self.trees.get(tree_id)

    def set_interaction_runner(
        self, runner: Callable[[str, "Player", "NPC", "GameState"], List[str]]
    ) -> None:
        self._interaction_runner = runner

    def format_node(self, npc_name: str, node: DialogueNode) -> List[str]:
        lines = [ui.dialogue(npc_name, node.text)]
        return lines

    def format_choices(self, node: DialogueNode) -> List[str]:
        lines: List[str] = []
        for index, choice in enumerate(node.choices, start=1):
            lines.append(ui.bullet(f"{index}. {choice.text} ({choice.id})"))
        return lines

    def apply_effects(
        self, node: DialogueNode, player: "Player", npc: "NPC", game_state: "GameState"
    ) -> List[str]:
        results: List[str] = []
        for effect in node.effects:
            effect_type = effect.get("type")
            if effect_type == "offer_quest":
                quest_id = effect.get("quest_id")
                if quest_id:
                    quest_message = quests.give_quest_if_available(player, quest_id)
                    if quest_message:
                        results.append(ui.info(quest_message))
                    if effect.get("advance_step"):
                        quest = player.quest_log.active_quests.get(quest_id)
                        if quest and quest.current_step == 0:
                            quest.advance()
                            results.append(ui.info("The assignment has been noted in your log."))
            elif effect_type == "change_reputation":
                faction_id = effect.get("faction_id")
                amount = int(effect.get("amount", 0))
                if faction_id and amount:
                    player.change_reputation(faction_id, amount)
                    results.append(
                        ui.info(
                            f"Your standing with {faction_id.replace('_', ' ').title()} changes by {amount}."
                        )
                    )
            elif effect_type == "interaction":
                interaction_name = effect.get("name")
                if interaction_name and self._interaction_runner:
                    results.extend(
                        self._interaction_runner(interaction_name, player, npc, game_state)
                    )
        return results

    def resolve_choice(
        self,
        tree: DialogueTree,
        choice_id: str,
        player: "Player",
        npc: "NPC",
        game_state: "GameState",
    ) -> List[str]:
        lines: List[str] = []
        target_node = tree.get_node(choice_id)
        if not target_node:
            return [ui.warning("The conversation trails off awkwardly.")]
        lines.extend(self.format_node(npc.name, target_node))
        lines.extend(self.apply_effects(target_node, player, npc, game_state))
        if target_node.next:
            follow_up = tree.get_node(target_node.next)
            if follow_up:
                lines.extend(self.format_node(npc.name, follow_up))
        return lines


dialogue_manager = DialogueManager()

