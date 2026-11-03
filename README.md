# Bike parking at Guelph's plazas

**[→ the page](https://skfd.github.io/guelph-plaza-bike-parking/)**

Stars for the Guelph plazas that make it easy to arrive by bike, and a friendly invitation to
go and look at the rest. The point is to give credit where it is earned and stay positive about
the plazas that are not there yet, or not on the map yet.

| | |
|---|---|
| ★ | a rack on the property |
| ★★ | a rack you can lock a frame to: stands, a post and ring, lockers or a bike shed |
| ★★★ | room for at least 10 bikes at racks like that |
| Rack next door | a rack within 100 m, not on the property yet |
| Go and look | no rack on the map yet |

A plaza without stars is unrated, never zero. OSM is a volunteer map, so no rack on the map only
means someone should go and look. Ratings use what the map records, so a missing rack type or
capacity can hold a plaza back. Every plaza says what earns its next star, and the rules live
in one place, at the top of the stars section in `analyze.py`.

## What is here

| | |
|---|---|
| `index.html` | the page |
| `REPORT.md` | the write-up: every plaza, its racks, and everything left out and why |
| `plazas.csv` | one row per plaza |
| `plazas.json` | the same with geometry, racks and tenants |
| `img/` | a small map per plaza with its outline and racks drawn on |
| `overpass_*.json` | the raw Overpass responses behind this run |

## Running it

```
fetch.py       # three Overpass pulls, about three minutes
analyze.py     # classify the plazas and score each, writes plazas.json
render.py      # the maps, stitched from OSM tiles cached in tiles/ (not committed)
report.py      # REPORT.md and plazas.csv
build_page.py  # index.html
```

Run them in that order. `render.py` adds the image paths to `plazas.json`, so it has to come
before the last two. Needs `requests`, `shapely`, `pyproj` and `pillow`.

Which plazas count is partly hand-judged: `EXCLUDE` and `MERGE` in `analyze.py` list OSM ids by
hand. After a refresh, read what changed in `plazas.csv` before trusting the totals, because a
newly named building will be counted as a plaza until someone says otherwise.

## Credit

Map data and tiles © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors,
available under the [Open Database Licence](https://opendatacommons.org/licenses/odbl/). The
derived figures and geometry here are a Produced Work from that data and carry the same
attribution. Code is MIT.
