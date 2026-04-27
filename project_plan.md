# 🎲 Game Shelf — Project Spec
 
A locally-running, conversational AI agent for board game discovery and game night recommendations. Powered by LangGraph, backed by BGG's public API, containerized with Docker, managed with uv, and exposing tools via MCP.
 
---
 
## Goals
 
1. **Learn the target stack** — Docker, uv, LangGraph, MCP — in a motivated, end-to-end project
2. **Build something genuinely useful** — a personal board game assistant you'll actually use
3. **Create a strong portfolio artifact** — multimodal input, stateful agent, MCP server, containerized deployment
---
 
## Two Core Modes
 
### 🔍 Discovery Mode
> "I love Wingspan because of the engine-building and the solo mode. What else might I like?"
 
The agent reasons about your taste, queries BGG, fetches game details, ranks results, and explains *why* each recommendation fits. If results are weak, it iterates with a refined query before responding.
 
### 🌙 Game Night Mode
> "Four players tonight, two are new to the hobby, we have about 90 minutes."
 
The agent works from your **owned collection first**, filters by player count, time, and complexity, and surfaces the best options. If there's a meaningful gap (e.g., nothing good at low complexity for 4 players), it may suggest one purchase.
 
---
 
## LangGraph — Agent Graph
 
```
                        ┌─────────────────┐
                        │   Entry Router   │
                        │  (classify query)│
                        └────────┬────────┘
                                 │
               ┌─────────────────┴──────────────────┐
               │                                    │
               ▼                                    ▼
   ┌───────────────────────┐           ┌───────────────────────┐
   │   DISCOVERY PATH      │           │   GAME NIGHT PATH     │
   │                       │           │                       │
   │  understand_taste     │           │  parse_constraints    │
   │  (extract mechanics,  │           │  (players, time,      │
   │   themes, complexity  │           │   experience level)   │
   │   from user input)    │           │                       │
   └──────────┬────────────┘           └──────────┬────────────┘
              │                                   │
              ▼                                   ▼
   ┌───────────────────────┐           ┌───────────────────────┐
   │   search_bgg          │           │   query_collection    │
   │  (BGG search + ranked │           │  (filter owned games  │
   │   candidate list)     │           │   by constraints)     │
   └──────────┬────────────┘           └──────────┬────────────┘
              │                                   │
              ▼                                   ▼
   ┌───────────────────────┐           ┌───────────────────────┐
   │  fetch_game_details   │           │  rank_and_explain     │◄──┐
   │  (BGG XML API:        │           │  (score each game,    │   │
   │   mechanics, weight,  │           │   generate reasoning) │   │
   │   ratings, category)  │           │                       │   │
   └──────────┬────────────┘           └──────────┬────────────┘   │
              │                                   │                │
              ▼                                   │    ┌───────────┴──────────┐
   ┌───────────────────────┐                      │    │  gap_check (optional)│
   │  rank_and_explain     │                      │    │  (if collection thin,│
   │  (score by taste fit, │                      │    │   suggest a purchase)│
   │   generate reasoning) │                      │    └──────────────────────┘
   └──────────┬────────────┘                      │
              │                                   │
              ▼                                   ▼
   ┌──────────────────────────────────────────────────┐
   │                 respond_to_user                  │
   │         (formatted, cited, conversational)       │
   └──────────────────────────────────────────────────┘
              │
              │  (if results unsatisfying)
              └──────────────────► refine_and_retry (back to search_bgg)
                                   max 2 iterations
```
 
### Conditional Edges
- **Entry Router → Discovery or Game Night** based on query classification
- **rank_and_explain → refine_and_retry** if confidence score is below threshold (Discovery path only)
- **query_collection → gap_check** if filtered results fall below a minimum count (Game Night path)
---
 
## MCP Server — Tool Definitions
 
The agent's capabilities are exposed as MCP tools, making the server usable from Claude Desktop or any MCP-compatible client.
 
| Tool | Description | Inputs |
|---|---|---|
| `search_bgg` | Search BGG for games by name or keyword | `query: str` |
| `get_game_details` | Fetch full metadata for a game by BGG ID | `game_id: int` |
| `list_collection` | Return all owned games, optionally filtered | `filters: dict (optional)` |
| `add_game` | Add a game to local collection | `bgg_id: int` |
| `remove_game` | Remove a game from local collection | `bgg_id: int` |
| `add_from_image` | Populate collection from a shelf photo | `image_path: str` |
| `get_taste_profile` | Return the stored user taste profile | — |
| `update_taste_profile` | Update taste preferences | `profile: dict` |
 
---
 
## Vision Pipeline — `add_from_image`
 
Bootstraps your collection from a photo of your game shelf. Removes the need to manually enter every game.
 
```
User provides shelf photo
        │
        ▼
GPT-4o vision call
→ extract list of visible game titles (with confidence scores)
        │
        ▼
BGG search for each title
→ resolve to canonical BGG game ID + metadata
        │
        ▼
Human-in-the-loop confirmation node
→ "I found these 14 games — does this look right?"
→ user can accept, remove false positives, or add missed titles
        │
        ▼
Write confirmed games to collection store
```
 
**Notes:**
- Flag low-confidence detections (stylized fonts, partial occlusion) for manual review
- Run BGG lookup in parallel (asyncio) for speed
- Confirmation step is not optional — shelf OCR is ~80-90% accurate at best
---
 
## Persistence Layer
 
Start simple, grow as needed.
 
### Phase 1 — JSON files (start here)
```
data/
  collection.json       # owned games + BGG metadata
  taste_profile.json    # preferred mechanics, themes, complexity range
  session_history.json  # past queries + recommendations
```
 
### Phase 2 — SQLite (optional upgrade)
Swap JSON files for a local SQLite DB once the schema stabilizes. Good practice for the portfolio and makes filtering/querying much cleaner.
 
### Schema sketch — `collection.json`
```json
{
  "games": [
    {
      "bgg_id": 266192,
      "title": "Wingspan",
      "year": 2019,
      "min_players": 1,
      "max_players": 5,
      "min_playtime": 40,
      "max_playtime": 70,
      "weight": 2.45,
      "mechanics": ["Hand Management", "Engine Building", "Set Collection"],
      "categories": ["Animals", "Nature"],
      "bgg_rating": 8.1,
      "owned_since": "2024-01-15",
      "notes": "Group favorite"
    }
  ]
}
```
 
---
 
## Project File Structure
 
```
game_shelf/
│
├── pyproject.toml              # uv-managed project config
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
│
├── src/
│   └── game_shelf/
│       ├── __init__.py
│       │
│       ├── agent/
│       │   ├── graph.py        # LangGraph graph definition (nodes + edges)
│       │   ├── nodes.py        # Individual node functions
│       │   ├── router.py       # Entry classifier, conditional edge logic
│       │   └── state.py        # AgentState TypedDict
│       │
│       ├── bgg/
│       │   ├── client.py       # BGG XML API wrapper (async)
│       │   └── models.py       # Pydantic models for BGG responses
│       │
│       ├── collection/
│       │   ├── store.py        # Read/write collection + taste profile
│       │   └── vision.py       # add_from_image pipeline
│       │
│       ├── mcp/
│       │   └── server.py       # MCP server exposing tools
│       │
│       └── main.py             # CLI entrypoint
│
├── data/                       # gitignored — local persistent state
│   ├── collection.json
│   ├── taste_profile.json
│   └── session_history.json
│
└── tests/
    ├── test_bgg_client.py
    ├── test_collection.py
    └── test_graph.py
```
 
---
 
## Key Dependencies
 
```toml
[project]
name = "game_shelf"
version = "0.1.0"
requires-python = ">=3.11"
 
dependencies = [
    "langgraph>=0.2",
    "langchain-openai>=0.2",
    "mcp>=1.0",           # MCP Python SDK
    "pydantic>=2.0",
    "httpx>=0.27",        # async HTTP for BGG API
    "xmltodict>=0.13",    # BGG returns XML
    "typer>=0.12",        # CLI interface
    "rich>=13.0",         # pretty terminal output
    "pillow>=10.0",       # image handling for shelf photo
    "python-dotenv>=1.0",
]
 
[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]
```
 
---
 
## Docker Setup
 
### `Dockerfile`
```dockerfile
FROM python:3.12-slim
 
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
 
WORKDIR /app
 
# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./
 
# Install dependencies (no project yet, just deps)
RUN uv sync --frozen --no-install-project
 
# Copy source
COPY src/ ./src/
 
# Install project
RUN uv sync --frozen
 
# Persist data directory as volume
VOLUME ["/app/data"]
 
CMD ["uv", "run", "python", "-m", "game_shelf.main"]
```
 
### `docker-compose.yml`
```yaml
services:
  game_shelf:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data    # persists collection across container restarts
    stdin_open: true
    tty: true
```
 
---
 
## Build Phases
 
Build this incrementally. Each phase produces something runnable.
 
### Phase 1 — Foundation (uv + BGG client)
- [ ] Init project with `uv init`, configure `pyproject.toml`
- [ ] Write async BGG XML API client with Pydantic response models
- [ ] Write collection store (read/write JSON)
- [ ] Simple CLI: `add-game`, `list-collection`
- **Milestone:** `uv run python -m game_shelf.main list-collection` works
### Phase 2 — Core Agent (LangGraph)
- [ ] Define `AgentState` TypedDict
- [ ] Implement Discovery path nodes: `understand_taste`, `search_bgg`, `fetch_game_details`, `rank_and_explain`
- [ ] Implement Game Night path nodes: `parse_constraints`, `query_collection`, `rank_and_explain`
- [ ] Wire up Entry Router and conditional edges
- [ ] Add `refine_and_retry` loop with iteration cap
- **Milestone:** Both conversation modes work end-to-end in the terminal
### Phase 3 — Docker
- [ ] Write `Dockerfile` with uv layer-caching pattern
- [ ] Write `docker-compose.yml` with data volume mount
- [ ] Verify collection persists across `docker compose down / up`
- [ ] Add `.env.example`, document setup in README
- **Milestone:** `docker compose up` → working agent, data survives restarts
### Phase 4 — MCP Server
- [ ] Implement MCP server in `mcp/server.py` exposing all 8 tools
- [ ] Test locally with Claude Desktop as MCP client
- [ ] Add MCP server as second service in `docker-compose.yml`
- **Milestone:** Ask Claude Desktop "what's in my collection?" and get a real answer
### Phase 5 — Vision Pipeline
- [ ] Implement `add_from_image` node: GPT-4o vision → BGG resolution → confirmation loop
- [ ] Wire as `add_from_image` MCP tool
- [ ] Test on an actual photo of your shelf
- **Milestone:** Shelf photo → populated collection with one command
### Phase 6 — Polish (optional)
- [ ] Upgrade collection store from JSON to SQLite
- [ ] Add taste profile memory that updates from conversation
- [ ] Push Docker image to Docker Hub or ECR
- [ ] Write architecture diagram for README
---
 
## What This Demonstrates (for job applications)
 
| Skill | Where it shows up |
|---|---|
| **LangGraph / agentic systems** | Multi-path graph, conditional edges, retry loop, human-in-the-loop |
| **Docker** | Multi-stage build, volume persistence, compose orchestration |
| **uv** | Dependency management, layer-cached Docker builds, script runner |
| **MCP** | Custom MCP server with real tool surface area |
| **Pydantic** | BGG response models, AgentState, collection schema |
| **Async Python** | BGG API client, parallel image resolution |
| **Multimodal AI** | Vision pipeline for shelf photo ingestion |
| **System design** | Clean separation of agent / API / storage / interface layers |
