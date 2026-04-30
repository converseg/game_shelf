from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar, Literal

import re

from pydantic import BaseModel, Field, field_validator, model_validator


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _to_kebab(value: str) -> str:
    s = value.strip().lower()
    s = s.replace("&", " and ")
    s = _NON_ALNUM_RE.sub("-", s)
    return s.strip("-")


# Canonical tag vocabularies.
# Start small; expand as you ingest more games.
VALID_CATEGORIES: tuple[str, ...] = (
    "animals",
    "card-game",
    "city-building",
    "civilization",
    "cooperative",
    "dice",
    "economic",
    "family",
    "medical",
    "negotiation",
    "science-fiction",
    "thematic",
    "trains",
    "zombies",
)

VALID_MECHANICS: tuple[str, ...] = (
    "card-drafting",
    "cooperative-game",
    "dice-rolling",
    "hand-management",
    "network-and-route-building",
    "point-to-point-movement",
    "push-your-luck",
    "resource-management",
    "route-building",
    "social-deduction",
    "solitaire",
    "set-collection",
    "simultaneous-action-selection",
    "tableau-building",
    "trick-taking",
    "trading",
    "traitor-game",
    "worker-placement",
)


_CATEGORY_ALIASES: dict[str, str] = {
    "co-op": "cooperative",
    "coop": "cooperative",
}

_MECHANIC_ALIASES: dict[str, str] = {
    "coop": "cooperative-game",
    "co-op": "cooperative-game",
}


def _canonicalize_tags(
    values: list[str],
    *,
    valid: tuple[str, ...],
    aliases: dict[str, str],
) -> tuple[list[str], list[str]]:
    valid_map = {_to_kebab(v): v for v in valid}
    canonical: list[str] = []
    custom: list[str] = []

    for raw in values:
        raw = str(raw).strip()
        if not raw:
            continue
        key = _to_kebab(raw)
        mapped = aliases.get(key) or valid_map.get(key)
        if mapped is not None:
            canonical.append(mapped)
        else:
            custom.append(key)

    canonical = sorted(set(canonical))
    custom = sorted(set(custom))
    return canonical, custom




class GameDetails(BaseModel):
    source: Literal["local_seed", "bgg_xml_api"] = "local_seed"
    source_id: str = Field(..., description="ID in the upstream data source (e.g., BGG thing id).")

    name: str
    year_published: int | None = None

    min_players: int | None = None
    max_players: int | None = None

    min_playtime_minutes: int | None = None
    max_playtime_minutes: int | None = None
    approx_playtime_minutes: int | None = Field(default=None, description="Approximate time it takes to play the game. If a range is given, this should be in the middle of the range; e.g. '40-60 min' should give approx_playtime_minutes=50.")

    description: str | None = None

    categories: list[str] = Field(default_factory=list)
    mechanics: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)

    categories_custom: list[str] = Field(
        default_factory=list,
        description="Non-canonical categories captured for later curation.",
    )
    mechanics_custom: list[str] = Field(
        default_factory=list,
        description="Non-canonical mechanics captured for later curation.",
    )

    weight: float | None = Field(default=None, description="BGG complexity weight (1.0-5.0).")

    valid_categories: ClassVar[tuple[str, ...]] = VALID_CATEGORIES
    valid_mechanics: ClassVar[tuple[str, ...]] = VALID_MECHANICS

    @field_validator("categories", "mechanics", "themes", mode="before")
    @classmethod
    def _ensure_list(cls, v):  # type: ignore[no-untyped-def]
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)

    @model_validator(mode="after")
    def _canonicalize_all_tags(self) -> "GameDetails":
        self.categories, self.categories_custom = _canonicalize_tags(
            self.categories, valid=VALID_CATEGORIES, aliases=_CATEGORY_ALIASES
        )
        self.mechanics, self.mechanics_custom = _canonicalize_tags(
            self.mechanics, valid=VALID_MECHANICS, aliases=_MECHANIC_ALIASES
        )
        self.themes = sorted({_to_kebab(t) for t in self.themes if str(t).strip()})
        return self


class CollectionGame(BaseModel):
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    game: GameDetails

    is_owned: bool = Field(default=True, description="Whether the user owns this game.")
    is_wishlist: bool = Field(default=False, description="Whether the user wants this game in the future.")

    personal_rating: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="The user's personal rating from 1-10 on this game.",
    )

    def give_rating(self, rating: int) -> None:
        self.personal_rating = rating


# Backwards-compat type alias (pre-refactor name).
OwnedGame = CollectionGame
