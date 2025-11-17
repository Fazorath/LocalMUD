from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Optional

import world
from content_loader import content_manager
from items import Item


TriggerEffect = Callable[["Player", "GameState"], None]


@dataclass
class Event:
    id: str
    trigger: str  # enter_room, random, time
    chance: float
    description: str
    room_id: Optional[str] = None
    effect: TriggerEffect = lambda player, state: None

    @classmethod
    def from_template(cls, data: dict) -> "Event":
        return cls(
            id=data.get("id", data.get("name", "event")),
            trigger=data.get("trigger", "random"),
            chance=float(data.get("chance", 1.0)),
            description=data.get("description", ""),
            room_id=data.get("room_id"),
        )


class EventManager:
    def __init__(self) -> None:
        self.events: List[Event] = []

    def register(self, event: Event) -> None:
        self.events.append(event)

    def trigger_enter_room(self, player: "Player", game_state: "GameState", room_id: str) -> None:
        for event in self.events:
            if event.trigger == "enter_room" and event.room_id == room_id:
                if random.random() <= event.chance:
                    print(event.description)
                    event.effect(player, game_state)

    def trigger_random(self, player: "Player", game_state: "GameState") -> None:
        for event in self.events:
            if event.trigger == "random" and random.random() <= event.chance:
                print(event.description)
                event.effect(player, game_state)

    def trigger_time_change(self, player: "Player", game_state: "GameState") -> None:
        for event in self.events:
            if event.trigger == "time":
                print(event.description.format(time=game_state.time_of_day))
                event.effect(player, game_state)


def build_event_manager() -> EventManager:
    manager = EventManager()
    _register_content_events(manager)

    def cremling_effect(player: "Player", _: "GameState") -> None:
        # Flavor only.
        pass

    manager.register(
        Event(
            id="cremling_skitter",
            trigger="enter_room",
            chance=1.0,
            room_id="bridgeman_barracks",
            description="A cremling darts beneath a bunk, startled by your footsteps.",
            effect=cremling_effect,
        )
    )

    def highstorm_effect(_: "Player", game_state: "GameState") -> None:
        game_state.highstorm_warning_active = True

    manager.register(
        Event(
            id="highstorm_warning",
            trigger="random",
            chance=0.1,
            room_id=None,
            description="Dark clouds boil on the horizon—word spreads of an approaching highstorm.",
            effect=highstorm_effect,
        )
    )

    def soldier_help_effect(player: "Player", _: "GameState") -> None:
        room = world.get_room("warcamp_plateau")
        existing = next((item for item in room.items if item.id == "aid_bundle"), None)
        if existing:
            return
        bundle = Item(
            id="aid_bundle",
            name="Field Aid Bundle",
            description="Bandages, antiseptic, and a single infused chip—left for whoever answers the call.",
        )
        room.items.append(bundle)

    manager.register(
        Event(
            id="soldier_help",
            trigger="enter_room",
            chance=1.0,
            room_id="warcamp_plateau",
            description="A soldier shouts for help, pointing to an abandoned aid bundle.",
            effect=soldier_help_effect,
        )
    )

    def time_effect(_: "Player", game_state: "GameState") -> None:
        if game_state.time_of_day == "morning":
            game_state.highstorm_warning_active = False

    manager.register(
        Event(
            id="time_shift",
            trigger="time",
            chance=1.0,
            room_id=None,
            description="The camp settles into {time}.",
            effect=time_effect,
        )
    )

    return manager


def _register_content_events(manager: EventManager) -> None:
    templates = content_manager.events or content_manager.load_events()
    for event_id, data in templates.items():
        template = dict(data)
        template.setdefault("id", event_id)
        manager.register(Event.from_template(template))

