from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Job:
    id: str
    name: str
    description: str
    reward_spheres: int
    cooldown_turns: int
    allowed_rooms: Tuple[str, ...] = ()
    remaining_cooldown: int = 0

    def can_do(self) -> bool:
        return self.remaining_cooldown == 0

    def do_job(self) -> Tuple[str, int]:
        if not self.can_do():
            return (f"{self.name} won't be available for {self.remaining_cooldown} more turn(s).", 0)
        self.remaining_cooldown = self.cooldown_turns
        return (f"You complete '{self.name}' and hand in the report.", self.reward_spheres)

    def tick(self) -> None:
        if self.remaining_cooldown > 0:
            self.remaining_cooldown -= 1


def create_jobs() -> List[Job]:
    return [
        Job(
            id="clean_spears",
            name="Clean Spears",
            description="Polish the bridgeman spears in the barracks rack.",
            reward_spheres=1,
            cooldown_turns=2,
        ),
        Job(
            id="carry_supplies",
            name="Carry Supplies",
            description="Haul gemheart crates across the warcamp plateau.",
            reward_spheres=2,
            cooldown_turns=3,
        ),
        Job(
            id="latrine_duty",
            name="Latrine Duty",
            description="Least glorious, but the warcamp needs it done.",
            reward_spheres=1,
            cooldown_turns=4,
        ),
        Job(
            id="weapon_cleaning",
            name="Weapon Cleaning",
            description="Cleaning spears and quarterstaves keeps the armory in shape.",
            reward_spheres=1,
            cooldown_turns=2,
            allowed_rooms=("training_yard", "bridgeman_barracks"),
        ),
        Job(
            id="dummy_repair",
            name="Dummy Repair",
            description="Repair wooden training dummies after sparring sessions.",
            reward_spheres=1,
            cooldown_turns=3,
            allowed_rooms=("training_yard",),
        ),
        Job(
            id="drill_assistant",
            name="Drill Assistant",
            description="Assist the drill instructor in teaching formations.",
            reward_spheres=2,
            cooldown_turns=4,
            allowed_rooms=("training_yard",),
        ),
    ]

