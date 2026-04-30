from __future__ import annotations

import json
from difflib import get_close_matches
from importlib import resources

from game_shelf.models import GameDetails


def _norm(s: str) -> str:
    return " ".join(s.lower().strip().split())


class LocalSeedDataSource:
    def __init__(self) -> None:
        package = resources.files("game_shelf.resources")
        seed_path = package.joinpath("games_seed.json")
        raw = json.loads(seed_path.read_text(encoding="utf-8"))

        self._by_name: dict[str, dict] = {}
        for item in raw.get("games", []):
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            self._by_name[_norm(name)] = item

    def lookup_by_name(self, name: str, limit: int = 5) -> list[GameDetails]:
        key = _norm(name)
        if not key:
            return []

        exact = self._by_name.get(key)
        results: list[GameDetails] = []
        if exact is not None:
            results.append(GameDetails.model_validate(exact))

        keys = list(self._by_name.keys())
        matches = get_close_matches(key, keys, n=limit, cutoff=0.6)
        for m in matches:
            if m == key:
                continue
            item = self._by_name.get(m)
            if item is None:
                continue
            results.append(GameDetails.model_validate(item))

        return results[:limit]

    def lookup_best(self, name: str) -> GameDetails | None:
        key = _norm(name)
        if not key:
            return None

        exact = self._by_name.get(key)
        if exact is not None:
            return GameDetails.model_validate(exact)

        matches = get_close_matches(key, list(self._by_name.keys()), n=1, cutoff=0.82)
        if not matches:
            return None
        item = self._by_name.get(matches[0])
        if item is None:
            return None
        return GameDetails.model_validate(item)

    def suggest(self, name: str, limit: int = 5) -> list[str]:
        key = _norm(name)
        if not key:
            return []
        keys = list(self._by_name.keys())
        close = get_close_matches(key, keys, n=limit, cutoff=0.6)
        suggestions: list[str] = []
        for k in close:
            item = self._by_name.get(k)
            if item and "name" in item:
                suggestions.append(str(item["name"]))
        return suggestions
