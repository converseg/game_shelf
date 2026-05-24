from __future__ import annotations

from difflib import get_close_matches
import os
from collections.abc import Iterable
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

from game_shelf.bgg import BggXmlApi2Client
from game_shelf.models import GameDetails


def _attr(elem: ET.Element | None, attr: str) -> str | None:
    if elem is None:
        return None
    return elem.get(attr)


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _clean_description(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(str(text).split()) or None


def _primary_name(item: ET.Element) -> str | None:
    for name in item.findall("./name"):
        if name.get("type") == "primary":
            return name.get("value")
    first = item.find("./name")
    return _attr(first, "value")


def _parse_thing_item(item: ET.Element) -> GameDetails:
    source_id = item.get("id") or ""

    categories = [
        l.get("value")
        for l in item.findall("./link[@type='boardgamecategory']")
        if l.get("value")
    ]
    mechanics = [
        l.get("value")
        for l in item.findall("./link[@type='boardgamemechanic']")
        if l.get("value")
    ]

    min_play = _int(_attr(item.find("./minplaytime"), "value"))
    max_play = _int(_attr(item.find("./maxplaytime"), "value"))
    playing = _int(_attr(item.find("./playingtime"), "value"))

    approx = None
    if min_play is not None and max_play is not None:
        approx = int(round((min_play + max_play) / 2))
    elif playing is not None:
        approx = playing

    weight = _float(_attr(item.find("./statistics/ratings/averageweight"), "value"))
    bgg_rating = _float(_attr(item.find("./statistics/ratings/average"), "value"))

    # For now, treat BGG categories as "themes" for prompt display; themes are free-form.
    details = GameDetails(
        source="bgg_xml_api",
        source_id=source_id,
        name=_primary_name(item) or source_id,
        year_published=_int(_attr(item.find("./yearpublished"), "value")),
        min_players=_int(_attr(item.find("./minplayers"), "value")),
        max_players=_int(_attr(item.find("./maxplayers"), "value")),
        min_playtime_minutes=min_play,
        max_playtime_minutes=max_play,
        approx_playtime_minutes=approx,
        description=_clean_description(item.findtext("./description")),
        categories=categories,
        mechanics=mechanics,
        themes=categories,
        weight=weight,
        bgg_rating=bgg_rating,
    )
    return details


class BggXmlApi2DataSource:
    def __init__(self, *, api_key: str | None = None) -> None:
        load_dotenv()
        self._api_key = api_key or os.environ.get("BGG_API_KEY")
        self._client = BggXmlApi2Client(api_key=self._api_key)

    def _thing_batched(self, *, ids: list[str], stats: bool) -> list[ET.Element]:
        items: list[ET.Element] = []

        def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
            for i in range(0, len(values), size):
                yield values[i : i + size]

        for chunk in _chunks(ids, 20):
            root = self._client.thing(id=chunk, stats=stats)
            items.extend(list(root.findall("./item")))
        return items

    def lookup_by_name(self, name: str, limit: int = 5) -> list[GameDetails]:
        root = self._client.search(query=name, type="boardgame")
        ids: list[str] = []
        for item in root.findall("./item"):
            item_id = item.get("id")
            if item_id:
                ids.append(item_id)
            if len(ids) >= limit:
                break
        if not ids:
            return []

        parsed: dict[str, GameDetails] = {}
        for item in self._thing_batched(ids=ids, stats=True):
            item_id = item.get("id")
            if not item_id:
                continue
            parsed[item_id] = _parse_thing_item(item)

        ordered: list[GameDetails] = []
        for item_id in ids:
            d = parsed.get(item_id)
            if d is not None:
                ordered.append(d)
        return ordered[:limit]

    def lookup_by_ids(self, ids: list[str], *, stats: bool = True) -> list[GameDetails]:
        clean = [str(i).strip() for i in ids if str(i).strip()]
        if not clean:
            return []

        parsed: dict[str, GameDetails] = {}
        for item in self._thing_batched(ids=clean, stats=stats):
            item_id = item.get("id")
            if not item_id:
                continue
            parsed[item_id] = _parse_thing_item(item)

        ordered: list[GameDetails] = []
        for item_id in clean:
            d = parsed.get(item_id)
            if d is not None:
                ordered.append(d)
        return ordered

    def lookup_best(self, name: str) -> GameDetails | None:
        matches = self.lookup_by_name(name, limit=1)
        return matches[0] if matches else None

    def suggest(self, name: str, limit: int = 5) -> list[str]:
        try:
            root = self._client.search(query=name, type="boardgame")
        except requests.RequestException:
            return []

        names: list[str] = []
        for item in root.findall("./item")[:limit]:
            n = _attr(item.find("./name"), "value")
            if n:
                names.append(n)

        if names:
            return names

        return []
