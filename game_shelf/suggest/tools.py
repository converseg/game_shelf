from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
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

@dataclass
class SuggestToolState:
    search_calls: int = 0
    allow_search: bool = True
    pending_user_guidance: str | None = None
    # Accumulated evidence for wrap-up behavior
    seen_search_results: list[dict[str, Any]] = field(default_factory=list)
    seen_things: dict[str, dict[str, Any]] = field(default_factory=dict)  # key = source_id


@tool
def ask_user(question: str) -> str:
    """Ask the user a clarifying question and return their free-form answer."""

    return str(click.prompt(question)).strip()


def build_suggest_tools(
    *,
    collection_path: str,
    max_bgg_candidates: int,
    no_bgg: bool,
    verbosity: int = 0,
    check_in_every_searches: int = 0,
) -> tuple[list[Any], SuggestToolState]:
    store = CollectionStore(Path(collection_path))
    state = SuggestToolState()

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

        nonlocal state
        if no_bgg:
            raise RuntimeError("BGG calls are disabled via --no-bgg.")

        state.search_calls += 1
        if check_in_every_searches > 0 and state.search_calls % check_in_every_searches == 0:
            guidance = str(
                click.prompt(
                    f"[suggest] Pausing after {state.search_calls} searches. What next? (e.g. 'keep going', 'wrap it up', or provide new constraints)",
                    default="keep going",
                    show_default=True,
                )
            ).strip()
            if guidance.lower() in {"wrap", "wrap it up", "stop", "stop searching", "finish"}:
                state.allow_search = False
                state.pending_user_guidance = "User asked to wrap it up now. Stop searching and produce final recommendations from current candidates."
            else:
                state.pending_user_guidance = f"User guidance during search: {guidance}"

        if not state.allow_search:
            note = state.pending_user_guidance or "User asked to wrap it up now."
            state.pending_user_guidance = None
            return [{"type": "wrap_up", "note": note}]

        client = BggXmlApi2Client(
            api_key=os.environ.get("BGG_API_KEY"),
            user_agent="game-shelf/0.1 (suggest)",
            verbose=verbosity >= 1,
        )
        with _BGG_LOCK:
            if verbosity >= 1:
                click.echo(f"[suggest] BGG search: {query!r} (limit={limit})", err=True)
            root = client.search(query=query, type="boardgame")

            # Heuristic fallback: BGG search can be picky with long queries.
            # If we got no items, retry with a shorter query (first 1-2 tokens).
            items = list(root.findall("./item"))
            if not items:
                words = [w for w in str(query).split() if w.strip()]
                shorter = None
                if len(words) >= 2:
                    shorter = " ".join(words[:2])
                elif len(words) == 1:
                    shorter = words[0]
                if shorter and shorter.lower() != str(query).strip().lower():
                    if verbosity >= 1:
                        click.echo(f"[suggest] no results; retrying with {shorter!r}", err=True)
                    root = client.search(query=shorter, type="boardgame")
                    items = list(root.findall("./item"))
        results: list[dict[str, Any]] = []
        for item in items[: min(limit, max_bgg_candidates)]:
            name_elem = item.find("./name")
            results.append(
                {
                    "source": "bgg_xml_api",
                    "source_id": item.get("id") or "",
                    "name": name_elem.get("value") if name_elem is not None else None,
                }
            )
        state.seen_search_results.extend(results)
        if verbosity >= 1:
            titles = [str(r.get("name") or "?") for r in results[:5]]
            click.echo(f"[suggest] top matches: {', '.join(titles) if titles else '(none)'}", err=True)

        if state.pending_user_guidance:
            note = state.pending_user_guidance
            state.pending_user_guidance = None
            # Return guidance to the agent in-band so it can adjust its plan without requiring
            # an additional tool call.
            return [{"type": "user_guidance", "note": note}] + results
        return results

    @tool
    def bgg_thing(ids: list[str]) -> list[dict[str, Any]]:
        """Fetch full BGG metadata for up to 20 ids (or more; will be batched)."""

        if no_bgg:
            raise RuntimeError("BGG calls are disabled via --no-bgg.")
        nonlocal state
        if not state.allow_search:
            note = state.pending_user_guidance or "User asked to wrap it up now."
            state.pending_user_guidance = None
            return [{"type": "wrap_up", "note": note}]
        client = BggXmlApi2Client(
            api_key=os.environ.get("BGG_API_KEY"),
            user_agent="game-shelf/0.1 (suggest)",
            verbose=verbosity >= 1,
        )
        parsed: list[dict[str, Any]] = []
        with _BGG_LOCK:
            clean_ids = [str(x) for x in ids if str(x).strip()]
            if verbosity >= 1:
                click.echo(f"[suggest] BGG thing: fetching {len(clean_ids)} ids", err=True)
            for chunk in _chunk(clean_ids, 20):
                if verbosity >= 1:
                    click.echo(f"[suggest] BGG thing batch: {len(chunk)} ids", err=True)
                root = client.thing(id=chunk, stats=True)
                for item in root.findall("./item"):
                    d = _parse_thing_item(item)
                    payload = d.model_dump(mode="json")
                    parsed.append(payload)
                    if d.source_id:
                        state.seen_things[d.source_id] = payload
        return parsed

    return [ask_user, list_collection, add_to_collection, bgg_search, bgg_thing], state
