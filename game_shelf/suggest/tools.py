from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
import os
import threading

import click
from langchain_core.tools import tool

from game_shelf.bgg import BggXmlApi2Client
from game_shelf.datasource.bgg_xml_api2 import _parse_thing_item
from game_shelf.models import CollectionGame
from game_shelf.models import GameDetails
from game_shelf.storage import CollectionStore


def _chunk(values: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


_BGG_LOCK = threading.Lock()


@tool
def ask_user(question: str) -> str:
    """Ask the user a clarifying question and return their free-form answer."""

    return str(click.prompt(question)).strip()


def build_suggest_tools(
    *,
    collection_path: str,
    max_bgg_candidates: int,
    no_bgg: bool,
) -> list[Any]:
    store = CollectionStore(Path(collection_path))

    @tool
    def list_collection() -> list[dict[str, Any]]:
        """Return the user's local collection as JSON."""

        items = store.load()
        return [item.model_dump(mode="json") for item in items]

    @tool
    def add_to_collection(
        *,
        source: str,
        source_id: str,
        name: str,
        owned: bool = True,
        wishlist: bool = False,
        rating: int | None = None,
    ) -> str:
        """Add a game to the local collection by source/source_id/name. (Used after user confirms.)"""

        game = GameDetails(source=source, source_id=source_id, name=name)
        item = CollectionGame(game=game, is_owned=owned, is_wishlist=wishlist, personal_rating=rating)
        store.upsert(item)
        return f"Added {name}."

    @tool
    def bgg_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search BoardGameGeek for board games by keyword/name. Returns a list of ids + names."""

        if no_bgg:
            raise RuntimeError("BGG calls are disabled via --no-bgg.")
        client = BggXmlApi2Client(api_key=os.environ.get("BGG_API_KEY"), user_agent="game-shelf/0.1 (suggest)")
        with _BGG_LOCK:
            root = client.search(query=query, type="boardgame")
        results: list[dict[str, Any]] = []
        for item in root.findall("./item")[: min(limit, max_bgg_candidates)]:
            name_elem = item.find("./name")
            results.append(
                {
                    "source": "bgg_xml_api",
                    "source_id": item.get("id") or "",
                    "name": name_elem.get("value") if name_elem is not None else None,
                }
            )
        return results

    @tool
    def bgg_thing(ids: list[str]) -> list[dict[str, Any]]:
        """Fetch full BGG metadata for up to 20 ids (or more; will be batched)."""

        if no_bgg:
            raise RuntimeError("BGG calls are disabled via --no-bgg.")
        client = BggXmlApi2Client(api_key=os.environ.get("BGG_API_KEY"), user_agent="game-shelf/0.1 (suggest)")
        parsed: list[dict[str, Any]] = []
        with _BGG_LOCK:
            for chunk in _chunk([str(x) for x in ids if str(x).strip()], 20):
                root = client.thing(id=chunk, stats=True)
                for item in root.findall("./item"):
                    d = _parse_thing_item(item)
                    parsed.append(d.model_dump(mode="json"))
        return parsed

    return [ask_user, list_collection, add_to_collection, bgg_search, bgg_thing]
