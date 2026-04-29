from __future__ import annotations

import argparse
from pathlib import Path

from game_shelf.datasource import LocalSeedDataSource
from game_shelf.models import OwnedGame
from game_shelf.storage import CollectionStore


def _default_collection_path() -> Path:
    return Path("data") / "collection.json"


def cmd_add(args: argparse.Namespace) -> int:
    datasource = LocalSeedDataSource()
    store = CollectionStore(args.collection_path)

    details = datasource.lookup_by_name(args.name)
    if details is None:
        suggestions = datasource.suggest(args.name)
        print(f'No match for "{args.name}".')
        if suggestions:
            print("Did you mean:")
            for s in suggestions:
                print(f"  - {s}")
        return 2

    store.upsert(OwnedGame(game=details))
    print(f'Added: {details.name} ({details.min_players}-{details.max_players} players)')
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    store = CollectionStore(_.collection_path)
    collection = store.load()
    if not collection:
        print("Collection is empty.")
        return 0

    for item in sorted(collection, key=lambda x: x.game.name.lower()):
        g = item.game
        players = (
            f"{g.min_players}-{g.max_players}"
            if g.min_players is not None and g.max_players is not None
            else "?"
        )
        playtime = (
            f"{g.min_playtime_minutes}-{g.max_playtime_minutes}m"
            if g.min_playtime_minutes is not None and g.max_playtime_minutes is not None
            else "?"
        )
        print(f"- {g.name} | players: {players} | time: {playtime} | source_id: {g.source_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="game-shelf")
    parser.add_argument(
        "--collection-path",
        type=Path,
        default=_default_collection_path(),
        help="Path to the local collection JSON file (default: data/collection.json)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add a game to your local collection by name")
    p_add.add_argument("name", help='Game name, e.g. "Catan"')
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List your local collection")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
