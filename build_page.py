"""Build index.html from plazas.json: the tally, then a card per plaza with its map."""
import json
from html import escape

d = json.load(open("plazas.json"))
plazas = sorted(d["plazas"], key=lambda p: (p.get("unnamed", False), p["name"].lower()))
DATE = d["generated"]

VERDICTS = {
    "none mapped": ("none", "None mapped"),
    "nearby only": ("near", "Nearby only"),
    "has parking": ("has", "Has bike parking"),
}
count = {v: sum(1 for p in plazas if p["verdict"] == v) for v in VERDICTS}


def osm(kind, i):
    return f"https://www.openstreetmap.org/{ {'n': 'node', 'w': 'way', 'r': 'relation'}[kind[0]] }/{i}"


def short_name(p):
    return p["name"] if not p.get("unnamed") else p["name"].split(" (")[0].replace("Unnamed plaza, ", "")


def rack_type(r):
    t = r["tags"]
    parts = [t.get("bicycle_parking", "type not tagged").replace("_", " ")]
    if t.get("covered") == "yes":
        parts.append("covered")
    if t.get("capacity"):
        parts.append(f"holds {t['capacity']}")
    return ", ".join(parts)


def card(p):
    cls, label = VERDICTS[p["verdict"]]
    name = escape(short_name(p))
    tenants = p["tenant_names"]
    if p["racks"]:
        items = "".join(f'<li><a href="{osm(r["type"], r["id"])}">{escape(rack_type(r))}</a></li>' for r in p["racks"])
        detail = f"<ul>{items}</ul>"
    else:
        nr = p["nearest_rack"]
        detail = f'<p>Nearest mapped rack is <a href="{osm(nr["type"], nr["id"])}">{p["nearest_rack_m"]} m away</a>.</p>'
    who = f'<p class="tenants">{escape(", ".join(tenants[:6]))}{"…" if len(tenants) > 6 else ""}</p>' if tenants else ""
    tag = ' <span class="unnamed">no name in OSM</span>' if p.get("unnamed") else ""
    return f"""<article class="card {cls}" data-verdict="{cls}">
<img src="{p['image']}" alt="Map of {name}" loading="lazy">
<div class="body">
<span class="pill">{label}</span>
<h3><a href="{osm(p['type'], p['id'])}">{name}</a>{tag}</h3>
{who}{detail}
</div>
</article>"""


tally = "".join(
    f'<button class="tile {VERDICTS[v][0]}" data-filter="{VERDICTS[v][0]}" aria-pressed="false">'
    f'<b>{count[v]}</b><span>{VERDICTS[v][1]}</span></button>'
    for v in VERDICTS
)
cards = "\n".join(card(p) for p in sorted(plazas, key=lambda p: list(VERDICTS).index(p["verdict"])))

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bike parking at Guelph's plazas</title>
<meta name="description" content="Which of Guelph's {len(plazas)} strip-mall plazas have bike parking in OpenStreetMap, and which still need someone to go and look.">
<style>
  :root {{
    --surface: #fcfcfb; --card: #ffffff; --line: #e6e5e1;
    --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #8a8981;
    --has: #4f7a28; --near: #b07d12; --none: #c2491d; --blue: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface: #131312; --card: #1d1d1b; --line: #33322e;
      --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #8a8981;
      --has: #8fae4d; --near: #d9a93a; --none: #e8764a; --blue: #6aa5ec;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--surface); color: var(--ink);
    font: 17px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main, header, footer {{ max-width: 1080px; margin: 0 auto; padding: 0 16px; }}
  header {{ padding-top: 48px; }}
  h1 {{ font-size: clamp(30px, 6vw, 46px); line-height: 1.1; margin: 0 0 16px; letter-spacing: -.02em; }}
  .lede {{ max-width: 42em; color: var(--ink-2); margin: 0 0 12px; }}
  a {{ color: var(--blue); }}
  .tally {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 28px 0; }}
  .tile {{ font: inherit; color: var(--ink); text-align: left; cursor: pointer; padding: 14px 16px;
    background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--c); border-radius: 8px; }}
  .tile b {{ display: block; font-size: 34px; line-height: 1.1; }}
  .tile span {{ color: var(--ink-2); font-size: 15px; }}
  .tile[aria-pressed="true"] {{ outline: 2px solid var(--c); }}
  .has {{ --c: var(--has); }} .near {{ --c: var(--near); }} .none {{ --c: var(--none); }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
  .card[hidden] {{ display: none; }}
  .card img {{ display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; background: var(--line); }}
  .body {{ padding: 12px 14px 14px; font-size: 15px; }}
  .pill {{ font-size: 13px; font-weight: 600; color: var(--c); }}
  h3 {{ margin: 2px 0 6px; font-size: 18px; line-height: 1.25; }}
  h3 a {{ color: inherit; text-decoration: none; }} h3 a:hover {{ text-decoration: underline; }}
  .unnamed {{ font-size: 13px; font-weight: 400; color: var(--ink-3); }}
  .tenants {{ color: var(--ink-2); margin: 0 0 6px; }}
  .body p, .body ul {{ margin: 0; }} .body ul {{ padding-left: 18px; }}
  footer {{ margin-top: 48px; padding-bottom: 48px; color: var(--ink-2); font-size: 15px; }}
  footer p {{ max-width: 46em; }}
  code {{ font-size: .92em; }}
  @media (max-width: 520px) {{ .tile {{ padding: 10px; }} .tile b {{ font-size: 26px; }} .tile span {{ font-size: 13px; }} }}
</style>
<script data-goatcounter="https://osm-ontario.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<header>
<h1>Bike parking at Guelph's plazas</h1>
<p class="lede">Can you lock a bike at the plaza? This goes through {len(plazas)} open-air, multi-tenant
plazas in Guelph and checks each against the racks in OpenStreetMap, as of {DATE}.</p>
<p class="lede"><strong>"None mapped" means go and look, not that there is no rack.</strong> OpenStreetMap is
a volunteer map, and a rack nobody has recorded will not show up here. If you find one, add it: open the
plaza's link, click Edit, and add a point tagged <code>amenity=bicycle_parking</code>.</p>
<div class="tally">{tally}</div>
</header>
<main>
<div class="grid">
{cards}
</div>
</main>
<footer>
<p>A plaza here is open-air, multi-tenant retail with shared surface parking: named plazas and shopping
centres, plus unnamed retail areas with at least four named businesses mapped inside. Big-box power centres
count. Enclosed malls, single-tenant buildings and downtown storefronts do not. "Nearby only" means a rack
within 100 m of the property but not on it. The <a href="https://github.com/skfd/guelph-plaza-bike-parking/blob/main/REPORT.md">full
report</a> has every exclusion and the <a href="plazas.csv">data as CSV</a>.</p>
<p>Map data and tiles © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, under
the <a href="https://opendatacommons.org/licenses/odbl/">Open Database Licence</a>.
<a href="https://github.com/skfd/guelph-plaza-bike-parking">Source on GitHub</a>.</p>
</footer>
<script>
const tiles = document.querySelectorAll('.tile'), cards = document.querySelectorAll('.card');
tiles.forEach(t => t.addEventListener('click', () => {{
  const on = t.getAttribute('aria-pressed') !== 'true';
  tiles.forEach(x => x.setAttribute('aria-pressed', 'false'));
  t.setAttribute('aria-pressed', String(on));
  cards.forEach(c => {{ c.hidden = on && c.dataset.verdict !== t.dataset.filter; }});
}}));
</script>
</body>
</html>
"""
open("index.html", "w", encoding="utf-8").write(page)
print(f"index.html written: {len(plazas)} plazas, {count}")
