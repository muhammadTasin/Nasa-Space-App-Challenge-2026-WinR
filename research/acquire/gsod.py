"""NOAA GSOD daily station data for every Bangladesh station -> one parquet per station.  No login.

GSOD is NOAA's archive of the daily SYNOP reports BMD sends over the WMO network, so it is
BMD's own station data (Tmax, Tmin, mean temp, dew point, rain, wind) - free, but with gaps.
We use it to bias-correct NASA POWER and to check IMERG against gauges.

Checked 26 Sep 2026: Rajshahi's 2011-2020 monthly mean Tmax from GSOD is within 0.4 degC of
BMD's published 1991-2020 normals. The archive currently ends 24 Aug 2025; the BMD data portal
(dataportal.bmd.gov.bd) sells the most recent 3 months.

Caveats kept in the output:
  * MAX/MIN flagged "*" were derived from hourly reports, not a max/min thermometer.
  * PRCP flag "I" means the day's total is incomplete; GSOD rain is weaker than its temperatures.
  * The data API ignores units=metric, so conversion from degF / inches happens here.

Usage: python research/acquire/gsod.py [--start 1981-01-01] [--batch 5]
"""
from __future__ import annotations

import argparse
import csv
import io
import time
from datetime import date

import numpy as np
import pandas as pd

from _common import SITES, out_dir, session, write_provenance

HISTORY = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
API = "https://www.ncei.noaa.gov/access/services/data/v1"
S = session()


def bd_stations() -> pd.DataFrame:
    h = pd.read_csv(io.StringIO(S.get(HISTORY, timeout=300).text), dtype=str)
    bd = h[h["CTRY"] == "BG"].copy()
    bd["station"] = bd["USAF"] + bd["WBAN"]
    bd = bd.drop_duplicates("station")
    return bd[["station", "USAF", "STATION NAME", "LAT", "LON", "ELEV(M)", "BEGIN", "END"]]


def fetch(stations: list[str], start: str) -> pd.DataFrame:
    for attempt in range(5):
        try:
            r = S.get(API, timeout=600, params={
                "dataset": "global-summary-of-the-day", "stations": ",".join(stations), "startDate": start,
                "endDate": str(date.today()), "format": "csv", "includeAttributes": "true"})
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text), dtype={"STATION": str}) if r.text.strip() else pd.DataFrame()
        except Exception as e:  # NOAA drops connections under load; back off and retry
            print("  retry", attempt + 1, type(e).__name__, flush=True)
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"gave up on {stations}")


def to_metric(d: pd.DataFrame) -> pd.DataFrame:
    f2c = lambda s, miss: ((s.where(s < miss) - 32) * 5 / 9).round(2)
    out = pd.DataFrame({
        "date": pd.to_datetime(d["DATE"]),
        "tmax_c": f2c(d["MAX"], 9999), "tmax_from_hourly": d["MAX_ATTRIBUTES"].astype(str).str.strip().eq("*"),
        "tmin_c": f2c(d["MIN"], 9999), "tmin_from_hourly": d["MIN_ATTRIBUTES"].astype(str).str.strip().eq("*"),
        "tmean_c": f2c(d["TEMP"], 9999), "dewp_c": f2c(d["DEWP"], 9999),
        "prcp_mm": (d["PRCP"].where(d["PRCP"] < 99) * 25.4).round(1),
        "prcp_flag": d["PRCP_ATTRIBUTES"].astype(str).str.strip(),
        "wind_ms": (d["WDSP"].where(d["WDSP"] < 999) * 0.514444).round(2),
    })
    return out.set_index("date").sort_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1981-01-01")
    ap.add_argument("--batch", type=int, default=5)
    args = ap.parse_args()
    meta = bd_stations()
    d = out_dir("stations", "gsod")
    rows = []
    ids = meta["station"].tolist()
    for i in range(0, len(ids), args.batch):
        chunk = ids[i:i + args.batch]
        raw = fetch(chunk, args.start)
        got = raw.groupby("STATION") if len(raw) else []
        for sid, g in got:
            m = meta[meta["station"] == sid].iloc[0]
            df = to_metric(g)
            slug = "".join(c for c in m["STATION NAME"].title() if c.isalnum())
            path = d / f"{sid[:5]}_{slug}.parquet"
            df.to_parquet(path)
            write_provenance(path, source="NOAA NCEI Global Summary of the Day (GSOD)", url=API, station=sid,
                             wmo=sid[:5], name=m["STATION NAME"], lat=m["LAT"], lon=m["LON"],
                             units={"temp": "degC", "prcp": "mm", "wind": "m/s"},
                             notes="converted from degF/inches; see module docstring for flag meanings")
            rows.append({"station": sid, "wmo": sid[:5], "name": m["STATION NAME"].title(), "lat": float(m["LAT"]),
                         "lon": float(m["LON"]), "elev_m": m["ELEV(M)"], "first": f"{df.index.min():%Y-%m-%d}",
                         "last": f"{df.index.max():%Y-%m-%d}", "days": len(df),
                         "tmax_days": int(df["tmax_c"].notna().sum()), "prcp_days": int(df["prcp_mm"].notna().sum())})
        print(f"batch {i // args.batch + 1}: {len(raw)} rows for {raw['STATION'].nunique() if len(raw) else 0}"
              f"/{len(chunk)} stations", flush=True)
        time.sleep(2)
    rows.sort(key=lambda r: r["name"])
    with open(SITES / "bmd_stations_gsod.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    total = sum(r["days"] for r in rows)
    print(f"{len(rows)} stations with data, {total:,} station-days -> {d}")


if __name__ == "__main__":
    main()
