from dataclasses import dataclass


@dataclass
class Item:
    id: str
    name: str
    description: str


@dataclass
class Weapon(Item):
    damage_min: int
    damage_max: int


SPHERE_MARK = Item(
    id="sphere_mark",
    name="Infused Mark",
    description="A diamond mark glowing softly with Stormlight; common currency and a handy light.",
)

TRAINING_SPEAR = Weapon(
    id="training_spear",
    name="Training Spear",
    description="A dull spear used on the practice grounds. Balanced but not truly lethal.",
    damage_min=1,
    damage_max=4,
)

STARTING_ITEMS = {
    SPHERE_MARK.id: SPHERE_MARK,
    TRAINING_SPEAR.id: TRAINING_SPEAR,
}

