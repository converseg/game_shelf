from __future__ import annotations

import html
import json
from pathlib import Path

from game_shelf.models import CollectionGame


def _status_label(item: CollectionGame) -> str:
    if item.is_owned and item.is_wishlist:
        return "Owned + wishlist"
    if item.is_owned:
        return "Owned"
    if item.is_wishlist:
        return "Wishlist"
    return "Tracked"


def _game_payload(item: CollectionGame) -> dict[str, object]:
    game = item.game
    return {
        "id": item.id,
        "name": game.name,
        "year": game.year_published,
        "source": game.source,
        "sourceId": game.source_id,
        "owned": item.is_owned,
        "wishlist": item.is_wishlist,
        "status": _status_label(item),
        "personalRating": item.personal_rating,
        "bggRating": game.bgg_rating,
        "minPlayers": game.min_players,
        "maxPlayers": game.max_players,
        "minPlaytime": game.min_playtime_minutes,
        "maxPlaytime": game.max_playtime_minutes,
        "weight": game.weight,
        "mechanics": sorted({*(game.mechanics or []), *(game.mechanics_custom or [])}),
        "categories": sorted({*(game.categories or []), *(game.categories_custom or [])}),
        "themes": game.themes,
        "description": game.description,
        "palette": _palette_for_id(item.id),
    }


def _palette_for_id(value: str) -> dict[str, str]:
    palettes = [
        {"body": "#1a52a8", "edge": "#0d2d66", "band": "#d4880a", "ink": "#fff8e8"},
        {"body": "#8f2f44", "edge": "#541827", "band": "#e3a73b", "ink": "#fff8e8"},
        {"body": "#256b4f", "edge": "#123b2b", "band": "#c98b2c", "ink": "#fff8e8"},
        {"body": "#563f8f", "edge": "#302352", "band": "#d7a22c", "ink": "#fff8e8"},
        {"body": "#a9472a", "edge": "#622416", "band": "#e0b043", "ink": "#fff8e8"},
        {"body": "#2f6f86", "edge": "#183e4c", "band": "#d98f2b", "ink": "#fff8e8"},
    ]
    return palettes[sum(ord(char) for char in value) % len(palettes)]


def render_shelf_html(collection: list[CollectionGame], *, collection_path: Path) -> str:
    games = [_game_payload(item) for item in sorted(collection, key=lambda x: x.game.name.lower())]
    data_json = (
        json.dumps(games, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    collection_label = html.escape(str(collection_path))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Game Shelf</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #171717;
      --panel: #24201d;
      --panel-2: #312820;
      --shelf: #6b3e23;
      --shelf-dark: #3f2418;
      --shelf-light: #9a6235;
      --text: #fff8e8;
      --muted: #c8b9a4;
      --line: #5c4636;
      --focus: #f0aa2a;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        var(--bg);
      background-size: 8px 8px;
      color: var(--text);
      font-family: "Courier New", Courier, monospace;
    }}

    button, input {{
      font: inherit;
    }}

    .app {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      min-height: 100vh;
    }}

    .main {{
      min-width: 0;
      padding: 28px;
    }}

    .topbar {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 22px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    .path {{
      max-width: 820px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}

    .controls {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .filter, .search {{
      min-height: 36px;
      border: 2px solid var(--line);
      background: var(--panel);
      color: var(--text);
      box-shadow: inset 0 -3px rgba(0,0,0,0.25);
    }}

    .filter {{
      padding: 0 12px;
      cursor: pointer;
    }}

    .filter[aria-pressed="true"] {{
      border-color: var(--focus);
      color: #1c1308;
      background: var(--focus);
    }}

    .search {{
      width: min(320px, 100%);
      padding: 0 12px;
    }}

    .room {{
      padding: 18px 18px 26px;
      border: 3px solid var(--line);
      background: linear-gradient(#25211f, #1b1918);
      box-shadow: 0 8px 0 rgba(0,0,0,0.24);
    }}

    .shelf-row {{
      position: relative;
      display: flex;
      align-items: end;
      gap: 4px;
      min-height: 276px;
      padding: 18px 14px 24px;
      margin: 0 0 28px;
      overflow-x: auto;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(0,0,0,0.12));
    }}

    .shelf-row::after {{
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 18px;
      background: linear-gradient(var(--shelf-light) 0 3px, var(--shelf) 3px 14px, var(--shelf-dark) 14px 18px);
      box-shadow: 0 8px 0 rgba(0,0,0,0.28);
    }}

    .spine {{
      position: relative;
      flex: 0 0 var(--spine-width);
      width: var(--spine-width);
      height: var(--spine-height);
      border: 0;
      padding: 0;
      color: var(--spine-ink);
      background: var(--spine-body);
      box-shadow:
        inset 5px 0 var(--spine-edge),
        inset -5px 0 var(--spine-edge),
        0 4px 0 rgba(0,0,0,0.35);
      cursor: pointer;
      image-rendering: pixelated;
    }}

    .spine::before,
    .spine::after {{
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      height: 22px;
      background: linear-gradient(#f0aa2a 0 3px, var(--spine-band) 3px 19px, #8a4a00 19px 22px);
    }}

    .spine::before {{ top: 0; }}
    .spine::after {{ bottom: 0; transform: rotate(180deg); }}

    .spine:hover,
    .spine:focus-visible {{
      outline: 3px solid var(--focus);
      outline-offset: 2px;
      transform: translateY(-4px);
    }}

    .spine-title {{
      position: absolute;
      inset: 34px 12px 62px;
      display: flex;
      align-items: center;
      justify-content: center;
      writing-mode: vertical-rl;
      transform: rotate(180deg);
      text-transform: uppercase;
      text-align: center;
      line-height: 1;
      font-weight: 700;
      font-size: 14px;
      text-shadow: 2px 2px var(--spine-edge);
      overflow: hidden;
    }}

    .spine-meta {{
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 32px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
    }}

    .pixel {{
      height: 13px;
      background: var(--spine-band);
      color: #1c1308;
      font-size: 10px;
      line-height: 13px;
      text-align: center;
      overflow: hidden;
    }}

    .empty {{
      padding: 44px;
      border: 2px dashed var(--line);
      color: var(--muted);
      text-align: center;
    }}

    .details {{
      border-left: 3px solid var(--line);
      background: var(--panel);
      padding: 24px;
      min-width: 0;
    }}

    .details h2 {{
      margin: 0 0 10px;
      font-size: 22px;
      line-height: 1.15;
    }}

    .badge {{
      display: inline-block;
      margin: 0 0 20px;
      padding: 5px 8px;
      background: var(--focus);
      color: #211407;
      font-size: 12px;
      font-weight: 700;
    }}

    .stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin: 0 0 18px;
    }}

    .stat {{
      min-height: 58px;
      padding: 10px;
      background: var(--panel-2);
      border: 2px solid var(--line);
    }}

    .label {{
      color: var(--muted);
      display: block;
      font-size: 11px;
      margin-bottom: 4px;
      text-transform: uppercase;
    }}

    .value {{
      font-size: 15px;
      overflow-wrap: anywhere;
    }}

    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 18px;
    }}

    .tag {{
      padding: 5px 7px;
      border: 2px solid var(--line);
      background: #1d1a18;
      color: var(--muted);
      font-size: 12px;
    }}

    .description {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      max-height: 260px;
      overflow: auto;
    }}

    @media (max-width: 920px) {{
      .app {{
        grid-template-columns: 1fr;
      }}

      .details {{
        border-left: 0;
        border-top: 3px solid var(--line);
      }}

      .topbar {{
        align-items: stretch;
        flex-direction: column;
      }}

      .controls {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <main class="main">
      <div class="topbar">
        <div>
          <h1>Game Shelf</h1>
          <div class="path">{collection_label}</div>
        </div>
        <div class="controls">
          <button class="filter" type="button" data-filter="all" aria-pressed="true">All</button>
          <button class="filter" type="button" data-filter="owned" aria-pressed="false">Owned</button>
          <button class="filter" type="button" data-filter="wishlist" aria-pressed="false">Wishlist</button>
          <input class="search" id="search" type="search" placeholder="Search shelf">
        </div>
      </div>
      <section class="room" id="shelf" aria-label="Board game shelf"></section>
    </main>
    <aside class="details" id="details" aria-live="polite"></aside>
  </div>

  <script>
    const games = {data_json};
    const shelf = document.querySelector("#shelf");
    const details = document.querySelector("#details");
    const search = document.querySelector("#search");
    const filterButtons = Array.from(document.querySelectorAll(".filter"));
    let activeFilter = "all";
    let selectedId = games[0]?.id ?? null;

    function fmt(value, suffix = "") {{
      return value === null || value === undefined || value === "" ? "-" : `${{value}}${{suffix}}`;
    }}

    function esc(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }}

    function playerText(game) {{
      if (game.minPlayers && game.maxPlayers) return `${{game.minPlayers}}-${{game.maxPlayers}}`;
      return "-";
    }}

    function timeText(game) {{
      if (game.minPlaytime && game.maxPlaytime) return `${{game.minPlaytime}}-${{game.maxPlaytime}}m`;
      return "-";
    }}

    function ratingText(value) {{
      return value === null || value === undefined ? "-" : `${{Number(value).toFixed(1)}}/10`;
    }}

    function spineSize(game) {{
      const weight = game.weight || 2.5;
      const maxTime = game.maxPlaytime || game.minPlaytime || 60;
      const width = Math.max(52, Math.min(88, 46 + Math.round(weight * 9)));
      const height = Math.max(178, Math.min(248, 164 + Math.round(maxTime / 2)));
      return {{ width, height }};
    }}

    function filteredGames() {{
      const query = search.value.trim().toLowerCase();
      return games.filter((game) => {{
        if (activeFilter === "owned" && !game.owned) return false;
        if (activeFilter === "wishlist" && !game.wishlist) return false;
        if (query && !game.name.toLowerCase().includes(query)) return false;
        return true;
      }});
    }}

    function renderShelf() {{
      const visible = filteredGames();
      if (!visible.length) {{
        shelf.innerHTML = '<div class="empty">No games match this view.</div>';
        selectedId = null;
        renderDetails(null);
        return;
      }}

      if (!visible.some((game) => game.id === selectedId)) {{
        selectedId = visible[0].id;
      }}

      const rows = [];
      for (let i = 0; i < visible.length; i += 8) {{
        rows.push(visible.slice(i, i + 8));
      }}

      shelf.innerHTML = rows.map((row) => `
        <div class="shelf-row">
          ${{row.map((game) => {{
            const size = spineSize(game);
            return `
              <button
                type="button"
                class="spine"
                data-id="${{game.id}}"
                aria-label="${{esc(game.name)}}"
                style="
                  --spine-width: ${{size.width}}px;
                  --spine-height: ${{size.height}}px;
                  --spine-body: ${{game.palette.body}};
                  --spine-edge: ${{game.palette.edge}};
                  --spine-band: ${{game.palette.band}};
                  --spine-ink: ${{game.palette.ink}};
                "
              >
                <span class="spine-title">${{esc(game.name)}}</span>
                <span class="spine-meta">
                  <span class="pixel">${{game.year || "----"}}</span>
                  <span class="pixel">${{game.bggRating ? Number(game.bggRating).toFixed(1) : "-"}}</span>
                </span>
              </button>
            `;
          }}).join("")}}
        </div>
      `).join("");

      shelf.querySelectorAll(".spine").forEach((button) => {{
        button.addEventListener("click", () => {{
          selectedId = button.dataset.id;
          renderDetails(games.find((game) => game.id === selectedId));
        }});
      }});

      renderDetails(games.find((game) => game.id === selectedId));
    }}

    function renderDetails(game) {{
      if (!game) {{
        details.innerHTML = `
          <h2>No game selected</h2>
          <p class="description">Add games with the CLI, then regenerate this page.</p>
        `;
        return;
      }}

      const tags = [...game.mechanics, ...game.categories, ...game.themes].slice(0, 16);
      details.innerHTML = `
        <h2>${{esc(game.name)}}</h2>
        <span class="badge">${{esc(game.status)}}</span>
        <div class="stat-grid">
          <div class="stat"><span class="label">Players</span><span class="value">${{esc(playerText(game))}}</span></div>
          <div class="stat"><span class="label">Time</span><span class="value">${{esc(timeText(game))}}</span></div>
          <div class="stat"><span class="label">My rating</span><span class="value">${{esc(ratingText(game.personalRating))}}</span></div>
          <div class="stat"><span class="label">BGG rating</span><span class="value">${{esc(ratingText(game.bggRating))}}</span></div>
          <div class="stat"><span class="label">Weight</span><span class="value">${{esc(fmt(game.weight))}}</span></div>
          <div class="stat"><span class="label">Source</span><span class="value">${{esc(game.source)}}:${{esc(game.sourceId)}}</span></div>
        </div>
        <div class="tags">${{tags.length ? tags.map((tag) => `<span class="tag">${{esc(tag)}}</span>`).join("") : '<span class="tag">No tags yet</span>'}}</div>
        <div class="description">${{esc(game.description || "No description stored.")}}</div>
      `;
    }}

    filterButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        activeFilter = button.dataset.filter;
        filterButtons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
        renderShelf();
      }});
    }});

    search.addEventListener("input", renderShelf);
    renderShelf();
  </script>
</body>
</html>
"""


def write_shelf_html(
    collection: list[CollectionGame],
    *,
    collection_path: Path,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_shelf_html(collection, collection_path=collection_path),
        encoding="utf-8",
    )
    return output_path
