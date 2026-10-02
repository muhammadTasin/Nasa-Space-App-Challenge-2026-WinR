"""What the fields actually did at the five pilots, crop years 2001-2025, seen by NASA MODIS (MOD13Q1 250 m NDVI,
the QA-filtered median of 9 x 9 pixels around each pilot point).

  crop cycles per year: growth peaks, the same method as first_look.py (agricultural year Nov-Oct)
  winter crop: the highest NDVI from 15 January to 15 March, after the Aman harvest (lentil, mustard, wheat, potato,
             Boro); 0.50 or more means winter crops cover most of the land around the point (Batiaghata's winter
             fallows read 0.31-0.34 in 2001-05, Tanore's Boro and Rabi fields 0.81-0.83 in 2020-24)
  low-green periods: 16-day composites from July to June with NDVI below 0.30, bare soil or standing water (in the
             haor this is mostly flood water), times 16 days

A 250 m pixel mixes fields, so these describe the landscape around each point; HLS 30 m maps would describe fields.

Output: research/pilots/field_cycles.csv (pilot x crop year)
Usage : python research/explore/field_cycles.py
"""
from __future__ import annotations

import pandas as pd

from first_look import crop_cycles
from signals_common import PILOTS, RESEARCH
from _common import DATA

WINTER_CROP_NDVI, LOW_GREEN_NDVI = 0.50, 0.30


def main() -> None:
    rows = []
    for sid in PILOTS:
        nd = pd.read_parquet(DATA / "ndvi" / "MOD13Q1" / f"{sid}.parquet")["ndvi_median_good"]
        nd.index = pd.to_datetime(nd.index)
        cycles = crop_cycles(sid)["per_year"]
        for y in range(2001, 2026):
            winter = nd.loc[f"{y + 1}-01-15":f"{y + 1}-03-15"]
            year = nd.loc[f"{y}-07-01":f"{y + 1}-06-30"]
            rows.append({"site_id": sid, "crop_year": f"{y}-{str(y + 1)[2:]}", "cycles_nov_oct": cycles.get(y + 1),
                         "winter_peak_ndvi": round(winter.max(), 3) if len(winter) else None,
                         "winter_crop_dominant": bool(winter.max() >= WINTER_CROP_NDVI) if len(winter) else None,
                         "low_green_days": int((year < LOW_GREEN_NDVI).sum() * 16) if len(year) >= 20 else None})
    d = pd.DataFrame(rows)
    d.to_csv(RESEARCH / "pilots" / "field_cycles.csv", index=False)
    d["y"] = d["crop_year"].str[:4].astype(int)
    first, last = d[d["y"] <= 2005], d[(d["y"] >= 2020) & (d["y"] <= 2024)]
    summ = pd.DataFrame({
        "cycles_2001_05": first.groupby("site_id")["cycles_nov_oct"].mean(),
        "cycles_2020_24": last.groupby("site_id")["cycles_nov_oct"].mean(),
        "winter_peak_2001_05": first.groupby("site_id")["winter_peak_ndvi"].mean(),
        "winter_peak_2020_24": last.groupby("site_id")["winter_peak_ndvi"].mean(),
        "winter_crop_share_2020_24": last.groupby("site_id")["winter_crop_dominant"].mean(),
        "low_green_days_2001_05": first.groupby("site_id")["low_green_days"].mean(),
        "low_green_days_2020_24": last.groupby("site_id")["low_green_days"].mean()}).round(2)
    pd.set_option("display.width", 200)
    print(summ.to_string())


if __name__ == "__main__":
    main()
