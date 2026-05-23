from __future__ import annotations

from difflib import get_close_matches
from pathlib import Path
import re
import textwrap

import click
import requests
from dotenv import load_dotenv

from game_shelf.datasource import BggXmlApi2DataSource
from game_shelf.datasource import LocalSeedDataSource
from game_shelf.models import CollectionGame
from game_shelf.models import GameDetails
from game_shelf.storage import CollectionStore
from game_shelf.suggest import run_suggest_agent
from game_shelf.suggest.models import SuggestConstraints
from game_shelf.suggest.models import SuggestInputs


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


def _to_kebab(value: str) -> str:
    return "-".join(value.strip().lower().replace("_", " ").split())


def _prompt_optional_int(label: str) -> int | None:
    raw = click.prompt(label, default="", show_default=False)
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as e:
        raise click.ClickException(f"{label}: expected an integer or blank.") from e


def _prompt_optional_float(label: str) -> float | None:
    raw = click.prompt(label, default="", show_default=False)
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as e:
        raise click.ClickException(f"{label}: expected a number or blank.") from e


def _prompt_csv_list(label: str) -> list[str]:
    raw = click.prompt(label, default="", show_default=False)
    parts = [p.strip() for p in str(raw).split(",")]
    return [_to_kebab(p) for p in parts if p.strip()]


def _parse_action(raw: str) -> tuple[str, str | None]:
    """
    Parses the user's action into (kind, value).
    - kind: "quit" | "refine" | "pick_index" | "pick_name" | "unknown"
    - value: index string or name string when applicable
    """

    s = str(raw or "").strip()
    if not s:
        return ("quit", None)

    low = s.lower().strip()
    if low in {"q", "quit", "exit"}:
        return ("quit", None)
    if low in {"r", "refine", "redo"}:
        return ("refine", None)

    m = re.match(r"^\s*(?:add|pick|choose)\s+(\d+)\s*$", low)
    if m:
        return ("pick_index", m.group(1))

    if re.match(r"^\d+\s*$", low):
        return ("pick_index", low)

    m = re.match(r"^\s*(?:add|pick|choose)\s+(.+?)\s*$", s, flags=re.IGNORECASE)
    if m:
        return ("pick_name", m.group(1).strip().strip('"'))

    # Treat any other non-empty input as a game-name attempt.
    return ("pick_name", s.strip().strip('"'))


def _find_recommendation_by_name(recs: list[dict], query: str) -> dict | None:
    q = _norm_name(query)
    if not q:
        return None

    # Exact normalized match
    for rec in recs:
        name = str(rec.get("name") or "").strip()
        if _norm_name(name) == q:
            return rec

    # Substring match
    for rec in recs:
        name = str(rec.get("name") or "").strip()
        if q in _norm_name(name):
            return rec

    # Fuzzy match
    names = [str(r.get("name") or "").strip() for r in recs if str(r.get("name") or "").strip()]
    if not names:
        return None
    best = get_close_matches(query, names, n=1, cutoff=0.75)
    if not best:
        return None
    for rec in recs:
        if str(rec.get("name") or "").strip() == best[0]:
            return rec
    return None


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
@click.option(
    "--local-db",
    is_flag=True,
    default=False,
    show_default=True,
    help="Use the built-in local seed database instead of BGG (offline mode).",
)
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
def add(
    obj: dict,
    name: str,
    local_db: bool,
    rating: int | None,
    owned: bool,
    wishlist: bool,
) -> None:
    load_dotenv()
    datasource = LocalSeedDataSource() if local_db else BggXmlApi2DataSource()
    store = CollectionStore(obj["collection_path"])

    try:
        candidates = datasource.lookup_by_name(name, limit=3)
    except requests.HTTPError as e:
        resp = getattr(e, "response", None)
        if resp is not None and resp.status_code == 401:
            raise click.ClickException(
                "BGG returned 401 Unauthorized. Set `BGG_API_KEY` in your environment/.env, or retry with "
                "`--local-db` for offline mode."
            ) from e
        raise
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


@cli.command()
@click.option(
    "--mode",
    type=click.Choice(["game-night", "buy"], case_sensitive=False),
    default=None,
    help="Suggestion mode (prompted if omitted).",
)
@click.option("--count", type=click.IntRange(1, 20), default=5, show_default=True)
@click.option("--model", type=str, default="claude-haiku-4-5", show_default=True)
@click.option("--dry-run", is_flag=True, default=False, show_default=True)
@click.option(
    "--debug-level",
    type=click.IntRange(0, 2),
    default=0,
    show_default=True,
    help="0=none, 1=BGG/tool logs, 2=also LangGraph debug stream.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    show_default=True,
    help="Alias for --debug-level 1.",
)
@click.option(
    "--max-agent-steps",
    type=click.IntRange(5, 200),
    default=35,
    show_default=True,
    help="Hard cap on LangGraph agent steps (limits tool/LLM cycles).",
)
@click.option(
    "--check-in-every-searches",
    type=click.IntRange(0, 50),
    default=0,
    show_default=True,
    help="If >0, pause every N BGG searches to confirm continuing.",
)
@click.option("--owned/--not-owned", "include_owned", default=True, show_default=True)
@click.option("--wishlist/--not-wishlist", "include_wishlist", default=False, show_default=True)
@click.option(
    "--max-bgg-candidates",
    type=click.IntRange(5, 200),
    default=30,
    show_default=True,
    help="(buy mode) Maximum BGG candidates to consider.",
)
@click.option(
    "--no-bgg",
    is_flag=True,
    default=False,
    show_default=True,
    help="Disallow BGG calls (buy mode will error).",
)
@click.pass_obj
def suggest(
    obj: dict,
    mode: str | None,
    count: int,
    model: str,
    dry_run: bool,
    debug_level: int,
    debug: bool,
    max_agent_steps: int,
    check_in_every_searches: int,
    include_owned: bool,
    include_wishlist: bool,
    max_bgg_candidates: int,
    no_bgg: bool,
) -> None:
    load_dotenv()
    store = CollectionStore(obj["collection_path"])

    chosen_mode = mode
    if chosen_mode is None:
        click.echo("What kind of suggestion do you want?")
        click.echo("  1) Game night tonight (from my collection)")
        click.echo("  2) Recommend a new game to buy")
        pick = click.prompt("Choose", type=click.IntRange(1, 2))
        chosen_mode = "game-night" if pick == 1 else "buy"

    constraints = SuggestConstraints()

    def collect_inputs() -> SuggestInputs:
        click.echo("")
        click.echo("Constraints (leave blank to skip):")
        constraints.players = _prompt_optional_int("Players (exact)")
        constraints.max_minutes = _prompt_optional_int("Max minutes")
        constraints.min_weight = _prompt_optional_float("Min weight (1.0-5.0)")
        constraints.max_weight = _prompt_optional_float("Max weight (1.0-5.0)")

        click.echo("")
        click.echo("Mechanics (comma-separated, kebab-case; blank to skip).")
        click.echo(f"Known mechanics: {', '.join(GameDetails.valid_mechanics)}")
        preferred_mechanics = _prompt_csv_list("Preferred mechanics")
        avoid_mechanics = _prompt_csv_list("Avoid mechanics")

        themes = _prompt_csv_list("Themes (comma-separated)")

        liked_games = click.prompt("Liked games (names; comma-separated)", default="", show_default=False)
        liked_games_list = [p.strip() for p in str(liked_games).split(",") if p.strip()]
        disliked_games = click.prompt(
            "Disliked games (names; comma-separated)", default="", show_default=False
        )
        disliked_games_list = [p.strip() for p in str(disliked_games).split(",") if p.strip()]

        return SuggestInputs(
            mode=chosen_mode,  # type: ignore[arg-type]
            count=count,
            include_owned=include_owned,
            include_wishlist=include_wishlist,
            constraints=constraints,
            preferred_mechanics=preferred_mechanics,
            avoid_mechanics=avoid_mechanics,
            themes=themes,
            liked_games=liked_games_list,
            disliked_games=disliked_games_list,
        )

    effective_debug_level = max(debug_level, 1 if debug else 0)

    inputs = collect_inputs()

    for iteration in range(3):
        try:
            result = run_suggest_agent(
                inputs=inputs,
                collection_path=str(obj["collection_path"]),
                model=model,
                max_bgg_candidates=max_bgg_candidates,
                no_bgg=no_bgg,
                debug_level=effective_debug_level,
                max_agent_steps=max_agent_steps,
                check_in_every_searches=check_in_every_searches,
            )
        except RuntimeError as e:
            raise click.ClickException(
                f"{e} If you're offline or missing credentials, try `--mode game-night`."
            ) from e
        except requests.HTTPError as e:
            resp = getattr(e, "response", None)
            if resp is not None and resp.status_code == 401:
                raise click.ClickException(
                    "BGG returned 401 Unauthorized. Set `BGG_API_KEY` in your environment/.env, or use "
                    "`--mode game-night` (collection-only)."
                ) from e
            raise

        click.echo("")
        recs = result.recommendations or []
        if not recs:
            click.echo(result.note or "No recommendations found (try loosening constraints).")
        else:
            click.echo("Recommendations:")
            for i, rec in enumerate(recs, start=1):
                name = str(rec.get("name") or "?")
                why = str(rec.get("why") or "").strip()
                source = str(rec.get("source") or "")
                source_id = str(rec.get("source_id") or "")
                click.echo(f"{i}) {name} | source: {source} | source_id: {source_id}")
                if why:
                    click.echo(f"   why: {why}")
            if result.note:
                click.echo("")
                click.echo(result.note)

        while True:
            click.echo("")
            click.echo(
                "Actions: enter a number, type a game name (or 'add <name>'), 'r' to refine, or 'q' to quit."
            )
            raw_action = click.prompt("Choose", default="q", show_default=True)
            kind, value = _parse_action(raw_action)

            if kind == "quit":
                return
            if kind == "refine":
                if iteration >= 2:
                    click.echo("Refine limit reached.")
                    return
                inputs = collect_inputs()
                break

            picked: dict | None = None
            if kind == "pick_index":
                if not recs:
                    click.echo(
                        "No recommendations to select by number. Type a game name, choose 'r' to refine, or 'q' to quit."
                    )
                    continue
                try:
                    idx = int(value or "")
                except ValueError:
                    click.echo("Invalid number.")
                    continue
                if not (1 <= idx <= len(recs)):
                    click.echo(f"Invalid recommendation number (choose 1-{len(recs)}).")
                    continue
                picked = recs[idx - 1]
            elif kind == "pick_name":
                assert value is not None
                if recs:
                    picked = _find_recommendation_by_name(recs, value)
                if picked is None:
                    # Allow adding by name even if the agent returned no recommendations.
                    picked = {"source": "bgg_xml_api", "source_id": "", "name": value}
            else:
                click.echo("Invalid choice.")
                continue

            source = str(picked.get("source") or "").strip()
            source_id = str(picked.get("source_id") or "").strip()
            name = str(picked.get("name") or "").strip()
            if not name:
                click.echo("Selected recommendation is missing required fields.")
                continue

            details: GameDetails | None = None
            if source == "bgg_xml_api":
                ds = BggXmlApi2DataSource()
                if source_id:
                    found = ds.lookup_by_ids([source_id])
                    details = found[0] if found else None
                if details is None:
                    details = ds.lookup_best(name)
            elif source == "local_seed":
                ds = LocalSeedDataSource()
                details = ds.lookup_best(name)

            if details is None:
                details = GameDetails(source=source or "bgg_xml_api", source_id=source_id or name, name=name)

            add_as = click.prompt(
                "Add as",
                type=click.Choice(["owned", "wishlist"], case_sensitive=False),
                default="owned",
                show_default=True,
            ).lower()
            rating = click.prompt(
                "Rating (1-10, blank to skip)",
                default="",
                show_default=False,
            ).strip()
            rating_value: int | None = None
            if rating:
                try:
                    rating_value = int(rating)
                except ValueError as e:
                    raise click.ClickException("Rating must be an integer 1-10 or blank.") from e
                if not (1 <= rating_value <= 10):
                    raise click.ClickException("Rating must be 1-10.")

            item = CollectionGame(
                game=details,
                personal_rating=rating_value,
                is_owned=(add_as == "owned"),
                is_wishlist=(add_as == "wishlist"),
            )
            if dry_run:
                click.echo(f"[dry-run] Would add: {details.name}")
                return
            store.upsert(item)
            click.echo(f"Added: {details.name}")
            return

        continue
