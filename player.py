from __future__ import annotations

import random
from typing import Dict, List, Optional, Set

import quests
import world
from enemies import Enemy
from items import Armor, Item, Weapon
from jobs import Job, create_jobs
from quests import QuestLog
from game_state import GameState
from npcs import NPC
import ui

CURRENCY_ITEM_VALUES: Dict[str, int] = {
    "sphere_mark": 1,
}


STANCE_PROFILES = {
    "aggressive": {"damage": 1.2, "hit": 10, "dodge": -10},
    "balanced": {"damage": 1.0, "hit": 0, "dodge": 0},
    "defensive": {"damage": 0.85, "hit": -5, "dodge": 12},
}

WEAPON_TYPES = ["spear", "sword", "knife", "shardblade", "fists"]

WOUND_THRESHOLDS = [
    (0.75, {"strength": -1, "dexterity": 0}, "Bruises bloom across your arms."),
    (0.5, {"strength": -1, "dexterity": -1}, "You wince as deeper aches slow your movements."),
    (0.25, {"strength": -2, "dexterity": -2}, "Blood loss leaves your limbs trembling."),
    (0.1, {"strength": -3, "dexterity": -3}, "You can barely stay upright through the pain."),
]


def _expand_alias(alias: str) -> set[str]:
    base = alias.strip().lower()
    with_spaces = base.replace("_", " ")
    tokens = [token for token in with_spaces.split() if token]
    variants = {base, with_spaces, with_spaces.replace(" ", "_")}
    for i in range(len(tokens)):
        suffix = " ".join(tokens[i:])
        variants.add(suffix)
    variants.update(tokens)
    for token in tokens:
        for length in range(3, len(token) + 1):
            variants.add(token[:length])
    return {variant for variant in variants if variant}


def _matches(key: str, *aliases: str) -> bool:
    normalized = key.strip().lower()
    for alias in aliases:
        if not alias:
            continue
        if normalized in _expand_alias(alias):
            return True
    return False


class Player:
    def __init__(self, name: str, starting_room: str):
        self.name = name or "Bridgeman"
        self.current_room = starting_room
        self.strength = 6
        self.dexterity = 5
        self.endurance = 6
        self.willpower = 5
        self.max_hp = 20 + self.endurance * 2
        self.current_hp = self.max_hp
        self.inventory: List[Item] = []
        self.equipped_weapon: Optional[Weapon] = None
        self.equipped_armor: Dict[str, Optional[Armor]] = {"head": None, "chest": None, "legs": None}
        self.stance: str = "balanced"
        self.quest_log = QuestLog()
        self.jobs: List[Job] = create_jobs()
        self.spheres = 0
        self.last_defeated_enemy_id: Optional[str] = None
        self.weapon_skill: Dict[str, int] = {weapon_type: 5 for weapon_type in WEAPON_TYPES}
        self.dodge_skill: int = 5
        self.technique_skills: Dict[str, int] = {"block": 5, "feint": 5, "discipline": 5}
        self.armor_rating: int = 0
        self.dodge_rating: int = 0
        self.reputation: Dict[str, int] = {}
        self.active_duel = None
        self._wound_modifiers: Dict[str, int] = {"strength": 0, "dexterity": 0}
        self._active_wound_thresholds: Set[float] = set()
        self.training_log: Dict[str, str] = {}
        self.calculate_armor_rating()
        self.calculate_dodge_rating()

    def _room(self) -> world.Room:
        return world.get_room(self.current_room)

    def move(self, direction: str) -> str:
        direction = direction.lower()
        room = self._room()
        target_id = room.exits.get(direction)
        if not target_id:
            return ui.warning("No pathway lies that direction.")
        self.current_room = target_id
        description = self.describe_room()
        quest_messages = quests.process_room_entry(self, target_id)
        if quest_messages:
            quest_details = [ui.info(message) for message in quest_messages]
            description = "\n".join([description] + quest_details)
        return description

    def pick_up(self, item_key: str) -> str:
        room = self._room()
        key = item_key.strip().lower()
        for item in list(room.items):
            if _matches(key, item.id, item.name):
                room.items.remove(item)
                currency_value = CURRENCY_ITEM_VALUES.get(
                    item.id, item.value if getattr(item, "type", None) == "currency" else 0
                )
                messages = []
                if currency_value:
                    self.add_spheres(currency_value)
                    messages.append(
                        ui.success(
                            f"You pocket the {item.name}. Stormlight marks: {self.spheres}"
                        )
                    )
                else:
                    self.inventory.append(item)
                    messages.append(ui.success(f"You stow the {item.name} with your gear."))
                quest_messages = quests.process_item_pickup(self, item.id)
                messages.extend(ui.info(msg) for msg in quest_messages)
                return "\n".join(messages)
        if not room.items:
            return ui.warning("No loose gear catches your eye here.")
        nearby = ", ".join(item.name for item in room.items)
        return ui.warning(f"You don't see that item here. Try one of: {nearby}.")

    def equip(self, item_key: str) -> str:
        key = item_key.strip().lower()
        for item in self.inventory:
            if _matches(key, item.id, item.name):
                if isinstance(item, Weapon):
                    self.equipped_weapon = item
                    return ui.success(f"You brace with the {item.name}.")
                if isinstance(item, Armor):
                    current = self.equipped_armor.get(item.slot)
                    if current is item:
                        return ui.hint(f"The {item.name} is already strapped on.")
                    self.equipped_armor[item.slot] = item
                    self.calculate_armor_rating()
                    self.calculate_dodge_rating()
                    note = f"{item.slot} armor" if item.slot else "armor"
                    message = f"You secure the {item.name} ({note})."
                    if current:
                        message += f" {current.name} is stowed away."
                    return ui.success(message)
                return ui.warning(f"The {item.name} can't be wielded.")
        return ui.warning("That item isn't in your satchel.")

    def list_inventory(self) -> str:
        if not self.inventory:
            return ui.warning(
                f"You carry nothing but the clothes on your back. Stormlight marks: {self.spheres}"
            )
        lines = [ui.help_heading("Inventory")]
        for item in self.inventory:
            marker = ""
            if item is self.equipped_weapon:
                marker = " (equipped weapon)"
            else:
                for slot, armor in self.equipped_armor.items():
                    if item is armor:
                        marker = f" (equipped {slot})"
                        break
            lines.append(ui.bullet(f"{item.name}{marker}"))
        lines.append(ui.section("Stormlight marks", str(self.spheres)))
        return "\n".join(lines)

    def attack(self, enemy_key: str) -> str:
        room = self._room()
        key = enemy_key.strip().lower()
        target = None
        for enemy in room.enemies:
            if _matches(key, enemy.id, enemy.name):
                target = enemy
                break
        if not target:
            return ui.warning("No foe by that name stands before you.")

        if self.current_hp <= 0:
            return ui.warning("Your vision swims. You can't fight in this state.")

        if self.equipped_weapon:
            base = random.randint(self.equipped_weapon.damage_min, self.equipped_weapon.damage_max)
            weapon_desc = self.equipped_weapon.name
            weapon_type = getattr(self.equipped_weapon, "weapon_type", "fists")
        else:
            base = random.randint(1, 2)
            weapon_desc = "your fists"
            weapon_type = "fists"
        stance_profile = STANCE_PROFILES[self.stance]
        dmg = max(1, int((base + self.effective_strength() // 2) * stance_profile["damage"]))
        self.gain_weapon_xp(weapon_type, 1)

        target.hp -= dmg
        result = [
            ui.success(f"You lash out with {weapon_desc}, dealing {dmg} damage to the {target.name}.")
        ]

        if target.hp <= 0:
            room.enemies.remove(target)
            result.append(ui.success(f"The {target.name} falls, armor clattering against the stone."))
            self.last_defeated_enemy_id = target.id
            quest_messages = quests.process_enemy_defeat(self, target.id)
            if quest_messages:
                result.extend(ui.info(msg) for msg in quest_messages)
            return " ".join(result)

        retaliation = random.randint(target.attack_min, target.attack_max)
        actual = self.take_damage(retaliation)
        result.append(
            ui.warning(
                f"The {target.name} counters for {actual} damage. You have {self.current_hp} HP remaining."
            )
        )

        if self.current_hp <= 0:
            result.append(ui.error("Stormlight fades from your vision as you collapse."))

        return " ".join(result)

    def describe_room(self) -> str:
        room = self._room()
        lines = [
            ui.divider(),
            ui.room_name(room.name),
            ui.narration(room.description),
        ]

        if room.exits:
            exit_lines = []
            for direction, dest in room.exits.items():
                destination = world.get_room(dest)
                dest_name = destination.name if destination else dest
                exit_lines.append(f"{direction} -> {dest_name}")
            exits = ", ".join(exit_lines)
            lines.append(ui.section("Exits", exits))

        if room.items:
            item_line = ", ".join(item.name for item in room.items)
            lines.append(ui.section("Items", item_line))

        if room.enemies:
            enemy_line = ", ".join(f"{enemy.name} ({enemy.hp} HP)" for enemy in room.enemies)
            lines.append(ui.section("Enemies", enemy_line))

        if room.npcs:
            npc_line = ", ".join(f"{npc.name} ({npc.id})" for npc in room.npcs)
            lines.append(ui.section("People", f"{npc_line} (talk <name>)"))

        lines.append(
            ui.section(
                "Health", f"{self.current_hp}/{self.max_hp} ({self.get_health_state()})"
            )
        )
        lines.append(ui.section("Stance", self.stance.title()))
        lines.append(ui.section("Stormlight marks", str(self.spheres)))
        lines.append(ui.divider())
        return "\n".join(lines)

    def add_spheres(self, amount: int) -> None:
        self.spheres += amount

    def calculate_armor_rating(self) -> int:
        rating = sum(
            armor.armor_value for armor in self.equipped_armor.values() if armor
        )
        self.armor_rating = rating
        return rating

    def calculate_dodge_rating(self) -> int:
        penalty = sum(armor.dodge_penalty for armor in self.equipped_armor.values() if armor)
        stance_bonus = STANCE_PROFILES[self.stance]["dodge"]
        base = self.effective_dexterity() * 2 + self.dodge_skill
        self.dodge_rating = max(0, base - penalty + stance_bonus)
        return self.dodge_rating

    def gain_weapon_xp(self, weapon_type: str, amount: int) -> None:
        current = self.weapon_skill.get(weapon_type, self.weapon_skill["fists"])
        self.weapon_skill[weapon_type] = min(100, current + amount)

    def gain_dodge_xp(self, amount: int) -> None:
        self.dodge_skill = min(100, self.dodge_skill + amount)
        self.calculate_dodge_rating()

    def gain_block_xp(self, amount: int) -> None:
        self.technique_skills["block"] = min(100, self.technique_skills["block"] + amount)

    def gain_feint_xp(self, amount: int) -> None:
        self.technique_skills["feint"] = min(100, self.technique_skills["feint"] + amount)

    def gain_discipline_xp(self, amount: int) -> None:
        self.technique_skills["discipline"] = min(100, self.technique_skills["discipline"] + amount)

    def take_damage(self, amount: int, armor_bonus: int = 0) -> int:
        mitigated = max(1, amount - (self.calculate_armor_rating() + armor_bonus))
        previous_ratio = self.current_hp / self.max_hp if self.max_hp else 0
        self.current_hp = max(0, self.current_hp - mitigated)
        self._update_wound_thresholds(previous_ratio)
        self.calculate_dodge_rating()
        return mitigated

    def heal(self, amount: int) -> int:
        previous_ratio = self.current_hp / self.max_hp if self.max_hp else 0
        healed = min(amount, self.max_hp - self.current_hp)
        self.current_hp += healed
        self._update_wound_thresholds(previous_ratio)
        self.calculate_dodge_rating()
        return healed

    def apply_training_fatigue(self, amount: int = 1) -> int:
        if self.current_hp <= 1:
            return 0
        fatigue = min(amount, self.current_hp - 1)
        previous_ratio = self.current_hp / self.max_hp if self.max_hp else 0
        self.current_hp -= fatigue
        self._update_wound_thresholds(previous_ratio)
        self.calculate_dodge_rating()
        return fatigue

    def can_train(self, npc_id: str, time_period: str) -> bool:
        return self.training_log.get(npc_id) != time_period

    def register_training(self, npc_id: str, time_period: str) -> None:
        self.training_log[npc_id] = time_period

    def get_health_state(self) -> str:
        if self.max_hp == 0:
            return "unknown"
        ratio = self.current_hp / self.max_hp
        if ratio >= 0.9:
            return "steady"
        if ratio >= 0.75:
            return "bruised"
        if ratio >= 0.5:
            return "wounded"
        if ratio >= 0.25:
            return "injured"
        return "critical"

    def change_stance(self, stance: str) -> str:
        stance = stance.lower()
        if stance not in STANCE_PROFILES:
            return ui.warning("Unknown stance. Choose aggressive, balanced, or defensive.")
        if stance == self.stance:
            return ui.hint(f"You are already in a {stance} stance.")
        self.stance = stance
        self.calculate_dodge_rating()
        return ui.info(f"You settle into a {stance} stance.")

    def effective_strength(self) -> int:
        return max(1, self.strength + self._wound_modifiers["strength"])

    def effective_dexterity(self) -> int:
        return max(1, self.dexterity + self._wound_modifiers["dexterity"])

    def _update_wound_thresholds(self, previous_ratio: float) -> None:
        if self.max_hp == 0:
            return
        current_ratio = self.current_hp / self.max_hp
        for threshold, mods, message in WOUND_THRESHOLDS:
            triggered = current_ratio <= threshold
            previously = threshold in self._active_wound_thresholds
            if triggered and not previously:
                self._active_wound_thresholds.add(threshold)
                self._wound_modifiers["strength"] += mods["strength"]
                self._wound_modifiers["dexterity"] += mods["dexterity"]
                print(ui.warning(message))
            elif not triggered and previously and current_ratio > threshold + 0.05:
                self._active_wound_thresholds.remove(threshold)
                self._wound_modifiers["strength"] -= mods["strength"]
                self._wound_modifiers["dexterity"] -= mods["dexterity"]

    def get_reputation(self, faction_id: str) -> int:
        return self.reputation.get(faction_id, 0)

    def change_reputation(self, faction_id: str, delta: int) -> None:
        self.reputation[faction_id] = self.get_reputation(faction_id) + delta

    def list_jobs(self) -> str:
        if not self.jobs:
            return ui.warning("No jobs available.")
        lines = [ui.help_heading("Available jobs")]
        for job in self.jobs:
            status = "ready" if job.can_do() else f"cooldown: {job.remaining_cooldown} turn(s)"
            lines.append(ui.bullet(f"{job.id}: {job.name} ({status})"))
            lines.append(
                ui.hint(f"  {job.description} | Reward: {job.reward_spheres} mark(s)")
            )
            if job.allowed_rooms:
                locations = ", ".join(job.allowed_rooms)
                lines.append(ui.hint(f"  Available at: {locations}"))
        return "\n".join(lines)

    def perform_job(self, job_id: str) -> str:
        job = next((job for job in self.jobs if job.id == job_id), None)
        if not job:
            return ui.warning("No such job is posted.")
        if job.allowed_rooms and self.current_room not in job.allowed_rooms:
            locations = ", ".join(job.allowed_rooms)
            return ui.warning(f"{job.name} must be handled at: {locations}.")
        if not job.can_do():
            return ui.warning(f"{job.name} is on cooldown for {job.remaining_cooldown} more turn(s).")
        message, reward = job.do_job()
        if reward:
            self.add_spheres(reward)
            message = f"{message} You earn {reward} mark(s)."
        return ui.success(message)

    def tick_jobs(self) -> None:
        for job in self.jobs:
            job.tick()

    def list_npcs(self) -> str:
        room = self._room()
        if not room.npcs:
            return ui.warning("No one of note lingers nearby.")
        lines = [ui.help_heading("You notice:")]
        for npc in room.npcs:
            interactions = f" [{', '.join(npc.interactions)}]" if npc.interactions else ""
            lines.append(ui.bullet(f"{npc.name} ({npc.id}) - {npc.role}{interactions}"))
        return "\n".join(lines)

    def talk_to(self, npc_key: str, game_state: GameState) -> str:
        key = npc_key.strip().lower()
        room = self._room()
        target: Optional[NPC] = None
        for npc in room.npcs:
            if _matches(key, npc.id, npc.name):
                target = npc
                break
        if not target:
            return ui.warning("No one by that name stands nearby.")

        lines: List[str] = []
        if target.lines:
            lines.append(ui.dialogue(target.name, target.lines[0]))

        if target.on_talk:
            lines.extend(ui.info(text) for text in target.on_talk(self, game_state))

        return "\n".join(lines)

    def find_npc_in_room(self, npc_key: str) -> Optional[NPC]:
        key = npc_key.strip().lower()
        room = self._room()
        for npc in room.npcs:
            if _matches(key, npc.id, npc.name):
                return npc
        return None

