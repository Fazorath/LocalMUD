from __future__ import annotations

import random
from typing import List, Optional

import quests
import world
from enemies import Enemy
from items import Item, Weapon
from jobs import Job, create_jobs
from quests import QuestLog
from game_state import GameState
from npcs import NPC


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
            return "No pathway lies that direction."
        self.current_room = target_id
        description = self.describe_room()
        quest_messages = quests.process_room_entry(self, target_id)
        if quest_messages:
            description = "\n".join([description] + quest_messages)
        return description

    def pick_up(self, item_key: str) -> str:
        room = self._room()
        key = item_key.strip().lower()
        for item in list(room.items):
            candidates = {
                item.id.lower(),
                item.name.lower(),
                item.name.lower().replace(" ", "_"),
            }
            if key in candidates:
                room.items.remove(item)
                self.inventory.append(item)
                messages = [f"You stow the {item.name} with your gear."]
                quest_messages = quests.process_item_pickup(self, item.id)
                messages.extend(quest_messages)
                return "\n".join(messages)
        return "You don't see that item here."

    def equip(self, item_key: str) -> str:
        key = item_key.strip().lower()
        for item in self.inventory:
            candidates = {
                item.id.lower(),
                item.name.lower(),
                item.name.lower().replace(" ", "_"),
            }
            if key in candidates:
                if isinstance(item, Weapon):
                    self.equipped_weapon = item
                    return f"You brace with the {item.name}."
                return f"The {item.name} can't be wielded."
        return "That item isn't in your satchel."

    def list_inventory(self) -> str:
        if not self.inventory:
            return f"You carry nothing but the clothes on your back. Stormlight marks: {self.spheres}"
        lines = ["You rummage through your satchel:"]
        for item in self.inventory:
            marker = " (equipped)" if item is self.equipped_weapon else ""
            lines.append(f"- {item.name}{marker}")
        lines.append(f"Stormlight marks: {self.spheres}")
        return "\n".join(lines)

    def attack(self, enemy_key: str) -> str:
        room = self._room()
        key = enemy_key.strip().lower()
        target = None
        for enemy in room.enemies:
            candidates = {
                enemy.id.lower(),
                enemy.name.lower(),
                enemy.name.lower().replace(" ", "_"),
            }
            if key in candidates:
                target = enemy
                break
        if not target:
            return "No foe by that name stands before you."

        if self.hp <= 0:
            return "Your vision swims. You can't fight in this state."

        if self.equipped_weapon:
            dmg = random.randint(self.equipped_weapon.damage_min, self.equipped_weapon.damage_max)
            weapon_desc = self.equipped_weapon.name
        else:
            dmg = random.randint(1, 2)
            weapon_desc = "your fists"

        target.hp -= dmg
        result = [f"You lash out with {weapon_desc}, dealing {dmg} damage to the {target.name}."]

        if target.hp <= 0:
            room.enemies.remove(target)
            result.append(f"The {target.name} falls, armor clattering against the stone.")
            self.last_defeated_enemy_id = target.id
            quest_messages = quests.process_enemy_defeat(self, target.id)
            if quest_messages:
                result.extend(quest_messages)
            return " ".join(result)

        retaliation = random.randint(target.attack_min, target.attack_max)
        self.hp -= retaliation
        result.append(
            f"The {target.name} counters for {retaliation} damage. You have {self.hp} HP remaining."
        )

        if self.hp <= 0:
            result.append("Stormlight fades from your vision as you collapse.")

        return " ".join(result)

    def describe_room(self) -> str:
        room = self._room()
        lines = [room.name, room.description]

        if room.exits:
            exits = ", ".join(f"{direction} -> {dest}" for direction, dest in room.exits.items())
            lines.append(f"Exits: {exits}")

        if room.items:
            item_line = ", ".join(item.name for item in room.items)
            lines.append(f"Items: {item_line}")

        if room.enemies:
            enemy_line = ", ".join(f"{enemy.name} ({enemy.hp} HP)" for enemy in room.enemies)
            lines.append(f"Enemies: {enemy_line}")

        lines.append(f"Stormlight marks: {self.spheres}")
        return "\n".join(lines)

    def add_spheres(self, amount: int) -> None:
        self.spheres += amount

    def list_jobs(self) -> str:
        if not self.jobs:
            return "No jobs available."
        lines = ["Available jobs:"]
        for job in self.jobs:
            status = "ready" if job.can_do() else f"cooldown: {job.remaining_cooldown} turn(s)"
            lines.append(f"- {job.id}: {job.name} ({status})")
            lines.append(f"  {job.description} | Reward: {job.reward_spheres} mark(s)")
        return "\n".join(lines)

    def perform_job(self, job_id: str) -> str:
        job = next((job for job in self.jobs if job.id == job_id), None)
        if not job:
            return "No such job is posted."
        if not job.can_do():
            return f"{job.name} is on cooldown for {job.remaining_cooldown} more turn(s)."
        message, reward = job.do_job()
        if reward:
            self.add_spheres(reward)
            message += f" You earn {reward} mark(s)."
        return message

    def tick_jobs(self) -> None:
        for job in self.jobs:
            job.tick()

    def list_npcs(self) -> str:
        room = self._room()
        if not room.npcs:
            return "No one of note lingers nearby."
        lines = ["You notice:"]
        for npc in room.npcs:
            lines.append(f"- {npc.name} ({npc.id}) - {npc.role}")
        return "\n".join(lines)

    def talk_to(self, npc_key: str, game_state: GameState) -> str:
        key = npc_key.strip().lower()
        room = self._room()
        target: Optional[NPC] = None
        for npc in room.npcs:
            candidates = {
                npc.id.lower(),
                npc.name.lower(),
                npc.name.lower().replace(" ", "_"),
            }
            if key in candidates:
                target = npc
                break
        if not target:
            return "No one by that name stands nearby."

        lines: List[str] = []
        if target.lines:
            lines.append(target.lines[0])

        if target.on_talk:
            lines.extend(target.on_talk(self, game_state))

        return "\n".join(lines)

