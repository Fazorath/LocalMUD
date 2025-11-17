from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from enemies import Enemy, PARSHENDI_SCOUT
from items import Item, SPHERE_MARK, TRAINING_SPEAR


@dataclass
class Room:
    id: str
    name: str
    description: str
    exits: Dict[str, str]
    items: List[Item] = field(default_factory=list)
    enemies: List[Enemy] = field(default_factory=list)


_rooms: Dict[str, Room] = {}


def load_world() -> Dict[str, Room]:
    """Initialize and return the Roshar layout."""
    global _rooms
    if _rooms:
        return _rooms

    _rooms = {
        "bridgeman_barracks": Room(
            id="bridgeman_barracks",
            name="Bridgeman Barracks",
            description=(
                "Cremlings skitter along the damp stone while narrow bunks groan under worn bedding. "
                "The distant rumble of a brewing highstorm vibrates through the walls."
            ),
            exits={"east": "warcamp_plateau"},
        ),
        "warcamp_plateau": Room(
            id="warcamp_plateau",
            name="Warcamp Plateau",
            description=(
                "Supply tents flap beneath bright gemstone lanterns. Bridgemen spar on dusty "
                "practice grounds while chasms carve the horizon."
            ),
            exits={"west": "bridgeman_barracks", "east": "chasm_rim", "south": "storage_bay"},
        ),
        "chasm_rim": Room(
            id="chasm_rim",
            name="Chasm Rim",
            description=(
                "The wind tugs at your clothing as it sweeps over the abyss. A makeshift wooden "
                "bridge stretches across the chasm, creaking with each gust."
            ),
            exits={"west": "warcamp_plateau"},
        ),
        "storage_bay": Room(
            id="storage_bay",
            name="Supply Storage Bay",
            description=(
                "Cracked chullsheds serve as makeshift storage, filled with racks of sparring gear "
                "and crates of infused spheres awaiting assignment."
            ),
            exits={"north": "warcamp_plateau"},
        ),
    }

    add_item("bridgeman_barracks", SPHERE_MARK)
    add_item("storage_bay", TRAINING_SPEAR)
    add_enemy("chasm_rim", PARSHENDI_SCOUT)

    return _rooms


def get_room(room_id: str) -> Room:
    if not _rooms:
        load_world()
    return _rooms[room_id]


def add_item(room_id: str, item: Item) -> None:
    get_room(room_id).items.append(item)


def add_enemy(room_id: str, enemy: Enemy) -> None:
    get_room(room_id).enemies.append(enemy)

