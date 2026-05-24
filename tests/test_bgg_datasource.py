from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import pytest

from game_shelf.bgg import BggXmlApi2Client
from game_shelf.datasource.bgg_xml_api2 import BggXmlApi2DataSource


SEARCH_XML = """<?xml version="1.0" encoding="utf-8"?>
<items total="1" termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgame" id="13">
    <name type="primary" value="Catan"/>
  </item>
</items>
"""

THING_XML = """<?xml version="1.0" encoding="utf-8"?>
<items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
  <item type="boardgame" id="13">
    <name type="primary" value="Catan"/>
    <yearpublished value="1995"/>
    <minplayers value="3"/>
    <maxplayers value="4"/>
    <minplaytime value="60"/>
    <maxplaytime value="120"/>
    <playingtime value="90"/>
    <description>Trade, build, and settle.</description>
    <link type="boardgamecategory" value="Economic"/>
    <link type="boardgamemechanic" value="Trading"/>
    <statistics>
      <ratings>
        <average value="7.1000"/>
        <averageweight value="2.3000"/>
      </ratings>
    </statistics>
  </item>
</items>
"""


def test_bgg_datasource_lookup_by_name_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = BggXmlApi2DataSource(api_key="test-key")

    def fake_search(*, query: str, type: str | None = "boardgame", exact: bool | None = None, **kw):
        assert query
        return ET.fromstring(SEARCH_XML)

    def fake_thing(*, id, stats=None, **kw):
        # The datasource calls /thing with ids as list.
        return ET.fromstring(THING_XML)

    monkeypatch.setattr(ds._client, "search", fake_search)
    monkeypatch.setattr(ds._client, "thing", fake_thing)

    results = ds.lookup_by_name("catan", limit=5)
    assert results
    d = results[0]
    assert d.source == "bgg_xml_api"
    assert d.source_id == "13"
    assert d.name.lower() == "catan"
    assert d.min_players == 3
    assert d.max_players == 4
    assert d.weight is not None
    assert d.bgg_rating is not None


@pytest.mark.integration
def test_bgg_api_search_real(use_bgg: bool) -> None:
    if not use_bgg:
        pytest.skip('Re-run with "--use-bgg" to run real BGG API tests.')

    client = BggXmlApi2Client(api_key=os.environ.get("BGG_API_KEY"))
    root = client.search(query="Catan", type="boardgame")
    items = list(root.findall("./item"))
    assert len(items) >= 1


@pytest.mark.integration
def test_bgg_api_thing_real(use_bgg: bool) -> None:
    if not use_bgg:
        pytest.skip('Re-run with "--use-bgg" to run real BGG API tests.')

    client = BggXmlApi2Client(api_key=os.environ.get("BGG_API_KEY"))
    root = client.thing(id=13, stats=False)
    items = list(root.findall("./item"))
    assert len(items) == 1
    assert items[0].get("id") == "13"
