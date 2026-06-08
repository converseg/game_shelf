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


def render_interactive_html() -> str:
    """Return the interactive frontend HTML served by the API server."""
    return _INTERACTIVE_HTML


_INTERACTIVE_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Game Shelf</title>
<style>
:root {
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
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    var(--bg);
  background-size: 8px 8px;
  color: var(--text);
  font-family: "Courier New", Courier, monospace;
}
button, input, select { font: inherit; }

.app { display: grid; grid-template-columns: minmax(0, 1fr) 380px; min-height: 100vh; }
.main { min-width: 0; padding: 28px; }

.topbar {
  display: flex; align-items: end; justify-content: space-between;
  gap: 12px; margin-bottom: 22px; flex-wrap: wrap;
}
.topbar-left h1 {
  margin: 0 0 4px; font-size: 28px; letter-spacing: 0; text-transform: uppercase;
}
.topbar-left .path { color: var(--muted); font-size: 11px; }
.controls { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.filter, .search, .btn {
  min-height: 36px; border: 2px solid var(--line);
  background: var(--panel); color: var(--text);
  box-shadow: inset 0 -3px rgba(0,0,0,0.25);
}
.filter { padding: 0 12px; cursor: pointer; }
.filter[aria-pressed="true"] {
  border-color: var(--focus); color: #1c1308; background: var(--focus);
}
.search { width: min(200px, 100%); padding: 0 10px; }
.btn { padding: 0 14px; cursor: pointer; }
.btn:hover, .btn:focus-visible {
  border-color: var(--focus); outline: none;
}
.btn-primary {
  background: var(--focus); color: #1c1308; border-color: var(--focus);
  font-weight: 700;
}
.btn-danger {
  border-color: #c0392b; color: #e74c3c;
}
.btn-danger:hover { background: #c0392b; color: #fff; border-color: #c0392b; }

.room {
  padding: 18px 18px 26px; border: 3px solid var(--line);
  background: linear-gradient(#25211f, #1b1918);
  box-shadow: 0 8px 0 rgba(0,0,0,0.24);
}

.shelf-row {
  position: relative; display: flex; align-items: end; gap: 4px;
  min-height: 276px; padding: 18px 14px 24px; margin: 0 0 28px;
  overflow-x: auto;
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(0,0,0,0.12));
}
.shelf-row::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: 0;
  height: 18px;
  background: linear-gradient(var(--shelf-light) 0 3px, var(--shelf) 3px 14px, var(--shelf-dark) 14px 18px);
  box-shadow: 0 8px 0 rgba(0,0,0,0.28);
}

.spine {
  position: relative; flex: 0 0 var(--spine-width); width: var(--spine-width);
  height: var(--spine-height); border: 0; padding: 0;
  color: var(--spine-ink); background: var(--spine-body);
  box-shadow: inset 5px 0 var(--spine-edge), inset -5px 0 var(--spine-edge), 0 4px 0 rgba(0,0,0,0.35);
  cursor: pointer; image-rendering: pixelated;
}
.spine::before, .spine::after {
  content: ""; position: absolute; left: 0; right: 0; height: 22px;
  background: linear-gradient(#f0aa2a 0 3px, var(--spine-band) 3px 19px, #8a4a00 19px 22px);
}
.spine::before { top: 0; }
.spine::after { bottom: 0; transform: rotate(180deg); }
.spine:hover, .spine:focus-visible {
  outline: 3px solid var(--focus); outline-offset: 2px;
  transform: translateY(-4px);
}
.spine.selected { outline: 3px solid #fff; outline-offset: 2px; }

.spine-title {
  position: absolute; inset: 34px 12px 62px;
  display: flex; align-items: center; justify-content: center;
  writing-mode: vertical-rl; transform: rotate(180deg);
  text-transform: uppercase; text-align: center;
  line-height: 1; font-weight: 700; font-size: 14px;
  text-shadow: 2px 2px var(--spine-edge); overflow: hidden;
}
.spine-meta {
  position: absolute; left: 12px; right: 12px; bottom: 32px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 4px;
}
.pixel {
  height: 13px; background: var(--spine-band); color: #1c1308;
  font-size: 10px; line-height: 13px; text-align: center; overflow: hidden;
}

.empty {
  padding: 44px; border: 2px dashed var(--line);
  color: var(--muted); text-align: center;
}

.details {
  border-left: 3px solid var(--line); background: var(--panel);
  padding: 24px; min-width: 0; overflow-y: auto; max-height: 100vh;
  display: flex; flex-direction: column;
}
.details h2 { margin: 0 0 10px; font-size: 22px; line-height: 1.15; }
.badge {
  display: inline-block; margin: 0 0 16px; padding: 5px 8px;
  background: var(--focus); color: #211407;
  font-size: 12px; font-weight: 700;
}
.stat-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 16px;
}
.stat {
  min-height: 58px; padding: 10px;
  background: var(--panel-2); border: 2px solid var(--line);
}
.label { color: var(--muted); display: block; font-size: 11px; margin-bottom: 4px; text-transform: uppercase; }
.value { font-size: 15px; overflow-wrap: anywhere; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.tag {
  padding: 5px 7px; border: 2px solid var(--line);
  background: #1d1a18; color: var(--muted); font-size: 12px;
}
.description {
  color: var(--muted); font-size: 13px; line-height: 1.45;
  max-height: 200px; overflow-y: auto; margin-bottom: 16px; flex-shrink: 0;
}

.actions { margin-top: auto; padding-top: 16px; border-top: 2px solid var(--line); }
.actions .btn { width: 100%; margin-bottom: 6px; }
.actions .btn:last-child { margin-bottom: 0; }

/* Toggle group */
.toggle-group { display: flex; gap: 4px; margin-bottom: 10px; }
.toggle-group .btn { flex: 1; text-align: center; font-size: 13px; min-height: 32px; }
.toggle-group .btn.active { background: var(--focus); color: #1c1308; border-color: var(--focus); }

/* Rating control */
.rating-control { display: flex; gap: 3px; margin-bottom: 10px; }
.rating-btn {
  width: 32px; height: 32px; border: 2px solid var(--line);
  background: var(--panel-2); color: var(--muted); cursor: pointer;
  font-size: 13px; text-align: center; line-height: 28px;
}
.rating-btn.active { background: var(--focus); color: #1c1308; border-color: var(--focus); }
.rating-btn:hover { border-color: var(--focus); }
.rating-clear {
  border: 2px solid var(--line); background: var(--panel-2); color: var(--muted);
  cursor: pointer; font-size: 12px; padding: 0 8px; height: 32px;
}

/* Modal overlay */
.modal-overlay {
  display: none; position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.7); align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: var(--panel); border: 3px solid var(--line);
  padding: 24px; width: min(520px, 94vw); max-height: 90vh; overflow-y: auto;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6);
}
.modal h2 { margin: 0 0 16px; font-size: 20px; }
.modal label { display: block; font-size: 12px; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }
.modal input[type="text"], .modal input[type="search"] {
  width: 100%; padding: 8px 10px; border: 2px solid var(--line);
  background: var(--panel-2); color: var(--text); margin-bottom: 12px;
}
.modal input[type="text"]:focus, .modal input[type="search"]:focus {
  border-color: var(--focus); outline: none;
}
.modal-row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.modal-row label { margin-bottom: 0; }
.modal .btn { margin-right: 6px; }

.search-result {
  padding: 10px; border: 2px solid var(--line); margin-bottom: 6px;
  cursor: pointer; background: var(--panel-2);
}
.search-result:hover, .search-result.selected {
  border-color: var(--focus); background: #3a3025;
}
.search-result .name { font-weight: 700; font-size: 15px; }
.search-result .meta { color: var(--muted); font-size: 12px; margin-top: 2px; }

.spinner {
  display: inline-block; width: 20px; height: 20px;
  border: 3px solid var(--line); border-top-color: var(--focus);
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 920px) {
  .app { grid-template-columns: 1fr; }
  .details { border-left: 0; border-top: 3px solid var(--line); max-height: 50vh; }
}
</style>
</head>
<body>

<div class="app" id="app">
  <main class="main">
    <div class="topbar">
      <div class="topbar-left">
        <h1>Game Shelf</h1>
        <div class="path" id="status-line">Loading...</div>
      </div>
      <div class="controls">
        <button class="filter" data-filter="all" aria-pressed="true">All</button>
        <button class="filter" data-filter="owned" aria-pressed="false">Owned</button>
        <button class="filter" data-filter="wishlist" aria-pressed="false">Wishlist</button>
        <input class="search" id="search" type="search" placeholder="Search shelf">
        <button class="btn btn-primary" id="btn-add">+ Add</button>
      </div>
    </div>
    <section class="room" id="shelf" aria-label="Board game shelf"></section>
  </main>
  <aside class="details" id="details" aria-live="polite">
    <p style="color:var(--muted);margin-top:40vh;text-align:center">Select a game to see details</p>
  </aside>
</div>

<!-- Add game modal -->
<div class="modal-overlay" id="modal-add">
  <div class="modal">
    <h2>Add Game</h2>
    <label for="bgg-search">Search BoardGameGeek</label>
    <input type="search" id="bgg-search" placeholder="Type a game name..." autocomplete="off">
    <div id="bgg-results"></div>
    <div style="margin-top:12px">
      <label>Add as</label>
      <div class="toggle-group">
        <button class="btn active" id="add-as-owned" type="button">Owned</button>
        <button class="btn" id="add-as-wishlist" type="button">Wishlist</button>
      </div>
    </div>
    <div>
      <label>Rating (optional)</label>
      <div class="rating-control" id="add-rating">
        <button class="rating-btn" data-rating="">-</button>
      </div>
    </div>
    <div class="modal-row">
      <button class="btn btn-primary" id="btn-add-save" disabled>Save</button>
      <button class="btn" id="btn-add-cancel">Cancel</button>
    </div>
  </div>
</div>

<!-- Confirm remove modal -->
<div class="modal-overlay" id="modal-confirm">
  <div class="modal" style="width:min(380px,94vw)">
    <h2>Remove Game</h2>
    <p id="confirm-text">Remove this game from your collection?</p>
    <div class="modal-row">
      <button class="btn btn-danger" id="btn-confirm-yes">Remove</button>
      <button class="btn" id="btn-confirm-no">Cancel</button>
    </div>
  </div>
</div>

<script>
// ---- State ----
let allGames = [];
let selectedId = null;
let activeFilter = 'all';
let searchQuery = '';

// Add modal state
let addSelected = null;  // BggSearchResult | null
let addAsOwned = true;
let addRating = null;

// ---- DOM refs ----
const shelf = document.getElementById('shelf');
const details = document.getElementById('details');
const search = document.getElementById('search');
const statusLine = document.getElementById('status-line');
const filterButtons = Array.from(document.querySelectorAll('.filter'));
const modalAdd = document.getElementById('modal-add');
const modalConfirm = document.getElementById('modal-confirm');

// ---- API helpers ----
async function api(method, path, body) {
  const opts = { method, headers: { 'Accept': 'application/json' } };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${{res.status}} ${{res.statusText}}: ${{text}}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function loadGames() {
  const params = new URLSearchParams();
  if (activeFilter !== 'all') params.set(activeFilter, 'true');
  if (searchQuery) params.set('query', searchQuery);
  return api('GET', '/api/games?' + params.toString());
}

// ---- Render ----
function fmt(val, suffix) {
  return (val === null || val === undefined || val === '') ? '-' : String(val) + (suffix || '');
}

function esc(val) {
  return String(val ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function spineSize(game) {
  const w = game.weight || 2.5;
  const t = game.maxPlaytime || game.minPlaytime || 60;
  return {
    width: Math.max(52, Math.min(88, 46 + Math.round(w * 9))),
    height: Math.max(178, Math.min(248, 164 + Math.round(t / 2)))
  };
}

function playerText(g) {
  return g.minPlayers && g.maxPlayers ? `${{g.minPlayers}}-${{g.maxPlayers}}` : '-';
}

function timeText(g) {
  return g.minPlaytime && g.maxPlaytime ? `${{g.minPlaytime}}-${{g.maxPlaytime}}m` : '-';
}

function ratingText(v) {
  return v === null || v === undefined ? '-' : `${{Number(v).toFixed(1)}}/10`;
}

function renderShelf(games) {
  if (!games.length) {
    shelf.innerHTML = '<div class="empty">No games match this view.</div>';
    if (selectedId && !games.some(g => g.id === selectedId)) {
      selectedId = null;
      renderDetails(null);
    }
    return;
  }

  if (!games.some(g => g.id === selectedId)) {
    selectedId = games[0].id;
  }

  const rows = [];
  for (let i = 0; i < games.length; i += 8) {
    rows.push(games.slice(i, i + 8));
  }

  shelf.innerHTML = rows.map(row =>
    '<div class="shelf-row">' +
    row.map(game => {
      const s = spineSize(game);
      return `<button type="button" class="spine ${{game.id === selectedId ? 'selected' : ''}}" data-id="${{game.id}}" aria-label="${{esc(game.name)}}" style="--spine-width:${{s.width}}px;--spine-height:${{s.height}}px;--spine-body:${{game.palette.body}};--spine-edge:${{game.palette.edge}};--spine-band:${{game.palette.band}};--spine-ink:${{game.palette.ink}}">
        <span class="spine-title">${{esc(game.name)}}</span>
        <span class="spine-meta">
          <span class="pixel">${{game.year || '----'}}</span>
          <span class="pixel">${{game.bggRating ? Number(game.bggRating).toFixed(1) : '-'}}</span>
        </span>
      </button>`;
    }).join('') +
    '</div>'
  ).join('');

  shelf.querySelectorAll('.spine').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedId = btn.dataset.id;
      renderShelf(games);
      const game = games.find(g => g.id === selectedId);
      if (game) renderDetails(game);
    });
  });

  const selected = games.find(g => g.id === selectedId);
  if (selected) renderDetails(selected);
}

function renderDetails(game) {
  if (!game) {
    details.innerHTML = '<p style="color:var(--muted);margin-top:40vh;text-align:center">Select a game to see details</p>';
    return;
  }

  const tags = [...(game.mechanics || []), ...(game.categories || []), ...(game.themes || [])].slice(0, 16);
  const ownedActive = game.owned ? 'active' : '';
  const wishlistActive = game.wishlist ? 'active' : '';

  // Build rating buttons
  let ratingHtml = '<div class="rating-control" id="detail-rating">';
  for (let i = 1; i <= 10; i++) {
    const active = game.personalRating === i ? 'active' : '';
    ratingHtml += `<button class="rating-btn ${{active}}" data-rating="${{i}}">${{i}}</button>`;
  }
  ratingHtml += `<button class="rating-clear" id="rating-clear">Clear</button></div>`;

  details.innerHTML = [
    `<h2>${{esc(game.name)}}</h2>`,
    `<span class="badge">${{esc(game.status)}}</span>`,
    `<div class="stat-grid">`,
    `  <div class="stat"><span class="label">Players</span><span class="value">${{esc(playerText(game))}}</span></div>`,
    `  <div class="stat"><span class="label">Time</span><span class="value">${{esc(timeText(game))}}</span></div>`,
    `  <div class="stat"><span class="label">My rating</span><span class="value">${{esc(ratingText(game.personalRating))}}</span></div>`,
    `  <div class="stat"><span class="label">BGG rating</span><span class="value">${{esc(ratingText(game.bggRating))}}</span></div>`,
    `  <div class="stat"><span class="label">Weight</span><span class="value">${{esc(fmt(game.weight))}}</span></div>`,
    `  <div class="stat"><span class="label">Source</span><span class="value">${{esc(game.source)}}:${{esc(game.sourceId)}}</span></div>`,
    `</div>`,
    `<div class="tags">${{tags.length ? tags.map(t => `<span class="tag">${{esc(t)}}</span>`).join('') : '<span class="tag">No tags yet</span>'}}</div>`,
    `<div class="description">${{esc(game.description || 'No description stored.')}}</div>`,
    `<div class="actions">`,
    `  <div class="toggle-group">`,
    `    <button class="btn ${{ownedActive}}" id="toggle-owned" type="button">Owned</button>`,
    `    <button class="btn ${{wishlistActive}}" id="toggle-wishlist" type="button">Wishlist</button>`,
    `  </div>`,
    ratingHtml,
    `<button class="btn btn-danger" id="btn-remove">Remove</button>`,
    `</div>`
  ].join('\n');

  // Wire up toggle buttons
  document.getElementById('toggle-owned').addEventListener('click', () => toggleOwned(game));
  document.getElementById('toggle-wishlist').addEventListener('click', () => toggleWishlist(game));
  document.getElementById('btn-remove').addEventListener('click', () => confirmRemove(game));

  // Wire up rating buttons
  document.querySelectorAll('#detail-rating .rating-btn').forEach(btn => {
    btn.addEventListener('click', () => setRating(game, parseInt(btn.dataset.rating)));
  });
  const clearBtn = document.getElementById('rating-clear');
  if (clearBtn) clearBtn.addEventListener('click', () => setRating(game, null));
}

// ---- Actions ----

async function toggleOwned(game) {
  const updated = await api('PATCH', `/api/games/${{game.id}}`, { owned: !game.owned });
  Object.assign(game, updated);
  refresh();
}

async function toggleWishlist(game) {
  const updated = await api('PATCH', `/api/games/${{game.id}}`, { wishlist: !game.wishlist });
  Object.assign(game, updated);
  refresh();
}

async function setRating(game, rating) {
  const updated = await api('PATCH', `/api/games/${{game.id}}`, { rating });
  Object.assign(game, updated);
  refresh();
}

function confirmRemove(game) {
  document.getElementById('confirm-text').textContent = `Remove "${{game.name}}" from your collection?`;
  modalConfirm.classList.add('open');
  document.getElementById('btn-confirm-yes').onclick = async () => {
    modalConfirm.classList.remove('open');
    await api('DELETE', `/api/games/${{game.id}}`);
    if (selectedId === game.id) selectedId = null;
    refresh();
  };
  document.getElementById('btn-confirm-no').onclick = () => modalConfirm.classList.remove('open');
}

// ---- Add modal ----

let addSearchTimeout = null;

function openAddModal() {
  addSelected = null;
  addAsOwned = true;
  addRating = null;
  document.getElementById('bgg-search').value = '';
  document.getElementById('bgg-results').innerHTML = '';
  document.getElementById('btn-add-save').disabled = true;
  document.getElementById('add-as-owned').className = 'btn active';
  document.getElementById('add-as-wishlist').className = 'btn';
  renderAddRating();
  modalAdd.classList.add('open');
  document.getElementById('bgg-search').focus();
}

document.getElementById('btn-add').addEventListener('click', openAddModal);
document.getElementById('btn-add-cancel').addEventListener('click', () => modalAdd.classList.remove('open'));

document.getElementById('add-as-owned').addEventListener('click', () => {
  addAsOwned = true;
  document.getElementById('add-as-owned').className = 'btn active';
  document.getElementById('add-as-wishlist').className = 'btn';
});
document.getElementById('add-as-wishlist').addEventListener('click', () => {
  addAsOwned = false;
  document.getElementById('add-as-wishlist').className = 'btn active';
  document.getElementById('add-as-owned').className = 'btn';
});

function renderAddRating() {
  let html = '<button class="rating-btn" data-rating="null">-</button>';
  for (let i = 1; i <= 10; i++) {
    const active = addRating === i ? 'active' : '';
    html += `<button class="rating-btn ${{active}}" data-rating="${{i}}">${{i}}</button>`;
  }
  document.getElementById('add-rating').innerHTML = html;
  document.querySelectorAll('#add-rating .rating-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      addRating = btn.dataset.rating === 'null' ? null : parseInt(btn.dataset.rating);
      renderAddRating();
    });
  });
}

document.getElementById('bgg-search').addEventListener('input', () => {
  clearTimeout(addSearchTimeout);
  const q = document.getElementById('bgg-search').value.trim();
  if (!q) { document.getElementById('bgg-results').innerHTML = ''; return; }
  addSearchTimeout = setTimeout(async () => {
    const results = document.getElementById('bgg-results');
    results.innerHTML = '<div style="padding:10px"><span class="spinner"></span> Searching...</div>';
    try {
      const data = await api('POST', '/api/bgg/search', { query: q, limit: 8 });
      if (!data.length) {
        results.innerHTML = '<div class="search-result" style="cursor:default">No results found</div>';
        return;
      }
      results.innerHTML = data.map(r =>
        `<div class="search-result" data-source-id="${{r.sourceId}}" data-name="${{esc(r.name)}}" data-year="${{r.year || ''}}" data-min-players="${{r.minPlayers || ''}}" data-max-players="${{r.maxPlayers || ''}}" data-min-playtime="${{r.minPlaytime || ''}}" data-max-playtime="${{r.maxPlaytime || ''}}" data-weight="${{r.weight || ''}}" data-bgg-rating="${{r.bggRating || ''}}" data-mechanics='${{esc(JSON.stringify(r.mechanics || []))}}' data-categories='${{esc(JSON.stringify(r.categories || []))}}'>
          <div class="name">${{esc(r.name)}}</div>
          <div class="meta">${{r.year ? 'Year: ' + r.year + ' | ' : ''}}Players: ${{r.minPlayers || '?'}}-${{r.maxPlayers || '?'}} | Time: ${{r.minPlaytime || '?'}}-${{r.maxPlaytime || '?'}}m${{r.bggRating ? ' | BGG: ' + Number(r.bggRating).toFixed(1) : ''}}</div>
        </div>`
      ).join('');
      results.querySelectorAll('.search-result').forEach(el => {
        el.addEventListener('click', () => {
          results.querySelectorAll('.search-result').forEach(r => r.classList.remove('selected'));
          el.classList.add('selected');
          addSelected = {
            source: 'bgg_xml_api',
            source_id: el.dataset.sourceId,
            name: el.dataset.name,
            year: el.dataset.year ? parseInt(el.dataset.year) : null,
            min_players: el.dataset.minPlayers ? parseInt(el.dataset.minPlayers) : null,
            max_players: el.dataset.maxPlayers ? parseInt(el.dataset.maxPlayers) : null,
            min_playtime_minutes: el.dataset.minPlaytime ? parseInt(el.dataset.minPlaytime) : null,
            max_playtime_minutes: el.dataset.maxPlaytime ? parseInt(el.dataset.maxPlaytime) : null,
            weight: el.dataset.weight ? parseFloat(el.dataset.weight) : null,
            bgg_rating: el.dataset.bggRating ? parseFloat(el.dataset.bggRating) : null,
            mechanics: JSON.parse(el.dataset.mechanics || '[]'),
            categories: JSON.parse(el.dataset.categories || '[]'),
          };
          document.getElementById('btn-add-save').disabled = false;
        });
      });
    } catch (e) {
      results.innerHTML = `<div class="search-result" style="cursor:default;color:#e74c3c">Error: ${{esc(e.message)}}</div>`;
    }
  }, 300);
});

document.getElementById('btn-add-save').addEventListener('click', async () => {
  if (!addSelected) return;
  const body = { ...addSelected, owned: addAsOwned, wishlist: !addAsOwned, rating: addRating };
  document.getElementById('btn-add-save').disabled = true;
  document.getElementById('btn-add-save').textContent = 'Saving...';
  try {
    await api('POST', '/api/games', body);
    modalAdd.classList.remove('open');
    refresh();
  } catch (e) {
    alert('Failed to add game: ' + e.message);
    document.getElementById('btn-add-save').disabled = false;
    document.getElementById('btn-add-save').textContent = 'Save';
  }
});

// ---- Refresh ----

async function refresh() {
  try {
    const games = await loadGames();
    allGames = games;
    statusLine.textContent = `${{games.length}} game${{games.length !== 1 ? 's' : ''}}`;
    renderShelf(games);
  } catch (e) {
    statusLine.textContent = 'Error loading collection: ' + e.message;
    shelf.innerHTML = '<div class="empty">Error loading collection. Is the API server running?</div>';
  }
}

// ---- Init ----

filterButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    activeFilter = btn.dataset.filter;
    filterButtons.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    refresh();
  });
});

search.addEventListener('input', () => {
  searchQuery = search.value.trim().toLowerCase();
  refresh();
});

// Close modals on overlay click
[modalAdd, modalConfirm].forEach(m => {
  m.addEventListener('click', (e) => {
    if (e.target === m) m.classList.remove('open');
  });
});

refresh();
</script>
</body>
</html>"""
