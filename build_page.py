"""Build index.html from plazas.json: the tally, then a card per plaza with its map."""
import json
from html import escape

d = json.load(open("plazas.json"))
plazas = sorted(d["plazas"], key=lambda p: (p.get("unnamed", False), p["name"].lower()))
DATE = d["generated"]

GROUPS = {"s3": "★★★", "s2": "★★", "s1": "★", "near": "Rack next door", "look": "Go and look"}


def group(p):
    return f"s{p['stars']}" if p["stars"] else {"rack next door": "near", "go and look": "look"}[p["verdict"]]


count = {g: sum(1 for p in plazas if group(p) == g) for g in GROUPS}
rated = count["s3"] + count["s2"] + count["s1"]


def osm(kind, i):
    return f"https://www.openstreetmap.org/{ {'n': 'node', 'w': 'way', 'r': 'relation'}[kind[0]] }/{i}"


def short_name(p):
    return p["name"] if not p.get("unnamed") else p["name"].split(" (")[0].replace("Unnamed plaza, ", "")


def card(p):
    g = group(p)
    name = escape(short_name(p))
    tenants = [n for n in p["tenant_names"] if "=" not in n]   # unnamed shops come through as shop=butcher
    if p["racks"]:
        n = p["rack_count"]
        room = f"room for {'at least ' if p['capacity_untagged'] else ''}{p['capacity']} bikes" if p["capacity"] else "capacity not on the map yet"
        detail = f"<p>{n} rack{'s' if n > 1 else ''}, {room}{', some covered' if p['covered'] else ''}.</p>"
    else:
        nr = p["nearest_rack"]
        detail = f'<p>Nearest rack on the map is <a href="{osm(nr["type"], nr["id"])}">{p["nearest_rack_m"]} m away</a>.</p>'
    hint = f'<p class="next">{escape(p["next_star"])}</p>' if p["next_star"] else ""
    who = f'<p class="tenants">{escape(", ".join(tenants[:6]))}{"…" if len(tenants) > 6 else ""}</p>' if tenants else ""
    tag = ' <span class="unnamed">no name in OSM</span>' if p.get("unnamed") else ""
    label = f'<span class="pill" aria-label="{p["stars"]} of 3 stars">{GROUPS[g]}</span>' if p["stars"] else f'<span class="pill">{GROUPS[g]}</span>'
    return f"""<article class="card {g}" data-group="{g}">
<img src="{p['image']}" alt="Map of {name}" loading="lazy">
<div class="body">
{label}
<h3><a href="{osm(p['type'], p['id'])}">{name}</a>{tag}</h3>
{who}{detail}{hint}
</div>
</article>"""


tally = "".join(
    f'<button class="tile {g}" data-filter="{g}" aria-pressed="false"><b>{count[g]}</b><span>{GROUPS[g]}</span></button>'
    for g in GROUPS
)
order = sorted(plazas, key=lambda p: (list(GROUPS).index(group(p)), -p["frame_spaces"], -p["capacity"], -len(p["tenant_names"])))
cards = "\n".join(card(p) for p in order)

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bike parking at Guelph's plazas</title>
<meta name="description" content="Stars for the Guelph plazas that make it easy to arrive by bike, and an invitation to go and look at the rest.">
<style>
  :root {{
    --surface: #fcfcfb; --card: #ffffff; --line: #e6e5e1;
    --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #8a8981;
    --star: #a86f00; --near: #2a78d6; --look: #6f6e68; --blue: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface: #131312; --card: #1d1d1b; --line: #33322e;
      --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #8a8981;
      --star: #f0b429; --near: #6aa5ec; --look: #a5a49b; --blue: #6aa5ec;
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
  .tally {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 28px 0; }}
  .tile {{ font: inherit; color: var(--ink); text-align: left; cursor: pointer; padding: 14px 16px;
    background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--c); border-radius: 8px; }}
  .tile b {{ display: block; font-size: 34px; line-height: 1.1; }}
  .tile span {{ color: var(--ink-2); font-size: 15px; }}
  .tile[aria-pressed="true"] {{ outline: 2px solid var(--c); }}
  .tile.s1 span, .tile.s2 span, .tile.s3 span {{ color: var(--star); font-size: 19px; letter-spacing: .08em; }}
  .s1, .s2, .s3 {{ --c: var(--star); }} .near {{ --c: var(--near); }} .look {{ --c: var(--look); }}
  .rules {{ border-collapse: collapse; margin: 0 0 32px; font-size: 16px; }}
  .rules td {{ padding: 4px 16px 4px 0; vertical-align: top; }}
  .rules td:first-child {{ color: var(--star); white-space: nowrap; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
  .card[hidden] {{ display: none; }}
  .card img {{ display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: contain; background: var(--line); }}
  .body {{ padding: 12px 14px 14px; font-size: 15px; }}
  .pill {{ font-size: 13px; font-weight: 600; color: var(--c); }}
  .s1 .pill, .s2 .pill, .s3 .pill {{ font-size: 19px; letter-spacing: .08em; }}
  .next {{ margin-top: 6px !important; color: var(--ink-2); }}
  h3 {{ margin: 2px 0 6px; font-size: 18px; line-height: 1.25; }}
  h3 a {{ color: inherit; text-decoration: none; }} h3 a:hover {{ text-decoration: underline; }}
  .unnamed {{ font-size: 13px; font-weight: 400; color: var(--ink-3); }}
  .tenants {{ color: var(--ink-2); margin: 0 0 6px; }}
  .body p, .body ul {{ margin: 0; }} .body ul {{ padding-left: 18px; }}
  footer {{ margin-top: 48px; padding-bottom: 48px; color: var(--ink-2); font-size: 15px; }}
  footer p {{ max-width: 46em; }}
  code {{ font-size: .92em; }}
  @media (max-width: 640px) {{ .tally {{ grid-template-columns: repeat(3, 1fr); }} .tile {{ padding: 10px; }} .tile b {{ font-size: 26px; }} .tile span {{ font-size: 13px; }} }}
</style>
<script data-goatcounter="https://osm-ontario.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<header>
<h1>Bike parking at Guelph's plazas</h1>
<p class="lede">Some of Guelph's plazas make it easy to arrive by bike, and they deserve credit for it.
{rated} of {len(plazas)} open-air plazas have earned stars so far, going by the racks in OpenStreetMap as of {DATE}.</p>
<p class="lede">A plaza without stars has not failed anything. OpenStreetMap is a volunteer map, so there may be
a rack nobody has recorded yet, and if there really is none, that is a chance for a first rack. Found one? Open the
plaza's link, click Edit, and add a point tagged <code>amenity=bicycle_parking</code>.</p>
<div class="tally">{tally}</div>
<table class="rules">
<tr><td>★</td><td>A rack on the property</td></tr>
<tr><td>★★</td><td>A rack you can lock a frame to: stands, a post and ring, lockers or a bike shed</td></tr>
<tr><td>★★★</td><td>Room for at least 10 bikes at racks like that</td></tr>
</table>
</header>
<main>
<div class="grid">
{cards}
</div>
</main>
<footer>
<p>A plaza here is open-air, multi-tenant retail with shared surface parking: named plazas and shopping
centres, plus unnamed retail areas with at least four named businesses mapped inside. Big-box power centres
count. Enclosed malls, single-tenant buildings and downtown storefronts do not. Ratings use only what the map
records, so a missing rack type or capacity can hold a plaza back, and each card says what earns its next star.
"Rack next door" means a rack within 100 m of the property but not on it. The <a href="https://github.com/skfd/guelph-plaza-bike-parking/blob/main/REPORT.md">full
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
  cards.forEach(c => {{ c.hidden = on && c.dataset.group !== t.dataset.filter; }});
}}));
</script>
</body>
</html>
"""
open("index.html", "w", encoding="utf-8").write(page)
print(f"index.html written: {len(plazas)} plazas, {count}")
