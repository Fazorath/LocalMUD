from dataclasses import dataclass
from typing import Dict


@dataclass
class Enemy:
    id: str
    name: str
    hp: int
    attack_min: int
    attack_max: int
    description: str

    @classmethod
    def from_template(cls, data: dict) -> "Enemy":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"].title()),
            hp=int(data.get("hp", 5)),
            attack_min=int(data.get("attack_min", 1)),
            attack_max=int(data.get("attack_max", 2)),
            description=data.get("description", ""),
        )


DEFAULT_ENEMY_TEMPLATES: Dict[str, dict] = {
    "parshendi_scout": {
        "id": "parshendi_scout",
        "name": "Parshendi Scout",
        "hp": 10,
        "attack_min": 1,
        "attack_max": 3,
        "description": "A lone Parshendi scout in carapace armor, scanning the chasms for Alethi movement.",
    }
}

PARSHENDI_SCOUT = Enemy.from_template(DEFAULT_ENEMY_TEMPLATES["parshendi_scout"])
