from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from game_shelf.frontend import _game_payload, render_interactive_html
from game_shelf.models import CollectionGame, GameDetails
from game_shelf.services import (
    add_game as svc_add_game,
    apply_metadata_updates,
    list_games as svc_list_games,
    preview_metadata_updates,
    rate_game as svc_rate_game,
    remove_game as svc_remove_game,
    search_games as svc_search_games,
    update_game as svc_update_game,
)
from game_shelf.storage import CollectionStore


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GameResponse(BaseModel):
    """Shape returned to the frontend — matches the existing static export."""

    id: str
    name: str
    year: int | None = None
    source: str
    sourceId: str
    owned: bool
    wishlist: bool
    status: str
    personalRating: int | None = None
    bggRating: float | None = None
    minPlayers: int | None = None
    maxPlayers: int | None = None
    minPlaytime: int | None = None
    maxPlaytime: int | None = None
    weight: float | None = None
    mechanics: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    description: str | None = None
    palette: dict[str, str] = Field(default_factory=dict)


class AddGameRequest(BaseModel):
    source: str = "bgg_xml_api"
    source_id: str = ""
    name: str
    year: int | None = None
    min_players: int | None = None
    max_players: int | None = None
    min_playtime_minutes: int | None = None
    max_playtime_minutes: int | None = None
    description: str | None = None
    weight: float | None = None
    bgg_rating: float | None = None
    mechanics: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    owned: bool = True
    wishlist: bool = False
    rating: int | None = Field(default=None, ge=1, le=10)


class UpdateGameRequest(BaseModel):
    owned: bool | None = None
    wishlist: bool | None = None
    rating: int | None = Field(default=None, ge=1, le=10)


class BggSearchRequest(BaseModel):
    query: str
    limit: int = 5


class BggSearchResult(BaseModel):
    sourceId: str
    name: str
    year: int | None = None
    minPlayers: int | None = None
    maxPlayers: int | None = None
    minPlaytime: int | None = None
    maxPlaytime: int | None = None
    weight: float | None = None
    bggRating: float | None = None
    mechanics: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    description: str | None = None


class MetadataDiff(BaseModel):
    field: str
    old: object = None
    new: object = None


class MetadataPreviewResponse(BaseModel):
    game_id: str
    game_name: str
    diffs: list[MetadataDiff] = Field(default_factory=list)


class MetadataRefreshResponse(BaseModel):
    updated_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_game_response(game: CollectionGame) -> GameResponse:
    """Convert a CollectionGame to the frontend-friendly response shape."""
    payload = _game_payload(game)
    return GameResponse(**payload)  # type: ignore[arg-type]


def _to_bgg_search_result(details: GameDetails) -> BggSearchResult:
    return BggSearchResult(
        sourceId=details.source_id,
        name=details.name,
        year=details.year_published,
        minPlayers=details.min_players,
        maxPlayers=details.max_players,
        minPlaytime=details.min_playtime_minutes,
        maxPlaytime=details.max_playtime_minutes,
        weight=details.weight,
        bggRating=details.bgg_rating,
        mechanics=sorted({*(details.mechanics or []), *(details.mechanics_custom or [])}),
        categories=sorted({*(details.categories or []), *(details.categories_custom or [])}),
        description=details.description,
    )


def _load_collection_or_404(collection_path: Path) -> list[CollectionGame]:
    """Load collection; raises 404 if empty (for single-game lookups)."""
    store = CollectionStore(collection_path)
    collection = store.load()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return collection


def _find_game_or_404(collection: list[CollectionGame], game_id: str) -> CollectionGame:
    for g in collection:
        if g.id == game_id:
            return g
    raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(collection_path: Path) -> FastAPI:
    """Build the FastAPI application wired to the given collection file."""

    app = FastAPI(title="Game Shelf API", version="0.1.0")

    # ------------------------------------------------------------------
    # Interactive frontend
    # ------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def index():
        """Serve the interactive frontend."""
        return HTMLResponse(content=render_interactive_html())

    # ------------------------------------------------------------------
    # Collection CRUD
    # ------------------------------------------------------------------

    @app.get("/api/games", response_model=list[GameResponse])
    def list_games_endpoint(
        owned: bool | None = None,
        wishlist: bool | None = None,
        query: str | None = None,
    ):
        """List games in the collection, with optional filters."""
        items = svc_list_games(
            collection_path,
            owned=owned,
            wishlist=wishlist,
            query=query,
        )
        return [_to_game_response(g) for g in items]

    @app.get("/api/games/{game_id}", response_model=GameResponse)
    def get_game(game_id: str):
        """Get a single game by its local UUID."""
        collection = _load_collection_or_404(collection_path)
        game = _find_game_or_404(collection, game_id)
        return _to_game_response(game)

    @app.post("/api/games", response_model=GameResponse, status_code=201)
    def add_game_endpoint(body: AddGameRequest):
        """Add a game to the collection.

        If a game with the same source+source_id already exists,
        it will be merged (preserving existing rating, added_at, id).
        """
        if not body.name.strip():
            raise HTTPException(status_code=422, detail="name is required")

        details = GameDetails(
            source=body.source,
            source_id=body.source_id or body.name,
            name=body.name.strip(),
            year_published=body.year,
            min_players=body.min_players,
            max_players=body.max_players,
            min_playtime_minutes=body.min_playtime_minutes,
            max_playtime_minutes=body.max_playtime_minutes,
            description=body.description,
            weight=body.weight,
            bgg_rating=body.bgg_rating,
            mechanics=body.mechanics,
            categories=body.categories,
            themes=body.themes,
        )
        game = svc_add_game(
            collection_path,
            details,
            owned=body.owned,
            wishlist=body.wishlist,
            rating=body.rating,
        )
        return _to_game_response(game)

    @app.patch("/api/games/{game_id}", response_model=GameResponse)
    def update_game_endpoint(game_id: str, body: UpdateGameRequest):
        """Update owned/wishlist flags and rating for a game."""
        updated = svc_update_game(
            collection_path,
            game_id,
            owned=body.owned,
            wishlist=body.wishlist,
            rating=body.rating,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
        return _to_game_response(updated)

    @app.delete("/api/games/{game_id}", status_code=204)
    def delete_game_endpoint(game_id: str):
        """Remove a game from the collection by UUID."""
        removed = svc_remove_game(collection_path, game_id)
        if removed is None:
            raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
        return None

    # ------------------------------------------------------------------
    # BGG search
    # ------------------------------------------------------------------

    @app.post("/api/bgg/search", response_model=list[BggSearchResult])
    def bgg_search(body: BggSearchRequest):
        """Search BGG by game name."""
        results = svc_search_games(body.query, limit=body.limit)
        return [_to_bgg_search_result(r) for r in results]

    # ------------------------------------------------------------------
    # Metadata refresh
    # ------------------------------------------------------------------

    @app.post("/api/metadata/preview", response_model=list[MetadataPreviewResponse])
    def metadata_preview():
        """Preview BGG metadata changes without applying them."""
        preview = preview_metadata_updates(collection_path)
        result: list[MetadataPreviewResponse] = []
        for item, diffs in preview.changed_games:
            result.append(
                MetadataPreviewResponse(
                    game_id=item.id,
                    game_name=item.game.name,
                    diffs=[
                        MetadataDiff(field=d.field, old=d.old, new=d.new) for d in diffs
                    ],
                )
            )
        return result

    @app.post("/api/metadata/refresh", response_model=MetadataRefreshResponse)
    def metadata_refresh():
        """Fetch fresh BGG metadata for BGG-sourced games and apply changes."""
        result = apply_metadata_updates(collection_path)
        return MetadataRefreshResponse(updated_count=len(result.changed_games))

    # ------------------------------------------------------------------
    # Health / info
    # ------------------------------------------------------------------

    @app.get("/api/health")
    def health():
        """Basic health check."""
        return {"status": "ok"}

    return app
