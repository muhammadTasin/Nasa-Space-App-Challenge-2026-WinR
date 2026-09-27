"""MODIS 250 m 16-day NDVI (MOD13Q1 Terra, optionally MYD13Q1 Aqua) via the ORNL DAAC
MODIS/VIIRS Web Service.  No login needed.

For each site we pull a 2 km x 2 km window (km=1 -> 9x9 pixels) of NDVI and pixel_reliability,
keep all pixels in a long table, and write a per-date summary (median of good pixels).
The service caps each request at 10 composites, so a 2000->today series is ~60 requests
per band per site; keep --workers low to be polite.

Note on continuity: Terra/Aqua MODIS are ending (Aqua full products through Aug 2026) and
Suomi-NPP VIIRS delivery stops 1 Nov 2026.  For anything operational use VIIRS on NOAA-20/21
(VJ113A1 / VJ213A1) via AppEEARS - see appeears_points.py.  MODIS stays the 2000-2025 baseline.

Usage: python research/acquire/ndvi_modis.py --sites pilot_sites [--products MOD13Q1 MYD13Q1]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf

import numpy as np
import pandas as pd

from _common import load_sites, out_dir, session, write_provenance

API = "https://modis.ornl.gov/rst/api/v1"
H = {"Accept": "application/json"}
BANDS = {"ndvi": "250m_16_days_NDVI", "rel": "250m_16_days_pixel_reliability"}
S = session()


def dates(product: str, lat: float, lon: float) -> list[str]:
    r = S.get(f"{API}/{product}/dates", params={"latitude": lat, "longitude": lon}, headers=H, timeout=120)
    r.raise_for_status()
    return [d["modis_date"] for d in r.json()["dates"]]


def chunk(product: str, band: str, lat: float, lon: float, d0: str, d1: str, km: int) -> list[dict]:
    r = S.get(f"{API}/{product}/subset", headers=H, timeout=300, params={
        "latitude": lat, "longitude": lon, "band": band, "startDate": d0, "endDate": d1,
        "kmAboveBelow": km, "kmLeftRight": km})
    r.raise_for_status()
    j = r.json()
    return [{"date": s["calendar_date"], "band": band, "pixel": i, "value": v, "scale": j.get("scale")}
            for s in j["subset"] for i, v in enumerate(s["data"])]


def site_series(site: dict, product: str, km: int, workers: int, force: bool) -> str:
    path = out_dir("ndvi", product) / f"{site['site_id']}.parquet"
    if path.exists() and not force:
        return f"skip {site['site_id']} {product} (cached)"
    ds = dates(product, site["lat"], site["lon"])
    jobs = [(band, ds[i], ds[min(i + 9, len(ds) - 1)]) for band in BANDS.values() for i in range(0, len(ds), 10)]
    rows: list[dict] = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for part in ex.map(lambda j: chunk(product, j[0], site["lat"], site["lon"], j[1], j[2], km), jobs):
            rows.extend(part)
    long = pd.DataFrame(rows)
    long["date"] = pd.to_datetime(long["date"])
    wide = long.pivot_table(index=["date", "pixel"], columns="band", values="value").reset_index()
    wide = wide.rename(columns={BANDS["ndvi"]: "ndvi_raw", BANDS["rel"]: "reliability"})
    wide["ndvi"] = wide["ndvi_raw"].where(wide["ndvi_raw"] > -3000) * 0.0001
    good = wide[wide["reliability"].isin([0, 1])]  # 0 good, 1 marginal; 2 snow, 3 cloudy, -1 fill
    summary = pd.DataFrame({
        "ndvi_median_good": good.groupby("date")["ndvi"].median(),
        "n_good": good.groupby("date")["ndvi"].count(),
        "ndvi_median_all": wide.groupby("date")["ndvi"].median(),
        "n_pixels": wide.groupby("date")["ndvi"].size(),
    })
    summary.to_parquet(path)
    wide.to_parquet(path.with_name(f"{site['site_id']}_pixels.parquet"))
    write_provenance(path, source=f"{product} v061 via ORNL DAAC MODIS/VIIRS Web Service", url=f"{API}/{product}/subset",
                     site=site, window_km=km, bands=list(BANDS.values()), scale=0.0001,
                     qa_rule="median of pixels with pixel_reliability in {0,1}")
    return (f"ok   {site['site_id']} {product}: {len(summary)} composites "
            f"{summary.index.min():%Y-%m-%d}..{summary.index.max():%Y-%m-%d}, "
            f"{np.round(summary['n_good'].sum() / max(1, summary['n_pixels'].sum()) * 100, 1)}% good pixels")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default="pilot_sites")
    ap.add_argument("--products", nargs="+", default=["MOD13Q1"])
    ap.add_argument("--km", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    for product in args.products:
        for site in load_sites(args.sites):
            try:
                print(site_series(site, product, args.km, args.workers, args.force), flush=True)
            except Exception as e:
                print("FAIL", site["site_id"], product, repr(e)[:300], flush=True)


if __name__ == "__main__":
    main()
