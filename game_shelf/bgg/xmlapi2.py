from __future__ import annotations

from datetime import date
from typing import Iterable
import xml.etree.ElementTree as ET

import requests


def _as_csv(values: str | Iterable[str] | None) -> str | None:
    if values is None:
        return None
    if isinstance(values, str):
        return values
    values_list = list(values)
    return ",".join(values_list) if values_list else None


def _as_id_csv(ids: str | int | Iterable[str | int]) -> str:
    if isinstance(ids, (str, int)):
        return str(ids)
    return ",".join(str(x) for x in ids)


class BggXmlApi2Client:
    """
    Minimal BGG XML API2 client.

    Docs (parameter names and behavior) are based on the public XML API2 docs.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://boardgamegeek.com/xmlapi2",
        user_agent: str = "game-shelf/0.1",
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.user_agent = user_agent
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get(self, path: str, params: dict[str, object | None]) -> str:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        clean_params = {k: v for k, v in params.items() if v is not None}
        resp = requests.get(url, params=clean_params, headers=self._headers(), timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.text

    # ---- Endpoints ----

    def search(
        self,
        *,
        query: str,
        type: str | Iterable[str] | None = "boardgame",
        exact: bool | None = None,
        **extra_params: object,
    ) -> ET.Element:
        """
        /search

        Parameters (XML API2):
        - query: search string
        - type: one or more types (comma-delimited) e.g. boardgame, boardgameexpansion
        - exact=1: limit results to exact matches
        """

        params: dict[str, object | None] = {
            "query": query,
            "type": _as_csv(type),
            "exact": 1 if exact else None,
        }
        params.update(extra_params)
        return ET.fromstring(self._get("search", params))

    def thing(
        self,
        *,
        id: str | int | Iterable[str | int],
        type: str | Iterable[str] | None = None,
        versions: bool | None = None,
        videos: bool | None = None,
        stats: bool | None = None,
        historical: bool | None = None,
        marketplace: bool | None = None,
        comments: bool | None = None,
        ratingcomments: bool | None = None,
        page: int | None = None,
        pagesize: int | None = None,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        **extra_params: object,
    ) -> ET.Element:
        """
        /thing

        Parameters (XML API2):
        - id: one id or comma-delimited list (max 20 items)
        - type: filter returned records to one or more thing types (comma-delimited)
        - versions=1, videos=1, stats=1, historical=1, marketplace=1
        - comments=1 or ratingcomments=1 (cannot be used together; comments wins)
        - page: page for historical/comments/ratings
        - pagesize: min 10, max 100
        - from/to: currently not supported by BGG (kept for completeness)
        """

        id_csv = _as_id_csv(id)
        if "," in id_csv:
            if len([x for x in id_csv.split(",") if x.strip()]) > 20:
                raise ValueError("BGG /thing supports a maximum of 20 ids per request.")

        def _date(d: date | str | None) -> str | None:
            if d is None:
                return None
            return d.isoformat() if isinstance(d, date) else str(d)

        params: dict[str, object | None] = {
            "id": id_csv,
            "type": _as_csv(type),
            "versions": 1 if versions else None,
            "videos": 1 if videos else None,
            "stats": 1 if stats else None,
            "historical": 1 if historical else None,
            "marketplace": 1 if marketplace else None,
            "comments": 1 if comments else None,
            "ratingcomments": 1 if (ratingcomments and not comments) else None,
            "page": page,
            "pagesize": pagesize,
            "from": _date(from_date),
            "to": _date(to_date),
        }
        params.update(extra_params)
        return ET.fromstring(self._get("thing", params))
