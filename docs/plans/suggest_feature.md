# `game-shelf suggest` — Feature Plan

## Summary

Add a new interactive CLI command: `game-shelf suggest`.

The session starts by asking the user which mode they want:
- **Game night tonight**: recommend games to play from the user’s collection.
- **Buy a new game**: recommend new games to purchase using BGG discovery (collection used as taste signal, not as the candidate pool).

The session uses:
- **Click** for prompts / interactive flow
- **Anthropic Claude** (`claude-haiku-4-5`) for ranking + explanations
- **LangGraph** for orchestration
- **BGG XML API2** (`search`, `thing`) for discovery + metadata in Buy mode

Users can pick a recommendation to add to owned/wishlist, optionally rate it, or give feedback to refine results.

## CLI / UX

### Command shape

`game-shelf suggest [OPTIONS]`

### Options (v1)

General:
- `--mode [game-night|buy]` (default: prompt interactively if omitted)
- `--count INTEGER` (default `5`) number of final recs
- `--model TEXT` (default `claude-haiku-4-5`)
- `--dry-run` (flag) don’t write any collection changes

Game-night mode:
- `--owned/--not-owned` (default `True`)
- `--wishlist/--not-wishlist` (default `False`)
  - Rationale: “tonight” usually means owned-only; wishlist inclusion is opt-in.

Buy mode:
- `--max-bgg-candidates INTEGER` (default `30`) cap the BGG candidate pool
- `--no-bgg` (flag) disallow BGG calls
  - If used in Buy mode, error with guidance (token missing/offline).

### First prompt (required if `--mode` not provided)

Ask:
> “What kind of suggestion do you want?”
- “Game night tonight (from my collection)”
- “Recommend a new game to buy”

### Shared Q&A prompts (v1)

All prompts should allow “skip/unknown” where reasonable.

1) Players
- Either a single `players` value or min/max.

2) Length
- Max minutes (or a range if we want).

3) Weight (optional)
- BGG complexity weight range (`min_weight`–`max_weight`) or skip.

4) Mechanics
- Multi-select from `GameDetails.valid_mechanics`
- Optional additional freeform mechanics (kebab-case normalized)

5) Themes (free-form)
- Comma-separated (kebab-case normalized)

6) Examples
- `liked_games`: 1–5 names (preferably from their collection, but allow anything)
- `disliked_games`: 0–3 names (optional)

### Output + actions (v1)

For each recommendation show:
- Name
- player range, playtime range
- weight (if available)
- key mechanics
- short “why this matches” explanation

Then prompt:
- Choose a recommendation number to **Add**
- Choose “refine” to answer targeted follow-ups and re-run
- Choose “q” to quit

If user chooses **Add**:
- Prompt: add as `owned` vs `wishlist`
- Prompt: optional rating (1–10)
- Persist via `CollectionStore.upsert(CollectionGame(...))` unless `--dry-run`

## Agent architecture (LangGraph)

### State (Pydantic model recommended)

`SuggestState` fields:
- `mode`: `"game-night"` | `"buy"`
- `constraints`: players, playtime, weight range
- `preferred_mechanics`, `avoid_mechanics`
- `themes`
- `liked_games`, `disliked_games`
- `collection_snapshot`: list of `CollectionGame` loaded once
- `candidates`: candidate list (collection-derived or BGG-derived)
- `ranked_recommendations`: final ranked list with explanation
- `iteration`: refine loop counter (cap at 2)

### Mode-specific flows

#### Game-night flow (collection candidate pool)

Nodes:
1. `collect_inputs` (interactive Q&A)
2. `load_collection`
3. `candidate_from_collection` (filter by constraints + owned/wishlist toggles)
4. `rank_and_explain` (Claude ranks filtered collection games)
5. `present_and_act`
6. `refine` loop (optional, max 2)

Key constraint: **No BGG calls** in this mode.

#### Buy flow (BGG candidate pool, collection as taste signal)

Nodes:
1. `collect_inputs`
2. `load_collection` (recommended: used to infer taste and to avoid recommending already-owned games)
3. `bgg_expand`
4. `rank_and_explain` (Claude ranks BGG candidates)
5. `present_and_act`
6. `refine` loop (optional, max 2)

## BGG integration (Buy mode)

Use existing `BggXmlApi2Client`:
- `search(query=..., type="boardgame", exact=...)`
- `thing(id=[...], stats=True)` in batches of <= 20 ids

Parsing into `GameDetails`:
- primary name, year
- min/max players
- min/max playtime + playingtime -> compute approx time
- description
- categories: `link[@type='boardgamecategory']`
- mechanics: `link[@type='boardgamemechanic']`
- weight: `statistics/ratings/averageweight` when `stats=True`
- `source="bgg_xml_api"`, `source_id=<thing id>`

Auth:
- `.env` `BGG_API_KEY` sent as `Authorization: Bearer <token>`

Error handling (v1):
- 401 -> ClickException: explain token + suggest Game-night or `--no-bgg`
- “queued” behavior (if encountered) -> retry with backoff for `thing`

Optional caching (v1):
- In-memory cache per run for `search` and `thing` results (useful across refine loop)

## LLM integration (Anthropic)

Model: `claude-haiku-4-5` default.

Prompting approach:
- Provide constraints + examples + compact candidate summaries
- Require strict JSON output following a schema (to avoid brittle parsing)
- Keep temperature moderate-low for stability

Auth:
- `.env` `ANTHROPIC_API_KEY`

## Test plan (v1)

Unit tests (no network):
- Collection filtering logic for Game-night
- Claude JSON parsing/validation (mock Anthropic output)

Fixture-based parsing tests (no network):
- Parse BGG `thing` XML fixtures into `GameDetails`

Manual acceptance:
- `game-shelf suggest` prompts for mode up front
- Game-night returns only collection games
- Buy returns BGG-based games and avoids recommending already-owned when possible
- Add-to-owned/wishlist + optional rating works and shows up in `game-shelf list`

## Assumptions / defaults

- `--mode` omitted => interactive mode prompt.
- Game-night defaults to owned-only unless wishlist is explicitly enabled.
- Buy mode uses BGG; collection is used for taste signals and to avoid duplicates.
- Refinement loop capped at 2 iterations to keep sessions short.
