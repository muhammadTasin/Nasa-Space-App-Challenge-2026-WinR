"""How far off are NASA POWER temperatures and IMERG rain at each pilot site, judged against the
nearest BMD station (NOAA GSOD copy)?  Output feeds the bias-correction step.

Per site: nearest station with enough overlap, distance, monthly mean Tmax/Tmin bias
(POWER minus station, same days only), daily Tmax correlation, and monthly rain agreement
(IMERG vs gauge, only months where the gauge has >= 25 complete days).

Usage: python research/explore/station_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, SITES, load_sites, out_dir  # noqa: E402

MIN_TMAX_DAYS = 1500  # about four full years of overlap
WINDOW = ("2011-01-01", "2025-08-24")  # common to every pilot station; POWER's bias drifts between decades


def km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


def main() -> None:
    st = pd.read_csv(SITES / "bmd_stations_gsod.csv", dtype={"station": str, "wmo": str})
    st = st[st["tmax_days"] >= MIN_TMAX_DAYS]
    res, rows = {}, []
    for site in load_sites("pilot_sites"):
        st = st.assign(dist_km=km(site["lat"], site["lon"], st["lat"], st["lon"]))
        near = st.nsmallest(1, "dist_km").iloc[0]
        g = pd.read_parquet(next((DATA / "stations" / "gsod").glob(f"{near['wmo']}_*.parquet")))
        p = pd.read_parquet(DATA / "power" / "daily" / f"{site['site_id']}.parquet")
        j = p.join(g, how="inner").loc[WINDOW[0]:WINDOW[1]]
        t = j[~j["tmax_from_hourly"] & j["tmax_c"].notna() & j["T2M_MAX"].notna()]
        n = j[~j["tmin_from_hourly"] & j["tmin_c"].notna() & j["T2M_MIN"].notna()]
        bias_max = (t["T2M_MAX"] - t["tmax_c"]).groupby(t.index.month).mean().round(1)
        bias_min = (n["T2M_MIN"] - n["tmin_c"]).groupby(n.index.month).mean().round(1)
        # rain: only full-day gauge totals (GSOD flags D, F, G = 4x6h, 2x12h or 1x24h reports),
        # then monthly totals where >= 25 such days exist
        r = j[j["prcp_mm"].notna() & j["prcp_flag"].isin(["D", "F", "G"]) & j["IMERG_PRECTOT"].notna()]
        mon = r.groupby(r.index.to_period("M")).agg(days=("prcp_mm", "size"), gauge=("prcp_mm", "sum"),
                                                    imerg=("IMERG_PRECTOT", "sum"))
        mon = mon[mon["days"] >= 25]
        rain = ({"months": int(len(mon)), "corr": round(float(mon["gauge"].corr(mon["imerg"])), 2),
                 "imerg_over_gauge": round(float(mon["imerg"].sum() / mon["gauge"].sum()), 2)}
                if len(mon) >= 12 else {"months": int(len(mon)), "note": "too few complete gauge months"})
        res[site["site_id"]] = {
            "station": f"{near['name']} ({near['wmo']})", "distance_km": round(float(near["dist_km"]), 1),
            "overlap": f"{t.index.min():%Y-%m} .. {t.index.max():%Y-%m}", "tmax_days": int(len(t)),
            "tmax_daily_corr": round(float(t["T2M_MAX"].corr(t["tmax_c"])), 2),
            "tmax_bias_by_month": bias_max.to_dict(), "tmin_bias_by_month": bias_min.to_dict(), "rain": rain}
        rows.append({"site": f"{site['name']}, {site['district']}", "station": res[site["site_id"]]["station"],
                     "km": round(float(near["dist_km"])), "tmax days": len(t),
                     "Tmax bias Apr": bias_max.get(4), "Tmax bias Jul": bias_max.get(7), "Tmax bias Jan": bias_max.get(1),
                     "Tmin bias Jan": bias_min.get(1), "Tmax corr": res[site["site_id"]]["tmax_daily_corr"],
                     "rain months": rain["months"], "IMERG/gauge": rain.get("imerg_over_gauge"),
                     "rain corr": rain.get("corr")})
    out = out_dir("explore")
    (out / "station_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
