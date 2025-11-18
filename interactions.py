from __future__ import annotations

import random
from typing import Dict, List, Optional, Protocol, TYPE_CHECKING

import ui
from dialogue import DialogueManager
import arena_rewards

if TYPE_CHECKING:
    from game_state import GameState
    from npcs import NPC
    from player import Player


class Interaction(Protocol):
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
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

    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
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
            pre_prompt_lines.extend(self.dialogue_manager.apply_effects(root_node, player, npc, game_state))
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
            lines.extend(
                self.dialogue_manager.resolve_choice(tree, resolved_id, player, npc, game_state)
            )
        return lines


class TradeInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        return [ui.info("Trade is not yet implemented.")]


class GambleInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        return [ui.info("Gambling is not yet implemented.")]


class TrainingInteraction:
    CONFIG: Dict[str, Dict[str, object]] = {
        "spearmaster": {
            "message": "You run drills with Spearmaster Tevlek.",
            "weapon_type": "spear",
            "weapon_xp": (2, 5),
            "dodge_xp": (1, 3),
            "discipline": 1,
        },
        "drill_instructor": {
            "message": "You repeat blocking forms until your arms ache.",
            "weapon_type": "spear",
            "weapon_xp": (1, 3),
            "dodge_xp": (1, 2),
            "block": 1,
            "discipline": 1,
        },
        "agility_mentor": {
            "message": "You practice footwork with Liftfoot Mara.",
            "dodge_xp": (2, 4),
            "feint": 1,
        },
    }

    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        config = self.CONFIG.get(npc.id)
        if not config:
            return [ui.warning(f"{npc.name} has no drills to share right now.")]
        period = game_state.time_of_day
        if not player.can_train(npc.id, period):
            return [ui.hint(f"{npc.name} tells you to return once the next bell sounds.")]

        lines = [ui.info(config["message"])]
        fatigue = player.apply_training_fatigue(1)
        if fatigue:
            lines.append(ui.hint("Training taxes your endurance (-1 HP)."))

        weapon_type = config.get("weapon_type")
        if weapon_type:
            xp_range = config.get("weapon_xp", (2, 4))
            weapon_gain = random.randint(*xp_range)
            player.gain_weapon_xp(weapon_type, weapon_gain)
            lines.append(ui.success(f"Your {weapon_type} handling improves. (+{weapon_gain})"))

        dodge_range = config.get("dodge_xp")
        if dodge_range:
            dodge_gain = random.randint(*dodge_range)
            player.gain_dodge_xp(dodge_gain)
            lines.append(ui.success(f"Your footwork sharpens. (Dodge +{dodge_gain})"))

        if config.get("block"):
            player.gain_block_xp(config["block"])
            lines.append(ui.info("You internalize the drill instructor's lessons. (Block +1)"))
        if config.get("feint"):
            player.gain_feint_xp(config["feint"])
            lines.append(ui.info("You learn to feint with confidence. (Feint +1)"))
        if config.get("discipline"):
            player.gain_discipline_xp(config["discipline"])
            lines.append(ui.info("Your stance discipline steadies. (Discipline +1)"))

        player.register_training(npc.id, period)
        return lines


class SparInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        if npc.id != "spearmaster":
            return [ui.warning(f"{npc.name} declines to spar right now.")]
        from duel import Duel  # avoid circular import

        duel = Duel(player, npc, sparring=True)
        duel.run()
        player.gain_weapon_xp("spear", 1)
        player.gain_dodge_xp(1)
        return [
            ui.info(
                "Spearmaster Tevlek taps your shoulder. 'Good form, but keep your guard up.'"
            )
        ]


class ArenaPanelInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        return [arena_rewards.format_arena_panel(player)]


class JoinArenaInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        if player.current_room != "grand_arena":
            return [ui.warning("You must be in the grand arena to enlist.")]
        game_state.arena_queue_ready = True
        return [ui.info("Your name is added to the arena roster.")]


class BetPromptInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        return [
            ui.info("Use 'bet challenger <amount>' or 'bet opponent <amount>' to wager marks.")
        ]


class HealInteraction:
    def run(self, player: "Player", npc: "NPC", game_state: "GameState") -> List[str]:
        cost = 0 if player.fame < 5 else 1
        return [player.receive_medic_heal(cost)]

