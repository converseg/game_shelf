from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import game_shelf.cli as cli_mod
from game_shelf.cli import cli
from game_shelf.models import CollectionGame, GameDetails
from game_shelf.storage import CollectionStore


# ---- backfill-bgg-ratings ----


def test_update_bgg_info_updates_items(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import xml.etree.ElementTree as ET

    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="1",
                game=GameDetails(source="bgg_xml_api", source_id="13", name="Catan", bgg_rating=None),
                is_owned=True,
                is_wishlist=False,
            )
        ]
    )

    class FakeClient:
        def __init__(self, api_key: str | None = None):  # type: ignore[no-untyped-def]
            self.api_key = api_key

        def thing(self, *, id, stats=None, **kw):  # type: ignore[no-untyped-def]
            return ET.fromstring(
                """<?xml version="1.0" encoding="utf-8"?>
<items>
  <item type="boardgame" id="13">
    <name type="primary" value="Catan (Refreshed)"/>
    <statistics>
      <ratings>
        <average value="7.1000"/>
      </ratings>
    </statistics>
  </item>
</items>
"""
            )

    monkeypatch.setattr(cli_mod, "BggXmlApi2Client", FakeClient)

    res = runner.invoke(
        cli,
        ["--collection-path", str(collection_path), "update-bgg-info", "--yes"],
    )
    assert res.exit_code == 0, res.output
    loaded = store.load()
    assert loaded[0].game.bgg_rating == pytest.approx(7.1)
    assert loaded[0].game.name == "Catan (Refreshed)"


# ---- add ----


def test_add_local_db_happy_path_persists(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    details = GameDetails(
        source="local_seed",
        source_id="local_compile",
        name="Compile",
        min_players=1,
        max_players=4,
        min_playtime_minutes=30,
        max_playtime_minutes=45,
    )

    class FakeLocalDS:
        def lookup_by_name(self, name: str, limit: int = 3):  # type: ignore[no-untyped-def]
            return [details]

        def suggest(self, name: str, limit: int = 5):  # type: ignore[no-untyped-def]
            return []

    monkeypatch.setattr(cli_mod, "LocalSeedDataSource", FakeLocalDS)

    res = runner.invoke(
        cli,
        [
            "--collection-path",
            str(collection_path),
            "add",
            "Compile",
            "--local-db",
            "--rating",
            "9",
            "--not-owned",
            "--wishlist",
        ],
        input="1\n",
    )
    assert res.exit_code == 0, res.output
    assert "Added: Compile" in res.output

    store = CollectionStore(collection_path)
    collection = store.load()
    assert len(collection) == 1
    item = collection[0]
    assert item.id
    assert item.game.source == "local_seed"
    assert item.game.source_id == "local_compile"
    assert item.personal_rating == 9
    assert item.is_owned is False
    assert item.is_wishlist is True


def test_add_no_matches_shows_suggestions(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeBggDS:
        def lookup_by_name(self, name: str, limit: int = 3):  # type: ignore[no-untyped-def]
            return []

        def suggest(self, name: str, limit: int = 5):  # type: ignore[no-untyped-def]
            return ["Catan", "Cat Lady"]

    monkeypatch.setattr(cli_mod, "BggXmlApi2DataSource", FakeBggDS)

    res = runner.invoke(
        cli,
        ["--collection-path", str(collection_path), "add", "Ctaan"],
    )
    assert res.exit_code == 2
    assert 'No match for "Ctaan".' in res.output
    assert "Did you mean:" in res.output
    assert "Catan" in res.output


# ---- list ----


def test_list_empty_collection(runner: CliRunner, collection_path: Path) -> None:
    res = runner.invoke(cli, ["--collection-path", str(collection_path), "list"])
    assert res.exit_code == 0, res.output
    assert "Collection is empty." in res.output


def test_list_includes_id_and_source(runner: CliRunner, collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="fixed",
                game=GameDetails(source="bgg_xml_api", source_id="13", name="Catan"),
                is_owned=True,
                is_wishlist=False,
                personal_rating=8,
            )
        ]
    )

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "list"])
    assert res.exit_code == 0, res.output
    assert "\n  id: fixed\n" in res.output
    assert "source: bgg_xml_api" in res.output
    assert "source_id: 13" in res.output


def test_list_filters_owned_and_wishlist(runner: CliRunner, collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="o",
                game=GameDetails(source="local_seed", source_id="o1", name="Owned Only"),
                is_owned=True,
                is_wishlist=False,
            ),
            CollectionGame(
                id="w",
                game=GameDetails(source="local_seed", source_id="w1", name="Wishlist Only"),
                is_owned=False,
                is_wishlist=True,
            ),
            CollectionGame(
                id="n",
                game=GameDetails(source="local_seed", source_id="n1", name="Neither"),
                is_owned=False,
                is_wishlist=False,
            ),
        ]
    )

    owned = runner.invoke(cli, ["--collection-path", str(collection_path), "list", "--owned"])
    assert owned.exit_code == 0, owned.output
    assert "Owned Only" in owned.output
    assert "Wishlist Only" not in owned.output
    assert "Neither" not in owned.output

    wishlist = runner.invoke(
        cli, ["--collection-path", str(collection_path), "list", "--wishlist"]
    )
    assert wishlist.exit_code == 0, wishlist.output
    assert "Wishlist Only" in wishlist.output
    assert "Owned Only" not in wishlist.output
    assert "Neither" not in wishlist.output

    both = runner.invoke(cli, ["--collection-path", str(collection_path), "list", "--owned", "--wishlist"])
    assert both.exit_code == 0, both.output
    assert "Owned Only" in both.output
    assert "Wishlist Only" in both.output
    assert "Neither" not in both.output


# ---- ui ----


def test_ui_writes_shelf_html_from_collection(runner: CliRunner, collection_path: Path, tmp_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="game-1",
                game=GameDetails(
                    source="bgg_xml_api",
                    source_id="13",
                    name="Catan",
                    year_published=1995,
                    min_players=3,
                    max_players=4,
                    min_playtime_minutes=60,
                    max_playtime_minutes=120,
                    bgg_rating=7.1,
                ),
                is_owned=True,
                is_wishlist=False,
                personal_rating=8,
            )
        ]
    )
    output_path = tmp_path / "shelf.html"

    res = runner.invoke(
        cli,
        ["--collection-path", str(collection_path), "ui", "--output", str(output_path)],
    )

    assert res.exit_code == 0, res.output
    assert "Wrote shelf UI:" in res.output
    html = output_path.read_text(encoding="utf-8")
    assert "<title>Game Shelf</title>" in html
    assert '"name": "Catan"' in html
    assert '"sourceId": "13"' in html
    assert "Board game shelf" in html


# ---- rate ----


def test_rate_updates_by_name_when_in_collection(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeLocalDS:
        def lookup_best(self, name: str):  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr(cli_mod, "LocalSeedDataSource", FakeLocalDS)

    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="1",
                game=GameDetails(source="bgg_xml_api", source_id="13", name="Catan"),
                is_owned=True,
                is_wishlist=False,
                personal_rating=None,
            )
        ]
    )

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "rate", "Catan", "9"])
    assert res.exit_code == 0, res.output
    assert "Rated: Catan = 9/10" in res.output

    loaded = store.load()
    assert loaded[0].personal_rating == 9


def test_rate_uses_local_seed_identity_when_available(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    details = GameDetails(source="local_seed", source_id="local_compile", name="Compile")

    class FakeLocalDS:
        def lookup_best(self, name: str):  # type: ignore[no-untyped-def]
            return details

    monkeypatch.setattr(cli_mod, "LocalSeedDataSource", FakeLocalDS)

    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="x",
                game=GameDetails(source="local_seed", source_id="local_compile", name="Compile"),
                is_owned=False,
                is_wishlist=True,
                personal_rating=None,
            )
        ]
    )

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "rate", "Compile", "7"])
    assert res.exit_code == 0, res.output
    assert "Rated: Compile = 7/10" in res.output

    loaded = store.load()
    assert loaded[0].personal_rating == 7


def test_rate_no_match_shows_closest_matches(
    runner: CliRunner, collection_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeLocalDS:
        def lookup_best(self, name: str):  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr(cli_mod, "LocalSeedDataSource", FakeLocalDS)

    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(id="1", game=GameDetails(source="local_seed", source_id="a", name="Catan")),
            CollectionGame(
                id="2", game=GameDetails(source="local_seed", source_id="b", name="Carcassonne")
            ),
        ]
    )

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "rate", "Ctaan", "6"])
    assert res.exit_code == 2
    assert 'No match for "Ctaan" in your collection.' in res.output
    assert "Closest matches:" in res.output


# ---- remove ----


def test_remove_by_id_removes_exact_match(runner: CliRunner, collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="abc",
                game=GameDetails(source="local_seed", source_id="local_compile", name="Compile"),
                is_owned=False,
                is_wishlist=True,
            )
        ]
    )

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "remove", "abc"])
    assert res.exit_code == 0, res.output

    loaded = store.load()
    assert loaded == []
    assert "Removed:" in res.output


def test_remove_by_id_warns_when_missing(runner: CliRunner, collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save([])

    res = runner.invoke(cli, ["--collection-path", str(collection_path), "remove", "missing"])
    assert res.exit_code == 2
    assert 'Warning: no game found with id "missing".' in res.output


def test_remove_by_source_id_refuses_on_duplicates(runner: CliRunner, collection_path: Path) -> None:
    store = CollectionStore(collection_path)
    store.save(
        [
            CollectionGame(
                id="1",
                game=GameDetails(source="local_seed", source_id="13", name="Seed Catan"),
                is_owned=True,
                is_wishlist=False,
            ),
            CollectionGame(
                id="2",
                game=GameDetails(source="bgg_xml_api", source_id="13", name="Catan"),
                is_owned=True,
                is_wishlist=False,
            ),
        ]
    )

    res = runner.invoke(
        cli,
        [
            "--collection-path",
            str(collection_path),
            "remove",
            "13",
            "--by",
            "source-id",
        ],
    )
    assert res.exit_code == 2
    assert 'Warning: 2 games match source_id "13".' in res.output
    assert "Refusing to remove" in res.output

