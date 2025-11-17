import world
from commands import handle_command
from events import build_event_manager
from game_state import GameState
from player import Player
import quests
import ui
from content_loader import content_manager
from dialogue import dialogue_manager
from factions import faction_manager
from interactions import (
    GambleInteraction,
    InteractionRegistry,
    SparInteraction,
    TalkInteraction,
    TradeInteraction,
    TrainingInteraction,
)

INTRO = (
    "=== BRIDGE FOUR: SHATTERED PLAINS ===\n"
    "You wake in the dim glow of an Alethi warcamp, storms rumbling across the distant plains."
)


def initialize_content() -> None:
    content_manager.load_all_content()
    quests.initialize_quests(content_manager)
    faction_manager.load(content_manager)
    dialogue_manager.load(content_manager)
    InteractionRegistry.register("talk", TalkInteraction(dialogue_manager))
    InteractionRegistry.register("trade", TradeInteraction())
    InteractionRegistry.register("gamble", GambleInteraction())
    InteractionRegistry.register("train", TrainingInteraction())
    InteractionRegistry.register("spar", SparInteraction())

    def _run_dialogue_interaction(name, player, npc, game_state):
        interaction = InteractionRegistry.get(name)
        if not interaction:
            return [ui.warning("They can't help with that right now.")]
        return interaction.run(player, npc, game_state)

    dialogue_manager.set_interaction_runner(_run_dialogue_interaction)


def main() -> None:
    initialize_content()
    world.load_world()
    game_state = GameState()
    event_manager = build_event_manager()

    print(ui.banner(INTRO))
    name = input(ui.info("What do the men call you? ")).strip() or "Bridgeman"
    player = Player(name=name, starting_room="bridgeman_barracks")

    print()
    print(ui.narration("You tighten your bridge-crew uniform and take stock."))
    print()
    print(player.describe_room())
    event_manager.trigger_enter_room(player, game_state, player.current_room)

    while True:
        try:
            current_room = world.get_room(player.current_room).name
            raw_command = input(ui.command_prompt(current_room, game_state.time_of_day, player.spheres))
        except (EOFError, KeyboardInterrupt):
            print()
            print(ui.info("The winds quiet as you leave the command tent."))
            break

        previous_room = player.current_room
        keep_playing = handle_command(player, raw_command, game_state)
        if not keep_playing:
            break

        game_state.advance_turn()

        if player.current_room != previous_room:
            event_manager.trigger_enter_room(player, game_state, player.current_room)

        event_manager.trigger_random(player, game_state)

        if game_state.maybe_change_time_of_day():
            event_manager.trigger_time_change(player, game_state)

        player.tick_jobs()


if __name__ == "__main__":
    main()

