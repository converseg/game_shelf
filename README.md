# Game Shelf

A small CLI for tracking a local board game collection/wishlist, with metadata lookup via BoardGameGeek (BGG) or an offline seed database.

## Features

- Add games to your collection and/or wishlist
- Store a personal rating (1–10)
- Suggest games to play (from your collection) or discover new games (via BGG)
- Saves to a local JSON file (defaults to an OS-specific app directory)

## Install

This repo uses `uv` for Python dependency management.

- Create venv + install deps: `uv sync`
- Install the CLI (editable): `uv pip install -e .`

## Usage

- Add a game (BGG lookup): `game-shelf add "Catan" --rating 8`
- Add a game in offline mode: `game-shelf add "Catan" --local-db`
- Add to wishlist: `game-shelf add "Compile" --wishlist`
- List collection: `game-shelf list`
- Rate a game already in your collection: `game-shelf rate "Catan" 9`
- Remove a game by id (UUID): `game-shelf remove <id>`
- Get suggestions: `game-shelf suggest`

## Data location

By default, your collection is stored at an OS-specific app directory (via Click), e.g. `collection.json` under the `game-shelf` app dir.

You can override this path for scripting/backups:

- `game-shelf --collection-path ./collection.json list`

## BGG configuration

If you see `401 Unauthorized`, set `BGG_API_KEY` (either in your shell environment or in a local `.env` file):

- Create `.env` with: `BGG_API_KEY=...`

If you don’t want any network calls, use `--local-db` (for `add`) or `--mode game-night` (for `suggest`).

## Development

- Run the CLI module: `uv run python -m game_shelf --help`
- Run the BGG smoke test script: `uv run python test_bgg.py`

## License

MIT (see `LICENSE`).

---

![Powered by BoardGameGeek](resources/powered_by_bgg.png)
