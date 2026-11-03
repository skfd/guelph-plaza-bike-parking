"""Classify Guelph plazas from the Overpass pulls and score each for bike parking.
Writes plazas.json (kept plazas + appendices) for render.py / report.py."""
import json
import re
from collections import Counter
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

to_m = Transformer.from_crs("EPSG:4326", "EPSG:32617", always_xy=True).transform   # UTM 17N
to_ll = Transformer.from_crs("EPSG:32617", "EPSG:4326", always_xy=True).transform

raw_pull = json.load(open("overpass_raw.json"))
raw = raw_pull["elements"]
unnamed = json.load(open("overpass_unnamed_retail.json"))["elements"]
pois = json.load(open("overpass_pois.json"))["elements"]


def geom_of(e):
    """Shapely polygon in metres for a way/relation with geom."""
    if e["type"] == "way":
        pts = [(p["lon"], p["lat"]) for p in e.get("geometry", [])]
        if len(pts) < 4:
            return None
        return transform(to_m, Polygon(pts)).buffer(0)
    if e["type"] == "relation":
        outers = []
        for m in e.get("members", []):
            if m.get("role") == "outer" and m.get("geometry"):
                pts = [(p["lon"], p["lat"]) for p in m["geometry"]]
                if len(pts) >= 4 and pts[0] == pts[-1]:
                    outers.append(Polygon(pts))
        if not outers:
            return None
        return transform(to_m, unary_union(outers)).buffer(0)
    return None


def centroid_ll(g):
    c = transform(to_ll, g.centroid)
    return c.y, c.x


# ---------- 1. named plazas: explicit inclusion rule ----------
# Rule: open-air, multi-tenant retail with shared surface parking.
EXCLUDE = {
    123274454: "enclosed downtown mall (Old Quebec Street), listed in the enclosed-malls appendix",
    121261616: "enclosed regional mall (Stone Road Mall), listed in the enclosed-malls appendix",
    121429569: "single-tenant big box (Walmart Supercentre), counted inside its plaza polygon",
    123418023: "single-use building (chiropractic clinic)",
    259225310: "Farmers' Market building",
    287908558: "cinema building inside Pergola Commons",
    559510908: "single-use medical office building",
    761343597: "social facility, not retail",
    772999962: "downtown retail landuse, not a plaza",
    1042080141: "university pedestrian plaza",
    1089966291: "university pedestrian plaza",
    1492356058: "university seating area",
    20304751: "university pedestrian plaza",
}
ENCLOSED = {123274454, 121261616}
# duplicates -> merge into the first id
MERGE = {217385469: 197749304,   # Hartsland Market Square second way
         399342520: 399321881,   # University Square -> University Square Plaza
         }

named = {}
for e in raw:
    t = e.get("tags", {})
    if t.get("amenity") == "bicycle_parking":
        continue
    g = geom_of(e)
    if g is None:
        continue
    named[e["id"]] = dict(id=e["id"], type=e["type"], name=t.get("name"), tags=t, geom=g)

for dup, keep in MERGE.items():
    if dup in named and keep in named:
        named[keep]["geom"] = unary_union([named[keep]["geom"], named[dup]["geom"]])
        named[keep].setdefault("merged", []).append(dup)
        del named[dup]

plazas, enclosed = [], []
for pid, p in named.items():
    if pid in ENCLOSED:
        enclosed.append(p)
        continue
    if pid in EXCLUDE:
        continue
    plazas.append(p)

kept_union = unary_union([p["geom"] for p in plazas + enclosed])


# ---------- 2. unnamed retail areas ----------
def poi_kind(t):
    for k in ("shop", "amenity", "healthcare", "office", "craft", "leisure"):
        if k in t:
            return f"{k}={t[k]}"
    return None


tenant_pts = []
for e in pois:
    t = e.get("tags", {})
    k = poi_kind(t)
    if not k:
        continue
    if e["type"] == "node":
        lat, lon = e["lat"], e["lon"]
    else:
        c = e.get("center")
        if not c:
            continue
        lat, lon = c["lat"], c["lon"]
    tenant_pts.append((Point(to_m(lon, lat)), t.get("name") or k, k, e))


NON_TENANT = {"amenity=fuel", "amenity=car_wash", "amenity=atm", "amenity=vending_machine", "amenity=parking",
              "shop=car", "shop=car_repair", "shop=car_parts", "shop=tyres", "shop=vacant", "shop=yes"}
TENANT_MIN = 4


def tenants_in(g, buf=5):
    gb = g.buffer(buf)
    return [(n, k, e) for pt, n, k, e in tenant_pts if gb.contains(pt) and k not in NON_TENANT]


unnamed_plazas, unnamed_rest = [], []
for e in unnamed:
    g = geom_of(e)
    if g is None:
        continue
    if g.intersects(kept_union) and g.intersection(kept_union).area > 0.2 * g.area:
        continue  # already covered by a named plaza
    ten = tenants_in(g)
    names = sorted({n for n, k, e2 in ten})
    lat, lon = centroid_ll(g)
    rec = dict(id=e["id"], type="way", tags=e.get("tags", {}), geom=g, tenants=ten, tenant_names=names,
               area_ha=g.area / 1e4, lat=lat, lon=lon)
    (unnamed_plazas if len(names) >= TENANT_MIN else unnamed_rest).append(rec)


def label_unnamed(rec):
    t = rec["tags"]
    street = t.get("addr:street")
    if not street:
        c = Counter(e2.get("tags", {}).get("addr:street") for n, k, e2 in rec["tenants"])
        c.pop(None, None)
        street = c.most_common(1)[0][0] if c else None
    hn = t.get("addr:housenumber")
    if not hn and street:
        nums = sorted({int(m.group()) for n, k, e2 in rec["tenants"]
                       if e2.get("tags", {}).get("addr:street") == street
                       and (m := re.match(r"\d+", e2["tags"].get("addr:housenumber", "")))})
        if nums:
            hn = str(nums[0]) if len(nums) == 1 or nums[0] == nums[-1] else f"{nums[0]}-{nums[-1]}"
    main = ", ".join(rec["tenant_names"][:3])
    base = f"{hn + ' ' if hn else ''}{street}" if street else f"retail area {rec['id']}"
    return f"Unnamed plaza, {base} ({main})"


for r in unnamed_plazas:
    r["name"] = label_unnamed(r)
    r["unnamed"] = True
    plazas.append(r)

# ---------- 3. gap check: POI clusters outside all polygons ----------
all_union = unary_union([p["geom"] for p in plazas + enclosed])
outside = [(pt, n, k, e) for pt, n, k, e in tenant_pts
           if not all_union.buffer(20).contains(pt)
           and k.split("=")[0] in ("shop", "amenity") and k != "amenity=fuel"]
downtown = named[772999962]["geom"].buffer(300) if 772999962 in named else None  # main-street storefront rows are not plazas
clusters = []
used = set()
for i, (pt, n, k, e) in enumerate(outside):
    if i in used:
        continue
    grp = [j for j, (pt2, *_) in enumerate(outside) if j not in used and pt.distance(pt2) <= 60]
    brands = {outside[j][1].split()[0].lower() for j in grp if outside[j][1] and "=" not in outside[j][1]}
    if len({outside[j][1] for j in grp}) >= 4 and len(brands) >= 3:
        used.update(grp)
        c = unary_union([outside[j][0] for j in grp]).centroid
        if downtown is not None and downtown.contains(c):
            continue
        lat, lon = centroid_ll(c)
        clusters.append(dict(lat=lat, lon=lon, names=sorted({outside[j][1] for j in grp})))

# ---------- 4. bike parking ----------
bp = []
for e in raw:
    t = e.get("tags", {})
    if t.get("amenity") != "bicycle_parking":
        continue
    if e["type"] == "node":
        lat, lon = e["lat"], e["lon"]
    else:
        c = e.get("center") or {}
        lat, lon = c.get("lat"), c.get("lon")
        if lat is None:
            continue
    bp.append(dict(id=e["id"], type=e["type"], lat=lat, lon=lon, pt=Point(to_m(lon, lat)), tags=t))


# ---------- 5. stars ----------
# Only a plaza with a rack on site is rated: an empty map is an unknown, never a low score.
# Types follow js/types.js in guelph-bike-parking. `rack` and `loops` are used too loosely
# to tell a frame rack from a wheel bender, so they count as not recorded yet.
FRAME_LOCKABLE = {"stands", "wide_stands", "safe_loops", "anchors", "wave", "bollard", "two-tier", "shed", "lockers", "building"}
NOT_FRAME = {"wall_loops", "ground_slots", "informal"}
THREE_STAR_SPACES = 10


def rate(racks):
    """Stars, spaces at frame-lockable racks, and what would earn the next star."""
    if not racks:
        return None, 0, "A first rack on the map earns the first star."
    kinds = [b["tags"].get("bicycle_parking") for b in racks]
    lockable = [b for b, k in zip(racks, kinds) if k in FRAME_LOCKABLE]
    unclear = [k for k in kinds if k not in FRAME_LOCKABLE and k not in NOT_FRAME]
    spaces = sum(int(b["tags"]["capacity"]) for b in lockable if b["tags"].get("capacity", "").isdigit())
    if not lockable:
        if unclear:
            return 1, 0, "The rack type is not clear on the map. Adding it could already earn a second star."
        return 1, 0, "A stand you can lock a frame to earns the second star."
    if spaces >= THREE_STAR_SPACES:
        return 3, spaces, None
    if unclear or any(not b["tags"].get("capacity", "").isdigit() for b in lockable):
        return 2, spaces, "Some rack details are missing from the map. Adding them could already earn a third star."
    more = THREE_STAR_SPACES - spaces
    return 2, spaces, f"Room for {more} more bike{'s' if more > 1 else ''} earns the third star."


def score(p):
    g = p["geom"]
    gb = g.buffer(30)
    racks = [b for b in bp if gb.contains(b["pt"])]
    cap = sum(int(b["tags"]["capacity"]) for b in racks if b["tags"].get("capacity", "").isdigit())
    untagged = sum(1 for b in racks if not b["tags"].get("capacity", "").isdigit())
    nearest = min(bp, key=lambda b: g.distance(b["pt"])) if bp else None
    nd = g.distance(nearest["pt"]) if nearest else None
    if racks:
        verdict = "rated"
    elif nd is not None and nd <= 100:
        verdict = "rack next door"
    else:
        verdict = "go and look"
    stars, spaces, next_star = rate(racks)
    p.update(stars=stars, frame_spaces=spaces, next_star=next_star,
             covered=any(b["tags"].get("covered") == "yes" for b in racks),
             racks=[dict(id=b["id"], type=b["type"], lat=b["lat"], lon=b["lon"], tags=b["tags"]) for b in racks],
             rack_count=len(racks), capacity=cap, capacity_untagged=untagged, verdict=verdict,
             nearest_rack_m=round(nd) if nd is not None else None,
             nearest_rack=dict(id=nearest["id"], type=nearest["type"], lat=nearest["lat"], lon=nearest["lon"]) if nearest else None)
    if "tenants" not in p:
        p["tenants"] = tenants_in(g)
        p["tenant_names"] = sorted({n for n, k, e in p["tenants"]})
    lat, lon = centroid_ll(g)
    p["lat"], p["lon"] = lat, lon
    p["area_ha"] = g.area / 1e4
    minx, miny, maxx, maxy = g.bounds
    w, s = to_ll(minx, miny)
    e_, n = to_ll(maxx, maxy)
    p["bbox"] = [s, w, n, e_]


for p in plazas + enclosed:
    score(p)


def dump(p):
    d = {k: v for k, v in p.items() if k not in ("geom", "tenants")}
    d["geom_ll"] = json.loads(json.dumps(transform(to_ll, p["geom"]).__geo_interface__))
    return d


out = dict(
    generated=raw_pull["osm3s"]["timestamp_osm_base"][:10],
    rule="open-air, multi-tenant retail with shared surface parking; enclosed malls listed separately",
    plazas=sorted([dump(p) for p in plazas], key=lambda p: p["name"]),
    enclosed=[dump(p) for p in enclosed],
    excluded=[dict(id=i, name=named[i]["name"] if i in named else None, reason=r)
              for i, r in EXCLUDE.items() if i not in ENCLOSED],
    unnamed_rest=[dict(id=r["id"], area_ha=round(r["area_ha"], 2), tenants=len(r["tenant_names"]),
                       tenant_names=r["tenant_names"], lat=r["lat"], lon=r["lon"])
                  for r in sorted(unnamed_rest, key=lambda r: -r["area_ha"])],
    clusters=clusters,
    bike_parking_total=len(bp),
)
json.dump(out, open("plazas.json", "w"), indent=1)
print(f"{len(plazas)} plazas ({sum(1 for p in plazas if p.get('unnamed'))} unnamed), {len(enclosed)} enclosed, "
      f"{len(unnamed_rest)} unnamed retail areas not plazas, {len(clusters)} unmapped clusters")
for p in sorted(plazas, key=lambda p: p["name"]):
    print(f"  {p['verdict']:12} racks={p['rack_count']:2} cap={p['capacity']:3} tenants={len(p['tenant_names']):2} "
          f"near={p['nearest_rack_m']} {p['area_ha']:.1f}ha  {p['name']}")
print("clusters:")
for c in clusters:
    print("  ", f"{c['lat']:.5f},{c['lon']:.5f}", c["names"][:6])
