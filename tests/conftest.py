from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--use-bgg",
        action="store_true",
        default=False,
        help="Run tests that make real BGG network calls.",
    )


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def collection_path(tmp_path: Path) -> Path:
    return tmp_path / "collection.json"


def write_collection(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"collection": items}, indent=2) + "\n", encoding="utf-8")


@pytest.fixture()
def use_bgg(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--use-bgg"))
