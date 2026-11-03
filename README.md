# Bike parking at Guelph's plazas

**[→ the page](https://skfd.github.io/guelph-plaza-bike-parking/)**

Which of Guelph's strip-mall plazas have bike parking, according to OpenStreetMap, and which
still need someone to go and look. Each open-air plaza is checked against the mapped racks and
gets one of three verdicts: on site, within 100 m, or none mapped.

"None mapped" is not "no rack". OSM is a volunteer map, so the verdict means go and look. Every
plaza links to its OSM entry so a missing rack can be added, and the next run picks it up.

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
