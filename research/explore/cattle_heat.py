"""Heat stress for the cows inside each rotation, at the five pilots, 2023-2025, from NASA POWER hourly temperature and
humidity (local solar time).

Temperature-humidity index (THI, NRC 1971), banded by the Livestock Weather Safety Index: below 75 normal, 75-78
alert, 79-83 danger, 84 and above emergency. Local zebu cattle tolerate more than crossbreds, so read the bands for
crossbred dairy cows. For each month: share of hours in each band, the nights that never cool below THI 72 (no
recovery), and the four coolest hours of the day, when cattle eat most willingly.

Output: research/pilots/cattle_heat.csv (pilot x month)
Usage : python research/explore/cattle_heat.py
"""
from __future__ import annotations

import pandas as pd

from first_look import thi
from signals_common import PILOTS, RESEARCH
from _common import DATA


def main() -> None:
    rows = []
    for sid in PILOTS:
        h = pd.read_parquet(DATA / "power" / "hourly" / f"{sid}_2023_2025.parquet")
        h.index = pd.to_datetime(h.index)
        h["thi"] = thi(h["T2M"], h["RH2M"])
        night = h[(h.index.hour >= 21) | (h.index.hour <= 5)]
        night_min = night["thi"].groupby((night.index - pd.Timedelta(hours=6)).date).min()  # 21:00-05:00 as one night
        night_min.index = pd.to_datetime(night_min.index)
        for m, g in h.groupby(h.index.month):
            coolest = g.groupby(g.index.hour)["thi"].mean().nsmallest(4).index.sort_values()
            nights = night_min[night_min.index.month == m]
            rows.append({"site_id": sid, "month": m, "mean_thi": round(g["thi"].mean(), 1),
                         "share_alert_75_78": round(((g["thi"] >= 75) & (g["thi"] < 79)).mean(), 3),
                         "share_danger_79_83": round(((g["thi"] >= 79) & (g["thi"] < 84)).mean(), 3),
                         "share_emergency_84": round((g["thi"] >= 84).mean(), 3),
                         "nights_without_relief_pct": round(100 * (nights >= 72).mean(), 1),
                         "coolest_hours": " ".join(f"{x:02d}:00" for x in coolest)})
    d = pd.DataFrame(rows)
    d.to_csv(RESEARCH / "pilots" / "cattle_heat.csv", index=False)
    pd.set_option("display.width", 200)
    hot = d[d["month"].isin([4, 5, 6, 7, 8, 9])]
    print(hot.pivot(index="site_id", columns="month", values="nights_without_relief_pct").to_string())
    print(hot.pivot(index="site_id", columns="month", values="share_danger_79_83").to_string())
    print(d[d["month"] == 5][["site_id", "coolest_hours"]].to_string(index=False))


if __name__ == "__main__":
    main()
