"""Connection check for one pilot (research, not the engine): do a BRRI rice variety's calendar, NASA weather and
rain, and SRDI soil data join up into advice a Tanore farmer could use?

Question: which T.Aman variety (BRRI dhan49, 135 days; the drought-tolerant BRRI dhan71, 115 days; ...), and what
does the choice mean for the Rabi crop after it? Chain, for the Tanore cell, seasons 2001-2025:
  1 NASA POWER: temperature, dew point, wind, sunshine, pressure -> FAO-56 Penman-Monteith reference ET0.
    Tmax/Tmin corrected by month against BMD's Rajshahi station (NOAA GSOD), 25 km away.
  2 NASA GPM IMERG (Final run, via POWER): daily rain; checked against the Rajshahi gauge.
  3 BRRI factsheets (crops/brri_rice_varieties.csv): seedbed window, seedling age, duration -> transplanting,
    flowering (~30 days before maturity) and harvest dates.
  4 FAO-56: rice crop coefficients by stage -> the crop's daily water use.
  5 Rainfed paddy water balance (rain in; crop use and 2 mm/day seepage out; 10 cm bunds): days with no standing
    water from 20 days before to 10 days after flowering, the drought-sensitive stage. 5 or more such days counts
    as a season that needed a rescue irrigation.
  6 Harvest date -> which Rabi crops still fit their sowing window (crops/crop_parameters.csv), each one's
    irrigation need from the same NASA data (FAO-56), and heat at wheat grain filling / Boro flowering.
  7 NASA SMAP L4 root-zone moisture, November-December 2023-2025: what an early harvest leaves in the soil.
  8 SRDI: the fertilizer card for Talanda union, medium-high land, and the soil atlas classes behind it.
  9 NASA MODIS NDVI: when Tanore's fields actually go bare after Aman, 2001-2025.
Assumptions to test with farmers and SAAOs: seepage 2 mm/day, bund 10 cm, 50 mm standing water at transplanting,
5 dry days at flowering = rescue irrigation, 7 days from harvest to the next sowing, 50 mm of soil water left for
an upland Rabi crop, 150 mm to puddle a Boro field.

Output: research/pilots/connect_tanore_aman.csv (variety x season), connect_tanore_rabi.csv (crop x season)
Usage : python research/explore/connect_check.py
"""
from __future__ import annotations

import math
import re
import sys
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message=".*'generic' unit for NumPy timedelta.*")  # pandas/numpy noise on date sums

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

SITE, LAT, ELEV = "RAJ_TANORE", 24.62, 21.0  # elevation from NASADEM (soil/landtype_proxy_pilots.csv)
SEASONS = range(2001, 2026)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], start=1)}
AMAN = ["BRRI dhan87", "BRRI dhan71", "BRRI dhan103", "BRRI dhan49", "BRRI dhan75"]
SEEPAGE, BUND, START_WATER, DRY_DAYS_RESCUE = 2.0, 100.0, 50.0, 5


def svp(t):
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def et0_fao56(p: pd.DataFrame) -> pd.Series:
    """FAO-56 Penman-Monteith reference evapotranspiration (mm/day) from POWER daily (community AG units)."""
    tmax, tmin = p["tmax"], p["tmin"]
    tmean = (tmax + tmin) / 2
    es, ea = (svp(tmax) + svp(tmin)) / 2, svp(p["T2MDEW"])
    delta = 4098 * svp(tmean) / (tmean + 237.3) ** 2
    gamma = 0.000665 * p["PS"]
    j = p.index.dayofyear.to_numpy()
    phi = math.radians(LAT)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    dec = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(dec))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    rs = p["ALLSKY_SFC_SW_DWN"]
    rso = (0.75 + 2e-5 * ELEV) * ra
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(ea)) * \
        (1.35 * np.clip(rs / rso, 0.3, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    u2 = p["WS2M"]
    return (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))


def kc_curve(n: int, kc: tuple, frac=(0.2, 0.2, 0.4, 0.2)) -> np.ndarray:
    """FAO-56 crop coefficient by day: flat initial, rising development, flat mid-season, falling late season."""
    ini, dev, mid = (max(1, round(n * f)) for f in frac[:3])
    late = max(1, n - ini - dev - mid)
    return np.concatenate([np.full(ini, kc[0]), np.linspace(kc[0], kc[1], dev, endpoint=False),
                           np.full(mid, kc[1]), np.linspace(kc[1], kc[2], late)])[:n]


def window(text: str, year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """'15 Jun-15 Jul', '5-15 Jul', 'mid Dec - Jan 1st week' -> dates in the given season year."""
    t = text.lower().replace("mid ", "15 ").replace("1st week", "4").replace("early ", "5 ").replace("late ", "25 ")
    t = re.sub(r"(\d{1,2})\s*-\s*(\d{1,2})\s+([a-z]{3})", r"\1 \3 - \2 \3", t)
    t = re.sub(r"([a-z]{3})\s+(\d{1,2})", r"\2 \1", t)  # 'jan 4' -> '4 jan'
    dates = [(int(d), MONTHS[m[:3]]) for d, m in re.findall(r"(\d{1,2})\s+([a-z]{3})", t) if m[:3] in MONTHS]
    (d0, m0), (d1, m1) = dates[0], dates[-1]
    start = pd.Timestamp(year, m0, d0)
    end = pd.Timestamp(year + (1 if m1 < m0 else 0), m1, d1)
    return start, end


def mid(a: str | float, b: float | None = None) -> float:
    if isinstance(a, str):
        nums = [float(x) for x in re.findall(r"\d+", a)]
        return sum(nums) / len(nums)
    return (a + b) / 2


def paddy(rain: np.ndarray, etc: np.ndarray) -> np.ndarray:
    """Standing water (mm) in a rainfed bunded paddy; below 0 the soil is drying (floor -60 mm)."""
    s, out = START_WATER, []
    for p, e in zip(rain, etc):
        s = min(s + p - e - (SEEPAGE if s > 0 else 0.0), BUND)
        s = max(s, -60.0)
        out.append(s)
    return np.array(out)


def main() -> None:
    # 1-2: NASA weather and rain, corrected and checked against BMD Rajshahi
    p = pd.read_parquet(DATA / "power" / "daily" / f"{SITE}.parquet")
    p.index = pd.to_datetime(p.index)
    g = pd.read_parquet(DATA / "stations" / "gsod" / "41895_ShahMokhdum.parquet")
    g.index = pd.to_datetime(g.index)
    both = p.join(g[["tmax_c", "tmin_c", "prcp_mm"]], how="inner")
    bias = both.groupby(both.index.month).apply(lambda d: pd.Series({
        "tmax": (d["T2M_MAX"] - d["tmax_c"]).mean(), "tmin": (d["T2M_MIN"] - d["tmin_c"]).mean(), "days": len(d)}))
    p["tmax"] = p["T2M_MAX"] - p.index.month.map(bias["tmax"]).to_numpy()
    p["tmin"] = p["T2M_MIN"] - p.index.month.map(bias["tmin"]).to_numpy()
    p["et0"] = et0_fao56(p)
    p["rain"] = p["IMERG_PRECTOT"]
    wet = both[both.index.month.isin([6, 7, 8, 9, 10])].dropna(subset=["prcp_mm"])
    months = wet.groupby([wet.index.year, wet.index.month]).agg(n=("prcp_mm", "count"), imerg=("IMERG_PRECTOT", "sum"),
                                                                  gauge=("prcp_mm", "sum"))
    months = months[months["n"] >= 28]
    print(f"BMD Rajshahi: POWER Tmax runs {bias['tmax'].round(1).to_dict()} C hot by month (corrected); "
          f"IMERG/gauge Jun-Oct over {len(months)} full months = {months['imerg'].sum() / months['gauge'].sum():.2f}")
    print(f"FAO-56 ET0 at Tanore: {p.loc['2001':'2025', 'et0'].resample('YE').sum().mean():.0f} mm/yr "
          f"(Oct {p[p.index.month == 10]['et0'].mean():.1f}, Jan {p[p.index.month == 1]['et0'].mean():.1f}, "
          f"Apr {p[p.index.month == 4]['et0'].mean():.1f} mm/day)")

    # 3-5: each Aman variety through 25 monsoons
    brri = pd.read_csv(RESEARCH / "crops" / "brri_rice_varieties.csv").set_index("variety")
    cp = pd.read_csv(RESEARCH / "crops" / "crop_parameters.csv").set_index("crop")
    rice_kc = tuple(cp.loc["T.Aman rice", ["kc_ini", "kc_mid", "kc_end"]])
    rows = []
    for v in AMAN:
        r = brri.loc[v]
        seedling = mid(r["seedling_age_days"])
        duration = mid(r["duration_days_min"], r["duration_days_max"])
        for y in SEASONS:
            s0, s1 = window(r["seedbed_sowing"], y)
            sown = s0 + (s1 - s0) / 2
            transplant = sown + pd.Timedelta(days=round(seedling))
            mature = sown + pd.Timedelta(days=round(duration))
            flower = mature - pd.Timedelta(days=30)
            days = pd.date_range(transplant, mature - pd.Timedelta(days=1))
            etc = kc_curve(len(days), rice_kc) * p.loc[days, "et0"].to_numpy()
            water = paddy(p.loc[days, "rain"].to_numpy(), etc)
            w = (days >= flower - pd.Timedelta(days=20)) & (days <= flower + pd.Timedelta(days=10))
            rows.append({"variety": v, "season": y, "transplant": transplant.date(), "flowering": flower.date(),
                         "maturity": mature.date(), "rain_field_mm": round(p.loc[days, "rain"].sum()),
                         "crop_water_use_mm": round(etc.sum()), "dry_days_at_flowering": int((water[w] <= 0).sum()),
                         "lowest_water_at_flowering_mm": round(water[w].min()),
                         "rain_at_flowering_mm": round(p.loc[days[w], "rain"].sum())})
    aman = pd.DataFrame(rows)
    aman["needs_rescue_irrigation"] = aman["dry_days_at_flowering"] >= DRY_DAYS_RESCUE
    aman["next_sowing"] = pd.to_datetime(aman["maturity"]) + pd.Timedelta(days=7)

    # 6: the Rabi crops after it: sowing fit, water need, heat
    rabi_def = {  # crop: (typical sowing (month, day), days in the field, crop_parameters row)
        "Lentil (BARI Masur-8)": ((11, 10), 112, "Lentil"),
        "Mustard (BARI Sarisha-14)": ((11, 10), 80, "Mustard"),
        "Wheat (BARI Gom 33), sown 20 Nov": ((11, 20), 105, "Wheat"),
        "Wheat (BARI Gom 33), sown 10 Dec": ((12, 10), 105, "Wheat"),
        "Maize (hybrid)": ((11, 25), 145, "Maize"),
    }
    r28 = brri.loc["BRRI dhan28"]
    rows = []
    for y in SEASONS:
        if y == 2025:
            continue  # the 2025-26 Rabi is only partly observed
        for crop, ((m, d), n, key) in rabi_def.items():
            sow = pd.Timestamp(y, m, d)
            days = pd.date_range(sow, periods=n)
            kc = tuple(cp.loc[key, ["kc_ini", "kc_mid", "kc_end"]])
            etc = kc_curve(n, kc, (0.15, 0.25, 0.4, 0.2)) * p.loc[days, "et0"].to_numpy()
            rain = p.loc[days, "rain"].to_numpy()
            eff = np.where(rain > 5, 0.8 * rain, 0).sum()
            heat = None
            if key == "Wheat":  # days above 30 C in the last 30 days (grain filling)
                heat = int((p.loc[days[-30:], "tmax"] > cp.loc["Wheat", "heat_threshold_c"]).sum())
            rows.append({"crop": crop, "season": f"{y}-{str(y + 1)[2:]}", "sown": sow.date(), "harvest": days[-1].date(),
                         "crop_water_use_mm": round(etc.sum()), "rain_mm": round(rain.sum()),
                         "net_irrigation_mm": round(max(0.0, etc.sum() - eff - 50)), "heat_days": heat})
        s0, s1 = window(r28["seedbed_sowing"], y)  # Boro, BRRI dhan28
        sown = s0 + (s1 - s0) / 2
        transplant = sown + pd.Timedelta(days=round(mid(r28["seedling_age_days"])))
        mature = sown + pd.Timedelta(days=round(r28["duration_days_min"]))
        days = pd.date_range(transplant, mature - pd.Timedelta(days=1))
        etc = kc_curve(len(days), tuple(cp.loc["Boro rice", ["kc_ini", "kc_mid", "kc_end"]])) * p.loc[days, "et0"].to_numpy()
        rain = p.loc[days, "rain"].sum()
        flower = mature - pd.Timedelta(days=30)
        fl = p.loc[flower - pd.Timedelta(days=7):flower + pd.Timedelta(days=7), "tmax"]
        rows.append({"crop": "Boro (BRRI dhan28)", "season": f"{y}-{str(y + 1)[2:]}", "sown": transplant.date(),
                     "harvest": mature.date(), "crop_water_use_mm": round(etc.sum()), "rain_mm": round(rain),
                     "net_irrigation_mm": round(max(0.0, 150 + etc.sum() + SEEPAGE * len(days) - rain)),
                     "heat_days": int((fl >= cp.loc["Boro rice", "heat_threshold_c"]).sum())})
    rabi = pd.DataFrame(rows)

    out = RESEARCH / "pilots"
    aman.to_csv(out / "connect_tanore_aman.csv", index=False)
    rabi.to_csv(out / "connect_tanore_rabi.csv", index=False)

    # summaries
    pd.set_option("display.width", 220)
    md = lambda s: pd.to_datetime(s).dt.strftime("%m-%d").sort_values().iloc[len(s) // 2]
    v = aman.groupby("variety", sort=False).agg(
        flowering=("flowering", md), maturity=("maturity", md), next_sowing=("next_sowing", md),
        rescue_seasons=("needs_rescue_irrigation", "sum"), median_dry_days=("dry_days_at_flowering", "median"),
        worst_dry_days=("dry_days_at_flowering", "max"), rain_at_flowering_mm=("rain_at_flowering_mm", "median"))
    v["rescue_seasons"] = v["rescue_seasons"].astype(int).astype(str) + " of 25"
    v["drought_tolerant"] = [bool(brri.loc[x, "drought_tolerant"]) for x in v.index]
    v["lentil_mustard_on_time"] = v["next_sowing"] <= "11-15"
    v["wheat_on_time"] = v["next_sowing"] <= "11-30"
    print("\nAman variety at Tanore, 25 monsoons (BRRI calendar x NASA IMERG rain x NASA POWER ET0):")
    print(v.to_string())
    w = rabi.groupby("crop", sort=False).agg(net_irrigation_median=("net_irrigation_mm", "median"),
                                             p10=("net_irrigation_mm", lambda s: s.quantile(0.1)),
                                             p90=("net_irrigation_mm", lambda s: s.quantile(0.9)),
                                             heat_days_median=("heat_days", "median"))
    boro = w.loc["Boro (BRRI dhan28)", "net_irrigation_median"]
    w["water_vs_boro_pct"] = (100 * w["net_irrigation_median"] / boro - 100).round()
    print("\nThe Rabi crop after it, 24 winters (FAO-56 x NASA POWER ET0 x NASA IMERG; heat = days over the crop's limit):")
    print(w.round(0).to_string())

    # 7: SMAP root-zone moisture after an early vs a late Aman harvest
    sm = pd.read_parquet(DATA / "appeears" / "l4" / "smap_l4_daily.parquet")
    sm = sm[sm["ID"] == SITE].set_index(pd.to_datetime(sm[sm["ID"] == SITE]["t"]))["SPL4SMGP_008_Geophysical_Data_sm_rootzone"]
    print("\nNASA SMAP L4 root-zone soil moisture at Tanore (m3/m3):")
    for y in (2023, 2024, 2025):
        vals = [f"{d}: {sm.get(pd.Timestamp(f'{y}-{d}'), float('nan')):.3f}" for d in ("11-01", "11-15", "12-01", "12-15")]
        print(f"  {y}", "  ".join(vals))

    # 8: SRDI soil card and atlas
    frs = pd.read_csv(RESEARCH / "soil" / "srdi_frs_doses.csv")
    nfc = lambda s: unicodedata.normalize("NFC", s)
    card = frs[(frs["site_id"] == SITE) & (frs["season"] == "Kharif-2")
               & frs["land_type_bn"].map(nfc).str.startswith(nfc("মাঝারি উঁচু"))
               & frs["crop_bn"].str.contains("৪৯", regex=False) & frs["crop_bn"].str.contains("৭১", regex=False)]
    bigha = 0.13378  # ha in one bigha (33 decimals)
    c = card.iloc[0]
    doses = {k.replace("_kg_ha", ""): round(c[k] * bigha, 1) for k in c.index if k.endswith("_kg_ha") and pd.notna(c[k]) and c[k] > 0}
    atlas = pd.read_csv(RESEARCH / "soil" / "srdi_fertility_pilots.csv").set_index("site_id").loc[SITE]
    print(f"\nSRDI card, Talanda union, medium-high land, T.Aman (group with BRRI dhan49 and 71), kg per bigha: {doses}")
    print("SRDI atlas, Tanore:", {k: atlas[k] for k in ("ph", "organic_matter", "p_wetland_rice", "k_wetland_rice", "zn", "b")})

    # 9: MODIS NDVI: when do the fields go bare after Aman?
    nd = pd.read_parquet(DATA / "ndvi" / "MOD13Q1" / f"{SITE}.parquet")["ndvi_median_good"]
    nd.index = pd.to_datetime(nd.index)
    drop = {}
    for y in SEASONS:
        s = nd[f"{y}-10-01":f"{y}-12-31"]
        if len(s) >= 4:
            drop[y] = s.diff().idxmin()  # the composite after the steepest fall = harvest
    drop = pd.Series(drop)
    early, late = drop[drop.index <= 2005], drop[drop.index >= 2021]
    doy = lambda s: int(np.median([d.dayofyear for d in s]))
    print(f"\nNASA MODIS NDVI, steepest fall after the Aman peak: 2001-05 median day {doy(early)} "
          f"({(pd.Timestamp(2001, 1, 1) + pd.Timedelta(days=doy(early) - 1)):%d %b}), 2021-25 median day {doy(late)} "
          f"({(pd.Timestamp(2001, 1, 1) + pd.Timedelta(days=doy(late) - 1)):%d %b}) (16-day composites, +-8 days)")


if __name__ == "__main__":
    main()
