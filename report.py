"""Write REPORT.md and plazas.csv from plazas.json (after render.py has added image paths)."""
import csv
import json

d = json.load(open("plazas.json"))
plazas, enclosed = d["plazas"], d["enclosed"]
DATE = d["generated"]


def osm(p):
    return f"https://www.openstreetmap.org/{'way' if p['type'][0] == 'w' else 'relation'}/{p['id']}"


def osm_el(t, i):
    return f"https://www.openstreetmap.org/{ {'n': 'node', 'w': 'way', 'r': 'relation'}[t[0]] }/{i}"


def map_link(lat, lon, z=18):
    return f"https://www.openstreetmap.org/#map={z}/{lat:.5f}/{lon:.5f}"


def verdict_icon(p):
    if p["verdict"] == "rated":
        return "⭐" * p["stars"]
    return {"rack next door": "📍 rack next door", "go and look": "👀 go and look"}[p["verdict"]]


def cap_text(p):
    if not p["racks"]:
        return ""
    s = str(p["capacity"]) if p["capacity"] else ""
    if p["capacity_untagged"]:
        s += (" + " if s else "") + f"{p['capacity_untagged']} rack{'s' if p['capacity_untagged'] > 1 else ''} untagged"
    return s


def rack_type(r):
    t = r["tags"]
    parts = [t.get("bicycle_parking", "type not tagged")]
    if t.get("covered") == "yes":
        parts.append("covered")
    if t.get("capacity"):
        parts.append(f"capacity {t['capacity']}")
    return ", ".join(parts)


def short_name(p):
    return p["name"] if not p.get("unnamed") else p["name"].split(" (")[0].replace("Unnamed plaza, ", "") + " (unnamed)"


def anchor(p):
    import re
    # GitHub's heading-slug rule: lowercase, drop punctuation, spaces to hyphens
    return re.sub(r"[^a-z0-9 -]", "", short_name(p).lower()).replace(" ", "-")


counts = {v: sum(1 for p in plazas if p["verdict"] == v) for v in ("rated", "rack next door", "go and look")}
stars = {n: sum(1 for p in plazas if p["stars"] == n) for n in (3, 2, 1)}
total_racks = len({(r["type"], r["id"]) for p in plazas for r in p["racks"]})  # distinct; a rack can sit in two buffers

L = []
L.append(f"# Bike parking at Guelph's strip-mall plazas\n")
L.append(f"*Survey of OpenStreetMap data, {DATE}. Prepared for bike advocacy use.*\n")
L.append("## Summary\n")
L.append(f"Guelph has **{len(plazas)} open-air plazas** in OpenStreetMap (plus 2 enclosed malls, listed at the end). "
         f"Of those {len(plazas)}:\n")
L.append(f"| Rating | Plazas |\n|---|---|\n"
         f"| ⭐⭐⭐ Room for at least 10 bikes at racks you can lock a frame to | {stars[3]} |\n"
         f"| ⭐⭐ A rack you can lock a frame to | {stars[2]} |\n"
         f"| ⭐ A rack on the property | {stars[1]} |\n"
         f"| 📍 Rack next door: within 100 m, not on the property yet | {counts['rack next door']} |\n"
         f"| 👀 Go and look: no rack on the map yet | {counts['go and look']} |\n")
L.append(f"Across all plazas, {total_racks} bike parking locations are mapped.\n")
L.append("**How the stars work.** Stars are for plazas that make it easy to arrive by bike. Frame-lockable means stands, post-and-ring bollards, lockers or a bike shed. Wheel-only racks and informal spots earn the first star but not the second. "
         "Ratings use only what OpenStreetMap records, so a missing rack type or capacity can hold a plaza back. Every plaza below says what earns its next star, and often that is just a detail for a mapper to add.\n")
L.append("**How to read the plazas without stars.** They have not failed anything. OpenStreetMap is a volunteer map, so a plaza with no rack on it may have one nobody has recorded yet. "
         "Treat 👀 as \"go and look\", not as \"there is no rack\". One that really has none is a chance for a first rack.\n")
L.append("**What counts as a plaza here.** Open-air, multi-tenant retail with shared surface parking. Named plazas and shopping centres are included on their name; retail areas with no name in the map are included when at least four named businesses are mapped inside them. "
         "That includes the big-box power centres (SmartCentres, Woodlawn Square, Clairfield Commons, Pergola Commons). "
         "It excludes enclosed malls (listed separately), single-tenant buildings, downtown main-street storefronts and the university's pedestrian plazas. "
         "Plazas with no name in the map are listed by street and house-number range with their first three tenants.\n")
L.append("**How to fix the map.** Every plaza links to its OpenStreetMap entry. Anyone can add a missing rack: open the link, click Edit, and add a point tagged `amenity=bicycle_parking` with the rack type and capacity. "
         "That keeps this report accurate for the next person who runs it.\n")
L.append("Companion files: `plazas.csv` (one row per plaza, for your own map), `img/` (screenshots), `analyze.py` and `render.py` (how this was produced).\n")

L.append("## All plazas at a glance\n")
L.append("| Plaza | Rating | Racks | Capacity | Tenants | Map |\n|---|---|---|---|---|---|")
for p in plazas:
    L.append(f"| [{short_name(p)}](#{anchor(p)}) | {verdict_icon(p)} | {p['rack_count'] or ''} | {cap_text(p)} | {len(p['tenant_names'])} | [OSM]({osm(p)}) |")
L.append("")

L.append("## Plazas to go and look at\n")
L.append("No rack on the map yet, most tenants first. Each one is either a rack waiting to be recorded or a good place for a first rack. Distance is from the edge of the plaza to the nearest mapped rack anywhere in the city.\n")
L.append("| Plaza | Nearest mapped rack | Tenants |\n|---|---|---|")
for p in sorted([p for p in plazas if p["verdict"] == "go and look"], key=lambda p: -len(p["tenant_names"])):
    L.append(f"| [{short_name(p)}](#{anchor(p)}) | {p['nearest_rack_m']} m | {len(p['tenant_names'])} |")
L.append("")

L.append("## Plaza by plaza\n")
L.append("Blue outline: the plaza as drawn in OpenStreetMap. Green circles: bike parking counted for this plaza (on the property or within 30 m of its edge). "
         "Grey circle: the nearest rack when there is none on site, where it falls inside the frame. Map tiles are the OpenStreetMap Standard layer.\n")
for p in plazas:
    L.append(f"### {short_name(p)}\n")
    L.append(f"**{verdict_icon(p)}**  ·  [OpenStreetMap]({osm(p)})  ·  [map view]({map_link(p['lat'], p['lon'])})  ·  {p['area_ha']:.1f} ha  ·  {len(p['tenant_names'])} tenants mapped\n")
    if p.get("unnamed"):
        L.append(f"No name in OpenStreetMap. Tenants: {', '.join(p['tenant_names'][:8])}{'…' if len(p['tenant_names']) > 8 else ''}.\n")
    L.append(f"![{short_name(p)}]({p['image']})\n")
    if p["racks"]:
        L.append("Bike parking found:\n")
        for r in p["racks"]:
            L.append(f"- [{r['type']} {r['id']}]({osm_el(r['type'], r['id'])}): {rack_type(r)}")
        L.append("")
    else:
        nr = p["nearest_rack"]
        L.append(f"No rack on the map here yet. Nearest mapped rack is {p['nearest_rack_m']} m away ([{nr['type']} {nr['id']}]({osm_el(nr['type'], nr['id'])})).\n")
    if p["next_star"]:
        L.append(f"Next star: {p['next_star']}\n")

L.append("## Enclosed malls (not strip plazas, listed for completeness)\n")
for p in enclosed:
    L.append(f"### {p['name']}\n")
    L.append(f"**{verdict_icon(p)}**  ·  [OpenStreetMap]({osm(p)})  ·  {p['rack_count']} racks, capacity {cap_text(p) or 'n/a'}\n")
    L.append(f"![{p['name']}]({p['image']})\n")
    for r in p["racks"]:
        L.append(f"- [{r['type']} {r['id']}]({osm_el(r['type'], r['id'])}): {rack_type(r)}")
    L.append("")

L.append("## Possible plazas not drawn as areas in OpenStreetMap\n")
L.append("Clusters of four or more businesses within 60 m of each other that fall outside every retail area in the map. "
         "Some are strip plazas nobody has outlined yet; some are storefront rows on a main street. Not screenshotted or scored.\n")
L.append("| Location | Businesses |\n|---|---|")
for c in d["clusters"]:
    L.append(f"| [{c['lat']:.5f}, {c['lon']:.5f}]({map_link(c['lat'], c['lon'])}) | {', '.join(c['names'][:6])}{'…' if len(c['names']) > 6 else ''} |")
L.append("")

L.append("## Retail areas checked and not treated as plazas\n")
L.append("Unnamed `landuse=retail` areas with fewer than four named businesses mapped: gas stations, car dealers, single stores, or simply under-mapped lots.\n")
L.append("| OSM way | Size | Businesses mapped |\n|---|---|---|")
for r in d["unnamed_rest"]:
    L.append(f"| [{r['id']}](https://www.openstreetmap.org/way/{r['id']}) | {r['area_ha']} ha | {', '.join(r['tenant_names']) or '—'} |")
L.append("")

L.append("## Named features excluded\n")
L.append("| Feature | Why |\n|---|---|")
for x in d["excluded"]:
    L.append(f"| [{x['name'] or x['id']}](https://www.openstreetmap.org/way/{x['id']}) | {x['reason']} |")
L.append("")

L.append("## Method\n")
L.append(f"Data: OpenStreetMap via the Overpass API, pulled {DATE}, City of Guelph boundary. "
         "Plaza polygons are `shop=mall`, named `landuse=retail`, named retail/commercial buildings whose name says Plaza, Mall, Centre, Square, Commons or Marketplace, "
         "and unnamed `landuse=retail` areas with four or more named businesses inside. "
         "Bike parking is every `amenity=bicycle_parking` inside the polygon or within 30 m of its edge (racks usually sit at the sidewalk or lot margin). "
         "\"Nearby only\" means the closest rack is within 100 m of the edge but not on the property. "
         "Screenshots are stitched from the OpenStreetMap Standard tile layer at zoom 17 or 18, which is where the bicycle-parking icon starts to render.\n")
L.append("Map data © OpenStreetMap contributors, ODbL. Map tiles © OpenStreetMap contributors.\n")

open("REPORT.md", "w", encoding="utf-8").write("\n".join(L))

with open("plazas.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["name", "verdict", "stars", "frame_spaces", "next_star", "racks", "capacity_tagged", "racks_without_capacity", "nearest_rack_m", "tenants", "area_ha", "lat", "lon", "osm_url", "screenshot"])
    for p in plazas + enclosed:
        w.writerow([short_name(p) if p in plazas else p["name"] + " (enclosed mall)", p["verdict"], p["stars"], p["frame_spaces"], p["next_star"], p["rack_count"], p["capacity"], p["capacity_untagged"],
                    p["nearest_rack_m"], len(p["tenant_names"]), round(p["area_ha"], 2), round(p["lat"], 6), round(p["lon"], 6), osm(p), p["image"]])
print("REPORT.md and plazas.csv written:", len(plazas), "plazas,", counts, stars)
