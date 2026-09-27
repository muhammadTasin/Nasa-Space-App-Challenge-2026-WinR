"""Rain so far this monsoon against normal, at each site, from three estimates, and whether they agree.

  imerg_late : this season from the IMERG Late run (research/acquire/imerg_nrt.py) against the Late run's own
               2001-2025 days at the same cell. Late has drifted dry against the gauge-adjusted Final run:
               Jun-Sep Late/Final stayed within 0.8-1.2 in 2001-2022 but fell to 0.58-0.64 at Tanore in
               2024-2025 (0.73-0.92 at the other pilots), so this estimate reads too dry now.
  imerg_adj  : this season's Late divided by the site's Late/Final ratio in Jun-Sep 2023-2025, against the Final
               run's 2001-2025 mean (POWER IMERG_PRECTOT is the Final run up to ~3 months ago).
  merra2     : NASA MERRA-2 corrected precipitation from POWER (PRECTOTCORR; its latest weeks come from NASA's
               near-real-time GEOS run, not the gauge-corrected reanalysis).

In late September 2026 these disagree (Tanore since 1 Jun: 50%, 71% and 107% of normal; ERA5 from Open-Meteo,
checked by hand, 75%), and BMD's station reports stopped reaching NOAA in August 2025. So `verdict` says "dry" or
"wet" only when every estimate does, and advice should say "uncertain" otherwise.

Output: research/pilots/rain_vs_normal.csv (one row per site and window)
Usage : python research/explore/rain_vs_normal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

RATIO_YEARS = (2023, 2025)  # recent Jun-Sep seasons where both Late and Final exist


def windows(last: pd.Timestamp) -> dict:
    """Since the monsoon's start, each month so far, and the last 30 days."""
    y = int(last.year)
    w = {"since 1 Jun": (pd.Timestamp(y, 6, 1), last), "last 30 days": (last - pd.DateOffset(days=29), last)}
    for m in range(6, last.month + 1):
        start = pd.Timestamp(y, m, 1)
        w[start.strftime("%b") + (" to date" if m == last.month else "")] = (start, min(start + pd.offsets.MonthEnd(0), last))
    return w


def same_days(s: pd.Series, a: pd.Timestamp, b: pd.Timestamp) -> pd.Series:
    """Totals over the month-day span a..b in every year of a daily series."""
    md = s.index.strftime("%m-%d")
    w = s[(md >= a.strftime("%m-%d")) & (md <= b.strftime("%m-%d"))]
    return w.groupby(w.index.year).sum()


def verdict(pcts: list) -> str:
    if all(p < 80 for p in pcts):
        return "dry"
    if all(p > 120 for p in pcts):
        return "wet"
    if all(80 <= p <= 120 for p in pcts):
        return "normal"
    return "uncertain (estimates disagree)"


def main() -> None:
    d = DATA / "imerg_nrt"
    now = pd.read_parquet(d / "imerg_daily_sites.parquet")
    base = pd.read_parquet(d / "imerg_late_baseline_sites.parquet")
    power = {sid: pd.read_parquet(DATA / "power" / "daily" / f"{sid}.parquet") for sid in now["site_id"].unique()}
    for p in power.values():
        p.index = pd.to_datetime(p.index)
    merra_last = min(p["PRECTOTCORR"].dropna().index.max() for p in power.values())
    last = pd.Timestamp(min(now["date"].max(), merra_last))  # one end date for every estimate
    wins = windows(last)
    rows = []
    for sid, g in now.groupby("site_id"):
        late = pd.concat([base[base["site_id"] == sid].set_index("date")["precip_mm"], g.set_index("date")["precip_mm"]])
        late = late[~late.index.duplicated(keep="last")]
        final, merra = power[sid]["IMERG_PRECTOT"].dropna(), power[sid]["PRECTOTCORR"].dropna()
        both = pd.concat([late.rename("late"), final.rename("final")], axis=1).dropna()
        both = both[(both.index.year >= RATIO_YEARS[0]) & (both.index.year <= RATIO_YEARS[1]) &
                    both.index.month.isin([6, 7, 8, 9])]
        ratio = both["late"].sum() / both["final"].sum()
        for name, (a, b) in wins.items():
            yl, yf, ym = same_days(late, a, b), same_days(final, a, b), same_days(merra, a, b)
            cur = yl.get(a.year)
            pct = {"imerg_late": 100 * cur / yl.loc[2001:2025].mean(),
                   "imerg_adj": 100 * cur / ratio / yf.loc[2001:2025].mean(),
                   "merra2": 100 * ym.get(a.year) / ym.loc[2001:2025].mean()}
            rows.append({"site_id": sid, "window": name, "from": a.date(), "to": b.date(),
                         "imerg_late_mm": round(cur, 1), "late_final_ratio": round(ratio, 2),
                         **{f"{k}_pct_of_normal": round(v) for k, v in pct.items()},
                         "imerg_late_years_drier_of_25": int((yl.loc[2001:2025] < cur).sum()),
                         "merra2_years_drier_of_25": int((ym.loc[2001:2025] < ym.get(a.year)).sum()),
                         "verdict": verdict(list(pct.values()))})
    out = pd.DataFrame(rows)
    path = RESEARCH / "pilots" / "rain_vs_normal.csv"
    out.to_csv(path, index=False)
    pd.set_option("display.width", 220)
    show = out[~out["site_id"].str.startswith("ADM2_") & out["window"].isin(["since 1 Jun", "last 30 days"])]
    print(f"as of {last:%Y-%m-%d}")
    print(show.drop(columns=["from", "to"]).to_string(index=False))
    print(out[out["window"] == "since 1 Jun"]["verdict"].value_counts().to_string())
    print(len(out), "rows ->", path.relative_to(RESEARCH.parent))


if __name__ == "__main__":
    main()
