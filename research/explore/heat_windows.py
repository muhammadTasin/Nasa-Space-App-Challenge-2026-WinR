"""Heat at the stages that decide yield, at the five pilots, seasons 1991-2025.

  Boro rice (BRRI dhan28) flowering, +-7 days: days at or above 35 C (spikelets fail) and the mean night minimum
  Aman rice flowering (BRRI dhan49 and dhan71), +-7 days: mean night minimum (warm nights cut rice yield)
  Wheat grain filling, the last 30 of 105 days, sown 20 November or 10 December: days above 30 C

NASA POWER daily temperatures, corrected month by month against the nearest BMD station (signals_common.py); crop
dates from the BRRI factsheets. Daily maxima stand in for the temperature at flowering time, so read the counts as
exposure, not as measured damage.

Output: research/pilots/heat_windows.csv (pilot x season), research/pilots/heat_trends.csv (pilot x measure)
Usage : python research/explore/heat_windows.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats

from signals_common import NEAREST_BMD, PILOTS, RESEARCH, around, brri_dates, corrected_power

warnings.filterwarnings("ignore", message=".*'generic' unit for NumPy timedelta.*")
SEASONS = range(1991, 2026)
MEASURES = ["boro_days_ge35", "boro_night_c", "aman49_night_c", "aman71_night_c", "wheat_20nov_days_gt30",
            "wheat_10dec_days_gt30"]


def main() -> None:
    rows = []
    for sid in PILOTS:
        p, bias = corrected_power(sid)
        for y in SEASONS:
            boro = around(p, brri_dates("BRRI dhan28", y - 1)["flowering"])
            a49 = around(p, brri_dates("BRRI dhan49", y)["flowering"])
            a71 = around(p, brri_dates("BRRI dhan71", y)["flowering"])
            fill = {d: p.loc[pd.Timestamp(y - 1, *d) + pd.Timedelta(days=75):pd.Timestamp(y - 1, *d) + pd.Timedelta(days=104)]
                    for d in ((11, 20), (12, 10))}
            rows.append({"site_id": sid, "season": y, "boro_flowering": brri_dates("BRRI dhan28", y - 1)["flowering"].date(),
                         "boro_days_ge35": int((boro["tmax"] >= 35).sum()), "boro_night_c": round(boro["tmin"].mean(), 2),
                         "aman49_night_c": round(a49["tmin"].mean(), 2), "aman71_night_c": round(a71["tmin"].mean(), 2),
                         "wheat_20nov_days_gt30": int((fill[(11, 20)]["tmax"] > 30).sum()),
                         "wheat_10dec_days_gt30": int((fill[(12, 10)]["tmax"] > 30).sum())})
        print(f"{sid}: corrected against BMD {NEAREST_BMD[sid][0]} ({NEAREST_BMD[sid][1]} km); "
              f"April Tmax bias {bias.loc[4, 'tmax']:+.1f} C, October Tmin bias {bias.loc[10, 'tmin']:+.1f} C")
    d = pd.DataFrame(rows)
    trends = []
    for (sid, m), s in ((k, d[d["site_id"] == k[0]].set_index("season")[k[1]]) for k in
                        ((sid, m) for sid in PILOTS for m in MEASURES)):
        ts = stats.theilslopes(s.values, s.index.values)
        tau = stats.kendalltau(s.index.values, s.values)
        trends.append({"site_id": sid, "measure": m, "mean_1991_2005": round(s.loc[1991:2005].mean(), 2),
                       "mean_2011_2025": round(s.loc[2011:2025].mean(), 2),
                       "trend_per_decade": round(ts.slope * 10, 2), "kendall_p": round(tau.pvalue, 3)})
    t = pd.DataFrame(trends)
    out = RESEARCH / "pilots"
    d.to_csv(out / "heat_windows.csv", index=False)
    t.to_csv(out / "heat_trends.csv", index=False)
    pd.set_option("display.width", 200)
    print(t.pivot(index="site_id", columns="measure", values="mean_2011_2025").round(1).to_string())
    print("\ntrend per decade (Kendall p < 0.05 marked *):")
    t["cell"] = t["trend_per_decade"].map("{:+.2f}".format) + np.where(t["kendall_p"] < 0.05, "*", " ")
    print(t.pivot(index="site_id", columns="measure", values="cell").to_string())


if __name__ == "__main__":
    main()
