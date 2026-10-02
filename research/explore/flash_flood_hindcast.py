"""Can NASA rain over the Meghalaya hills flag the haor's pre-monsoon flash floods, and which Boro varieties are cut
before them?

Upstream rain: GPM IMERG (Final run, via NASA POWER) at the Sohra (Cherrapunji) cell on the Meghalaya plateau, and
at the Sunamganj district centroid and the Dharmapasha pilot, 15 March - 15 May of 2001-2025: the largest 3-day total
and when it fell. Labels: FFWC's Annual Flood Reports (research/floods/haor_flash_flood_years.csv): flash floods
before mid-May in 2010, 2017, 2018 (mid-May) and 2019 (short); none in 2014, 2020 and 2021; the other years are
not stated; FFWC's 2010 report adds 2004. With eight labelled years this tests thresholds, it does not calibrate a
warning: Sohra is among the wettest places on Earth, so a burst alone flags too many springs, and river gauges
(FFWC, on request) must confirm before any call goes out.

Escape: each Boro variety's harvest (BRRI seedbed midpoint + duration, and two weeks earlier, as haor farmers sow
early) against the first upstream 3-day burst at or above a threshold each season.

Output: research/floods/flash_flood_hindcast.csv (one row per year), flash_flood_thresholds.csv, boro_flood_escape.csv
Usage : python research/explore/flash_flood_hindcast.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from signals_common import RESEARCH, brri_dates, power

warnings.filterwarnings("ignore", message=".*'generic' unit for NumPy timedelta.*")
SITES = {"sohra": "UP_SOHRA", "sunamganj": "ADM2_Sunamganj", "dharmapasha": "SUN_DHARMAPASHA"}
YEARS = range(2001, 2026)
LABEL = {"yes": 1, "late": 1, "short": 1, "no": 0}
# a flood year named in a later report: FFWC 2010 calls that spring's pre-monsoon high water "similar to the year of 2004"
EXTRA_LABELS = {2004: ("yes", "yes (FFWC 2010 report compares 2010 with 2004)")}
THRESHOLDS = [100, 150, 200, 250]
BORO = ["BRRI dhan88", "BRRI dhan81", "BRRI dhan29", "BRRI dhan28", "BRRI dhan89", "BRRI dhan92"]


def season(r: pd.Series, y: int) -> pd.Series:
    return r.loc[f"{y}-03-15":f"{y}-05-15"]


def main() -> None:
    rain = {k: power(v)["IMERG_PRECTOT"] for k, v in SITES.items()}
    labels = pd.read_csv(RESEARCH / "floods" / "haor_flash_flood_years.csv").set_index("year")
    rows = []
    for y in YEARS:
        rec = {"year": y}
        for k, r in rain.items():
            s = season(r, y)
            r3 = s.rolling(3).sum()
            rec[f"{k}_max3_mm"] = round(r3.max(), 1)
            rec[f"{k}_max3_end"] = r3.idxmax().date()
            rec[f"{k}_total_mm"] = round(s.sum())
        lab = labels["flash_flood_before_15_may"].get(y)
        rec["ffwc_says"] = lab if isinstance(lab, str) else "no report"
        rec["flash_flood"] = LABEL.get(lab, np.nan) if isinstance(lab, str) else np.nan
        rows.append(rec)
    h = pd.DataFrame(rows).set_index("year")
    for y, (lab, why) in EXTRA_LABELS.items():
        h.loc[y, ["ffwc_says", "flash_flood"]] = [why, LABEL[lab]]
    yes = h.index[h["flash_flood"] == 1]
    no = h.index[h["flash_flood"] == 0]
    print(f"Sohra largest 3-day rain, 15 Mar-15 May: flood years {dict(h.loc[yes, 'sohra_max3_mm'])}; "
          f"no-flood years {dict(h.loc[no, 'sohra_max3_mm'])}")
    skill, first_burst = [], {}
    for thr in THRESHOLDS:
        burst = h["sohra_max3_mm"] >= thr
        early = pd.Series({y: bool((season(rain["sohra"], y).rolling(3).sum().loc[:f"{y}-04-15"] >= thr).any())
                           for y in YEARS})
        skill.append({"threshold_mm": thr, "flood_years_caught": f"{int(burst[yes].sum())} of {len(yes)}",
                      "no_flood_years_flagged": f"{int(burst[no].sum())} of {len(no)}",
                      "seasons_flagged": f"{int(burst.sum())} of {len(h)}",
                      "seasons_flagged_before_15_apr": f"{int(early.sum())} of {len(h)}"})
        first_burst[thr] = {}
        for y in YEARS:
            r3 = season(rain["sohra"], y).rolling(3).sum()
            hit = r3[r3 >= thr]
            first_burst[thr][y] = hit.index[0] if len(hit) else pd.NaT
        h[f"first_burst_{thr}mm"] = [d.date() if pd.notna(d) else None for d in first_burst[thr].values()]
    s = pd.DataFrame(skill)
    esc = []
    for thr in (THRESHOLDS[0], THRESHOLDS[-1]):
        for v in BORO:
            for shift, label in ((0, "BRRI calendar"), (-14, "two weeks early")):
                harvests = {y: brri_dates(v, y - 1, shift)["maturity"] for y in YEARS}
                caught = [y for y in YEARS if pd.notna(first_burst[thr][y]) and first_burst[thr][y] < harvests[y]]
                doy = int(np.median([d.dayofyear for d in harvests.values()]))
                esc.append({"burst_mm": thr, "variety": v, "sowing": label,
                            "median_harvest": (pd.Timestamp(2001, 1, 1) + pd.Timedelta(days=doy - 1)).strftime("%d %b"),
                            "seasons_with_burst": int(sum(pd.notna(d) for d in first_burst[thr].values())),
                            "burst_before_harvest": len(caught), "caught_years": " ".join(map(str, caught))})
    e = pd.DataFrame(esc)
    h = h.reset_index()
    out = RESEARCH / "floods"
    h.to_csv(out / "flash_flood_hindcast.csv", index=False)
    s.to_csv(out / "flash_flood_thresholds.csv", index=False)
    e.to_csv(out / "boro_flood_escape.csv", index=False)
    pd.set_option("display.width", 220)
    print(s.to_string(index=False))
    print(e[["burst_mm", "variety", "sowing", "median_harvest", "burst_before_harvest", "seasons_with_burst",
             "caught_years"]].to_string(index=False))


if __name__ == "__main__":
    main()
