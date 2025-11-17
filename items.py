from dataclasses import dataclass
from typing import Dict


@dataclass
class Item:
    id: str
    name: str
    description: str
    type: str = "generic"
    value: int = 0

    @classmethod
    def from_template(cls, data: dict) -> "Item":
        item_type = data.get("type", "generic")
        if item_type == "weapon":
            return Weapon.from_template(data)
        if item_type == "armor":
            return Armor.from_template(data)
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            description=data.get("description", ""),
            type=item_type,
            value=int(data.get("value", 0)),
        )


@dataclass
class Weapon(Item):
    damage_min: int = 1
    damage_max: int = 2
    weapon_type: str = "fists"

    @classmethod
    def from_template(cls, data: dict) -> "Weapon":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            description=data.get("description", ""),
            type="weapon",
            value=int(data.get("value", 0)),
            damage_min=int(data.get("damage_min", 1)),
            damage_max=int(data.get("damage_max", 2)),
            weapon_type=data.get("weapon_type", "fists"),
        )


@dataclass
class Armor(Item):
    slot: str = "chest"
    armor_value: int = 0
    dodge_penalty: int = 0

    @classmethod
    def from_template(cls, data: dict) -> "Armor":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            description=data.get("description", ""),
            type="armor",
            value=int(data.get("value", 0)),
            slot=data.get("slot", "chest"),
            armor_value=int(data.get("armor_value", 0)),
            dodge_penalty=int(data.get("dodge_penalty", 0)),
        )


DEFAULT_ITEM_TEMPLATES: Dict[str, dict] = {
    "sphere_mark": {
        "id": "sphere_mark",
        "type": "currency",
        "name": "Infused Mark",
        "description": "A diamond mark glowing softly with Stormlight; common currency and a handy light.",
        "value": 1,
    },
    "training_spear": {
        "id": "training_spear",
        "type": "weapon",
        "name": "Training Spear",
        "description": "A dull spear used on the practice grounds. Balanced but not truly lethal.",
        "damage_min": 1,
        "damage_max": 4,
        "weapon_type": "spear",
    },
}

SPHERE_MARK = Item.from_template(DEFAULT_ITEM_TEMPLATES["sphere_mark"])
TRAINING_SPEAR = Item.from_template(DEFAULT_ITEM_TEMPLATES["training_spear"])

STARTING_ITEMS = {
    SPHERE_MARK.id: SPHERE_MARK,
    TRAINING_SPEAR.id: TRAINING_SPEAR,
}

