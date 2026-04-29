from __future__ import annotations

import json
from pathlib import Path

from game_shelf.models import OwnedGame


class CollectionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[OwnedGame]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        items = raw.get("collection", [])
        return [OwnedGame.from_dict(item) for item in items]

    def save(self, collection: list[OwnedGame]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"collection": [item.to_dict() for item in collection]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def upsert(self, owned_game: OwnedGame) -> None:
        collection = self.load()
        existing_index: int | None = None
        for i, item in enumerate(collection):
            if (item.game.source, item.game.source_id) == (owned_game.game.source, owned_game.game.source_id):
                existing_index = i
                break

        if existing_index is None:
            collection.append(owned_game)
        else:
            collection[existing_index] = owned_game
        self.save(collection)
