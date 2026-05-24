# Frontend / UI (Future) — Planning Notes

## Goal

Add an optional local web UI for Game Shelf so users can:

- Visually browse their shelf (owned + wishlist) in a fun, friendly way
- Add / remove / update games and metadata
- Use the existing “suggest” capabilities via an embedded chat panel

An aspirational UI idea is an **8-bit style “shelf” graphic** with **AI-generated game boxes** for each title.

This doc is intentionally forward-looking; it outlines options and questions so we can evolve the backend cleanly.

---

## UX concept

### Primary views

- **Shelf view**
  - Toggle: `Owned` / `Wishlist` / `All`
  - Search + filters (players, playtime, weight, tags)
  - Each game renders as a small “box” tile
  - Click a game to open a right-side details drawer (metadata + notes + actions)

- **Suggest view (chat)**
  - Split layout: shelf list on left, chat on right
  - “Game night” and “Buy” modes
  - Recommendations appear as clickable cards; one click can add to owned/wishlist

### 8-bit shelf art

Two reasonable approaches:

1) **Deterministic pixel-art generation (no LLM required)**
   - Always works offline
   - Generate a simple pixel-art “box” per game from:
     - title text (monospace pixel font)
     - palette chosen from a hash of game UUID
     - optional small iconography (meeple, dice, cards, etc.)
   - Great default baseline

2) **AI-generated boxes (optional)**
   - Better “wow factor”
   - Not generated live in the frontend
   - Generated at **add-time** (CLI or service/API), then stored locally alongside the collection data
   - Still keep deterministic boxes as fallback

If we do AI boxes: generate once per game (per style preset), store the asset path + prompt metadata, and reuse (no UI-time generation).

---

## Backend changes to support a frontend (beyond the CLI)

Right now the CLI is the primary entrypoint. A UI will be much easier if we introduce a stable programmatic API.

### Recommended: add an HTTP API layer

Add a small **FastAPI** server (local-only by default) that wraps existing core logic:

- Collection CRUD (owned/wishlist/status/rating/notes)
- BGG search + lookup
- Metadata refresh (“update-bgg-info”)
- Suggest session orchestration

Key benefits:

- Frontend talks to HTTP, not a subprocess CLI
- Clear request/response models
- Easy to add websocket/SSE streaming for chat
- Reusable for other clients (mobile, scripts, etc.)

### What should move out of the CLI

To avoid duplicating behavior between CLI and UI:

- Create a “service layer” module (e.g. `game_shelf/services/...`) with functions like:
  - `add_game(...)`, `remove_game(...)`, `list_games(...)`, `rate_game(...)`
  - `search_bgg(...)`, `get_bgg_details(...)`, `update_bgg_info(...)`
- CLI becomes mostly argument parsing + rendering.
- HTTP API calls the same service functions.

### API shape (sketch)

- `GET /api/games?owned=true&wishlist=false&query=...`
- `POST /api/games` (add from BGG id or local entry)
- `PATCH /api/games/{id}` (rating, notes, owned/wishlist flags)
- `DELETE /api/games/{id}`
- `POST /api/bgg/search`
- `GET /api/bgg/things/{source_id}` (or `POST` to batch)
- `POST /api/games/update-bgg-info` (preview + apply)

For chat:

- `POST /api/suggest/sessions` (create session; returns `session_id`)
- `POST /api/suggest/sessions/{session_id}/messages`
- `GET /api/suggest/sessions/{session_id}` (history)
- Optional streaming: websocket `/ws/suggest/{session_id}`

### Concurrency + file safety

The collection is a JSON file today. A UI means:

- Multiple writes close together (rapid clicks)
- Possible concurrent access (UI + CLI)

Minimum changes:

- Add a file lock around writes (platform-specific; can be a best-effort lock)
- Atomic writes (write temp file then replace)

If that gets annoying, this is the moment to consider a **SQLite** backend (still local, still simple, safer concurrency).

---

## MCP: how it fits with a UI

We likely want *both*:

1) **MCP server**
   - Lets external assistants/clients call tools like `list_collection`, `add_game`, `remove_game`, `suggest`
   - Useful for Claude Desktop, other agent shells, and “automation” use cases

2) **HTTP API**
   - Purpose-built for a web UI (fast, predictable, streaming)

Design recommendation:

- Make the **service layer** the source of truth.
- Implement both HTTP routes and MCP tools as thin adapters over that service layer.

For the UI, MCP can still be useful:

- “Bring your own agent” workflows (UI can point at a running MCP server)
- Debug / inspect tools from MCP clients while the UI is running

---

## Frontend questions / suggestions

### Stack

- **Vite + React** (or SvelteKit) for a fast local UI
- Tailwind or a small design system for consistent layout
- For “8-bit” feel: pixel font + crisp scaling (avoid blur), limited palette, subtle dithering

### Offline-first defaults

Even if we add AI features, try to keep a good offline experience:

- Deterministic pixel-art boxes always available
- Cached BGG metadata; UI shows last-updated time
- Suggest “game-night” mode can work without network if it uses only local data

### Search + filtering

Worth planning early because it shapes the API:

- full-text query (by name)
- owned / wishlist toggles
- player count and playtime filters
- weight range
- tags (mechanics/categories/themes)

### Suggest + chat UX

- Let the user “pin” a few games as examples
- Display recommendation cards with:
  - BGG rating, weight, players, time
  - “Add to owned” / “Add to wishlist” buttons
- Keep a transcript that can be exported (nice for debugging and sharing)

### Asset caching for box art

If AI-generated (at add-time, not live):

- Store artifacts under a local `assets/` directory keyed by game UUID + style preset
- Provide a “regenerate art” button per game
- Never regenerate automatically without explicit user action (prevents surprise costs)

---

## Milestones (proposed)

1) Service layer extraction (CLI uses it)
2) FastAPI server with basic CRUD + list
3) Frontend shelf view (owned/wishlist/all) + details drawer
4) Frontend add/remove/rate/edit metadata flows
5) Chat panel wired to suggest sessions (non-streaming first)
6) Pixel-art box generation baseline
7) Optional AI box generation + caching + settings panel
