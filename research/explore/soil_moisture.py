"""How much water is left in the root zone for the crop after Aman, and how fast does it go? NASA GLDAS-2.2 root-zone
soil moisture (top metre, mm of water; Catchment model with GRACE data assimilation, 2003-2025) at the five pilots,
checked against NASA SMAP Level-4 root-zone moisture over the days both cover (Sep 2023 - Jun 2026).

  root-zone water on 20 October (relay sowing into standing Aman), 10 November (after an early Aman such as BRRI
  dhan71), 19 November (after BRRI dhan49) and 1 December: median and 10th-90th percentile over 23 seasons
  water lost between 10 and 19 November: what a nine-day earlier harvest keeps for lentil or mustard

Model soil water is not a field measurement; the number to take away is the drying rate and the difference between
dates, which the SMAP comparison checks.

Output: research/pilots/soil_moisture_rotation.csv
Usage : python research/explore/soil_moisture.py  (after research/acquire/gldas_da.py)
"""
from __future__ import annotations

import pandas as pd
from scipy import stats

from signals_common import PILOTS, RESEARCH
from _common import DATA

DATES = {"20_oct": (10, 20), "10_nov": (11, 10), "19_nov": (11, 19), "01_dec": (12, 1)}


def main() -> None:
    g = pd.read_parquet(DATA / "gldas" / "gldas_da_sites.parquet")
    g["date"] = pd.to_datetime(g["date"])
    sm = pd.read_parquet(DATA / "appeears" / "l4" / "smap_l4_daily.parquet")
    sm["t"] = pd.to_datetime(sm["t"])
    rows = []
    for sid in PILOTS:
        x = g[g["site_id"] == sid].set_index("date")["rootzone_mm"]
        rec = {"site_id": sid}
        vals = {k: pd.Series({y: x.get(pd.Timestamp(y, *md)) for y in range(2003, 2026)}) for k, md in DATES.items()}
        for k, v in vals.items():
            rec[f"{k}_median_mm"] = round(v.median())
            rec[f"{k}_p10_mm"], rec[f"{k}_p90_mm"] = round(v.quantile(0.1)), round(v.quantile(0.9))
        loss = vals["10_nov"] - vals["19_nov"]
        rec["lost_10_to_19_nov_median_mm"] = round(loss.median(), 1)
        rec["lost_10_to_19_nov_p10_p90_mm"] = f"{loss.quantile(0.1):.1f}-{loss.quantile(0.9):.1f}"
        s = sm[sm["ID"] == sid].set_index("t")["SPL4SMGP_008_Geophysical_Data_sm_rootzone"]
        both = pd.concat([x.rename("gldas"), s.rename("smap")], axis=1).dropna()
        rec["smap_overlap_days"] = len(both)
        rec["smap_spearman"] = round(stats.spearmanr(both["gldas"], both["smap"]).statistic, 2)
        nov = both[(both.index.month == 11)]
        rec["smap_nov_drying_m3m3_per_10d"] = round(nov["smap"].diff(10).mean(), 4)
        rec["gldas_nov_drying_mm_per_10d"] = round(nov["gldas"].diff(10).mean(), 1)
        rows.append(rec)
    d = pd.DataFrame(rows)
    d.to_csv(RESEARCH / "pilots" / "soil_moisture_rotation.csv", index=False)
    pd.set_option("display.width", 220)
    print(d[["site_id", "20_oct_median_mm", "10_nov_median_mm", "19_nov_median_mm", "01_dec_median_mm",
             "lost_10_to_19_nov_median_mm", "lost_10_to_19_nov_p10_p90_mm", "smap_overlap_days", "smap_spearman",
             "smap_nov_drying_m3m3_per_10d", "gldas_nov_drying_mm_per_10d"]].to_string(index=False))


if __name__ == "__main__":
    main()
