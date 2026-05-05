import textwrap
import xml.etree.ElementTree as ET

import click
import requests
from dotenv import load_dotenv
import os

from game_shelf.bgg import BggXmlApi2Client


def _attr(elem: ET.Element | None, attr: str) -> str | None:
    if elem is None:
        return None
    return elem.get(attr)


def _text(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    text = elem.text.strip()
    return text or None


def search(query: str, *, limit: int, api_key: str | None) -> list[dict]:
    client = BggXmlApi2Client(api_key=api_key, user_agent="game-shelf-test/0.1")
    root = client.search(query=query, type="boardgame")
    results: list[dict] = []
    for item in root.findall("./item")[:limit]:
        results.append(
            {
                "id": item.get("id"),
                "name": _attr(item.find("./name"), "value"),
                "year": _attr(item.find("./yearpublished"), "value"),
            }
        )
    return results


def thing(game_id: str, *, api_key: str | None) -> dict:
    client = BggXmlApi2Client(api_key=api_key, user_agent="game-shelf-test/0.1")
    root = client.thing(id=game_id, stats=True)
    item = root.find("./item")
    if item is None:
        raise RuntimeError(f"No item returned for id={game_id}")

    primary_name = None
    for name in item.findall("./name"):
        if name.get("type") == "primary":
            primary_name = name.get("value")
            break

    description = _text(item.find("./description"))
    if description:
        description = " ".join(description.split())

    return {
        "id": game_id,
        "name": primary_name,
        "year": _attr(item.find("./yearpublished"), "value"),
        "minplayers": _attr(item.find("./minplayers"), "value"),
        "maxplayers": _attr(item.find("./maxplayers"), "value"),
        "playingtime": _attr(item.find("./playingtime"), "value"),
        "description": description,
    }


@click.command()
@click.argument("query", required=False, default="catan")
@click.option("--limit", type=int, default=5, show_default=True)
@click.option("--details/--no-details", default=True, show_default=True)
def main(query: str, limit: int, details: bool) -> None:
    load_dotenv()
    api_key = os.environ.get("BGG_API_KEY")
    print("Powered by BGG")

    if not api_key:
        click.echo("BGG_API_KEY is not set (continuing anyway).")

    try:
        results = search(query, limit=limit, api_key=api_key)
    except requests.HTTPError as e:
        resp = getattr(e, "response", None)
        if resp is not None and resp.status_code == 401:
            raise click.ClickException(
                "BGG returned 401 Unauthorized. Ensure `BGG_API_KEY` is set to your token and is sent as "
                "`Authorization: Bearer <token>`."
            ) from e
        raise
    if not results:
        click.echo(f"No results for query={query!r}")
        return

    click.echo(f"Top matches for {query!r}:")
    for r in results:
        year = f" ({r['year']})" if r.get("year") else ""
        click.echo(f"- {r.get('id')}: {r.get('name')}{year}")

    best_id = results[0].get("id")
    if not details or not best_id:
        return

    d = thing(str(best_id), api_key=api_key)
    click.echo("\nDetails for first match:")
    click.echo(f"- id: {d.get('id')}")
    click.echo(f"- name: {d.get('name')}")
    click.echo(f"- players: {d.get('minplayers')}–{d.get('maxplayers')}")
    click.echo(f"- playingtime: {d.get('playingtime')} min")
    if d.get("description"):
        click.echo("- description:")
        click.echo(
            textwrap.fill(
                d["description"][:600] + ("…" if len(d["description"]) > 600 else ""),
                width=88,
                subsequent_indent="  ",
            )
        )


if __name__ == "__main__":
    main()
