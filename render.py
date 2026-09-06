"""Render one Standard-layer (OSM Carto) screenshot per plaza from plazas.json.
Stitches tiles from tile.openstreetmap.org, draws the plaza outline and the bike racks
that were counted, adds ODbL attribution. Tiles are cached in tiles/."""
import json
import math
import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont

UA = "guelph-plaza-bike-report/0.1 (toronto@comentality.com)"
TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
os.makedirs("tiles", exist_ok=True)
os.makedirs("img", exist_ok=True)
sess = requests.Session()
sess.headers["User-Agent"] = UA


def ll_to_px(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n * 256
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n * 256
    return x, y


def tile(z, x, y):
    path = f"tiles/{z}_{x}_{y}.png"
    if not os.path.exists(path):
        for attempt in range(3):
            r = sess.get(TILE.format(z=z, x=x, y=y), timeout=30)
            if r.status_code == 200:
                open(path, "wb").write(r.content)
                time.sleep(0.15)
                break
            time.sleep(2)
        else:
            raise RuntimeError(f"tile {z}/{x}/{y}: {r.status_code}")
    return Image.open(path).convert("RGBA")


def metres_per_deg_lon(lat):
    return 111320 * math.cos(math.radians(lat))


def render(p, out):
    s, w, n, e = p["bbox"]
    lat0 = (s + n) / 2
    width_m = (e - w) * metres_per_deg_lon(lat0)
    height_m = (n - s) * 111320
    span = max(width_m, height_m)
    # z18 keeps a small plaza legible; z17 for the big power centres. Never below 17: OSM Carto
    # only draws the bicycle_parking icon from z17 up.
    z = 18 if span <= 320 else 17
    pad_m = 60 if z == 18 else 90
    pad_lat = pad_m / 111320
    pad_lon = pad_m / metres_per_deg_lon(lat0)
    s, w, n, e = s - pad_lat, w - pad_lon, n + pad_lat, e + pad_lon
    x0, y0 = ll_to_px(n, w, z)
    x1, y1 = ll_to_px(s, e, z)
    tx0, ty0, tx1, ty1 = int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
    canvas = Image.new("RGBA", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            canvas.paste(tile(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
    ox, oy = tx0 * 256, ty0 * 256

    def px(lat, lon):
        x, y = ll_to_px(lat, lon, z)
        return x - ox, y - oy

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    geom = p["geom_ll"]
    rings = []
    if geom["type"] == "Polygon":
        rings = [geom["coordinates"][0]]
    elif geom["type"] == "MultiPolygon":
        rings = [poly[0] for poly in geom["coordinates"]]
    for ring in rings:
        pts = [px(lat, lon) for lon, lat in ring]
        d.line(pts + [pts[0]], fill=(30, 90, 220, 230), width=4)
    for r in p["racks"]:
        cx, cy = px(r["lat"], r["lon"])
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=(20, 150, 40, 255), width=4)
    if not p["racks"] and p.get("nearest_rack"):
        r = p["nearest_rack"]
        cx, cy = px(r["lat"], r["lon"])
        if 0 <= cx < canvas.width and 0 <= cy < canvas.height:
            d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=(120, 120, 120, 255), width=3)
    canvas = Image.alpha_composite(canvas, overlay)
    crop = canvas.crop((int(x0 - ox), int(y0 - oy), int(x1 - ox), int(y1 - oy)))
    # attribution strip (ODbL requirement)
    d = ImageDraw.Draw(crop)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    text = "© OpenStreetMap contributors"
    tw = d.textlength(text, font=font)
    d.rectangle([crop.width - tw - 10, crop.height - 20, crop.width, crop.height], fill=(255, 255, 255, 200))
    d.text((crop.width - tw - 5, crop.height - 18), text, fill=(60, 60, 60, 255), font=font)
    crop.convert("RGB").save(out, optimize=True)
    return z, crop.size


if __name__ == "__main__":
    data = json.load(open("plazas.json"))
    todo = data["plazas"] + data["enclosed"]
    for i, p in enumerate(todo, 1):
        out = f"img/{p['type'][0]}{p['id']}.png"
        z, size = render(p, out)
        p["image"] = out
        p["zoom"] = z
        print(f"{i:2}/{len(todo)} z{z} {size[0]}x{size[1]} {out}  {p['name']}")
    json.dump(data, open("plazas.json", "w"), indent=1)
