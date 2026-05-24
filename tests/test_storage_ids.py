from __future__ import annotations

import json
from pathlib import Path

from game_shelf.models import CollectionGame, GameDetails
from game_shelf.storage import CollectionStore


def _read_collection(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("collection", []))


def test_load_assigns_uuid_ids(collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    # Legacy item without "id"
    store.save(
        [
            CollectionGame(
                id="fixed-id",
                game=GameDetails(source="local_seed", source_id="local_compile", name="Compile"),
                is_owned=False,
                is_wishlist=True,
            )
        ]
    )
    # Manually remove id from JSON to simulate old file.
    items = _read_collection(collection_path)
    items[0].pop("id", None)
    collection_path.write_text(json.dumps({"collection": items}, indent=2) + "\n", encoding="utf-8")

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].id
    # Ensure migration persisted back to disk.
    persisted = _read_collection(collection_path)
    assert persisted[0].get("id") == loaded[0].id


def test_upsert_preserves_existing_id(collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    existing = CollectionGame(
        id="my-stable-id",
        game=GameDetails(source="bgg_xml_api", source_id="13", name="CATAN"),
        is_owned=True,
        is_wishlist=False,
        personal_rating=7,
    )
    store.save([existing])

    # Upsert same (source, source_id) with different fields should keep the old id.
    updated = CollectionGame(
        id="new-id-that-should-not-win",
        game=GameDetails(source="bgg_xml_api", source_id="13", name="Catan"),
        is_owned=False,
        is_wishlist=True,
        personal_rating=None,
    )
    store.upsert(updated)

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].id == "my-stable-id"
    assert loaded[0].personal_rating == 7
    assert loaded[0].is_owned is False
    assert loaded[0].is_wishlist is True

