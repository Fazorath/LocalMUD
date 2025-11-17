from __future__ import annotations

import random
from typing import Dict, List, Tuple

import ui
from content_loader import content_manager
from items import Item, Weapon, STARTING_ITEMS
from npcs import NPC
from player import Player, STANCE_PROFILES

ACTION_MODIFIERS: Dict[str, Dict[str, float]] = {
    "strike": {"hit": 0, "damage": 1.0, "dodge": 0, "armor": 0},
    "feint": {"hit": 12, "damage": 0.65, "dodge": 0, "armor": 0},
    "block": {"hit": -5, "damage": 0.75, "dodge": 6, "armor": 4},
    "dodge": {"hit": -12, "damage": 0.45, "dodge": 18, "armor": 0},
}

FISTS = Weapon(
    id="fists",
    name="your fists",
    description="Bare-knuckled determination.",
    type="weapon",
    damage_min=1,
    damage_max=2,
    weapon_type="fists",
)


class Duel:
    def __init__(self, player: Player, opponent: NPC, sparring: bool = False) -> None:
        if not opponent.combat_profile:
            raise ValueError("Opponent lacks a combat profile.")
        self.player = player
        self.opponent = opponent
        self.profile = opponent.combat_profile
        self.enemy_hp = self.profile.hp
        self.enemy_max_hp = self.profile.hp
        self.enemy_stance = (self.profile.preferred_stances or ["balanced"])[0]
        self.enemy_weapon = self._load_weapon(self.profile.weapon_id)
        self.enemy_strength = 6 + self.profile.aggression // 10
        self.enemy_dexterity = 5 + self.profile.awareness // 10
        self.active = True
        self.round = 1
        self._forced_yield = False
        self.sparring = sparring
        self._player_hp_snapshot = player.current_hp
        self._xp_multiplier = 2 if sparring else 1

    def run(self) -> None:
        print(ui.banner(f"You square off against {self.opponent.name}."))
        print(
            ui.hint(
                "Choose actions each exchange: strike / feint / block / dodge / "
                "stance <type> / yield"
            )
        )
        self.player.active_duel = self
        self.player.calculate_dodge_rating()
        try:
            while self.active and self.player.current_hp > 0 and self.enemy_hp > 0:
                print(ui.divider(char="="))
                print(ui.info(f"Round {self.round} - Stance: {self.player.stance.title()}"))
                player_choice = self._prompt_player_action()
                if player_choice["action"] == "yield":
                    self._player_yield()
                    break
                enemy_action = self._choose_enemy_action(player_choice)
                self._maybe_adjust_enemy_stance()
                self._resolve_round(player_choice, enemy_action)
                self.round += 1
        finally:
            self.player.active_duel = None
            self.active = False
            if self.sparring:
                self.player.current_hp = min(self.player.max_hp, self._player_hp_snapshot)
                self.player.calculate_dodge_rating()
        self._summarize_outcome()

    def request_yield(self) -> None:
        self._forced_yield = True
        self._player_yield()

    def _prompt_player_action(self) -> Dict[str, str]:
        choice = input(
            ui.hint("Action (strike/feint/block/dodge/stance <type>/yield): ")
        ).strip().lower()
        if not choice:
            return {"action": "strike"}
        if choice == "yield":
            return {"action": "yield"}
        if choice.startswith("stance"):
            parts = choice.split()
            if len(parts) >= 2:
                return {"action": "stance", "stance": parts[1]}
            return {"action": "stance", "stance": "balanced"}
        if choice in ACTION_MODIFIERS:
            return {"action": choice}
        return {"action": "strike"}

    def _choose_enemy_action(self, player_choice: Dict[str, str]) -> str:
        hp_ratio = self.enemy_hp / self.enemy_max_hp if self.enemy_max_hp else 1
        if hp_ratio < 0.2:
            return "dodge"
        roll = random.randint(1, 100)
        aggression = self.profile.aggression // 2 if self.sparring else self.profile.aggression
        if roll <= aggression:
            return "strike"
        if roll <= aggression + 15:
            return "feint"
        if hp_ratio < 0.5 and roll % 2 == 0:
            return "dodge"
        return random.choice(["strike", "block", "feint"])

    def _maybe_adjust_enemy_stance(self) -> None:
        hp_ratio = self.enemy_hp / self.enemy_max_hp if self.enemy_max_hp else 1
        desired = self.enemy_stance
        if hp_ratio < 0.3 and "defensive" in self.profile.preferred_stances:
            desired = "defensive"
        elif hp_ratio > 0.7 and "aggressive" in self.profile.preferred_stances:
            desired = "aggressive"
        else:
            desired = random.choice(self.profile.preferred_stances or ["balanced"])
        if desired != self.enemy_stance:
            self.enemy_stance = desired
            print(ui.hint(f"{self.opponent.name} shifts into a {desired} stance."))

    def _resolve_round(self, player_choice: Dict[str, str], enemy_action: str) -> None:
        player_action = self._normalize_player_action(player_choice)
        player_effect = ACTION_MODIFIERS.get(player_action, ACTION_MODIFIERS["strike"])
        enemy_effect = ACTION_MODIFIERS.get(enemy_action, ACTION_MODIFIERS["strike"])
        player_initiative = random.randint(1, 20) + self.player.effective_dexterity()
        enemy_initiative = random.randint(1, 20) + self.enemy_dexterity
        if player_action == "dodge":
            player_initiative += 2
        if enemy_action == "dodge":
            enemy_initiative += 2
        order = ["player", "enemy"] if player_initiative >= enemy_initiative else ["enemy", "player"]

        if player_action == "dodge":
            self.player.gain_dodge_xp(1)

        for actor in order:
            if not self.active:
                break
            if actor == "player":
                lines = self._player_offense(player_action, player_effect, enemy_effect)
                for line in lines:
                    print(line)
                if self.enemy_hp <= 0:
                    self.active = False
                    break
            else:
                lines = self._enemy_offense(enemy_action, enemy_effect, player_effect)
                for line in lines:
                    print(line)
                if self.player.current_hp <= 0:
                    self.active = False
                    break

    def _player_offense(
        self, action_name: str, player_effect: Dict[str, float], enemy_effect: Dict[str, float]
    ) -> List[str]:
        lines: List[str] = []
        weapon, weapon_type = self._player_weapon()
        stance_profile = STANCE_PROFILES[self.player.stance]
        weapon_skill = self.player.weapon_skill.get(weapon_type, self.player.weapon_skill["fists"])
        enemy_dodge = self._enemy_dodge_rating(enemy_effect)
        hit_score = (
            weapon_skill * 5
            + self.player.effective_strength()
            + stance_profile["hit"]
            + player_effect["hit"]
        )
        roll = random.randint(1, 100)
        if roll <= max(15, hit_score - enemy_dodge):
            damage = self._calculate_player_damage(weapon, player_effect, stance_profile)
            self.enemy_hp = max(0, self.enemy_hp - damage)
            self.player.gain_weapon_xp(weapon_type, 2 * self._xp_multiplier)
            lines.append(
                ui.success(
                    f"You {action_name} with the {weapon.name}, dealing {damage} damage. "
                    f"{self.opponent.name} has {self.enemy_hp} HP remaining."
                )
            )
        else:
            self.player.gain_weapon_xp(weapon_type, 1 * self._xp_multiplier)
            lines.append(ui.hint(f"Your {action_name} fails to connect."))
        if self.sparring and self.enemy_hp <= max(1, self.enemy_max_hp // 5):
            self.enemy_hp = max(1, self.enemy_hp)
            self.active = False
            lines.append(ui.info(f"{self.opponent.name} steps back, ending the spar."))
        return lines

    def _enemy_offense(
        self, action_name: str, enemy_effect: Dict[str, float], player_effect: Dict[str, float]
    ) -> List[str]:
        lines: List[str] = []
        stance_profile = STANCE_PROFILES.get(self.enemy_stance, STANCE_PROFILES["balanced"])
        weapon_type = getattr(self.enemy_weapon, "weapon_type", "spear")
        weapon_skill = self.profile.weapon_skill.get(weapon_type, 25)
        player_dodge = self.player.calculate_dodge_rating() + player_effect["dodge"]
        hit_score = (
            weapon_skill * 5
            + self.enemy_strength
            + stance_profile["hit"]
            + enemy_effect["hit"]
        )
        roll = random.randint(1, 100)
        if roll <= max(12, hit_score - player_dodge):
            damage = self._calculate_enemy_damage(enemy_effect, stance_profile)
            taken = self.player.take_damage(damage, armor_bonus=int(player_effect["armor"]))
            if self.sparring:
                taken = max(1, taken // 2)
                self.player.current_hp = max(1, self.player.current_hp)
            lines.append(
                ui.warning(
                    f"{self.opponent.name} {action_name}s for {taken} damage. "
                    f"You have {self.player.current_hp}/{self.player.max_hp} HP."
                )
            )
        else:
            self.player.gain_dodge_xp(1 * self._xp_multiplier)
            lines.append(ui.info(f"You evade {self.opponent.name}'s {action_name}."))
        return lines

    def _enemy_dodge_rating(self, enemy_effect: Dict[str, float]) -> int:
        stance_bonus = STANCE_PROFILES.get(self.enemy_stance, STANCE_PROFILES["balanced"])["dodge"]
        return self.enemy_dexterity * 2 + self.profile.awareness // 2 + stance_bonus + int(
            enemy_effect["dodge"]
        )

    def _calculate_player_damage(
        self, weapon: Weapon, player_effect: Dict[str, float], stance_profile: Dict[str, float]
    ) -> int:
        base = random.randint(weapon.damage_min, weapon.damage_max)
        strength_bonus = self.player.effective_strength()
        damage = (base + max(1, strength_bonus // 2)) * player_effect["damage"]
        damage *= stance_profile["damage"]
        if self.sparring:
            damage = max(1, damage // 2)
        return max(1, int(damage))

    def _calculate_enemy_damage(
        self, enemy_effect: Dict[str, float], stance_profile: Dict[str, float]
    ) -> int:
        base = random.randint(self.enemy_weapon.damage_min, self.enemy_weapon.damage_max)
        strength_bonus = self.enemy_strength // 2
        damage = (base + max(1, strength_bonus)) * enemy_effect["damage"]
        damage *= stance_profile["damage"]
        if self.sparring:
            damage = max(1, damage // 2)
        return max(1, int(damage))

    def _normalize_player_action(self, player_choice: Dict[str, str]) -> str:
        action = player_choice["action"]
        if action == "stance":
            stance_name = player_choice.get("stance", "balanced")
            print(self.player.change_stance(stance_name))
            return "block"
        return action

    def _player_weapon(self) -> Tuple[Weapon, str]:
        weapon = self.player.equipped_weapon or FISTS
        weapon_type = getattr(weapon, "weapon_type", "fists")
        return weapon, weapon_type

    def _load_weapon(self, weapon_id: str) -> Weapon:
        template = content_manager.items.get(weapon_id)
        if template:
            item = Item.from_template(template)
            if isinstance(item, Weapon):
                return item
        fallback = STARTING_ITEMS.get(weapon_id)
        if isinstance(fallback, Weapon):
            return fallback
        return FISTS

    def _player_yield(self) -> None:
        self.active = False
        print(ui.warning("You lower your weapon and yield the duel."))
        print(ui.info(f"{self.opponent.name} nods, accepting your surrender."))

    def _summarize_outcome(self) -> None:
        print(ui.divider(char="="))
        if self.player.current_hp <= 0:
            print(ui.error("You collapse, the duel lost."))
        elif self.enemy_hp <= 0:
            print(ui.success(f"{self.opponent.name} yields the duel. Victory is yours."))
            self.player.gain_weapon_xp("fists", 1 * self._xp_multiplier)
        elif self._forced_yield:
            print(ui.hint("The duel ends at your request."))
        else:
            print(ui.hint("The duel concludes without a decisive victor."))

