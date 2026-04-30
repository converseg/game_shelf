from __future__ import annotations

import json
from pathlib import Path

from game_shelf.models import CollectionGame


class CollectionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[CollectionGame]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        items = raw.get("collection", [])
        return [CollectionGame.model_validate(item) for item in items]

    def save(self, collection: list[CollectionGame]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"collection": [item.model_dump(mode="json") for item in collection]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def upsert(self, collection_game: CollectionGame) -> None:
        collection = self.load()
        existing_index: int | None = None
        for i, item in enumerate(collection):
            if (item.game.source, item.game.source_id) == (
                collection_game.game.source,
                collection_game.game.source_id,
            ):
                existing_index = i
                break

        if existing_index is None:
            collection.append(collection_game)
        else:
            existing = collection[existing_index]
            merged = collection_game
            if collection_game.personal_rating is None:
                merged = merged.model_copy(update={"personal_rating": existing.personal_rating})
            merged = merged.model_copy(update={"added_at": existing.added_at})
            collection[existing_index] = merged
        self.save(collection)

    def set_rating(self, *, source: str, source_id: str, rating: int) -> bool:
        collection = self.load()
        for i, item in enumerate(collection):
            if (item.game.source, item.game.source_id) == (source, source_id):
                collection[i] = item.model_copy(update={"personal_rating": rating})
                self.save(collection)
                return True
        return False
