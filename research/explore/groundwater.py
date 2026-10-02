"""How fast is the water under the pilots falling? NASA GRACE/GRACE-FO (JPL mascons: total water storage over
Bangladesh, the north-west Barind and the north-east haor, 2002-2026) and NASA GLDAS-2.2 with GRACE data assimilation
(groundwater storage in the 25 km cell of each pilot and district, 2003 to mid-2026).

Trends per year, Theil-Sen over 2003-2025: the annual mean, and the March-May low when Boro is pumped hardest.
GRACE sees about 300 km, so a region's number describes the aquifer under the whole region; GLDAS spreads it to
25 km with a land model, which is finer but still not a well reading. BWDB's observation wells would check it.

Output: research/pilots/groundwater_trend.csv
Usage : python research/explore/groundwater.py  (after research/acquire/gldas_da.py)
"""
from __future__ import annotations

import pandas as pd
from scipy import stats

from signals_common import PILOTS, RESEARCH
from _common import DATA

YEARS = (2003, 2025)


def trend(s: pd.Series) -> tuple[float, float]:
    s = s.loc[YEARS[0]:YEARS[1]].dropna()
    return stats.theilslopes(s.values, s.index.values).slope, stats.kendalltau(s.index.values, s.values).pvalue


def main() -> None:
    rows = []
    g = pd.read_csv(DATA / "grace" / "grace_lwe_cm_bangladesh.csv", parse_dates=["time"]).set_index("time")
    for region in ("bangladesh", "nw_barind", "ne_haor"):
        s = g[region]
        annual = s.groupby(s.index.year).mean()[s.groupby(s.index.year).size() >= 8]
        dry = s[s.index.month.isin([3, 4, 5])].groupby(s[s.index.month.isin([3, 4, 5])].index.year).mean()
        (a, pa), (b, pb) = trend(annual), trend(dry)
        rows.append({"source": "GRACE/GRACE-FO total water storage", "area": region, "unit": "cm",
                     "annual_trend_per_year": round(a, 2), "annual_p": round(pa, 3),
                     "dry_season_trend_per_year": round(b, 2), "dry_season_p": round(pb, 3),
                     "change_2003_07_to_2021_25": round(annual.loc[2021:2025].mean() - annual.loc[2003:2007].mean(), 1)})
    d = pd.read_parquet(DATA / "gldas" / "gldas_da_sites.parquet")
    d["date"] = pd.to_datetime(d["date"])
    for sid, x in d.groupby("site_id"):
        x = x.set_index("date")["gws_mm"]
        annual = x.groupby(x.index.year).mean()
        dry = x[x.index.month.isin([3, 4, 5])].groupby(x[x.index.month.isin([3, 4, 5])].index.year).min()
        (a, pa), (b, pb) = trend(annual), trend(dry)
        rows.append({"source": "GLDAS-2.2 groundwater (GRACE-assimilated)", "area": sid, "unit": "mm",
                     "annual_trend_per_year": round(a, 1), "annual_p": round(pa, 3),
                     "dry_season_trend_per_year": round(b, 1), "dry_season_p": round(pb, 3),
                     "change_2003_07_to_2021_25": round(annual.loc[2021:2025].mean() - annual.loc[2003:2007].mean())})
    out = pd.DataFrame(rows)
    out.to_csv(RESEARCH / "pilots" / "groundwater_trend.csv", index=False)
    pd.set_option("display.width", 200)
    print(out[out["source"].str.startswith("GRACE")].to_string(index=False))
    print(out[out["area"].isin(PILOTS + ["UP_SOHRA"])].to_string(index=False))
    districts = out[out["area"].str.startswith("ADM2_")].sort_values("annual_trend_per_year")
    print("fastest-falling districts:", districts.head(8)[["area", "annual_trend_per_year"]].to_string(index=False))
    print(f"districts with a falling trend (p<0.05): {int(((districts['annual_trend_per_year'] < 0) & (districts['annual_p'] < 0.05)).sum())} of {len(districts)}")


if __name__ == "__main__":
    main()
