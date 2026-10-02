"""Groundwater and root-zone soil moisture from NASA GLDAS-2.2 (Catchment land model with GRACE data assimilation),
daily at 0.25 deg, through GES DISC's Giovanni time-series service.

GLDAS-2.2 CLSM assimilates GRACE/GRACE-FO water storage, so its groundwater follows the satellites while giving a
daily series for a 25 km cell instead of GRACE's ~300 km. Its root-zone moisture (top 1 m, mm of water) starts in
2003, twelve years before SMAP. Latency is about three months.

Needs an Earthdata Login (.env) with "NASA GESDISC DATA ARCHIVE" authorised.
Output: research/data/gldas/gldas_da_sites.parquet (site_id, date, gws_mm, rootzone_mm) for the pilots, the
        upstream point and the 64 district centroids
Usage : python research/acquire/gldas_da.py
"""
from __future__ import annotations

import time
from datetime import date

import pandas as pd

from _common import giovanni_series, load_dotenv, load_sites, out_dir, write_provenance

VARS = {"gws_mm": "GLDAS_CLSM025_DA1_D_2_2_GWS_tavg", "rootzone_mm": "GLDAS_CLSM025_DA1_D_2_2_SoilMoist_RZ_tavg"}


def main() -> None:
    load_dotenv()
    import earthaccess
    earthaccess.login(strategy="environment")
    s = earthaccess.get_requests_https_session()
    sites = load_sites("pilot_sites") + load_sites("upstream_points") + load_sites("districts")
    frames = []
    for x in sites:
        cols = {}
        for col, data in VARS.items():
            for attempt in range(4):
                try:
                    cols[col] = giovanni_series(s, data, x["lat"], x["lon"], "2003-01-01", str(date.today()))
                    break
                except Exception:  # transient server error: wait and retry
                    if attempt == 3:
                        raise
                    time.sleep(10 * (attempt + 1))
        df = pd.DataFrame(cols).rename_axis("date").reset_index()
        frames.append(df.assign(site_id=x["site_id"]))
        print(x["site_id"], len(df), "days,", f"groundwater {df['gws_mm'].iloc[0]:.0f} -> {df['gws_mm'].iloc[-1]:.0f} mm",
              flush=True)
    out = out_dir("gldas") / "gldas_da_sites.parquet"
    pd.concat(frames, ignore_index=True)[["site_id", "date", *VARS]].to_parquet(out, index=False)
    write_provenance(out, source="NASA GLDAS-2.2 CLSM with GRACE data assimilation, daily 0.25 deg "
                     "(GLDAS_CLSM025_DA1_D 2.2), GES DISC Giovanni time-series service", variables=VARS,
                     sites=len(sites), units="mm of water")


if __name__ == "__main__":
    main()
