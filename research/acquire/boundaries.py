"""geoBoundaries (CC BY 4.0) Bangladesh admin units -> GeoJSON cache + district centroid site list.

ADM2 = 64 districts, ADM3 = 544 upazilas, ADM4 = 5,160 unions (2020 boundaries).
Usage:  python research/acquire/boundaries.py [--levels ADM2 ADM3]
"""
from __future__ import annotations

import argparse
import csv
import json

from _common import SITES, out_dir, session, write_provenance

API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/{level}/"


def ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Planar shoelace on lon/lat; fine for district-sized polygons."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if a == 0:
        return 0.0, ring[0][0], ring[0][1]
    return abs(a), cx / (6 * a), cy / (6 * a)


def centroid(geom: dict) -> tuple[float, float]:
    """Centroid of the largest polygon, so island districts don't land in the sea."""
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    best = max((ring_area_centroid(p[0]) for p in polys), key=lambda t: t[0])
    return round(best[2], 4), round(best[1], 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="+", default=["ADM2", "ADM3"])
    args = ap.parse_args()
    s = session()
    d = out_dir("boundaries")
    for level in args.levels:
        meta = s.get(API.format(level=level), timeout=60).json()
        url = meta["simplifiedGeometryGeoJSON"]
        gj = s.get(url, timeout=300).json()
        path = d / f"BGD_{level}_simplified.geojson"
        path.write_text(json.dumps(gj), encoding="utf-8")
        write_provenance(path, source="geoBoundaries gbOpen", license=meta.get("boundaryLicense"),
                         url=url, year=meta.get("boundaryYearRepresented"), units=meta.get("admUnitCount"))
        rows = []
        for f in gj["features"]:
            lat, lon = centroid(f["geometry"])
            p = f["properties"]
            slug = "".join(c for c in p.get("shapeName", "") if c.isalnum())
            # geoBoundaries carries no parent names, so "district" is only known at ADM2
            rows.append({"site_id": f"{level}_{slug}", "name": p.get("shapeName"),
                         "district": p.get("shapeName") if level == "ADM2" else "",
                         "lat": lat, "lon": lon, "shape_id": p.get("shapeID")})
        seen: dict[str, int] = {}
        for r in rows:
            seen[r["site_id"]] = seen.get(r["site_id"], 0) + 1
        for r in rows:  # duplicate names (common at upazila level) get a shapeID suffix
            if seen[r["site_id"]] > 1:
                r["site_id"] += "_" + str(r["shape_id"])[-6:]
        out = SITES / ("districts.csv" if level == "ADM2" else f"{level.lower()}_centroids.csv")
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["name"]))
        print(f"{level}: {len(rows)} units -> {path.name}, centroids -> {out.name}")


if __name__ == "__main__":
    main()
