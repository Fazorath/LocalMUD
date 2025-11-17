from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from content_loader import content_manager
from enemies import DEFAULT_ENEMY_TEMPLATES, Enemy, PARSHENDI_SCOUT
from items import Item, STARTING_ITEMS
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

    @classmethod
    def from_template(cls, data: dict) -> "Room":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            description=data.get("description", ""),
            exits=dict(data.get("exits", {})),
            items=[],
            enemies=[],
            npcs=[],
        )


_rooms: Dict[str, Room] = {}


def load_world() -> Dict[str, Room]:
    """Initialize and return the Roshar layout."""
    global _rooms
    if _rooms:
        return _rooms
    templates = content_manager.rooms or content_manager.load_rooms()
    if templates:
        _rooms = {
            room_id: Room.from_template(room_data) for room_id, room_data in templates.items()
        }
        _populate_room_contents()
    else:
        _rooms = _build_fallback_world()
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


def _build_fallback_world() -> Dict[str, Room]:
    rooms = {
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
        "training_yard": Room(
            id="training_yard",
            name="Combat Training Yard",
            description=(
                "A packed-earth arena ringed with wooden posts. Spears thud against dummies "
                "while instructors watch every movement."
            ),
            exits={"south": "warcamp_plateau"},
        ),
    }

    rooms["warcamp_plateau"].exits["north"] = "training_yard"
    rooms["training_yard"].exits["south"] = "warcamp_plateau"
    rooms["training_yard"].items.append(
        Item(
            id="training_dummy",
            name="Training Dummy",
            description="A battered wooden post wrapped in hemp and leather.",
        )
    )

    rooms["bridgeman_barracks"].items.append(STARTING_ITEMS["sphere_mark"])
    rooms["storage_bay"].items.append(STARTING_ITEMS["training_spear"])
    rooms["chasm_rim"].enemies.append(PARSHENDI_SCOUT)
    rooms["bridgeman_barracks"].npcs.append(
        NPC(
            id="sergeant",
            name="Bridge Sergeant",
            role="gruff overseer of your bridge crew",
            room_id="bridgeman_barracks",
            lines=[
                "The sergeant eyes you, making sure you're not slacking.",
                "Bridge crews don't survive by taking it easy.",
            ],
        )
    )
    rooms["warcamp_plateau"].npcs.append(
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
        )
    )
    rooms["storage_bay"].npcs.append(
        NPC(
            id="armorer",
            name="Veteran Armorer",
            role="patches dented plate and keeps blades sharp",
            room_id="storage_bay",
            lines=[
                "The armorer polishes a dented breastplate with practiced motions.",
                "Keep the gear clean and it might just keep you alive.",
            ],
        )
    )
    return rooms


def _populate_room_contents() -> None:
    for room in _rooms.values():
        template = content_manager.rooms.get(room.id, {})
        for item_id in template.get("items", []):
            room.items.append(_create_item(item_id))
        for enemy_data in template.get("enemies", []):
            room.enemies.append(_create_enemy(enemy_data))
        for npc_id in template.get("npcs", []):
            npc = _create_npc(npc_id)
            if npc:
                room.npcs.append(npc)


def _create_item(item_id: str) -> Item:
    item_template = content_manager.items.get(item_id)
    if item_template:
        return Item.from_template(item_template)
    return STARTING_ITEMS.get(item_id, Item(id=item_id, name=item_id.title(), description=""))


def _create_enemy(enemy_data) -> Enemy:
    if isinstance(enemy_data, dict):
        return Enemy.from_template(enemy_data)
    template = DEFAULT_ENEMY_TEMPLATES.get(enemy_data)
    if template:
        return Enemy.from_template(template)
    return PARSHENDI_SCOUT


def _create_npc(npc_id: str) -> NPC | None:
    data = content_manager.npcs.get(npc_id)
    if not data:
        return None
    npc = NPC.from_template(data)
    if npc.id == "quartermaster":
        npc.on_talk = quartermaster_on_talk
    return npc

