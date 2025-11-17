from __future__ import annotations

from difflib import get_close_matches
from typing import Dict, List, Optional

import quests
from game_state import GameState
from player import Player
import ui

HELP_SECTIONS: Dict[str, List[str]] = {
    "Movement": [
        "look - survey your surroundings",
        "move <direction> - travel toward an exit",
        "<direction> - shortcut for move (east, west, south, etc.)",
    ],
    "Gear & Combat": [
        "take <item> - pick up an item",
        "inventory / inv - list carried items",
        "equip <item> - wield a weapon",
        "attack <enemy> - engage a foe",
    ],
    "People & Quests": [
        "npcs - see who is nearby",
        "talk <npc> - speak to someone nearby",
        "quests - list quest status",
        "quest <id> - show quest details",
        "accept <id> - add a quest",
    ],
    "Work & Social": [
        "jobs - list daily jobs",
        "job <id> - attempt a job",
        "say <message> - speak aloud",
    ],
    "Meta": [
        "turn - show current time and turn",
        "help - show this list",
        "quit / exit - leave the game",
    ],
}

SHORT_DIRECTIONS = {"north", "south", "east", "west", "up", "down", "in", "out"}
KNOWN_COMMANDS = {
    "look",
    "move",
    "go",
    *SHORT_DIRECTIONS,
    "take",
    "inventory",
    "inv",
    "equip",
    "attack",
    "npcs",
    "talk",
    "quests",
    "quest",
    "accept",
    "jobs",
    "job",
    "say",
    "turn",
    "help",
    "quit",
    "exit",
}


def _help_text() -> str:
    blocks = [ui.help_heading("Commands")]
    for section, entries in HELP_SECTIONS.items():
        blocks.append(ui.help_section(section, entries))
    return "\n\n".join(blocks)


def _suggest_command(word: str) -> Optional[str]:
    matches = get_close_matches(word, KNOWN_COMMANDS, n=1, cutoff=0.6)
    return matches[0] if matches else None


def handle_command(player: Player, text: str, game_state: GameState) -> bool:
    command = text.strip()
    if not command:
        print(ui.hint("The winds carry only silence."))
        return True

    parts = command.split()
    verb = parts[0].lower()
    args = parts[1:]

    if verb in {"quit", "exit"}:
        print(ui.info("You shoulder your bridge gear and head back toward camp. Journey complete."))
        return False

    if verb == "help":
        print(_help_text())
        return True

    if verb == "turn":
        info = f"Turn {game_state.turn_count} - {game_state.time_of_day.title()}"
        if game_state.highstorm_warning_active:
            info += " (Highstorm warning active)"
        print(ui.info(info))
        return True

    if verb == "look":
        print(player.describe_room())
        return True

    if verb in {"inventory", "inv"}:
        print(player.list_inventory())
        return True

    if verb in {"move", "go"}:
        if not args:
            print(ui.hint("Choose a direction: east, west, north, south..."))
            return True
        print(player.move(args[0]))
        return True

    if verb in SHORT_DIRECTIONS:
        print(player.move(verb))
        return True

    if verb == "take":
        if not args:
            print(ui.hint("Specify the item you want to take."))
            return True
        item_key = " ".join(args)
        print(player.pick_up(item_key))
        return True

    if verb == "equip":
        if not args:
            print(ui.hint("Specify the item you want to equip."))
            return True
        item_key = " ".join(args)
        print(player.equip(item_key))
        return True

    if verb == "attack":
        if not args:
            print(ui.hint("Name a target to attack."))
            return True
        target_key = " ".join(args)
        print(player.attack(target_key))
        return True

    if verb == "npcs":
        print(player.list_npcs())
        return True

    if verb == "talk":
        if not args:
            print(ui.hint("Speak to whom?"))
            return True
        npc_key = " ".join(args)
        print(player.talk_to(npc_key, game_state))
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
            print(ui.hint("Specify the quest id to inspect."))
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
                print(ui.warning("No quest by that id."))
        return True

    if verb == "accept":
        if not args:
            print(ui.hint("Specify the quest id to accept."))
            return True
        quest_id = args[0].lower()
        quest = quests.create_quest(quest_id)
        if not quest:
            print(ui.warning("No quest by that id."))
            return True
        print(player.quest_log.add(quest))
        return True

    if verb == "jobs":
        print(player.list_jobs())
        return True

    if verb == "job":
        if not args:
            print(ui.hint("Specify the job id to attempt."))
            return True
        print(player.perform_job(args[0].lower()))
        return True

    if verb == "say":
        if not args:
            print(ui.hint("You mouth words but no sound escapes."))
            return True
        message = " ".join(args)
        print(ui.info(f"You say: {message}"))
        return True

    suggestion = _suggest_command(verb)
    base = ui.error(f"'{verb}' isn't a known command.")
    hint_text = (
        ui.hint(f"Try '{suggestion}' instead.") if suggestion else ui.hint("Type 'help' for options.")
    )
    print(f"{base} {hint_text}")
    return True

