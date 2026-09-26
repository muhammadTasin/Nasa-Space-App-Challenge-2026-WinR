"""First look: is the 'field shift' visible in the cached NASA data?  EXPLORATORY ONLY.

Single grid cell per site (MERRA-2 0.5 deg for temperature/soil wetness, IMERG 0.1 deg for rain),
not yet checked against BMD station records.  Every definition used is printed with the result
so nothing is hidden.  Writes research/data/explore/first_look.json + CSVs for charts.

Usage: python research/explore/first_look.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal, stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, load_sites, out_dir  # noqa: E402

P1, P2 = (1991, 2005), (2011, 2025)  # two 15-year periods with a 5-year gap
# Station check for the reanalysis cell. Rajshahi city is ~25 km from the Tanore cell centre.
BMD_NORMALS_TMAX = {"RAJ_TANORE": {"station": "Rajshahi (BMD)", "Mar": 33.0, "Apr": 35.8, "May": 35.3,
                                   "source": "BMD 1991-2020 normals as tabulated on en.wikipedia.org/wiki/Rajshahi"}}


def load(site_id: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / "power" / "daily" / f"{site_id}.parquet")


def compare(yearly: pd.Series, p1=P1, p2=P2) -> dict:
    a = yearly.loc[p1[0]:p1[1]].dropna()
    b = yearly.loc[p2[0]:p2[1]].dropna()
    ts = stats.theilslopes(yearly.dropna().values, yearly.dropna().index.values)
    return {"p1": f"{p1[0]}-{p1[1]}", "p1_mean": round(float(a.mean()), 2),
            "p2": f"{p2[0]}-{p2[1]}", "p2_mean": round(float(b.mean()), 2),
            "change": round(float(b.mean() - a.mean()), 2),
            "mann_whitney_p": round(float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue), 4),
            "theil_sen_per_decade": round(float(ts.slope * 10), 3)}


def hot_days(df: pd.DataFrame, thr: float) -> pd.Series:
    """Days with Tmax >= thr between 15 Mar and 15 May (Boro flowering / grain fill)."""
    w = df[(df.index.month.isin([3, 4, 5])) & ~((df.index.month == 3) & (df.index.day < 15))
           & ~((df.index.month == 5) & (df.index.day > 15))]
    return (w["T2M_MAX"] >= thr).groupby(w.index.year).sum().loc[1991:2025]


def onset_lm(rain: pd.Series, year: int) -> float:
    """Rainy-season onset, day-of-year (Liebmann & Marengo 2001): the day after the minimum of the
    cumulative daily-rain anomaly (vs the 2001-2025 mean daily rain), searched 1 Apr - 31 Aug."""
    clim = rain.loc["2001":"2025"].mean()
    s = rain.loc[f"{year}-04-01":f"{year}-08-31"].fillna(0.0) - clim
    return float(s.cumsum().idxmin().dayofyear + 1)


def onset(rain: pd.Series, year: int, thr: float = 30.0) -> float | None:
    """Threshold onset, day-of-year.  First day from 15 May with >= thr mm over 5 days
    and >= 3 wet days (>= 1 mm), NOT followed by 10+ consecutive dry days in the next 30 days.
    Kept only as a cautionary baseline: pre-monsoon storms trigger it almost at once."""
    r = rain.loc[f"{year}-05-15":f"{year}-09-30"].fillna(0.0).values
    for i in range(len(r) - 35):
        win = r[i:i + 5]
        if win.sum() >= thr and (win >= 1).sum() >= 3:
            nxt = (r[i + 5:i + 35] < 1).astype(int)
            longest = max((len(s) for s in "".join(map(str, nxt)).split("0")), default=0)
            if longest < 10:
                return float(pd.Timestamp(f"{year}-05-15").dayofyear + i)
    return None


def season_total(rain: pd.Series, months: list[int], shift_year_for: tuple = ()) -> pd.Series:
    r = rain[rain.index.month.isin(months)]
    yr = r.index.year + np.where(np.isin(r.index.month, shift_year_for), 1, 0)
    return r.groupby(yr).sum(min_count=20)


def thi(t: pd.Series, rh: pd.Series) -> pd.Series:
    """NRC (1971) temperature-humidity index used for cattle heat stress."""
    return (1.8 * t + 32) - (0.55 - 0.0055 * rh) * (1.8 * t - 26)


def crop_cycles(site_id: str) -> dict | None:
    """Count NDVI growth peaks per agricultural year (Nov-Oct) from MODIS MOD13Q1."""
    f = DATA / "ndvi" / "MOD13Q1" / f"{site_id}.parquet"
    if not f.exists():
        return None
    s = pd.read_parquet(f)["ndvi_median_good"].resample("8D").mean().interpolate(limit=4)
    sm = pd.Series(signal.savgol_filter(s.bfill().ffill().values, 7, 2), index=s.index)
    peaks, _ = signal.find_peaks(sm.values, prominence=0.08, height=0.35, distance=6)
    pk = sm.index[peaks]
    agyear = pk.year + (pk.month >= 11)
    per_year = pd.Series(1, index=agyear).groupby(level=0).sum().reindex(range(2001, 2026), fill_value=0)
    return {"definition": "Savitzky-Golay(7,2) smoothed 8-day NDVI; peaks with height>=0.35, prominence>=0.08, "
                          ">=48 days apart; agricultural year Nov-Oct",
            "cycles_2001_2005": round(float(per_year.loc[2001:2005].mean()), 2),
            "cycles_2021_2025": round(float(per_year.loc[2021:2025].mean()), 2),
            "per_year": per_year.to_dict()}


def main() -> None:
    out = out_dir("explore")
    res: dict = {"caveat": "Exploratory. One grid cell per site; reanalysis (MERRA-2) and satellite (IMERG, MODIS) "
                           "values, not yet validated against BMD stations.", "sites": {}}
    heat_rows, onset_rows, monsoon_rows = [], [], []
    for site in load_sites("pilot_sites"):
        sid = site["site_id"]
        df = load(sid)
        r: dict = {"name": f"{site['name']}, {site['district']}", "stress": site["stress"]}
        for thr in (35, 33):
            hd = hot_days(df, thr)
            r[f"hot_days_tmax{thr}_15mar_15may"] = compare(hd)
            if thr == 35:
                heat_rows += [{"site_id": sid, "year": y, "hot_days": int(v)} for y, v in hd.items()]
        tmin = df["T2M_MIN"].groupby(df.index.year).mean().loc[1991:2025]
        r["annual_mean_tmin_c"] = compare(tmin)
        rain = df["IMERG_PRECTOT"]
        on_s = pd.Series({y: onset_lm(rain, y) for y in range(2001, 2026)})
        r["onset_liebmann_doy"] = {**compare(on_s, (2001, 2012), (2013, 2025)),
                                   "iqr_days": float(on_s.quantile(.75) - on_s.quantile(.25)),
                                   "definition": " ".join(onset_lm.__doc__.split())}
        thr_on = pd.Series({y: onset(rain, y) for y in range(1999, 2026)}, dtype=float)
        r["onset_threshold_doy_cautionary"] = {**compare(thr_on, (1999, 2011), (2012, 2025)),
                                               "definition": " ".join(onset.__doc__.split())}
        onset_rows += [{"site_id": sid, "year": y, "onset_doy_liebmann": v} for y, v in on_s.items()]
        mons = season_total(rain, [6, 7, 8, 9]).loc[1999:2025]
        monsoon_rows += [{"site_id": sid, "year": y, "jun_sep_mm": round(float(v), 1)} for y, v in mons.items()]
        if sid in BMD_NORMALS_TMAX:
            mm = df.loc["1991":"2020", "T2M_MAX"].groupby(df.loc["1991":"2020"].index.month).mean()
            r["tmax_bias_vs_bmd"] = {"station": BMD_NORMALS_TMAX[sid]["station"],
                                     "source": BMD_NORMALS_TMAX[sid]["source"],
                                     **{m: {"power": round(float(mm[i]), 1), "bmd": v,
                                            "bias": round(float(mm[i]) - v, 1)}
                                        for m, i, v in (("Mar", 3, BMD_NORMALS_TMAX[sid]["Mar"]),
                                                        ("Apr", 4, BMD_NORMALS_TMAX[sid]["Apr"]),
                                                        ("May", 5, BMD_NORMALS_TMAX[sid]["May"]))}}
        r["rain_premonsoon_mar_may_mm"] = compare(season_total(rain, [3, 4, 5]).loc[1999:2025], (1999, 2011), (2012, 2025))
        r["rain_monsoon_jun_sep_mm"] = compare(season_total(rain, [6, 7, 8, 9]).loc[1999:2025], (1999, 2011), (2012, 2025))
        r["rain_rabi_nov_mar_mm"] = compare(season_total(rain, [11, 12, 1, 2, 3], (11, 12)).loc[2000:2025],
                                            (2000, 2012), (2013, 2025))
        gw = df["GWETROOT"][df.index.month.isin([12, 1, 2, 3])]
        r["rabi_rootzone_wetness_dec_mar"] = compare(
            gw.groupby(gw.index.year + (gw.index.month == 12)).mean().loc[1992:2025], (1992, 2005), (2011, 2025))
        t = thi(df["T2M"], df["RH2M"])
        r["cattle_days_daily_mean_thi_ge_78"] = compare((t >= 78).groupby(t.index.year).sum().loc[1991:2025])
        cyc = crop_cycles(sid)
        if cyc:
            r["ndvi_crop_cycles_per_year"] = cyc
        res["sites"][sid] = r
        print(sid, json.dumps({k: v for k, v in r.items() if k != "ndvi_crop_cycles_per_year"}, ensure_ascii=False)[:1500], "\n")

    # Cattle, hourly: coolest hours in the April 2024 heatwave at the dairy site
    hp = DATA / "power" / "hourly" / "SIR_ULLAHPARA_2023_2025.parquet"
    if hp.exists():
        h = pd.read_parquet(hp)
        h["THI"] = thi(h["T2M"], h["RH2M"])
        apr = h.loc["2024-04-01":"2024-04-30"]
        prof = apr.groupby(apr.index.hour)["THI"].mean().round(1)
        res["cattle_hourly_ullahpara_apr2024"] = {
            "share_hours_thi_ge_78": round(float((apr["THI"] >= 78).mean()), 3),
            "days_where_night_min_thi_stays_ge_72": int((apr["THI"].resample("D").min() >= 72).sum()),
            "mean_thi_by_hour_lst": prof.to_dict(),
            "coolest_4_hours_lst": sorted(prof.nsmallest(4).index.tolist())}
    # Haor flash-flood trigger: upstream Meghalaya rain (Sohra) vs local, 15 Mar - 15 May
    up = load("UP_SOHRA")["IMERG_PRECTOT"]
    loc = load("SUN_DHARMAPASHA")["IMERG_PRECTOT"]
    ff = []
    for y in range(1999, 2026):
        for name, s in (("upstream_sohra", up), ("local_dharmapasha", loc)):
            w = s.loc[f"{y}-03-15":f"{y}-05-15"].rolling(3).sum()
            ff.append({"year": y, "point": name, "max_3day_mm": round(float(w.max()), 1),
                       "date_of_max": f"{w.idxmax():%Y-%m-%d}"})
    ffd = pd.DataFrame(ff)
    upd = ffd[ffd.point == "upstream_sohra"].set_index("year")
    res["haor_flash_flood_trigger"] = {
        "definition": "max 3-day IMERG rainfall between 15 Mar and 15 May",
        "upstream_rank_of_2017": int(upd["max_3day_mm"].rank(ascending=False).loc[2017]),
        "upstream_2017": upd.loc[2017].to_dict(), "upstream_2022": upd.loc[2022].to_dict(),
        "upstream_median_mm": float(upd["max_3day_mm"].median()),
        "top5_upstream_years": upd["max_3day_mm"].nlargest(5).to_dict()}
    ffd.to_csv(out / "haor_trigger.csv", index=False)
    pd.DataFrame(heat_rows).to_csv(out / "hot_days.csv", index=False)
    pd.DataFrame(onset_rows).to_csv(out / "onset.csv", index=False)
    pd.DataFrame(monsoon_rows).to_csv(out / "monsoon_rain.csv", index=False)
    (out / "first_look.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in res if k.startswith(("cattle_hourly", "haor"))}, indent=1, default=str))


if __name__ == "__main__":
    main()
