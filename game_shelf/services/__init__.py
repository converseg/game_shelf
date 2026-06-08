from __future__ import annotations

from game_shelf.services.collection import list_games
from game_shelf.services.collection import add_game
from game_shelf.services.collection import remove_game
from game_shelf.services.collection import remove_by_source
from game_shelf.services.collection import rate_game
from game_shelf.services.collection import update_game

from game_shelf.services.bgg import search_games
from game_shelf.services.bgg import lookup_game
from game_shelf.services.bgg import preview_metadata_updates
from game_shelf.services.bgg import apply_metadata_updates

__all__ = [
    "list_games",
    "add_game",
    "remove_game",
    "remove_by_source",
    "rate_game",
    "update_game",
    "search_games",
    "lookup_game",
    "preview_metadata_updates",
    "apply_metadata_updates",
]
