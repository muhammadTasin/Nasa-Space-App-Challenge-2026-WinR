"""Near-real-time daily rain from NASA GPM IMERG (Late run, else Early run), cut to Bangladesh by OPeNDAP.

POWER's IMERG_PRECTOT arrives ~12 days late; the IMERG Late daily files (GPM_3IMERGDL, ~14 h latency) and Early
files (GPM_3IMERGDE, ~4 h) are at NASA GES DISC within about two days. Only a 0.1 deg window over Bangladesh and
the Meghalaya hills upstream of the haor is requested (50 x 65 cells), so each day is a few kB.

Compare it only with a baseline from the same run. The Late run has no gauge adjustment, and in the 2025 monsoon
(Jul-Aug) it caught 52% (Tanore) to 86% (Mithapukur) of the gauge-adjusted Final run that POWER's history
(1998-2025) is built from; POWER's recent weeks are Late. `--baseline` gets the Late run for whole years so
"rain so far against normal" uses one product. It asks NASA's Giovanni time-series service (listed for this
collection in CMR) for each site's cell: one call returns 25 years of days in ~5 s, where cutting the same days
out of the daily files over OPeNDAP takes ~4 h. The two give the same numbers (Tanore 2001-2002: 730 days, largest
difference 0.000002 mm).

Needs an Earthdata Login (.env, see .env.example) with "NASA GESDISC DATA ARCHIVE" authorised in the profile.
Output: research/data/imerg_nrt/days/<date>_<run>.csv (cache), imerg_daily_bd.parquet (grid),
        imerg_daily_sites.parquet (pilots, upstream point, district centroids; the cell containing each point);
        with --baseline: imerg_late_baseline_sites.parquet (the same cells)
Usage : python research/acquire/imerg_nrt.py [--days 120]
        python research/acquire/imerg_nrt.py --baseline 2001 2025
"""
from __future__ import annotations

import argparse
import math
import re
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from _common import load_dotenv, load_sites, out_dir, write_provenance

OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3"
GIOVANNI = "https://api.giovanni.earthdata.nasa.gov/timeseries"
RUNS = [("L", "GPM_3IMERGDL.07"), ("E", "GPM_3IMERGDE.07")]  # Late preferred, Early for the newest days
LON0, LON1, LAT0, LAT1 = 2679, 2728, 1104, 1168  # indices: 87.95-92.85 E, 20.45-26.85 N
LONS = -179.95 + 0.1 * np.arange(LON0, LON1 + 1)
LATS = -89.95 + 0.1 * np.arange(LAT0, LAT1 + 1)


def cell(lon: float, lat: float) -> tuple[int, int]:
    """Index of the 0.1 deg cell containing a point (a point on a cell edge goes east/north, as in POWER)."""
    return (int(math.floor((lon - (LONS[0] - 0.05)) / 0.1 + 1e-6)),
            int(math.floor((lat - (LATS[0] - 0.05)) / 0.1 + 1e-6)))


def sites() -> list[dict]:
    return load_sites("pilot_sites") + load_sites("upstream_points") + load_sites("districts")


def point_series(s, data: str, lat: float, lon: float, start: str, end: str) -> pd.Series:
    """A whole daily series at one point from the Giovanni time-series service (mm/day, NaN where undefined)."""
    r = s.get(GIOVANNI, params={"data": data, "location": f"[{lat},{lon}]",
                                "time": f"{start}T00:00:00/{end}T23:59:59"}, timeout=600)
    r.raise_for_status()
    head, _, body = r.text.partition("Timestamp (UTC),Data")
    undef = float(re.search(r"^undef,(.+)$", head, re.M).group(1))
    rows = [line.split(",") for line in body.strip().splitlines()]
    v = pd.Series([float(x[1]) for x in rows], index=pd.to_datetime([x[0][:10] for x in rows]))
    return v.where(v != undef)


def baseline(s, y0: int, y1: int) -> None:
    """Late-run daily series for whole years at the cell the near-real-time feed reads for each site (the cell
    centre is sent, so both read the same cell)."""
    rows = []
    for x in sites():
        i, j = cell(x["lon"], x["lat"])
        for attempt in range(4):
            try:
                v = point_series(s, "GPM_3IMERGDL_07_precipitation", round(float(LATS[j]), 2),
                                 round(float(LONS[i]), 2), f"{y0}-01-01", f"{y1}-12-31")
                break
            except Exception:  # transient server error: wait and retry
                if attempt == 3:
                    raise
                time.sleep(10 * (attempt + 1))
        rows.append(pd.DataFrame({"site_id": x["site_id"], "date": v.index, "precip_mm": v.to_numpy()}))
        print(x["site_id"], len(v), "days", f"{v.sum() / (y1 - y0 + 1):.0f} mm/yr", flush=True)
    out = out_dir("imerg_nrt") / "imerg_late_baseline_sites.parquet"
    pd.concat(rows, ignore_index=True).to_parquet(out, index=False)
    write_provenance(out, source="NASA GPM IMERG V07 Late run daily (GPM_3IMERGDL), GES DISC Giovanni "
                     "time-series service", url=GIOVANNI, years=f"{y0}-{y1}", sites=len(rows),
                     note="same product and cells as the near-real-time feed")


def fetch_day(s, day: date, runs=RUNS) -> tuple[np.ndarray, str] | None:
    for run, coll in runs:
        for version in ("V07C", "V07B"):
            name = f"3B-DAY-{run}.MS.MRG.3IMERG.{day:%Y%m%d}-S000000-E235959.{version}.nc4"
            url = f"{OPENDAP}/{coll}/{day:%Y/%m}/{name}.ascii?precipitation[0:0][{LON0}:{LON1}][{LAT0}:{LAT1}]"
            r = s.get(url, timeout=120)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            # one row per longitude, values along latitude; Hyrax labels rows "precipitation.precipitation[...]",
            # older DAP2 servers "[0][i],"
            rows = [line.split(",")[1:] for line in r.text.splitlines()
                    if line.startswith("precipitation.precipitation[") or re.match(r"^\[0\]\[\d+\],", line)]
            a = np.array(rows, dtype=float)  # [lon][lat]
            if a.shape != (LON1 - LON0 + 1, LAT1 - LAT0 + 1):
                raise ValueError(f"{name}: unexpected shape {a.shape}")
            a[a < 0] = np.nan  # fill value
            return a, f"{run}:{version}"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--baseline", type=int, nargs=2, metavar=("FIRST_YEAR", "LAST_YEAR"))
    args = ap.parse_args()
    load_dotenv()
    import earthaccess
    earthaccess.login(strategy="environment")
    s = earthaccess.get_requests_https_session()
    if args.baseline:
        baseline(s, *args.baseline)
        return
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
    rows = []
    for x in sites():
        i, j = cell(x["lon"], x["lat"])
        at = grid[(grid["lon"] == round(LONS[i], 2)) & (grid["lat"] == round(LATS[j], 2))]
        rows.append(at.assign(site_id=x["site_id"])[["site_id", "date", "run", "precip_mm"]])
    series = pd.concat(rows, ignore_index=True)
    series.to_parquet(d / "imerg_daily_sites.parquet", index=False)
    write_provenance(d / "imerg_daily_sites.parquet", source="the 0.1 deg cell of imerg_daily_bd.parquet containing "
                     "each site", sites=len(rows))
    print(f"{grid['date'].nunique()} days, {grid['date'].min():%Y-%m-%d} to {grid['date'].max():%Y-%m-%d};",
          grid.groupby("run")["date"].nunique().to_dict())


if __name__ == "__main__":
    main()
