# BGG XML API2 quick notes

All endpoints are `GET` under the base URL:

- `https://boardgamegeek.com/xmlapi2/`

Responses are XML.

## Auth (Bearer token)

BGG may require an authorized token for XML API2 requests.

Send a Bearer token header:

```
Authorization: Bearer <token>
```

In this repo, we store the token in `.env` as `BGG_API_KEY`.

## Core endpoints (useful for `game-shelf`)

### `search`

Find candidate items by name (good for our interactive “pick 1/2/3” flow).

- Example: `/search?query=catan&type=boardgame`
- Useful params:
  - `query`: search string
  - `type`: `boardgame`, `boardgameexpansion`, etc.
  - `exact=1`: restrict to exact matches

### `thing`

Fetch full details for an item id (this is the main “hydrate details” call).

- Example: `/thing?id=13&stats=1`
- Useful params:
  - `id`: one id or a comma-delimited list (BGG limits apply)
  - `stats=1`: include rating/rank stats
  - `videos=1`: include videos
  - `versions=1`: include version info

Recommended mapping for `game-shelf`:
- name, year
- min/max players
- playing time
- description
- links for categories/mechanics (and other tags)

## Nice-to-have endpoints (future features)

### `collection`

Fetch a BGG user’s collection.

Potential use in `game-shelf`:
- “import from BGG username”
- optional periodic sync (probably manual opt-in)

### `plays`

Fetch logged plays for a user or item.

Potential use:
- play history / “most played”
- stats dashboards

### `user`

Fetch public profile information for a user (and optional buddies/guilds/top/hot lists).

Potential use:
- support collection/plays import workflows

### `hot`

Fetch BGG “hotness” lists.

Potential use:
- discovery / trending recommendations (not required for collection tracking)

### `family`

Fetch “family” records (higher-level groupings like boardgame families).

Potential use:
- series/editions/collections metadata

## Community endpoints (likely out-of-scope)

These are more about forums/community than collection management, but could be added later:

- `forumlist`: list forums for a `thing` or `family`
- `forum`: list threads in a forum
- `thread`: read a forum thread
- `guild`: guild info + member roster

## What we should support first

1. `search` + `thing` (required for add-by-name + metadata hydration)
2. Optionally `collection` import
3. Optionally `plays` for play history
