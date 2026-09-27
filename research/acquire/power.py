"""NASA POWER daily point data -> one parquet per site.  No login needed.

Two calls per site:
  * LST call  - MERRA-2 / CERES meteorology, radiation, soil wetness, ET (1991 -> today)
  * UTC call  - IMERG_PRECTOT (GPM IMERG precipitation at native 0.1 deg). POWER only
                serves IMERG with time-standard=UTC; with LST it silently returns -999.
Optional hourly T2M/RH2M/WS2M/SW for cattle heat-stress (THI) work.

Usage:
  python research/acquire/power.py --sites pilot_sites
  python research/acquire/power.py --sites districts --workers 3
  python research/acquire/power.py --sites pilot_sites --hourly-years 2024 2025
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from _common import load_sites, out_dir, session, write_provenance

URL = "https://power.larc.nasa.gov/api/temporal/{res}/point"
MET = ("T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,QV2M,WS2M,PS,ALLSKY_SFC_SW_DWN,"
       "PRECTOTCORR,GWETTOP,GWETROOT,GWETPROF,EVPTRNS,TS")
HOURLY = "T2M,RH2M,WS2M,ALLSKY_SFC_SW_DWN"
S = session()


def _get(res: str, lat: float, lon: float, params: str, start: str, end: str, tstd: str) -> tuple[pd.DataFrame, dict]:
    r = S.get(URL.format(res=res), timeout=300, params={
        "parameters": params, "community": "AG", "latitude": lat, "longitude": lon,
        "start": start, "end": end, "format": "JSON", "time-standard": tstd})
    r.raise_for_status()
    j = r.json()
    df = pd.DataFrame(j["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d%H" if res == "hourly" else "%Y%m%d")
    df = df.replace(j["header"].get("fill_value", -999.0), np.nan)
    return df, {"header": j["header"], "messages": j.get("messages"),
                "units": {k: v.get("units") for k, v in j.get("parameters", {}).items()}}


def daily(site: dict, start: str, force: bool) -> str:
    path = out_dir("power", "daily") / f"{site['site_id']}.parquet"
    if path.exists() and not force:
        return f"skip {site['site_id']} (cached)"
    end = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    met, m1 = _get("daily", site["lat"], site["lon"], MET, start, end, "LST")
    time.sleep(1)
    imerg, m2 = _get("daily", site["lat"], site["lon"], "IMERG_PRECTOT", "19980101", end, "UTC")
    df = met.join(imerg, how="outer")
    df.index.name = "date"
    df.to_parquet(path)
    last_imerg = imerg["IMERG_PRECTOT"].last_valid_index()
    write_provenance(path, source="NASA POWER daily point API (community=AG)", url=URL.format(res="daily"),
                     site=site, parameters=MET + ",IMERG_PRECTOT",
                     notes="MET in LST; IMERG_PRECTOT requested separately in UTC (POWER requirement).",
                     power_sources=m1["header"].get("sources"), power_api=m1["header"].get("api"),
                     units={**m1["units"], **m2["units"]})
    return f"ok   {site['site_id']}: {len(df)} days, IMERG to {last_imerg:%Y-%m-%d}"


def hourly(site: dict, years: list[int], force: bool) -> str:
    path = out_dir("power", "hourly") / f"{site['site_id']}_{years[0]}_{years[-1]}.parquet"
    if path.exists() and not force:
        return f"skip {site['site_id']} hourly (cached)"
    parts = []
    for y in years:
        end = min(date(y, 12, 31), date.today() - timedelta(days=5))
        df, meta = _get("hourly", site["lat"], site["lon"], HOURLY, f"{y}0101", end.strftime("%Y%m%d"), "LST")
        parts.append(df)
        time.sleep(1)
    df = pd.concat(parts)
    df.index.name = "time_lst"
    df.to_parquet(path)
    write_provenance(path, source="NASA POWER hourly point API (community=AG)", url=URL.format(res="hourly"),
                     site=site, parameters=HOURLY, time_standard="LST", units=meta["units"])
    return f"ok   {site['site_id']} hourly: {len(df)} hours"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default="pilot_sites")
    ap.add_argument("--start", default="19910101", help="first day for the MERRA-2 meteorology")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--hourly-years", type=int, nargs="*", default=[])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sites = load_sites(args.sites)
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(daily, s, args.start, args.force) for s in sites]
        if args.hourly_years:
            futs += [ex.submit(hourly, s, sorted(args.hourly_years), args.force) for s in sites]
        for f in cf.as_completed(futs):
            try:
                print(f.result(), flush=True)
            except Exception as e:  # keep going; report at the end
                print("FAIL", repr(e)[:300], flush=True)


if __name__ == "__main__":
    main()
