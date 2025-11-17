from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from content_loader import ContentManager


@dataclass
class Faction:
    id: str
    name: str
    description: str


class FactionManager:
    def __init__(self) -> None:
        self.factions: Dict[str, Faction] = {}

    def load(self, content_manager: ContentManager) -> None:
        templates = content_manager.factions or content_manager.load_factions()
        self.factions = {
            faction_id: Faction(
                id=faction_id,
                name=template.get("name", faction_id.title()),
                description=template.get("description", ""),
            )
            for faction_id, template in templates.items()
        }

    def get(self, faction_id: str) -> Optional[Faction]:
        return self.factions.get(faction_id)


faction_manager = FactionManager()

