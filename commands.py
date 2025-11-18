from __future__ import annotations

from difflib import get_close_matches
from typing import Dict, List, Optional

import arena_rewards
import quests
from arena_engine import ArenaMatch
from duel import Duel
from game_state import GameState
from player import Player
import ui
from interactions import InteractionRegistry

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
        "train <npc> - practice drills with an instructor",
        "spar <npc> - run a supervised sparring match",
        "stance <type> - adopt a combat stance",
        "duel <npc> - challenge an opponent to a duel",
        "fight <rank> - enter an arena bout",
        "yield - concede the current duel",
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
        "arena - view arena status",
        "join arena - enlist for a bout",
        "bet <fighter> <amount> - wager on arena fights",
        "collect - claim stored arena winnings",
        "interact <who> <interaction> - use special actions like trade",
    ],
    "Meta": [
        "turn - show current time and turn",
        "help - show this list",
        "quit / exit - leave the game",
    ],
}

SHORT_DIRECTIONS = {"north", "south", "east", "west", "up", "down", "in", "out"}
def _normalize_id(text: str) -> str:
    return text.strip().lower().replace(" ", "_")


def _resolve_quest_id(player: Player, query: str) -> Optional[str]:
    normalized = _normalize_id(query)
    # Exact template id match
    if normalized in quests.QUEST_TEMPLATES:
        return normalized

    # Match quest names from templates
    for quest_id, template in quests.QUEST_TEMPLATES.items():
        if normalized == _normalize_id(template.get("name", quest_id)):
            return quest_id

    # Match active/completed quest ids or names
    for collection in (player.quest_log.active_quests, player.quest_log.completed_quests):
        for quest_id, quest in collection.items():
            if normalized in {
                quest_id,
                _normalize_id(quest_id),
                _normalize_id(quest.name),
            }:
                return quest_id
    return None


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
    "train",
    "spar",
    "arena",
    "join",
    "fight",
    "bet",
    "collect",
    "quests",
    "quest",
    "accept",
    "jobs",
    "job",
    "say",
    "duel",
    "yield",
    "stance",
    "interact",
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


def _run_registered_interaction(
    player: Player, npc, interaction_name: str, game_state: GameState
) -> bool:
    interaction = InteractionRegistry.get(interaction_name)
    if not interaction:
        print(ui.warning("You can't do that here."))
        return False
    allowed = [name.lower() for name in (npc.interactions or [])]
    if interaction_name != "talk" and interaction_name not in allowed:
        print(ui.warning(f"{npc.name} doesn't seem open to that."))
        return False
    for line in interaction.run(player, npc, game_state):
        print(line)
    return True


def _ensure_arena_location(player: Player) -> bool:
    if player.current_room != "grand_arena":
        print(ui.warning("You need to be at the grand arena for that."))
        return False
    return True


def _show_arena_panel(player: Player) -> None:
    print(arena_rewards.format_arena_panel(player))


def _resolve_bet(game_state: GameState, player: Player, player_victory: bool) -> None:
    bet = game_state.arena_bet
    if not bet:
        return
    target = bet.get("fighter")
    amount = bet.get("amount", 0)
    if target == "challenger" and player_victory:
        winnings = amount * 2
        player.add_arena_winnings(winnings)
        print(ui.success(f"Thresh pays out {winnings} marks on your win."))
    elif target == "opponent" and not player_victory:
        winnings = amount * 2
        player.add_arena_winnings(winnings)
        print(ui.success(f"Thresh pays out {winnings} marks on the upset."))
    else:
        print(ui.hint("Your wager evaporates into the cheering crowd."))
    game_state.arena_bet = None


def _start_arena_match(player: Player, game_state: GameState, rank: str) -> None:
    match = ArenaMatch(player, rank)
    result = match.run()
    print(result["message"])
    game_state.arena_queue_ready = False
    victory = result["victory"]
    if victory:
        fame_gain = result["fame"]
        if fame_gain:
            player.add_fame(fame_gain)
            print(ui.success(f"Fame +{fame_gain}."))
        mark_reward = result["marks"]
        if mark_reward:
            player.add_arena_winnings(mark_reward)
            print(ui.success(f"Arena purse stored: {mark_reward} marks. Use 'collect' later."))
        item = result.get("item")
        if item:
            player.inventory.append(item)
            print(ui.success(f"You receive {item.name}."))
    else:
        print(ui.warning("Medics hurry you from the sands."))
    _resolve_bet(game_state, player, victory)


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

    if verb == "stance":
        if not args:
            print(ui.hint("Choose a stance: aggressive, balanced, or defensive."))
            return True
        print(player.change_stance(args[0]))
        return True

    if verb == "npcs":
        print(player.list_npcs())
        return True

    if verb == "talk":
        if not args:
            print(ui.hint("Speak to whom?"))
            return True
        npc_key = " ".join(args)
        npc = player.find_npc_in_room(npc_key)
        if not npc:
            print(ui.warning("No one by that name stands nearby."))
            return True
        _run_registered_interaction(player, npc, "talk", game_state)
        return True

    if verb == "arena":
        if not _ensure_arena_location(player):
            return True
        _show_arena_panel(player)
        return True

    if verb == "duel":
        if not args:
            print(ui.hint("Name the opponent you wish to challenge."))
            return True
        npc_key = " ".join(args)
        npc = player.find_npc_in_room(npc_key)
        if not npc:
            print(ui.warning("No one by that name stands nearby."))
            return True
        if not getattr(npc, "combat_profile", None):
            print(ui.warning(f"{npc.name} refuses your challenge."))
            return True
        duel = Duel(player, npc)
        duel.run()
        return True

    if verb in {"train", "spar"}:
        if not args:
            print(ui.hint(f"Name the instructor you wish to {verb}."))
            return True
        npc_key = " ".join(args)
        npc = player.find_npc_in_room(npc_key)
        if not npc:
            print(ui.warning("No one by that name stands nearby."))
            return True
        if not _run_registered_interaction(player, npc, verb, game_state):
            return True
        return True

    if verb == "interact":
        if len(args) < 2:
            print(ui.hint("Usage: interact <who> <interaction>"))
            return True
        target_key = " ".join(args[:-1])
        interaction_name = args[-1].lower()
        npc = player.find_npc_in_room(target_key)
        if not npc:
            print(ui.warning("No one by that name stands nearby."))
            return True
        _run_registered_interaction(player, npc, interaction_name, game_state)
        return True

    if verb == "join":
        if not args or args[0].lower() != "arena":
            print(ui.hint("Usage: join arena"))
            return True
        if not _ensure_arena_location(player):
            return True
        if game_state.arena_queue_ready:
            print(ui.hint("You're already queued for the next bout."))
            return True
        game_state.arena_queue_ready = True
        print(ui.success("Your name is inked onto the arena roster."))
        return True

    if verb == "fight":
        if not args:
            print(ui.hint("Specify the arena rank: bronze, silver, gold, champion."))
            return True
        if not _ensure_arena_location(player):
            return True
        rank = args[0].lower()
        if rank not in {"bronze", "silver", "gold", "champion"}:
            print(ui.warning("Unknown arena tier."))
            return True
        if not player.can_access_arena_rank(rank):
            print(ui.warning("Earn more fame before attempting that tier."))
            return True
        if not game_state.arena_queue_ready:
            print(ui.hint("Join the queue first (join arena)."))
            return True
        _start_arena_match(player, game_state, rank)
        return True

    if verb == "bet":
        if len(args) < 2:
            print(ui.hint("Usage: bet <challenger|opponent> <amount>"))
            return True
        if not _ensure_arena_location(player):
            return True
        fighter = args[0].lower()
        if fighter not in {"challenger", "opponent"}:
            print(ui.warning("Bet on 'challenger' or 'opponent'."))
            return True
        try:
            amount = int(args[1])
        except ValueError:
            print(ui.warning("Bet amount must be numeric."))
            return True
        if amount <= 0:
            print(ui.warning("Bet amount must be positive."))
            return True
        if player.spheres < amount:
            print(ui.warning("You don't have enough marks to cover that bet."))
            return True
        if game_state.arena_bet:
            print(ui.warning("You already have a wager pending."))
            return True
        player.spheres -= amount
        game_state.arena_bet = {"fighter": fighter, "amount": amount}
        print(ui.success(f"You wager {amount} mark(s) on the {fighter}."))
        return True

    if verb == "collect":
        if not _ensure_arena_location(player):
            return True
        print(player.collect_arena_winnings())
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
        query = " ".join(args)
        quest_id = _resolve_quest_id(player, query)
        if not quest_id:
            print(ui.warning("No quest by that id."))
            return True
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
        query = " ".join(args)
        quest_id = _resolve_quest_id(player, query)
        if not quest_id:
            print(ui.warning("No quest by that id."))
            return True
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

    if verb == "yield":
        if player.active_duel:
            player.active_duel.request_yield()
        else:
            print(ui.hint("You're not currently engaged in a duel."))
        return True

    suggestion = _suggest_command(verb)
    base = ui.error(f"'{verb}' isn't a known command.")
    hint_text = (
        ui.hint(f"Try '{suggestion}' instead.") if suggestion else ui.hint("Type 'help' for options.")
    )
    print(f"{base} {hint_text}")
    return True

