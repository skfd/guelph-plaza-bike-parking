import json, requests, sys
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
r = requests.post("https://overpass-api.de/api/interpreter", data={"data": Q},
                  headers={"User-Agent": "guelph-plaza-bike-report/0.1 (toronto@comentality.com)"}, timeout=240)
r.raise_for_status()
d = r.json()
json.dump(d, open("overpass_raw.json", "w"), indent=1)
els = d["elements"]
bp = [e for e in els if e.get("tags", {}).get("amenity") == "bicycle_parking"]
pl = [e for e in els if e.get("tags", {}).get("amenity") != "bicycle_parking"]
print("bike parking:", len(bp), " plaza candidates:", len(pl))
for e in pl:
    t = e["tags"]
    print(e["type"][0], e["id"], "|", t.get("name"), "|", t.get("shop") or "", t.get("landuse") or "", t.get("building") or "", t.get("amenity") or "")
