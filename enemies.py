from dataclasses import dataclass


@dataclass
class Enemy:
    id: str
    name: str
    hp: int
    attack_min: int
    attack_max: int
    description: str


PARSHENDI_SCOUT = Enemy(
    id="parshendi_scout",
    name="Parshendi Scout",
    hp=10,
    attack_min=1,
    attack_max=3,
    description="A lone Parshendi scout in carapace armor, scanning the chasms for Alethi movement.",
)

