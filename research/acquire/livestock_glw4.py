"""FAO Gridded Livestock of the World v4 (GLW4), cattle 2015, summed by Bangladesh district.

Gilbert M. et al. (2018) Global distribution data for cattle, buffaloes, horses, sheep, goats, pigs, chickens
and ducks in 2010. Sci Data 5:180227. Dataset: doi:10.7910/DVN/LHBICE (Harvard Dataverse, CC0).
File: 5_Ct_2015_Da.tif = cattle head per ~10 km cell (dasymetric). Each cell is assigned to the district
containing its centre; border cells can land on either side, so treat district totals as approximate.

Output: research/crops/cattle_by_district_glw4.csv. Usage: python research/acquire/livestock_glw4.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from _common import DATA, RESEARCH, out_dir, session, write_provenance

URL = "https://dataverse.harvard.edu/api/access/datafile/6769711"  # 5_Ct_2015_Da.tif
Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, str(RESEARCH / "explore"))


def district_polygons() -> list:
    gj = json.loads((DATA / "boundaries" / "BGD_ADM2_simplified.geojson").read_text(encoding="utf-8"))
    out = []
    for f in gj["features"]:
        g = f["geometry"]
        rings = [p[0] for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]])]
        out.append((f["properties"]["shapeName"], rings))
    return out


def inside(x: float, y: float, ring: list) -> bool:
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def main() -> None:
    d = out_dir("livestock")
    tif = d / "GLW4_cattle_2015_Da.tif"
    if not tif.exists():
        s = session()
        s.headers["User-Agent"] = "Mozilla/5.0 (WinR research; NASA Space Apps)"
        r = s.get(URL, timeout=300)
        r.raise_for_status()
        tif.write_bytes(r.content)
        write_provenance(tif, source="FAO GLW4 cattle 2015 (dasymetric), Harvard Dataverse doi:10.7910/DVN/LHBICE",
                         url=URL, license="CC0 1.0")
    im = Image.open(tif)
    scale = im.tag_v2.get(33550)   # ModelPixelScale (dx, dy, 0)
    tie = im.tag_v2.get(33922)     # ModelTiepoint (i, j, k, x, y, z)
    arr = np.asarray(im, dtype="float64")
    dx, dy = scale[0], scale[1]
    x0, y0 = tie[3], tie[4]
    arr[(arr < 0) | ~np.isfinite(arr)] = 0
    polys = district_polygons()
    lon_min, lon_max, lat_min, lat_max = 88.0, 92.75, 20.55, 26.7
    c0, c1 = int((lon_min - x0) / dx), int((lon_max - x0) / dx) + 1
    r0, r1 = int((y0 - lat_max) / dy), int((y0 - lat_min) / dy) + 1
    totals: dict[str, float] = {}
    cells: dict[str, int] = {}
    for r in range(r0, r1):
        lat = y0 - (r + 0.5) * dy
        for c in range(c0, c1):
            lon = x0 + (c + 0.5) * dx
            v = arr[r, c]
            if v <= 0:
                continue
            for name, rings in polys:
                if any(inside(lon, lat, ring) for ring in rings):
                    totals[name] = totals.get(name, 0.0) + v
                    cells[name] = cells.get(name, 0) + 1
                    break
    area = pd.read_csv(RESEARCH / "bbs" / "intensity.csv")[["district", "total_area_000acre"]]
    df = pd.DataFrame({"district": list(totals), "cattle_head_2015": [round(v) for v in totals.values()],
                       "cells": [cells[k] for k in totals]}).sort_values("cattle_head_2015", ascending=False)
    df = df.merge(area, on="district", how="left")
    df["cattle_per_km2"] = (df["cattle_head_2015"] / (df["total_area_000acre"] * 1000 * 0.00404686)).round(1)
    df = df.drop(columns="total_area_000acre")
    df["source"] = "FAO GLW4 cattle 2015 (Gilbert et al. 2018), doi:10.7910/DVN/LHBICE, CC0"
    out = RESEARCH / "crops" / "cattle_by_district_glw4.csv"
    df.to_csv(out, index=False)
    print(f"pixel {dx:.4f} deg; {len(df)} districts; Bangladesh total {df['cattle_head_2015'].sum():,.0f} head")
    print(df.head(8)[["district", "cattle_head_2015", "cattle_per_km2"]].to_string(index=False))


if __name__ == "__main__":
    main()
