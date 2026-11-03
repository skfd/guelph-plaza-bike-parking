import json, requests, time
Q = r'''
[out:json][timeout:180];
area["boundary"="administrative"]["admin_level"="6"]["name"="Guelph"]->.g;
(
  nwr["shop"="mall"](area.g);
  nwr["landuse"="retail"]["name"](area.g);
  nwr["building"~"retail|commercial"]["name"~"Plaza|Mall|Centre|Center|Square|Common|Crossing|Marketplace|Shopping|Village|Market",i](area.g);
  nwr["name"~"Plaza|Strip Mall|Shopping Centre|Shopping Center|Marketplace|Shopping Plaza|Town Centre|Commons",i]["name"!~"Parking",i](area.g);
)->.plazas;
(
  nwr["amenity"="bicycle_parking"](area.g);
)->.bp;
(.plazas; .bp;);
out tags center geom;
'''

AREA = '''[out:json][timeout:180];
area["boundary"="administrative"]["admin_level"="6"]["name"="Guelph"]->.g;
'''
# landuse=retail with no name: a plaza if enough named businesses sit inside it
Q_UNNAMED = AREA + '''
way["landuse"="retail"][!"name"](area.g);
out tags geom;
'''
# tenants to count inside those areas, and every building for its address
Q_POIS = AREA + '''
(
  nwr["shop"](area.g);
  nwr["office"](area.g);
  nwr["healthcare"](area.g);
  nwr["craft"](area.g);
  nwr["leisure"="fitness_centre"](area.g);
  nwr["amenity"~"^(atm|bank|bar|cafe|car_wash|clinic|dentist|doctors|fast_food|fuel|hospital|ice_cream|library|pharmacy|post_office|pub|restaurant|veterinary)$"](area.g);
  nwr["building"](area.g);
);
out tags center;
'''


def pull(query, path):
    for attempt in range(4):
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query},
                          headers={"User-Agent": "guelph-plaza-bike-report/0.1 (toronto@comentality.com)"}, timeout=240)
        if r.status_code not in (429, 504):
            break
        time.sleep(60)
    r.raise_for_status()
    d = r.json()
    json.dump(d, open(path, "w"), indent=1)
    print(path, len(d["elements"]), d["osm3s"]["timestamp_osm_base"])
    return d


d = pull(Q, "overpass_raw.json")
pull(Q_UNNAMED, "overpass_unnamed_retail.json")
pull(Q_POIS, "overpass_pois.json")
els = d["elements"]
bp = [e for e in els if e.get("tags", {}).get("amenity") == "bicycle_parking"]
pl = [e for e in els if e.get("tags", {}).get("amenity") != "bicycle_parking"]
print("bike parking:", len(bp), " plaza candidates:", len(pl))
for e in pl:
    t = e["tags"]
    print(e["type"][0], e["id"], "|", t.get("name"), "|", t.get("shop") or "", t.get("landuse") or "", t.get("building") or "", t.get("amenity") or "")
