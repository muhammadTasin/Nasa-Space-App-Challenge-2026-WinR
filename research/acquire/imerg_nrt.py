"""Near-real-time daily rain from NASA GPM IMERG (Late run, else Early run), cut to Bangladesh by OPeNDAP.

POWER's IMERG_PRECTOT arrives ~12 days late; the IMERG Late daily files (GPM_3IMERGDL, ~14 h latency) and Early
files (GPM_3IMERGDE, ~4 h) are at NASA GES DISC within about two days. Only a 0.1 deg window over Bangladesh and
the Meghalaya hills upstream of the haor is requested (50 x 65 cells), so each day is a few kB.

Needs an Earthdata Login (.env, see .env.example) with "NASA GESDISC DATA ARCHIVE" authorised in the profile.
Output: research/data/imerg_nrt/days/<date>_<run>.csv (cache), imerg_daily_bd.parquet (grid),
        imerg_daily_sites.parquet (pilots, upstream point, district centroids; nearest cell)
Usage : python research/acquire/imerg_nrt.py [--days 120]
"""
from __future__ import annotations

import argparse
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from _common import load_dotenv, load_sites, out_dir, write_provenance

OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3"
RUNS = [("L", "GPM_3IMERGDL.07"), ("E", "GPM_3IMERGDE.07")]  # Late preferred, Early for the newest days
LON0, LON1, LAT0, LAT1 = 2679, 2728, 1104, 1168  # indices: 87.95-92.85 E, 20.45-26.85 N
LONS = -179.95 + 0.1 * np.arange(LON0, LON1 + 1)
LATS = -89.95 + 0.1 * np.arange(LAT0, LAT1 + 1)


def fetch_day(s, day: date) -> tuple[np.ndarray, str] | None:
    for run, coll in RUNS:
        for version in ("V07C", "V07B"):
            name = f"3B-DAY-{run}.MS.MRG.3IMERG.{day:%Y%m%d}-S000000-E235959.{version}.nc4"
            url = f"{OPENDAP}/{coll}/{day:%Y/%m}/{name}.ascii?precipitation[0:0][{LON0}:{LON1}][{LAT0}:{LAT1}]"
            r = s.get(url, timeout=120)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            rows = [line.split(",")[1:] for line in r.text.splitlines() if re.match(r"^\[0\]\[\d+\],", line)]
            a = np.array(rows, dtype=float)  # [lon][lat]
            if a.shape != (LON1 - LON0 + 1, LAT1 - LAT0 + 1):
                raise ValueError(f"{name}: unexpected shape {a.shape}")
            a[a < 0] = np.nan  # fill value
            return a, f"{run}:{version}"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    args = ap.parse_args()
    load_dotenv()
    import earthaccess
    earthaccess.login(strategy="environment")
    s = earthaccess.get_requests_https_session()
    cache = out_dir("imerg_nrt", "days")
    frames = []
    for k in range(args.days, 0, -1):
        day = date.today() - timedelta(days=k)
        hit = sorted(cache.glob(f"{day:%Y%m%d}_*.csv"))
        late = [h for h in hit if "_L" in h.name]
        if late or (hit and k > 3):  # an Early day is re-fetched while a Late file may still appear
            path = (late or hit)[0]
        else:
            got = fetch_day(s, day)
            if got is None:
                print(day, "not yet published")
                continue
            a, run = got
            for h in hit:
                h.unlink()
            path = cache / f"{day:%Y%m%d}_{run.replace(':', '_')}.csv"
            lon, lat = np.meshgrid(LONS, LATS, indexing="ij")
            pd.DataFrame({"lat": lat.ravel().round(2), "lon": lon.ravel().round(2),
                          "precip_mm": a.ravel()}).to_csv(path, index=False)
            print(day, run, f"max {np.nanmax(a):.0f} mm")
        g = pd.read_csv(path)
        g.insert(0, "date", pd.Timestamp(day))
        g.insert(1, "run", path.stem.split("_", 1)[1])
        frames.append(g)
    grid = pd.concat(frames, ignore_index=True)
    d = out_dir("imerg_nrt")
    grid.to_parquet(d / "imerg_daily_bd.parquet", index=False)
    write_provenance(d / "imerg_daily_bd.parquet", source="NASA GPM IMERG V07 daily, Late run (Early where Late "
                     "is not out yet), GES DISC OPeNDAP", url=OPENDAP, window="87.95-92.85E, 20.45-26.85N, 0.1 deg",
                     days=int(grid["date"].nunique()), units="mm/day")
    sites = load_sites("pilot_sites") + load_sites("upstream_points") + load_sites("districts")
    rows = []
    for x in sites:
        i, j = int(round((x["lon"] - LONS[0]) / 0.1)), int(round((x["lat"] - LATS[0]) / 0.1))
        cell = grid[(grid["lon"] == round(LONS[i], 2)) & (grid["lat"] == round(LATS[j], 2))]
        rows.append(cell.assign(site_id=x["site_id"])[["site_id", "date", "run", "precip_mm"]])
    series = pd.concat(rows, ignore_index=True)
    series.to_parquet(d / "imerg_daily_sites.parquet", index=False)
    write_provenance(d / "imerg_daily_sites.parquet", source="nearest 0.1 deg cell of imerg_daily_bd.parquet",
                     sites=len(sites))
    print(f"{grid['date'].nunique()} days, {grid['date'].min():%Y-%m-%d} to {grid['date'].max():%Y-%m-%d};",
          grid.groupby("run")["date"].nunique().to_dict())


if __name__ == "__main__":
    main()
