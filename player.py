from __future__ import annotations

import random
from typing import Dict, List, Optional

import quests
import world
from enemies import Enemy
from items import Item, Weapon
from jobs import Job, create_jobs
from quests import QuestLog
from game_state import GameState
from npcs import NPC
import ui

CURRENCY_ITEM_VALUES: Dict[str, int] = {
    "sphere_mark": 1,
}


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
        self.hp = 20
        self.inventory: List[Item] = []
        self.equipped_weapon: Optional[Weapon] = None
        self.quest_log = QuestLog()
        self.jobs: List[Job] = create_jobs()
        self.spheres = 0
        self.last_defeated_enemy_id: Optional[str] = None

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
                currency_value = CURRENCY_ITEM_VALUES.get(item.id, 0)
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
                return ui.warning(f"The {item.name} can't be wielded.")
        return ui.warning("That item isn't in your satchel.")

    def list_inventory(self) -> str:
        if not self.inventory:
            return ui.warning(
                f"You carry nothing but the clothes on your back. Stormlight marks: {self.spheres}"
            )
        lines = [ui.help_heading("Inventory")]
        for item in self.inventory:
            marker = " (equipped)" if item is self.equipped_weapon else ""
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

        if self.hp <= 0:
            return ui.warning("Your vision swims. You can't fight in this state.")

        if self.equipped_weapon:
            dmg = random.randint(self.equipped_weapon.damage_min, self.equipped_weapon.damage_max)
            weapon_desc = self.equipped_weapon.name
        else:
            dmg = random.randint(1, 2)
            weapon_desc = "your fists"

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
        self.hp -= retaliation
        result.append(
            ui.warning(
                f"The {target.name} counters for {retaliation} damage. You have {self.hp} HP remaining."
            )
        )

        if self.hp <= 0:
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

        lines.append(ui.section("Stormlight marks", str(self.spheres)))
        lines.append(ui.divider())
        return "\n".join(lines)

    def add_spheres(self, amount: int) -> None:
        self.spheres += amount

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
        return "\n".join(lines)

    def perform_job(self, job_id: str) -> str:
        job = next((job for job in self.jobs if job.id == job_id), None)
        if not job:
            return ui.warning("No such job is posted.")
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
            lines.append(ui.bullet(f"{npc.name} ({npc.id}) - {npc.role}"))
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

