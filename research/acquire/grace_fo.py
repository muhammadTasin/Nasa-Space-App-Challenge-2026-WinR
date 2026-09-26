"""GRACE / GRACE-FO JPL mascon (RL06.3 v04, CRI-filtered 0.5 deg grid) -> Bangladesh water-storage
anomaly series.  Needs an Earthdata Login plus `pip install earthaccess xarray netCDF4`.

GRACE mascons are ~3 deg (~300 km) native, so this is regional context ("the whole north-west
is losing stored water"), never a farm-level number.  Say so on screen.

Usage: python research/acquire/grace_fo.py
"""
from __future__ import annotations

import numpy as np

from _common import load_dotenv, out_dir, write_provenance

SHORT_NAME = "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"
BOXES = {  # lat_min, lat_max, lon_min, lon_max
    "bangladesh": (20.5, 26.7, 88.0, 92.7),
    "nw_barind": (24.0, 25.5, 88.0, 89.5),
    "ne_haor": (24.2, 25.3, 90.5, 92.0),
}


def main() -> None:
    import earthaccess
    import pandas as pd
    import xarray as xr

    load_dotenv()
    earthaccess.login(strategy="environment")  # EARTHDATA_USERNAME / EARTHDATA_PASSWORD
    d = out_dir("grace")
    files = earthaccess.download(earthaccess.search_data(short_name=SHORT_NAME), local_path=str(d))
    ds = xr.open_dataset(files[0])
    lwe = ds["lwe_thickness"]  # cm equivalent water height, anomaly vs 2004.0-2009.999 mean
    out = {}
    for name, (la0, la1, lo0, lo1) in BOXES.items():
        sub = lwe.sel(lat=slice(la0, la1), lon=slice(lo0, lo1))  # dataset lon is 0..360; BD is <180 so fine
        w = np.cos(np.deg2rad(sub.lat))
        out[name] = sub.weighted(w).mean(("lat", "lon")).to_series()
    df = pd.DataFrame(out)
    df.index.name = "time"
    path = d / "grace_lwe_cm_bangladesh.csv"
    df.to_csv(path)
    # the monsoon swing (40-56 cm) dwarfs the trend, so remove each month's mean before fitting
    from scipy import stats
    yrs = (df.index - df.index[0]).days / 365.25
    trends = {k: float(stats.theilslopes(df[k] - df[k].groupby(df.index.month).transform("mean"), yrs).slope)
              for k in df}
    write_provenance(path, source=f"{SHORT_NAME} via earthaccess (PO.DAAC)", boxes=BOXES,
                     trend_cm_per_year=trends, caveat="~300 km native resolution; regional signal only")
    print(df.tail(), "\ntrend cm/yr:", {k: round(v, 2) for k, v in trends.items()})


if __name__ == "__main__":
    main()
