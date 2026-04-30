from __future__ import annotations

from difflib import get_close_matches
from pathlib import Path
import textwrap

import click

from game_shelf.datasource import LocalSeedDataSource
from game_shelf.models import GameDetails
from game_shelf.models import CollectionGame
from game_shelf.storage import CollectionStore


def _default_collection_path() -> Path:
    app_dir = Path(click.get_app_dir("game-shelf"))
    return app_dir / "collection.json"


def _norm_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _truncate(text: str | None, *, max_len: int) -> str:
    if not text:
        return "-"
    s = " ".join(str(text).split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _format_game_summary(details: GameDetails) -> str:
    players = (
        f"{details.min_players}-{details.max_players}"
        if details.min_players is not None and details.max_players is not None
        else "?"
    )
    playtime = (
        f"{details.min_playtime_minutes}-{details.max_playtime_minutes}m"
        if details.min_playtime_minutes is not None and details.max_playtime_minutes is not None
        else "?"
    )
    year = details.year_published if details.year_published is not None else "?"
    return f"{details.name} | players: {players} | time: {playtime} | year: {year} | source_id: {details.source_id}"


def _print_candidate(idx: int, details: GameDetails) -> None:
    click.echo(f"{idx}) {details.name} (source_id: {details.source_id})")

    players = (
        f"{details.min_players}-{details.max_players}"
        if details.min_players is not None and details.max_players is not None
        else "?"
    )
    playtime = (
        f"{details.min_playtime_minutes}-{details.max_playtime_minutes}m"
        if details.min_playtime_minutes is not None and details.max_playtime_minutes is not None
        else "?"
    )
    click.echo(f"   players: {players} | time: {playtime}")

    mechanics = sorted({*(details.mechanics or []), *(details.mechanics_custom or [])})
    themes = sorted(set(details.themes or []))

    click.echo(f"   mechanics: {', '.join(mechanics) if mechanics else '-'}")
    click.echo(f"   themes: {', '.join(themes) if themes else '-'}")

    desc = _truncate(details.description, max_len=360)
    wrapped = textwrap.fill(desc, width=92, initial_indent="   description: ", subsequent_indent="               ")
    click.echo(wrapped)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--collection-path",
    type=click.Path(path_type=Path),
    default=_default_collection_path(),
    show_default=True,
    help="Path to the local collection JSON file.",
)
@click.pass_context
def cli(ctx: click.Context, collection_path: Path) -> None:
    ctx.obj = {"collection_path": collection_path}


@cli.command()
@click.argument("name")
@click.option("--rating", type=click.IntRange(1, 10), default=None, help="Personal rating (1-10).")
@click.option(
    "--owned/--not-owned",
    default=True,
    show_default=True,
    help="Mark whether you own this game.",
)
@click.option(
    "--wishlist/--not-wishlist",
    default=False,
    show_default=True,
    help="Mark whether this game is on your wishlist.",
)
@click.pass_obj
def add(obj: dict, name: str, rating: int | None, owned: bool, wishlist: bool) -> None:
    datasource = LocalSeedDataSource()
    store = CollectionStore(obj["collection_path"])

    candidates = datasource.lookup_by_name(name, limit=3)
    if not candidates:
        suggestions = datasource.suggest(name)
        click.echo(f'No match for "{name}".')
        if suggestions:
            click.echo("Did you mean:")
            for s in suggestions:
                click.echo(f"  - {s}")
        raise SystemExit(2)

    click.echo("Matches:")
    for i, d in enumerate(candidates, start=1):
        _print_candidate(i, d)
    none_choice = len(candidates) + 1
    click.echo(f"{none_choice}) None of these")

    chosen: int | None = None
    while chosen is None:
        value = click.prompt("Choose", type=int)
        if value == none_choice:
            click.echo("Not added.")
            return
        if 1 <= value <= len(candidates):
            chosen = value
        else:
            click.echo(f"Please enter 1-{len(candidates)} or {none_choice}.")

    details = candidates[chosen - 1]

    store.upsert(
        CollectionGame(game=details, personal_rating=rating, is_owned=owned, is_wishlist=wishlist)
    )
    click.echo(f"Added: {details.name} ({details.min_players}-{details.max_players} players)")


@cli.command(name="list")
@click.pass_obj
def list_collection(obj: dict) -> None:
    store = CollectionStore(obj["collection_path"])
    collection = store.load()
    if not collection:
        click.echo("Collection is empty.")
        return

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
        rating = f"{item.personal_rating}/10" if item.personal_rating is not None else "-"
        owned = "yes" if item.is_owned else "no"
        wishlist = "yes" if item.is_wishlist else "no"
        click.echo(
            f"- {g.name} | owned: {owned} | wishlist: {wishlist} | rating: {rating} | players: {players} | time: {playtime} | source_id: {g.source_id}"
        )


@cli.command()
@click.argument("name")
@click.argument("rating", type=click.IntRange(1, 10))
@click.pass_obj
def rate(obj: dict, name: str, rating: int) -> None:
    store = CollectionStore(obj["collection_path"])

    datasource = LocalSeedDataSource()
    details = datasource.lookup_best(name)
    if details is not None:
        if store.set_rating(source=details.source, source_id=details.source_id, rating=rating):
            click.echo(f"Rated: {details.name} = {rating}/10")
            return
        click.echo(f'"{details.name}" is not in your collection yet. Add it first.')
        raise SystemExit(2)

    collection = store.load()
    target = _norm_name(name)
    matches = [item for item in collection if _norm_name(item.game.name) == target]
    if len(matches) == 1:
        g = matches[0].game
        if store.set_rating(source=g.source, source_id=g.source_id, rating=rating):
            click.echo(f"Rated: {g.name} = {rating}/10")
            return

    if not collection:
        click.echo("Collection is empty.")
        raise SystemExit(2)

    names = [item.game.name for item in collection]
    suggestions = get_close_matches(name, names, n=5, cutoff=0.6)
    click.echo(f'No match for "{name}" in your collection.')
    if suggestions:
        click.echo("Closest matches:")
        for s in suggestions:
            click.echo(f"  - {s}")
    raise SystemExit(2)
