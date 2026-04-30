## Local dev (stub data source)

This project currently uses a local seed data source (no BGG network calls yet).

- Install deps: `uv sync`
- Install the CLI (editable): `uv pip install -e .`
- Add a game: `game-shelf add "Catan" --rating 8`
- Add a wishlist game: `game-shelf add "Compile" --wishlist`
- List collection: `game-shelf list`
- Rate a game already in your collection: `game-shelf rate "Catan" 9`

Collection data is saved to an OS-specific app directory by default (override via `--collection-path`).
