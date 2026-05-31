# Frontend Actions + Local API Plan

## Goal

Turn the current generated shelf UI into an interactive local UI that can use the same behaviors as the CLI:

- Add games
- Remove games
- Rate games
- Run suggest flows
- Eventually expose the same capabilities through MCP

The current `game-shelf ui` command is a useful first step because it proves the collection can render as a shelf. The next step is making actions write back to the collection without duplicating CLI logic in frontend code.

## Core Approach

Extract the command behavior into shared Python service functions, then make the CLI, HTTP API, and MCP server call those same functions.

```text
CLI commands
    |
    v
service layer  <---- HTTP API for frontend
    ^
    |
MCP tools
```

This keeps the CLI as a thin adapter and avoids having the frontend shell out to `game-shelf add`, `game-shelf remove`, etc.

## Service Layer

Create modules under something like `game_shelf/services/`.

Initial functions:

- `list_games(filters)`
- `add_game(query_or_source_id, owned, wishlist, rating, source_mode)`
- `remove_game(game_id)`
- `rate_game(game_id, rating)`
- `update_game(game_id, owned, wishlist, notes, tags, etc.)`
- `update_bgg_info(...)`

Suggest-specific functions:

- `create_suggest_session(mode, constraints)`
- `send_suggest_message(session_id, message)`
- `accept_suggestion(session_id, recommendation_id, destination)`

The CLI should keep prompts, formatting, and `click` concerns. The service layer should own validation, collection lookup, BGG lookup, and writes.

## Local HTTP API

Add a small local API server, likely FastAPI.

Proposed routes:

- `GET /api/games`
  - Filters: `owned`, `wishlist`, `query`, `players`, `max_playtime`, `min_weight`, `max_weight`
- `GET /api/games/{id}`
- `POST /api/games`
  - Add from BGG lookup, local seed, or manual/local entry
- `PATCH /api/games/{id}`
  - Update rating, owned/wishlist flags, notes, and eventually local metadata overrides
- `DELETE /api/games/{id}`
- `POST /api/bgg/search`
- `GET /api/bgg/things/{source_id}`
- `POST /api/games/update-bgg-info`
  - Preview changes first, then apply after confirmation

Suggest routes:

- `POST /api/suggest/sessions`
- `GET /api/suggest/sessions/{session_id}`
- `POST /api/suggest/sessions/{session_id}/messages`
- Later: `GET /api/suggest/sessions/{session_id}/stream` or websocket support

## CLI Shape

Keep the current static export:

- `game-shelf ui`
  - Generate read-only `shelf.html`

Add a served mode:

- `game-shelf ui --serve`
  - Starts the local API server and serves the frontend

Possible options:

- `--host 127.0.0.1`
- `--port 8765`
- `--open`
- `--reload` for development only

## Frontend Actions

### Add

Add flow should probably be a modal or drawer:

- Search by title
- Show BGG/local matches as cards
- Select one
- Choose owned/wishlist
- Optional initial rating
- Save

Later, add a manual/local game option for games not in BGG.

### Remove

From the right-side details panel:

- Remove button
- Confirmation step showing the game name and UUID
- Delete by local UUID only

### Rate

From the details panel:

- Rating control from 1-10
- Clear rating option
- Save immediately or with an explicit save button

### Suggest

Use a side chat panel:

- Mode selector: game night / buy
- Chat transcript
- Recommendation cards with metadata
- Buttons to add a recommendation to owned or wishlist

Streaming can wait. A normal request/response chat is enough for the first version.

## File Safety

The static UI only reads, but an interactive UI will write frequently.

Minimum changes:

- Atomic writes for `collection.json`
- File lock around writes
- Clear error if another process is writing

If this becomes clunky, move collection storage to SQLite. A local SQLite DB would make filtering, concurrent UI writes, and future MCP usage cleaner.

## MCP Alignment

MCP should use the same service layer as the API.

Likely MCP tools:

- `list_collection`
- `get_game`
- `add_game`
- `remove_game`
- `rate_game`
- `update_bgg_info`
- `suggest_game_night`
- `suggest_buy`

This makes the project usable from the CLI, browser UI, and external MCP clients without separate implementations.

## Milestones

1. Extract collection service functions from CLI.
2. Make CLI commands call the service layer.
3. Add local HTTP API for list/rate/remove.
4. Convert frontend from generated static data to API-backed data.
5. Add UI actions for rate/remove.
6. Add UI add flow with BGG/local search.
7. Add suggest chat panel.
8. Add MCP tools using the same service functions.
9. Revisit storage: add file locking or move to SQLite.

