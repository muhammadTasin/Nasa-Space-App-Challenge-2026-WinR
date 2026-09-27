"""A land-type proxy (how high the land is, how often it is under water) for each upazila and pilot site.

Bangladesh's land types (high, medium high, medium low, low, very low land) are defined by normal monsoon flood
depth, and they decide which rotations are possible; SRDI's upazila guides give them but are not reachable from
here. This combines two open 30 m layers:
  * NASA NASADEM elevation (SRTM reprocessed; via Microsoft Planetary Computer, anonymous token)
  * JRC Global Surface Water 1984-2021 (Pekel et al. 2016): `occurrence` = % of clear Landsat views that saw
    water, `seasonality` = months with water in 2021
Landsat cannot see through monsoon cloud, so occurrence understates flooding at its peak; read it as "stays wet
into the dry season" (haor, beels, low land), not as flood depth. NASADEM's vertical error (a few metres, more
under trees and buildings) is large against Bangladesh's relief, so use elevation relative to the surroundings.

Output: research/soil/landtype_proxy_upazila.csv, research/soil/landtype_proxy_pilots.csv
        (GSW tiles cached in research/data/gsw/)
Usage : python research/acquire/landtype_proxy.py
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from rasterio.windows import from_bounds

from _common import DATA, RESEARCH, load_sites, out_dir, session, write_provenance

GSW = "https://storage.googleapis.com/global-surface-water/downloads2021/{layer}/{layer}_{tile}v1_4_2021.tif"
GSW_TILES = ["80E_30N", "90E_30N"]  # 80-90 E and 90-100 E, 20-30 N
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/nasadem"
STEP = 3  # read every layer at 90 m (a third of native) to keep 544 upazilas quick


def gsw_paths(s) -> dict[str, list]:
    d = out_dir("gsw")
    paths = {}
    for layer in ("occurrence", "seasonality"):
        for tile in GSW_TILES:
            p = d / f"{layer}_{tile}.tif"
            if not p.exists():
                url = GSW.format(layer=layer, tile=tile)
                with s.get(url, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(p, "wb") as fh:
                        for block in r.iter_content(1 << 20):
                            fh.write(block)
                write_provenance(p, source="JRC Global Surface Water v1.4 (1984-2021), Pekel et al. 2016",
                                 url=url, license="free with attribution (EC JRC / Google)")
            paths.setdefault(layer, []).append(p)
    return paths


def nasadem_hrefs(s) -> dict[str, str]:
    token = s.get(TOKEN, timeout=60).json()["token"]
    items = s.post(STAC, json={"collections": ["nasadem"], "bbox": [87.9, 20.5, 92.8, 26.8], "limit": 100},
                   timeout=120).json()["features"]
    return {f["id"]: f["assets"]["elevation"]["href"] + "?" + token for f in items}


def tiles_for(bounds, hrefs) -> list[str]:
    """NASADEM 1-degree tiles (named by their south-west corner) overlapping lon/lat bounds."""
    w, s_, e, n = bounds
    out = []
    for lat in range(math.floor(s_), math.floor(n) + 1):
        for lon in range(math.floor(w), math.floor(e) + 1):
            key = f"NASADEM_HGT_n{lat:02d}e{lon:03d}"
            if key in hrefs:
                out.append(hrefs[key])
    return out


def read_mosaic(paths, bounds, shape=None):
    """Read the lon/lat bounds from one or more EPSG:4326 rasters onto one grid (nearest): the first layer sets
    the grid at STEP times its native pixel, later layers pass that `shape` so every array lines up."""
    w, s_, e, n = bounds
    arrays, transform = [], None
    for p in paths:
        with rasterio.open(p) as src:
            if shape is None:
                res = abs(src.transform.a) * STEP
                shape = (max(1, round((n - s_) / res)), max(1, round((e - w) / res)))
            height, width = shape
            win = from_bounds(w, s_, e, n, src.transform)
            a = src.read(1, window=win, out_shape=(height, width), boundless=True, fill_value=src.nodata or 0,
                         resampling=rasterio.enums.Resampling.nearest)
            nodata = src.nodata
            transform = rasterio.transform.from_bounds(w, s_, e, n, width, height)
            a = a.astype("float32")
            if nodata is not None:
                a[a == nodata] = np.nan
            arrays.append(a)
    stack = np.stack(arrays)
    return np.nanmax(stack, axis=0) if len(arrays) > 1 else stack[0], transform


def stats(dem, occ, sea, mask) -> dict:
    d, o, se = dem[mask], occ[mask], sea[mask]
    o = np.where(np.isnan(o), 0, o)
    se = np.where(np.isnan(se), 0, se)
    d = d[np.isfinite(d)]
    return {"elev_p10_m": float(np.percentile(d, 10)) if len(d) else None,
            "elev_median_m": float(np.median(d)) if len(d) else None,
            "elev_p90_m": float(np.percentile(d, 90)) if len(d) else None,
            "share_never_water": round(float((o == 0).mean()), 3),
            "share_water_ge10pct": round(float((o >= 10).mean()), 3),
            "share_water_ge50pct": round(float((o >= 50).mean()), 3),
            "share_water_ge3months_2021": round(float((se >= 3).mean()), 3),
            "share_water_ge6months_2021": round(float((se >= 6).mean()), 3), "n_cells": int(mask.sum())}


def main() -> None:
    s = session()
    rasterio_env = rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
    gsw = gsw_paths(s)
    hrefs = nasadem_hrefs(s)
    upz = json.loads((DATA / "boundaries" / "BGD_ADM3_simplified.geojson").read_text(encoding="utf-8"))["features"]
    rows = []
    with rasterio_env:
        for k, f in enumerate(upz):
            geom = f["geometry"]
            coords = np.array([c for ring in (geom["coordinates"] if geom["type"] == "Polygon" else
                                              [r for poly in geom["coordinates"] for r in poly]) for c in ring])
            b = (coords[:, 0].min(), coords[:, 1].min(), coords[:, 0].max(), coords[:, 1].max())
            dem, t = read_mosaic(["/vsicurl/" + h for h in tiles_for(b, hrefs)], b)
            occ, _ = read_mosaic(gsw["occurrence"], b, shape=dem.shape)
            sea, _ = read_mosaic(gsw["seasonality"], b, shape=dem.shape)
            mask = features.geometry_mask([geom], out_shape=dem.shape, transform=t, invert=True)
            rows.append({"upazila": f["properties"]["shapeName"], "shape_id": f["properties"]["shapeID"],
                         **stats(dem, occ, sea, mask)})
            if k % 50 == 0:
                print(k, f["properties"]["shapeName"], rows[-1]["elev_median_m"], rows[-1]["share_water_ge10pct"],
                      flush=True)
        pil = []
        for p in load_sites("pilot_sites"):
            r_deg = 5 / 111.0  # 5 km around the point
            b = (p["lon"] - r_deg, p["lat"] - r_deg, p["lon"] + r_deg, p["lat"] + r_deg)
            dem, t = read_mosaic(["/vsicurl/" + h for h in tiles_for(b, hrefs)], b)
            occ, _ = read_mosaic(gsw["occurrence"], b, shape=dem.shape)
            sea, _ = read_mosaic(gsw["seasonality"], b, shape=dem.shape)
            yy, xx = np.mgrid[0:dem.shape[0], 0:dem.shape[1]]
            cy, cx = dem.shape[0] / 2, dem.shape[1] / 2
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= (dem.shape[0] / 2) ** 2
            st = stats(dem, occ, sea, mask)
            centre = dem[int(cy) - 1:int(cy) + 2, int(cx) - 1:int(cx) + 2]
            st["site_elev_m"] = float(np.nanmedian(centre))
            st["site_above_local_p10_m"] = round(st["site_elev_m"] - st["elev_p10_m"], 1)
            pil.append({"site_id": p["site_id"], **st})
    src = ("NASA NASADEM (Planetary Computer) and JRC Global Surface Water 1984-2021, read at 90 m; "
           "research/acquire/landtype_proxy.py")
    out = RESEARCH / "soil"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).round(3).assign(source=src).to_csv(out / "landtype_proxy_upazila.csv", index=False)
    pd.DataFrame(pil).round(3).assign(source=src).to_csv(out / "landtype_proxy_pilots.csv", index=False)
    print(pd.DataFrame(pil).drop(columns="n_cells").to_string())


if __name__ == "__main__":
    main()
