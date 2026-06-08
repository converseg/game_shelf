from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from game_shelf.bgg import BggXmlApi2Client
from game_shelf.datasource.bgg_xml_api2 import _parse_thing_item
from game_shelf.models import CollectionGame, GameDetails
from game_shelf.storage import CollectionStore


# ---------------------------------------------------------------------------
# Search / lookup (read-only BGG queries)
# ---------------------------------------------------------------------------


def search_games(
    query: str,
    *,
    limit: int = 5,
    api_key: str | None = None,
) -> list[GameDetails]:
    """Search BGG by name, returning up to *limit* matches."""
    from game_shelf.datasource import BggXmlApi2DataSource

    ds = BggXmlApi2DataSource(api_key=api_key)
    return ds.lookup_by_name(query, limit=limit)


def lookup_game(
    source_id: str,
    *,
    api_key: str | None = None,
) -> GameDetails | None:
    """Fetch a single BGG game by its numeric source ID."""
    from game_shelf.datasource import BggXmlApi2DataSource

    ds = BggXmlApi2DataSource(api_key=api_key)
    results = ds.lookup_by_ids([source_id])
    return results[0] if results else None


# ---------------------------------------------------------------------------
# Metadata refresh (batch update from BGG)
# ---------------------------------------------------------------------------


@dataclass
class GameDiff:
    """Describes a single changed field between old and new metadata."""

    field: str
    old: object
    new: object


@dataclass
class MetadataPreview:
    """Result of previewing BGG metadata updates for a collection."""

    changed_games: list[tuple[CollectionGame, list[GameDiff]]] = field(default_factory=list)
    unchanged_count: int = 0
    failed_ids: list[str] = field(default_factory=list)


def _fmt(v: object) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _diff_details(old: GameDetails, new: GameDetails) -> list[GameDiff]:
    diffs: list[GameDiff] = []

    def check(field: str, a: object, b: object) -> None:
        if a != b:
            diffs.append(GameDiff(field, a, b))

    check("name", old.name, new.name)
    check("year_published", old.year_published, new.year_published)
    check("min_players", old.min_players, new.min_players)
    check("max_players", old.max_players, new.max_players)
    check("min_playtime_minutes", old.min_playtime_minutes, new.min_playtime_minutes)
    check("max_playtime_minutes", old.max_playtime_minutes, new.max_playtime_minutes)
    check("weight", old.weight, new.weight)
    check("bgg_rating", old.bgg_rating, new.bgg_rating)

    def list_key(values: list[str]) -> str:
        return ", ".join(sorted(values))

    if list_key(old.mechanics) != list_key(new.mechanics):
        check("mechanics", old.mechanics, new.mechanics)
    if list_key(old.categories) != list_key(new.categories):
        check("categories", old.categories, new.categories)
    if list_key(old.themes) != list_key(new.themes):
        check("themes", old.themes, new.themes)

    if (old.description or "") != (new.description or ""):
        check("description", old.description, new.description)

    return diffs


def _chunk(values: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


def _fetch_bgg_details(
    ids: list[str],
    *,
    client: BggXmlApi2Client | None = None,
    api_key: str | None = None,
) -> tuple[dict[str, GameDetails], list[str]]:
    """Fetch GameDetails for a list of BGG source IDs.

    Returns (fetched_map, failed_ids).
    """
    if client is None:
        client = BggXmlApi2Client(api_key=api_key)

    fetched: dict[str, GameDetails] = {}
    failed: list[str] = []

    for chunk in _chunk(ids, 20):
        root = client.thing(id=chunk, stats=True)
        for item in root.findall("./item"):
            item_id = item.get("id") or ""
            if item_id:
                fetched[item_id] = _parse_thing_item(item)

    for sid in ids:
        if sid not in fetched:
            failed.append(sid)

    return fetched, failed


def preview_metadata_updates(
    path: Path,
    *,
    client: BggXmlApi2Client | None = None,
    api_key: str | None = None,
) -> MetadataPreview:
    """Fetch fresh BGG metadata for all BGG-sourced games in the collection.

    Returns a preview of what would change, without modifying the collection.

    Pass *client* to inject a fake BGG client for testing.
    """
    store = CollectionStore(path)
    collection = store.load()

    target_ids = sorted(
        {
            g.game.source_id
            for g in collection
            if g.game.source == "bgg_xml_api" and g.game.source_id
        }
    )

    if not target_ids:
        return MetadataPreview()

    fetched, failed = _fetch_bgg_details(target_ids, client=client, api_key=api_key)

    preview = MetadataPreview(failed_ids=failed)
    changed_count = 0

    for item in collection:
        if item.game.source != "bgg_xml_api":
            continue
        sid = item.game.source_id
        if not sid or sid not in fetched:
            continue
        new_details = fetched[sid]
        diffs = _diff_details(item.game, new_details)
        if diffs:
            preview.changed_games.append((item, diffs))
            changed_count += 1

    preview.unchanged_count = len(target_ids) - changed_count
    return preview


def apply_metadata_updates(
    path: Path,
    *,
    client: BggXmlApi2Client | None = None,
    api_key: str | None = None,
) -> MetadataPreview:
    """Fetch fresh BGG metadata and apply all changes to the collection.

    Returns a preview of what was changed.

    Pass *client* to inject a fake BGG client for testing.
    """
    store = CollectionStore(path)
    collection = store.load()

    preview = preview_metadata_updates(path, client=client, api_key=api_key)

    if not preview.changed_games:
        return preview

    changed_ids = {g.game.source_id for g, _ in preview.changed_games}
    fetched, _ = _fetch_bgg_details(list(changed_ids), client=client, api_key=api_key)

    updated: list[CollectionGame] = []
    for item in collection:
        if item.game.source == "bgg_xml_api" and item.game.source_id in fetched:
            new_details = fetched[item.game.source_id]
            diffs = _diff_details(item.game, new_details)
            if diffs:
                updated.append(item.model_copy(update={"game": new_details}))
                continue
        updated.append(item)

    store.save(updated)
    return preview
