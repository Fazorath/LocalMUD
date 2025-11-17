from __future__ import annotations

from typing import Dict, List, Optional, Protocol, TYPE_CHECKING

import ui
from dialogue import DialogueManager

if TYPE_CHECKING:
    from npcs import NPC
    from player import Player


class Interaction(Protocol):
    def run(self, player: "Player", npc: "NPC") -> List[str]:
        ...


class InteractionRegistry:
    _registry: Dict[str, Interaction] = {}

    @classmethod
    def register(cls, name: str, interaction: Interaction) -> None:
        cls._registry[name] = interaction

    @classmethod
    def get(cls, name: str) -> Optional[Interaction]:
        return cls._registry.get(name)


class TalkInteraction:
    def __init__(self, dialogue_manager: DialogueManager):
        self.dialogue_manager = dialogue_manager

    def run(self, player: "Player", npc: "NPC") -> List[str]:
        lines: List[str] = []
        pre_prompt_lines: List[str] = []
        root_line = npc.lines[0] if npc.lines else None
        if root_line:
            pre_prompt_lines.append(ui.dialogue(npc.name, root_line))

        tree = self.dialogue_manager.get_tree(getattr(npc, "dialogue_id", None))
        if not tree:
            if npc.lines and len(npc.lines) > 1:
                pre_prompt_lines.append(ui.dialogue(npc.name, npc.lines[1]))
            for line in pre_prompt_lines:
                print(line)
            return []

        root_node = tree.get_node("root")
        if not root_node:
            for line in pre_prompt_lines:
                print(line)
            return [ui.warning(f"{npc.name} seems distracted.")]

        pre_prompt_lines.extend(self.dialogue_manager.format_node(npc.name, root_node))
        if not root_node.choices:
            pre_prompt_lines.extend(self.dialogue_manager.apply_effects(root_node, player))
            for line in pre_prompt_lines:
                print(line)
            return []

        pre_prompt_lines.extend(self.dialogue_manager.format_choices(root_node))
        for line in pre_prompt_lines:
            print(line)
        choice_input = input(ui.hint("Choose an option (number or id): ")).strip().lower()
        resolved_id: Optional[str] = None
        if choice_input.isdigit():
            idx = int(choice_input) - 1
            if 0 <= idx < len(root_node.choices):
                resolved_id = root_node.choices[idx].id
        else:
            for choice in root_node.choices:
                if choice.id.lower() == choice_input:
                    resolved_id = choice.id
                    break
        if not resolved_id and root_node.choices:
            resolved_id = root_node.choices[0].id
            lines.append(ui.hint("You hesitate, defaulting to the first option."))

        if resolved_id:
            lines.extend(self.dialogue_manager.resolve_choice(tree, resolved_id, player, npc.name))
        return lines


class TradeInteraction:
    def run(self, player: "Player", npc: "NPC") -> List[str]:
        return [ui.info("Trade is not yet implemented.")]


class GambleInteraction:
    def run(self, player: "Player", npc: "NPC") -> List[str]:
        return [ui.info("Gambling is not yet implemented.")]

