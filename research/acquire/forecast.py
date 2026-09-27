"""Weather forecasts for the alert triggers, from Open-Meteo (free for non-commercial use, CC BY 4.0).

NASA's own GEOS-FP forecasts (NCCS OPeNDAP / datashare) did not answer from here, so this pulls the ECMWF and
NOAA model runs that Open-Meteo redistributes:
  deterministic : ECMWF IFS 0.25 deg, 16 days, hourly + daily (T, RH, rain, wind, sun, FAO ET0); NOAA GFS daily
                  as a second opinion
  ensemble      : ECMWF ENS, 51 members, 15 days -> probabilities (rain >= 20 / 50 mm, Tmax >= 36 deg C)
  seasonal      : 6 months, 51 members, summarised by month (ensemble median and spread)
  skill         : (--skill) archived ECMWF runs at 1-7 days' lead for the pilots since 2024, to score how well
                  a heat or heavy-rain alert would have been forecast against POWER / IMERG
Sites: the 5 pilots, the upstream Meghalaya point (haor flash floods) and the 64 district centroids.

Output: research/data/forecast/<run date>/*.parquet (+ .provenance.json)
Usage : python research/acquire/forecast.py [--skill]
"""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd

from _common import load_sites, out_dir, session, write_provenance

URL = {"forecast": "https://api.open-meteo.com/v1/forecast",
       "ensemble": "https://ensemble-api.open-meteo.com/v1/ensemble",
       "seasonal": "https://seasonal-api.open-meteo.com/v1/seasonal",
       "previous": "https://previous-runs-api.open-meteo.com/v1/forecast"}
HOURLY = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "wind_speed_10m",
          "shortwave_radiation", "et0_fao_evapotranspiration", "vapour_pressure_deficit"]
DAILY = ["temperature_2m_max", "temperature_2m_min", "relative_humidity_2m_max", "relative_humidity_2m_min",
         "precipitation_sum", "precipitation_hours", "wind_speed_10m_max", "shortwave_radiation_sum",
         "et0_fao_evapotranspiration"]
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0); ECMWF IFS/ENS open data and NOAA GFS"


def sites() -> list[dict]:
    rows = load_sites("pilot_sites") + load_sites("upstream_points") + load_sites("districts")
    return list({r["site_id"]: r for r in rows}.values())


def fetch(s, kind: str, locs: list[dict], params: dict, chunk: int = 25) -> list[tuple[dict, dict]]:
    """Call one API for many locations (Open-Meteo accepts comma-separated coordinates)."""
    out = []
    for i in range(0, len(locs), chunk):
        part = locs[i:i + chunk]
        p = {"latitude": ",".join(f"{x['lat']:.4f}" for x in part),
             "longitude": ",".join(f"{x['lon']:.4f}" for x in part), "timezone": "Asia/Dhaka", **params}
        r = s.get(URL[kind], params=p, timeout=180)
        r.raise_for_status()
        j = r.json()
        out += list(zip(part, j if isinstance(j, list) else [j]))
    return out


def frame(pairs, block: str) -> pd.DataFrame:
    dfs = []
    for site, j in pairs:
        d = pd.DataFrame(j[block])
        d.insert(0, "site_id", site["site_id"])
        dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    return df


def thi(t: pd.Series, rh: pd.Series) -> pd.Series:
    """Temperature-humidity index for cattle (NRC 1971), as in explore/first_look.py."""
    return (1.8 * t + 32) - (0.55 - 0.0055 * rh) * (1.8 * t - 26)


def members(df: pd.DataFrame, var: str) -> pd.DataFrame:
    return df[[c for c in df.columns if c == var or c.startswith(var + "_member")]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="store_true", help="also pull archived runs (1-7 day lead) for the pilots")
    args = ap.parse_args()
    s, locs = session(), sites()
    d = out_dir("forecast", f"{date.today():%Y%m%d}")

    # 1. deterministic ECMWF IFS, hourly and daily, plus NOAA GFS daily
    ec = fetch(s, "forecast", locs, {"models": "ecmwf_ifs025", "forecast_days": 16, "hourly": ",".join(HOURLY),
                                     "daily": ",".join(DAILY)})
    hourly, daily = frame(ec, "hourly"), frame(ec, "daily")
    hourly["thi"] = thi(hourly["temperature_2m"], hourly["relative_humidity_2m"]).round(1)
    daily = daily.merge(hourly.assign(time=hourly["time"].dt.normalize()).groupby(["site_id", "time"])["thi"]
                        .max().rename("thi_max").reset_index(), on=["site_id", "time"], how="left")
    gfs = frame(fetch(s, "forecast", locs, {"models": "gfs_seamless", "forecast_days": 16,
                                            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum"}), "daily")
    daily = daily.merge(gfs.rename(columns={c: f"gfs_{c}" for c in gfs.columns if c not in ("site_id", "time")}),
                        on=["site_id", "time"], how="left")

    # 2. ECMWF ensemble: probabilities per site and day
    en = frame(fetch(s, "ensemble", locs, {"models": "ecmwf_ifs025", "forecast_days": 15,
                                           "daily": "precipitation_sum,temperature_2m_max"}), "daily")
    rain, tmax = members(en, "precipitation_sum"), members(en, "temperature_2m_max")
    prob = en[["site_id", "time"]].copy()
    prob["n_members"] = rain.notna().sum(axis=1)
    prob["rain_median_mm"] = rain.median(axis=1).round(1)
    prob["rain_p90_mm"] = rain.quantile(0.9, axis=1).round(1)
    for mm in (20, 50, 100):
        prob[f"p_rain_ge_{mm}mm"] = (rain.ge(mm).sum(axis=1) / prob["n_members"]).round(2)
    prob["tmax_median"] = tmax.median(axis=1).round(1)
    for t in (36, 38, 40):
        prob[f"p_tmax_ge_{t}c"] = (tmax.ge(t).sum(axis=1) / prob["n_members"]).round(2)

    # 3. seasonal: monthly ensemble median and 10-90% range
    se = frame(fetch(s, "seasonal", locs, {"daily": "temperature_2m_max,temperature_2m_min,precipitation_sum"}),
               "daily")
    se["month"] = se["time"].dt.to_period("M").astype(str)
    monthly = []
    for var, how in (("precipitation_sum", "sum"), ("temperature_2m_max", "mean"), ("temperature_2m_min", "mean")):
        m = members(se, var)
        g = pd.concat([se[["site_id", "month"]], m], axis=1).groupby(["site_id", "month"]).agg(how)
        stat = pd.DataFrame({f"{var}_{how}_median": g.median(axis=1), f"{var}_{how}_p10": g.quantile(0.1, axis=1),
                             f"{var}_{how}_p90": g.quantile(0.9, axis=1)}).round(1)
        monthly.append(stat)
    seasonal = pd.concat(monthly, axis=1).reset_index()
    seasonal["days_in_forecast"] = se.groupby(["site_id", "month"]).size().values  # < 28: a partial month

    outputs = {"ecmwf_hourly": hourly, "ecmwf_daily": daily, "ensemble_probabilities": prob,
               "seasonal_monthly": seasonal}
    if args.skill:
        pilots = load_sites("pilot_sites") + load_sites("upstream_points")
        leads = [f"{v}_previous_day{k}" for v in ("temperature_2m", "precipitation") for k in range(1, 8)]
        sk = frame(fetch(s, "previous", pilots, {"models": "ecmwf_ifs025", "start_date": "2024-01-01",
                                                 "end_date": str(date.today()), "hourly": ",".join(
                                                     ["temperature_2m", "precipitation"] + leads)}), "hourly")
        outputs["skill_hourly_by_lead"] = sk
    for name, df in outputs.items():
        path = d / f"{name}.parquet"
        df.to_parquet(path, index=False)
        write_provenance(path, source=ATTRIBUTION, url=URL["forecast"], sites=len(df["site_id"].unique()),
                         rows=len(df), note="forecast issued on the retrieval date; times in Asia/Dhaka")
        print(f"{name:24s} {len(df):8,d} rows  {df['site_id'].nunique()} sites")


if __name__ == "__main__":
    main()
