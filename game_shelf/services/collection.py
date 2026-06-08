from __future__ import annotations

from pathlib import Path

from game_shelf.models import CollectionGame, GameDetails
from game_shelf.storage import CollectionStore


def list_games(
    path: Path,
    *,
    owned: bool | None = None,
    wishlist: bool | None = None,
    query: str | None = None,
) -> list[CollectionGame]:
    """Load and optionally filter the collection.

    Parameters
    ----------
    owned:
        If True, only owned games. If False, only non-owned games. If None, no filter.
    wishlist:
        If True, only wishlist games. If False, only non-wishlist games. If None, no filter.
    query:
        Case-insensitive substring match against game name.
    """
    store = CollectionStore(path)
    collection = store.load()

    if owned is not None:
        collection = [g for g in collection if g.is_owned == owned]
    if wishlist is not None:
        collection = [g for g in collection if g.is_wishlist == wishlist]
    if query:
        q = query.strip().lower()
        collection = [g for g in collection if q in g.game.name.lower()]

    return collection


def add_game(
    path: Path,
    details: GameDetails,
    *,
    owned: bool = True,
    wishlist: bool = False,
    rating: int | None = None,
) -> CollectionGame:
    """Add a game to the collection (or merge if same source+source_id)."""
    store = CollectionStore(path)
    game = CollectionGame(
        game=details,
        personal_rating=rating,
        is_owned=owned,
        is_wishlist=wishlist,
    )
    store.upsert(game)
    return game


def remove_game(path: Path, game_id: str) -> CollectionGame | None:
    """Remove a single game by its local UUID.

    Returns the removed game, or None if not found.
    Raises ValueError if multiple games match (shouldn't happen with UUIDs).
    """
    store = CollectionStore(path)
    collection = store.load()

    matches = [g for g in collection if g.id == game_id]
    if not matches:
        return None
    if len(matches) > 1:
        msg = f"Internal error: {len(matches)} games share id {game_id!r}"
        raise ValueError(msg)

    kept = [g for g in collection if g.id != game_id]
    store.save(kept)
    return matches[0]


def remove_by_source(
    path: Path,
    source_id: str,
    *,
    source: str | None = None,
    remove_all: bool = False,
) -> list[CollectionGame]:
    """Remove games matching a source ID, optionally narrowed by source name.

    Returns the list of removed games.
    Raises ValueError if multiple matches exist and remove_all is False.
    """
    store = CollectionStore(path)
    collection = store.load()

    matches = [
        g
        for g in collection
        if g.game.source_id == source_id and (source is None or g.game.source == source)
    ]

    if not matches:
        return []

    if len(matches) > 1 and not remove_all:
        names = [f"{g.game.name} (source={g.game.source})" for g in matches]
        msg = (
            f"{len(matches)} games match source_id {source_id!r}: "
            f"{'; '.join(names)}. "
            "Use remove_all=True or narrow with source=."
        )
        raise ValueError(msg)

    kept = [
        g
        for g in collection
        if not (g.game.source_id == source_id and (source is None or g.game.source == source))
    ]
    store.save(kept)
    return matches


def rate_game(
    path: Path,
    source: str,
    source_id: str,
    rating: int,
) -> CollectionGame | None:
    """Set a personal rating (1-10) for a game identified by source+source_id.

    Returns the updated game, or None if not found.
    """
    if not (1 <= rating <= 10):
        raise ValueError(f"Rating must be 1-10, got {rating}")

    store = CollectionStore(path)
    found = store.set_rating(source=source, source_id=source_id, rating=rating)
    if not found:
        return None

    # Reload to return the updated object
    collection = store.load()
    for g in collection:
        if (g.game.source, g.game.source_id) == (source, source_id):
            return g
    return None


def update_game(
    path: Path,
    game_id: str,
    *,
    owned: bool | None = None,
    wishlist: bool | None = None,
    rating: int | None = None,
) -> CollectionGame | None:
    """Update fields of a game identified by its local UUID.

    Returns the updated game, or None if not found.
    """
    store = CollectionStore(path)
    collection = store.load()

    for i, game in enumerate(collection):
        if game.id != game_id:
            continue

        kwargs: dict[str, object] = {}
        if owned is not None:
            kwargs["is_owned"] = owned
        if wishlist is not None:
            kwargs["is_wishlist"] = wishlist
        if rating is not None:
            if not (1 <= rating <= 10):
                raise ValueError(f"Rating must be 1-10, got {rating}")
            kwargs["personal_rating"] = rating

        updated = game.model_copy(update=kwargs)
        collection[i] = updated
        store.save(collection)
        return updated

    return None
