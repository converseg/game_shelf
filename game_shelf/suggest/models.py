from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from game_shelf.models import CollectionGame
from game_shelf.models import GameDetails


SuggestMode = Literal["game-night", "buy"]


class SuggestConstraints(BaseModel):
    players: int | None = None
    max_minutes: int | None = None
    min_weight: float | None = None
    max_weight: float | None = None


class SuggestInputs(BaseModel):
    mode: SuggestMode
    count: int = 5

    include_owned: bool = True
    include_wishlist: bool = False

    constraints: SuggestConstraints = Field(default_factory=SuggestConstraints)

    preferred_mechanics: list[str] = Field(default_factory=list)
    avoid_mechanics: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)

    liked_games: list[str] = Field(default_factory=list)
    disliked_games: list[str] = Field(default_factory=list)


class SuggestRecommendation(BaseModel):
    game: GameDetails
    score: float = 0.0
    why: str = ""


class SuggestContext(BaseModel):
    inputs: SuggestInputs
    collection: list[CollectionGame] = Field(default_factory=list)
    candidates: list[GameDetails] = Field(default_factory=list)
    recommendations: list[SuggestRecommendation] = Field(default_factory=list)

