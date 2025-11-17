import quests
import world
from commands import handle_command
from events import build_event_manager
from game_state import GameState
from player import Player

INTRO = (
    "=== BRIDGE FOUR: SHATTERED PLAINS ===\n"
    "You wake in the dim glow of an Alethi warcamp, storms rumbling across the distant plains."
)


def main() -> None:
    world.load_world()
    game_state = GameState()
    event_manager = build_event_manager()

    print(INTRO)
    name = input("What do the men call you? ").strip() or "Bridgeman"
    player = Player(name=name, starting_room="bridgeman_barracks")
    initial_quest = quests.create_quest("first_errand")
    if initial_quest:
        print(player.quest_log.add(initial_quest))

    print("\nYou tighten your bridge-crew uniform and take stock.\n")
    print(player.describe_room())
    event_manager.trigger_enter_room(player, game_state, player.current_room)

    while True:
        try:
            raw_command = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\nThe winds quiet as you leave the command tent.")
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

