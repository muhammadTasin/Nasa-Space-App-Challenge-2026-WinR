"""ISRIC SoilGrids 2.0 (250 m, CC BY 4.0) soil properties per site -> CSV.  No login needed.

This is the "local soil information" baseline until SRDI (Soil Resource Development Institute)
upazila soil guides / fertilizer-recommendation data are added.  ISRIC asks for fair use
(about 5 calls per minute), so calls are spaced out.

Usage: python research/acquire/soilgrids.py --sites pilot_sites
"""
from __future__ import annotations

import argparse
import time

import pandas as pd

from _common import load_sites, out_dir, session, write_provenance

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPS = ["soc", "nitrogen", "phh2o", "clay", "sand", "silt", "cec", "bdod"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]
VALUES = ["mean", "Q0.05", "Q0.95"]  # keep the uncertainty band, not just the mean


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default="pilot_sites")
    ap.add_argument("--pause", type=float, default=13.0)
    args = ap.parse_args()
    s = session()
    rows = []
    for site in load_sites(args.sites):
        params = [("lon", site["lon"]), ("lat", site["lat"])]
        params += [("property", p) for p in PROPS] + [("depth", d) for d in DEPTHS] + [("value", v) for v in VALUES]
        j = s.get(URL, params=params, timeout=180).json()
        for layer in j["properties"]["layers"]:
            um = layer["unit_measure"]
            for d in layer["depths"]:
                for v in VALUES:
                    raw = d["values"].get(v)
                    rows.append({"site_id": site["site_id"], "property": layer["name"], "depth": d["label"], "stat": v,
                                 "value": None if raw is None else raw / um["d_factor"], "units": um["target_units"]})
        print("ok", site["site_id"], flush=True)
        time.sleep(args.pause)
    df = pd.DataFrame(rows)
    path = out_dir("soil") / f"soilgrids_{args.sites}.csv"
    df.to_csv(path, index=False)
    write_provenance(path, source="ISRIC SoilGrids 2.0 REST API", url=URL, license="CC BY 4.0",
                     properties=PROPS, depths=DEPTHS, stats=VALUES)
    print(df[(df.stat == "mean") & (df.depth == "0-5cm")].pivot(index="site_id", columns="property", values="value").round(2))


if __name__ == "__main__":
    main()
