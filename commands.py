from __future__ import annotations

from typing import List

import quests
from game_state import GameState
from player import Player

HELP_LINES: List[str] = [
    "look - survey your surroundings",
    "move <direction> - travel toward an exit",
    "<direction> - shortcut for move (east, west, south, etc.)",
    "take <item_id> - pick up an item",
    "inventory / inv - list carried items",
    "equip <item_id> - wield a weapon",
    "attack <enemy_id> - engage a foe",
    "quests - list quest status",
    "quest <id> - show quest details",
    "accept <id> - add a quest",
    "jobs - list daily jobs",
    "job <id> - attempt a job",
    "say <message> - speak aloud",
    "turn - show current time and turn",
    "help - show this list",
    "quit / exit - leave the game",
]

SHORT_DIRECTIONS = {"north", "south", "east", "west", "up", "down", "in", "out"}


def handle_command(player: Player, text: str, game_state: GameState) -> bool:
    command = text.strip()
    if not command:
        print("The winds carry only silence.")
        return True

    parts = command.split()
    verb = parts[0].lower()
    args = parts[1:]

    if verb in {"quit", "exit"}:
        print("You shoulder your bridge gear and head back toward camp. Journey complete.")
        return False

    if verb == "help":
        print("Commands:")
        for line in HELP_LINES:
            print(f"- {line}")
        return True

    if verb == "turn":
        info = f"Turn {game_state.turn_count} - {game_state.time_of_day.title()}"
        if game_state.highstorm_warning_active:
            info += " (Highstorm warning active)"
        print(info)
        return True

    if verb == "look":
        print(player.describe_room())
        return True

    if verb in {"inventory", "inv"}:
        print(player.list_inventory())
        return True

    if verb in {"move", "go"}:
        if not args:
            print("Choose a direction: east, west, north, south...")
            return True
        print(player.move(args[0]))
        return True

    if verb in SHORT_DIRECTIONS:
        print(player.move(verb))
        return True

    if verb == "take":
        if not args:
            print("Specify the item id you want to take.")
            return True
        print(player.pick_up(args[0]))
        return True

    if verb == "equip":
        if not args:
            print("Specify the item id you want to equip.")
            return True
        print(player.equip(args[0]))
        return True

    if verb == "attack":
        if not args:
            print("Name a target to attack.")
            return True
        print(player.attack(args[0]))
        return True

    if verb == "quests":
        print(player.quest_log.list_active())
        print(player.quest_log.list_completed())
        available = [
            quest_id
            for quest_id in quests.QUEST_TEMPLATES
            if quest_id not in player.quest_log.active_quests
            and quest_id not in player.quest_log.completed_quests
        ]
        if available:
            print(f"Available quest ids: {', '.join(available)} (accept <id>)")
        return True

    if verb == "quest":
        if not args:
            print("Specify the quest id to inspect.")
            return True
        quest_id = args[0].lower()
        details = player.quest_log.describe(quest_id)
        if details:
            print(details)
        else:
            template = quests.QUEST_TEMPLATES.get(quest_id)
            if template:
                print(
                    f"{template['name']}: {template['description']} "
                    "(accept this quest to begin tracking)."
                )
            else:
                print("No quest by that id.")
        return True

    if verb == "accept":
        if not args:
            print("Specify the quest id to accept.")
            return True
        quest_id = args[0].lower()
        quest = quests.create_quest(quest_id)
        if not quest:
            print("No quest by that id.")
            return True
        print(player.quest_log.add(quest))
        return True

    if verb == "jobs":
        print(player.list_jobs())
        return True

    if verb == "job":
        if not args:
            print("Specify the job id to attempt.")
            return True
        print(player.perform_job(args[0].lower()))
        return True

    if verb == "say":
        if not args:
            print("You mouth words but no sound escapes.")
            return True
        message = " ".join(args)
        print(f"You say: {message}")
        return True

    print(f"'{verb}' isn't a known command. Type 'help' for options.")
    return True

