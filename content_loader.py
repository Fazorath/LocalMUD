from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_json_files_from_dir(path: Path) -> Dict[str, dict]:
    data: Dict[str, dict] = {}
    if not path.exists():
        return data
    for file_path in sorted(path.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        entry_id = payload.get("id") or file_path.stem
        data[entry_id] = payload
    return data


class ContentManager:
    def __init__(self) -> None:
        self.base_path = Path("content")
        self.items: Dict[str, dict] = {}
        self.npcs: Dict[str, dict] = {}
        self.rooms: Dict[str, dict] = {}
        self.quests: Dict[str, dict] = {}
        self.factions: Dict[str, dict] = {}
        self.events: Dict[str, dict] = {}
        self.dialogue: Dict[str, dict] = {}

    def load_all_content(self, base_path: str = "content") -> None:
        self.base_path = Path(base_path)
        self.items = self.load_items()
        self.npcs = self.load_npcs()
        self.rooms = self.load_rooms()
        self.quests = self.load_quests()
        self.factions = self.load_factions()
        self.events = self.load_events()
        self.dialogue = self.load_dialogue()

    def load_items(self) -> Dict[str, dict]:
        return load_json_files_from_dir(self.base_path / "items")

    def load_npcs(self) -> Dict[str, dict]:
        return load_json_files_from_dir(self.base_path / "npcs")

    def load_rooms(self) -> Dict[str, dict]:
        return load_json_files_from_dir(self.base_path / "rooms")

    def load_quests(self) -> Dict[str, dict]:
        return load_json_files_from_dir(self.base_path / "quests")

    def load_dialogue(self) -> Dict[str, dict]:
        return load_json_files_from_dir(self.base_path / "dialogue")

    def load_factions(self) -> Dict[str, dict]:
        path = self.base_path / "factions.json"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data

    def load_events(self) -> Dict[str, dict]:
        path = self.base_path / "events.json"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data


content_manager = ContentManager()

