from __future__ import annotations

from typing import Protocol

from game_shelf.models import GameDetails


class GameDataSource(Protocol):
    def lookup_by_name(self, name: str) -> GameDetails | None:
        """Return best-match details for a game name, or None if not found."""

    def suggest(self, name: str, limit: int = 5) -> list[str]:
        """Return near-match names to help the user correct typos."""

