from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from enemies import Enemy, PARSHENDI_SCOUT
from items import Item, SPHERE_MARK, TRAINING_SPEAR
from npcs import NPC, quartermaster_on_talk


@dataclass
class Room:
    id: str
    name: str
    description: str
    exits: Dict[str, str]
    items: List[Item] = field(default_factory=list)
    enemies: List[Enemy] = field(default_factory=list)
    npcs: List[NPC] = field(default_factory=list)


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

    add_npc(
        "bridgeman_barracks",
        NPC(
            id="sergeant",
            name="Bridge Sergeant",
            role="gruff overseer of your bridge crew",
            room_id="bridgeman_barracks",
            lines=[
                "The sergeant eyes you, making sure you're not slacking.",
                "Bridge crews don't survive by taking it easy.",
            ],
        ),
    )
    add_npc(
        "warcamp_plateau",
        NPC(
            id="quartermaster",
            name="Quartermaster",
            role="keeps track of gear and spheres",
            room_id="warcamp_plateau",
            lines=[
                "The quartermaster flips through a list of supplies.",
                "Lose my gear and you'll be running extra chasm duty.",
            ],
            on_talk=quartermaster_on_talk,
        ),
    )
    add_npc(
        "storage_bay",
        NPC(
            id="armorer",
            name="Veteran Armorer",
            role="patches dented plate and keeps blades sharp",
            room_id="storage_bay",
            lines=[
                "The armorer polishes a dented breastplate with practiced motions.",
                "Keep the gear clean and it might just keep you alive.",
            ],
        ),
    )

    return _rooms


def get_room(room_id: str) -> Room:
    if not _rooms:
        load_world()
    return _rooms[room_id]


def add_item(room_id: str, item: Item) -> None:
    get_room(room_id).items.append(item)


def add_enemy(room_id: str, enemy: Enemy) -> None:
    get_room(room_id).enemies.append(enemy)


def add_npc(room_id: str, npc: NPC) -> None:
    get_room(room_id).npcs.append(npc)

