from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

import ui
from items import Item, Weapon
import arena_rewards
from player import Player, STANCE_PROFILES


@dataclass
class ArenaOpponent:
    name: str
    hp: int
    weapon_type: str
    damage_min: int
    damage_max: int
    aggression: int
    awareness: int
    preferred_stances: List[str]


ARENA_OPPONENTS: Dict[str, List[ArenaOpponent]] = {
    "bronze": [
        ArenaOpponent("Arena Brawler", 18, "fists", 1, 4, 40, 30, ["aggressive", "balanced"]),
        ArenaOpponent("Spear Novice", 20, "spear", 1, 5, 35, 35, ["balanced"]),
    ],
    "silver": [
        ArenaOpponent("Shieldbearer Vex", 28, "spear", 2, 5, 45, 40, ["defensive", "balanced"]),
        ArenaOpponent("Parshendi Duelist", 30, "sword", 2, 6, 50, 45, ["aggressive", "balanced"]),
    ],
    "gold": [
        ArenaOpponent("Veteran Blademaster", 36, "sword", 3, 7, 55, 50, ["balanced", "aggressive"]),
        ArenaOpponent("Chasmfiend Youngling", 42, "fists", 4, 8, 60, 30, ["aggressive"]),
    ],
    "champion": [
        ArenaOpponent("The Unbroken Line", 50, "spear", 4, 9, 65, 55, ["balanced", "defensive"]),
    ],
}


class ArenaMatch:
    def __init__(self, player: Player, rank: str) -> None:
        self.player = player
        self.rank = rank
        self.opponent = random.choice(ARENA_OPPONENTS[rank])
        self.enemy_hp = self.opponent.hp
        self.player_fatigue = 10
        self.enemy_fatigue = 10
        self.player_morale = 50
        self.enemy_morale = 50
        self.crowd_favor = 50
        self.round = 1
        self.active = True
        self.player_yield = False

    def run(self) -> Dict[str, object]:
        print(ui.banner(f"The crowd roars as you face {self.opponent.name}!"))
        while self.active and self.player.current_hp > 0 and self.enemy_hp > 0:
            self._print_round_banner()
            player_action = self._prompt_action()
            if player_action == "yield":
                self.player_yield = True
                break
            enemy_action = self._enemy_action(player_action)
            self._resolve_actions(player_action, enemy_action)
            self._decay_states()
            self.round += 1
        victory = self.enemy_hp <= 0 and self.player.current_hp > 0 and not self.player_yield
        message = (
            "The crowd erupts in cheers." if victory else "Gasps ripple through the stands."
        )
        fame_gain = arena_rewards.fame_reward(self.rank) if victory else 0
        marks = arena_rewards.roll_mark_reward(self.rank) if victory else 0
        item = arena_rewards.maybe_roll_item(self.rank) if victory else None
        return {
            "victory": victory,
            "message": message,
            "fame": fame_gain,
            "marks": marks,
            "item": item,
        }

    def _print_round_banner(self) -> None:
        status = f"Fatigue {self.player_fatigue}/100 | Morale {self.player_morale}/100 | Crowd {self.crowd_favor}"
        print(ui.divider(char="="))
        print(ui.info(f"Round {self.round} - {status}"))

    def _prompt_action(self) -> str:
        choice = input(
            ui.hint("Action (strike/feint/block/dodge/stance <type>/yield): ")
        ).strip().lower()
        if not choice:
            return "strike"
        if choice.startswith("stance"):
            parts = choice.split()
            if len(parts) >= 2:
                self.player.change_stance(parts[1])
            return "stance"
        if choice in {"strike", "feint", "block", "dodge", "yield"}:
            return choice
        return "strike"

    def _enemy_action(self, player_action: str) -> str:
        hp_ratio = self.enemy_hp / self.opponent.hp
        fatigue_penalty = self.enemy_fatigue // 20
        aggression = max(10, self.opponent.aggression - fatigue_penalty * 5)
        if hp_ratio < 0.2:
            return "dodge"
        roll = random.randint(1, 100)
        if roll <= aggression:
            return "strike"
        if roll <= aggression + 15:
            return "feint"
        if roll % 3 == 0:
            return "block"
        return "dodge"

    def _resolve_actions(self, player_action: str, enemy_action: str) -> None:
        order = ["player", "enemy"]
        if random.randint(0, 1):
            order.reverse()
        if player_action == "dodge":
            self.player.gain_dodge_xp(1)
        for actor in order:
            if not self.active:
                break
            if actor == "player":
                self._player_attack(player_action, enemy_action)
            else:
                self._enemy_attack(enemy_action, player_action)
        if self.enemy_hp <= 0 or self.player.current_hp <= 0:
            self.active = False

    def _player_attack(self, action: str, enemy_action: str) -> None:
        if action == "stance":
            print(ui.info("You shift your footing."))
            self.crowd_favor = min(100, self.crowd_favor + 2)
            return
        weapon = self.player.equipped_weapon or Weapon(
            id="fists",
            name="your fists",
            description="Bare knuckles",
            type="weapon",
            damage_min=1,
            damage_max=3,
            weapon_type="fists",
        )
        weapon_type = getattr(weapon, "weapon_type", "fists")
        weapon_skill = self.player.weapon_skill.get(weapon_type, 5)
        stance_profile = STANCE_PROFILES.get(self.player.stance, STANCE_PROFILES["balanced"])
        fatigue_penalty = self.player_fatigue // 15
        hit_score = (
            weapon_skill * 5
            + self.player.effective_strength()
            + stance_profile["hit"]
            - fatigue_penalty
        )
        enemy_dodge = self.opponent.awareness * 2 + self.enemy_fatigue // 10
        if random.randint(1, 100) <= max(10, hit_score - enemy_dodge):
            base = random.randint(weapon.damage_min, weapon.damage_max)
            dmg = int((base + self.player.effective_strength() // 2) * stance_profile["damage"])
            if action == "feint":
                dmg = max(1, dmg - 1)
                self.crowd_favor = min(100, self.crowd_favor + 5)
            if action == "block":
                dmg = max(1, dmg - 2)
            self.enemy_hp = max(0, self.enemy_hp - dmg)
            self.player.gain_weapon_xp(weapon_type, 2)
            self.player_morale = min(100, self.player_morale + 5)
            self.enemy_morale = max(0, self.enemy_morale - 5)
            print(ui.success(f"You {action} and hit {self.opponent.name} for {dmg}!"))
            if self.enemy_hp == 0:
                print(ui.info("The crowd roars at the finishing blow!"))
        else:
            self.player.gain_weapon_xp(weapon_type, 1)
            self.crowd_favor = max(0, self.crowd_favor - 3)
            print(ui.hint("Your attack glances off uselessly."))
        self.player_fatigue = min(100, self.player_fatigue + 7)

    def _enemy_attack(self, action: str, player_action: str) -> None:
        if action == "block":
            self.enemy_fatigue = min(100, self.enemy_fatigue + 3)
            print(ui.info(f"{self.opponent.name} steadies their stance."))
            return
        stance_profile = STANCE_PROFILES.get(
            random.choice(self.opponent.preferred_stances), STANCE_PROFILES["balanced"]
        )
        fatigue_penalty = self.enemy_fatigue // 15
        hit_score = (
            self.opponent.aggression * 2
            + stance_profile["hit"]
            - fatigue_penalty
            + self.enemy_morale // 10
        )
        player_dodge = self.player.calculate_dodge_rating()
        if player_action == "block":
            player_dodge -= 5
        if random.randint(1, 100) <= max(12, hit_score - player_dodge):
            base = random.randint(self.opponent.damage_min, self.opponent.damage_max)
            dmg = int((base + self.opponent.aggression // 15) * stance_profile["damage"])
            if action == "feint":
                dmg = max(1, dmg - 1)
            taken = self.player.take_damage(dmg)
            self.crowd_favor = max(0, self.crowd_favor - 5)
            self.enemy_morale = min(100, self.enemy_morale + 4)
            self.player_morale = max(0, self.player_morale - 6)
            print(
                ui.warning(
                    f"{self.opponent.name} {action}s for {taken} damage. "
                    f"You have {self.player.current_hp} HP."
                )
            )
        else:
            print(ui.info(f"You evade {self.opponent.name}'s {action}."))
        self.enemy_fatigue = min(100, self.enemy_fatigue + 8)

    def _decay_states(self) -> None:
        self.player_morale = max(0, self.player_morale - 1)
        self.enemy_morale = max(0, self.enemy_morale - 1)
        self.crowd_favor = max(0, min(100, self.crowd_favor + random.randint(-2, 2)))

