"""Daily NASA update for every upazila of Bangladesh.

NASA POWER, no login, a 0.5 degree grid (104 points over Bangladesh), about 3 days behind: rain, maximum and
minimum temperature, humidity, and root-zone and surface soil wetness. Each upazila takes the nearest grid point.
Rain and soil wetness are also compared with the same dates in each of the past 10 years.

GPM IMERG, 0.1 degree, 1 to 2 days behind: rain from research/data/imerg_nrt/imerg_daily_bd.parquet, refreshed by
`python research/acquire/imerg_nrt.py --days 10` (needs an Earthdata Login). Skipped when the file is missing or old.

Output: services/api/data/live/upazila_conditions.json (summary and one record per upazila), read by the API.
Usage : python research/live/daily_update.py [--imerg-parquet PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
UPAZILAS = ROOT / "research" / "sites" / "upazilas.csv"
DEFAULT_IMERG = ROOT / "research" / "data" / "imerg_nrt" / "imerg_daily_bd.parquet"
OUT = ROOT / "services" / "api" / "data" / "live" / "upazila_conditions.json"

POWER = "https://power.larc.nasa.gov/api/temporal/daily/regional"
BBOX = {"latitude-min": 20.5, "latitude-max": 26.7, "longitude-min": 88.0, "longitude-max": 92.7}
PARAMS = ["PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "GWETROOT", "GWETTOP"]
NORMAL_YEARS = 10
HOT_C = 35.0  # rice flowers start to fail at about 35 C
SOHRA = (25.27, 91.73)  # upstream of the Sunamganj haors, where the flash-flood trigger is read


def power_regional(param: str, start: date, end: date) -> dict:
    """{(lat, lon): {YYYYMMDD: value}} for one parameter; POWER allows one parameter per regional request."""
    q = {"parameters": param, "community": "AG", "start": f"{start:%Y%m%d}", "end": f"{end:%Y%m%d}", "format": "JSON", **BBOX}
    for attempt in range(4):
        try:
            r = requests.get(POWER, params=q, timeout=180)
            r.raise_for_status()
            feats = r.json()["features"]
            return {(round(f["geometry"]["coordinates"][1], 3), round(f["geometry"]["coordinates"][0], 3)):
                    f["properties"]["parameter"][param] for f in feats}
        except (requests.RequestException, KeyError, ValueError) as e:
            if attempt == 3:
                raise
            print(f"  POWER {param} retry after: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    return {}


def valid(series: dict, day: str):
    v = series.get(day)
    return None if v is None or v <= -998 else v


def rank_of(value: float, past: list[float]) -> int:
    """How many of the past years were lower than this year (0 to len(past))."""
    return sum(1 for p in past if p < value)


def status(rank: int, n: int, low: str, high: str) -> str:
    if n < 6:
        return "unknown"
    if rank <= n * .2:
        return low
    if rank >= n * .8:
        return high
    return "normal"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--imerg-parquet", type=Path, default=DEFAULT_IMERG)
    args = ap.parse_args()

    ups = list(csv.DictReader(open(UPAZILAS, encoding="utf-8")))
    today = date.today()
    start = today - timedelta(days=45)
    print(f"NASA POWER daily, {start} to {today}, all of Bangladesh")
    grid = {p: power_regional(p, start, today) for p in PARAMS}
    points = list(grid["PRECTOTCORR"])

    # the latest day with data for every parameter (sea points have no soil wetness, so look across all points)
    def last_day(p: str) -> str:
        return max(d for series in grid[p].values() for d, v in series.items() if v is not None and v > -998)
    latest = min(last_day(p) for p in PARAMS)
    latest_d = datetime.strptime(latest, "%Y%m%d").date()
    print(f"  latest complete day {latest_d} ({(today - latest_d).days} days behind)")

    # the same 30-day window in each of the past years, for rain and soil wetness
    print(f"Normals: the same window in {latest_d.year - NORMAL_YEARS}-{latest_d.year - 1}")
    past = {"PRECTOTCORR": {}, "GWETROOT": {}}
    for y in range(latest_d.year - NORMAL_YEARS, latest_d.year):
        try:
            end_y = latest_d.replace(year=y)
        except ValueError:  # 29 February
            end_y = latest_d.replace(year=y, day=28)
        for p in past:
            past[p][y] = power_regional(p, end_y - timedelta(days=29), end_y)

    def window(series: dict, end: date, n: int) -> list:
        return [valid(series, f"{end - timedelta(days=k):%Y%m%d}") for k in range(n)]

    def nearest(lat: float, lon: float):
        return min(points, key=lambda q: (q[0] - lat) ** 2 + ((q[1] - lon) * math.cos(math.radians(lat))) ** 2)

    # IMERG 0.1 degree rain, when the parquet is there and recent
    imerg = None
    if args.imerg_parquet.exists():
        import pandas as pd
        g = pd.read_parquet(args.imerg_parquet)
        g["date"] = pd.to_datetime(g["date"]).dt.date
        last = g["date"].max()
        if (today - last).days <= 7:
            g = g[g["date"] > last - timedelta(days=7)]
            imerg = {"last": last, "runs": g[g["date"] == last]["run"].iloc[0],
                     "cells": {(round(r.lat, 2), round(r.lon, 2), r.date): r.precip_mm for r in g.itertuples()}}
            print(f"GPM IMERG through {last} ({imerg['runs']})")
        else:
            print(f"GPM IMERG parquet is old (last {last}); skipped")
    else:
        print("GPM IMERG parquet not found; skipped (run research/acquire/imerg_nrt.py --days 10 with an Earthdata Login)")

    def imerg_cell(lat: float, lon: float):
        return round(math.floor(lat * 10) / 10 + .05, 2), round(math.floor(lon * 10) / 10 + .05, 2)

    def imerg_sum(lat: float, lon: float, n: int):
        if not imerg:
            return None
        cl, cn = imerg_cell(lat, lon)
        vals = [imerg["cells"].get((cl, cn, imerg["last"] - timedelta(days=k))) for k in range(n)]
        return None if any(v is None for v in vals) else round(sum(vals), 1)

    records = []
    for u in ups:
        lat, lon = float(u["lat"]), float(u["lon"])
        q = nearest(lat, lon)
        s = {p: grid[p][q] for p in PARAMS}
        rain = window(s["PRECTOTCORR"], latest_d, 30)
        tmax7 = window(s["T2M_MAX"], latest_d, 7)
        rain30 = sum(v for v in rain if v is not None)
        soil = valid(s["GWETROOT"], latest)
        past_rain = [sum(v for v in window(past["PRECTOTCORR"][y][q], latest_d.replace(year=y) if not (latest_d.month == 2 and latest_d.day == 29) else latest_d.replace(year=y, day=28), 30) if v is not None)
                     for y in past["PRECTOTCORR"]]
        past_soil = [v for y in past["GWETROOT"]
                     if (v := valid(past["GWETROOT"][y][q], f"{latest_d.replace(year=y) if not (latest_d.month == 2 and latest_d.day == 29) else latest_d.replace(year=y, day=28):%Y%m%d}")) is not None]
        mean_rain = sum(past_rain) / len(past_rain) if past_rain else None
        rec = {
            "id": u["site_id"], "name": u["name"], "district": u["district"], "lat": round(lat, 4), "lon": round(lon, 4),
            "power": {
                "date": f"{latest_d}", "gridLat": q[0], "gridLon": q[1],
                "rain1": round(rain[0], 1), "rain7": round(sum(v for v in rain[:7] if v is not None), 1), "rain30": round(rain30, 1),
                "rain30PctOfNormal": round(100 * rain30 / mean_rain) if mean_rain else None,
                "rain30Rank": rank_of(rain30, past_rain), "rainStatus": status(rank_of(rain30, past_rain), len(past_rain), "dry", "wet"),
                "tmax": round(tmax7[0], 1), "tmin": round(valid(s["T2M_MIN"], latest), 1), "rh": round(valid(s["RH2M"], latest)),
                "hotDays7": sum(1 for v in tmax7 if v is not None and v >= HOT_C),
                "soilRoot": round(soil, 3), "soilTop": round(valid(s["GWETTOP"], latest), 3),
                "soilRank": rank_of(soil, past_soil), "soilYears": len(past_soil),
                "soilStatus": status(rank_of(soil, past_soil), len(past_soil), "dry", "wet"),
            },
            "imerg": None,
        }
        if imerg:
            rec["imerg"] = {"date": f"{imerg['last']}", "run": imerg["runs"], "rain1": imerg_sum(lat, lon, 1),
                            "rain3": imerg_sum(lat, lon, 3), "rain7": imerg_sum(lat, lon, 7)}
        records.append(rec)

    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "upazilas": len(records),
        "districts": len({r["district"] for r in records}),
        "normalYears": f"{latest_d.year - NORMAL_YEARS}-{latest_d.year - 1}",
        "sources": [
            {"id": "power", "name": "NASA POWER daily (MERRA-2 / GEOS-IT, precipitation from GPM IMERG)", "latestDate": f"{latest_d}",
             "lagDays": (today - latest_d).days, "grid": "0.5 degree", "login": False},
            {"id": "imerg", "name": "NASA GPM IMERG daily (Early run for the newest day, then Late)",
             "latestDate": f"{imerg['last']}" if imerg else None, "lagDays": (today - imerg["last"]).days if imerg else None,
             "grid": "0.1 degree", "login": True},
        ],
        "haorUpstream": {"place": "Sohra, Meghalaya", "lat": SOHRA[0], "lon": SOHRA[1],
                         "imergRain3": imerg_sum(*SOHRA, 3), "date": f"{imerg['last']}" if imerg else None,
                         "watchMm": 200, "warningMm": 250},
        "method": {
            "rainStatus": "30-day rain against the same 30 days in each past year: dry if at or below the 2nd lowest of 10, wet if at or above the 8th",
            "soilStatus": "root-zone soil wetness (0 to 1) against the same date in each past year, with the same cut-offs",
            "hotDays7": f"days in the last 7 with a maximum of {HOT_C:.0f} C or more",
            "caution": ("POWER's newest weeks come from near-real-time inputs (GEOS-IT, IMERG Early/Late), which read drier "
                        "than the reprocessed archive used for past years, so dry labels are provisional until SMAP confirms them"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "upazilas": records}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dry = sum(r["power"]["soilStatus"] == "dry" for r in records)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(records)} upazilas, {dry} with drier soil than usual, "
          f"Sohra 3-day IMERG rain {summary['haorUpstream']['imergRain3']} mm")


if __name__ == "__main__":
    main()
