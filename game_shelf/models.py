from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class GameDetails:
    source: Literal["local_seed", "bgg_xml_api"] = "local_seed"
    source_id: str = ""

    name: str = ""
    year_published: int | None = None

    min_players: int | None = None
    max_players: int | None = None

    min_playtime_minutes: int | None = None
    max_playtime_minutes: int | None = None

    description: str | None = None

    categories: list[str] = field(default_factory=list)
    mechanics: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)

    weight: float | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "GameDetails":
        return GameDetails(
            source=data.get("source", "local_seed"),
            source_id=str(data.get("source_id", "")),
            name=str(data.get("name", "")),
            year_published=data.get("year_published"),
            min_players=data.get("min_players"),
            max_players=data.get("max_players"),
            min_playtime_minutes=data.get("min_playtime_minutes"),
            max_playtime_minutes=data.get("max_playtime_minutes"),
            description=data.get("description"),
            categories=list(data.get("categories", []) or []),
            mechanics=list(data.get("mechanics", []) or []),
            themes=list(data.get("themes", []) or []),
            weight=data.get("weight"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "name": self.name,
            "year_published": self.year_published,
            "min_players": self.min_players,
            "max_players": self.max_players,
            "min_playtime_minutes": self.min_playtime_minutes,
            "max_playtime_minutes": self.max_playtime_minutes,
            "description": self.description,
            "categories": self.categories,
            "mechanics": self.mechanics,
            "themes": self.themes,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class OwnedGame:
    game: GameDetails
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OwnedGame":
        added_raw = data.get("added_at")
        added_at = (
            datetime.fromisoformat(added_raw.replace("Z", "+00:00"))
            if isinstance(added_raw, str) and added_raw
            else datetime.now(timezone.utc)
        )
        return OwnedGame(game=GameDetails.from_dict(dict(data.get("game") or {})), added_at=added_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_at": self.added_at.isoformat().replace("+00:00", "Z"),
            "game": self.game.to_dict(),
        }
