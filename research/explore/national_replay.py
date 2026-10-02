"""The 25-season replay for every district of Bangladesh, so the engine can advise any upazila.

The same chain as connect_check.py (Tanore), run at each district's NASA POWER point, seasons 2001-2025:
  NASA POWER weather -> FAO-56 Penman-Monteith ET0, maximum and minimum temperature corrected by month against
  the nearest BMD station within 100 km (NOAA GSOD; none is used where no station is that close);
  GPM IMERG rain (Final run, via POWER); BRRI and BARI calendars; FAO-56 crop coefficients;
  the rainfed paddy water balance (5 or more dry days around flowering = a rescue irrigation);
  each Rabi crop's net irrigation, and heat at wheat grain filling and Boro flowering.
Records are written in the engine's AmanRecord and RabiRecord shapes (research/export/eden_release.py).

Fertilizer: the SRDI Talanda card stands in until each upazila's own card is added. Context: GLDAS-2.2 groundwater
(pilots/groundwater_trend.csv) and GLW4 cattle density per district.

Output: packages/rotation-engine/src/data/national_replay.json
Usage : python research/explore/national_replay.py   (needs the POWER district cache from research/acquire)
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "export"))
sys.path.insert(0, str(HERE.parents[0] / "acquire"))
import connect_check as cc  # noqa: E402  (kc_curve, window, mid, paddy, svp, constants)
import eden_release as er  # noqa: E402  (span, typical, RABI, AMAN, srdi_doses)
from _common import DATA, RESEARCH  # noqa: E402

ROOT = RESEARCH.parent
OUT = ROOT / "packages" / "rotation-engine" / "src" / "data" / "national_replay.json"
norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower())


def et0(p: pd.DataFrame, lat: float, elev: float = 10.0) -> pd.Series:
    """FAO-56 Penman-Monteith, as connect_check.et0_fao56 but for any latitude."""
    tmax, tmin = p["tmax"], p["tmin"]
    tmean = (tmax + tmin) / 2
    es, ea = (cc.svp(tmax) + cc.svp(tmin)) / 2, cc.svp(p["T2MDEW"])
    delta = 4098 * cc.svp(tmean) / (tmean + 237.3) ** 2
    gamma = 0.000665 * p["PS"]
    j = p.index.dayofyear.to_numpy()
    phi = math.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    dec = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(dec))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    rs = p["ALLSKY_SFC_SW_DWN"]
    rso = (0.75 + 2e-5 * elev) * ra
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(ea)) * \
        (1.35 * np.clip(rs / rso, 0.3, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    u2 = p["WS2M"]
    return (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))


def nearest_station(lat: float, lon: float, stations: pd.DataFrame) -> dict | None:
    d = np.hypot(stations["lat"] - lat, (stations["lon"] - lon) * math.cos(math.radians(lat))) * 111
    i = d.idxmin()
    return {**stations.loc[i].to_dict(), "km": round(float(d[i]))} if d[i] <= 100 else None


def weather(site: str, lat: float, lon: float, stations: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
    p = pd.read_parquet(DATA / "power" / "daily" / f"{site}.parquet")
    p.index = pd.to_datetime(p.index)
    st = nearest_station(lat, lon, stations)
    p["tmax"], p["tmin"] = p["T2M_MAX"], p["T2M_MIN"]
    if st:
        g = pd.read_parquet(st["path"])
        g.index = pd.to_datetime(g.index)
        both = p.join(g[["tmax_c", "tmin_c"]], how="inner").dropna(subset=["tmax_c", "tmin_c"])
        if len(both) >= 3 * 365:
            bias = both.groupby(both.index.month).apply(lambda d: pd.Series({
                "tmax": (d["T2M_MAX"] - d["tmax_c"]).mean(), "tmin": (d["T2M_MIN"] - d["tmin_c"]).mean()}))
            p["tmax"] = p["T2M_MAX"] - p.index.month.map(bias["tmax"]).to_numpy()
            p["tmin"] = p["T2M_MIN"] - p.index.month.map(bias["tmin"]).to_numpy()
        else:
            st = None
    p["et0"] = et0(p, lat)
    p["rain"] = p["IMERG_PRECTOT"].fillna(p["PRECTOTCORR"]) if "IMERG_PRECTOT" in p else p["PRECTOTCORR"]
    return p, ({"name": st["name"], "wmo": int(st["wmo"]), "km": st["km"]} if st else None)


def replay(p: pd.DataFrame, brri: pd.DataFrame, cp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """connect_check.py steps 3-6 for one place."""
    rice_kc = tuple(cp.loc["T.Aman rice", ["kc_ini", "kc_mid", "kc_end"]])
    rows = []
    for v in er.AMAN:
        r = brri.loc[v]
        seedling = cc.mid(r["seedling_age_days"])
        duration = cc.mid(r["duration_days_min"], r["duration_days_max"])
        for y in cc.SEASONS:
            s0, s1 = cc.window(r["seedbed_sowing"], y)
            sown = s0 + (s1 - s0) / 2
            transplant = sown + pd.Timedelta(days=round(seedling))
            mature = sown + pd.Timedelta(days=round(duration))
            flower = mature - pd.Timedelta(days=30)
            days = pd.date_range(transplant, mature - pd.Timedelta(days=1))
            etc = cc.kc_curve(len(days), rice_kc) * p.loc[days, "et0"].to_numpy()
            water = cc.paddy(p.loc[days, "rain"].to_numpy(), etc)
            w = (days >= flower - pd.Timedelta(days=20)) & (days <= flower + pd.Timedelta(days=10))
            night = p.loc[flower - pd.Timedelta(days=7):flower + pd.Timedelta(days=7), "tmin"].mean()
            rows.append({"variety": v, "season": y, "transplant": transplant.date(), "flowering": flower.date(),
                         "maturity": mature.date(), "crop_water_use_mm": round(etc.sum()),
                         "dry_days_at_flowering": int((water[w] <= 0).sum()), "night_c": float(night)})
    aman = pd.DataFrame(rows)
    aman["needs_rescue_irrigation"] = aman["dry_days_at_flowering"] >= cc.DRY_DAYS_RESCUE
    aman["next_sowing"] = pd.to_datetime(aman["maturity"]) + pd.Timedelta(days=7)

    rabi_def = {"Lentil (BARI Masur-8)": ((11, 10), 112, "Lentil"), "Mustard (BARI Sarisha-14)": ((11, 10), 80, "Mustard"),
                "Wheat (BARI Gom 33), sown 20 Nov": ((11, 20), 105, "Wheat"),
                "Wheat (BARI Gom 33), sown 10 Dec": ((12, 10), 105, "Wheat")}
    r28 = brri.loc["BRRI dhan28"]
    rows = []
    for y in cc.SEASONS:
        if y == 2025:
            continue
        for crop, ((m, d), n, key) in rabi_def.items():
            days = pd.date_range(pd.Timestamp(y, m, d), periods=n)
            kc = tuple(cp.loc[key, ["kc_ini", "kc_mid", "kc_end"]])
            etc = cc.kc_curve(n, kc, (0.15, 0.25, 0.4, 0.2)) * p.loc[days, "et0"].to_numpy()
            rain = p.loc[days, "rain"].to_numpy()
            eff = np.where(rain > 5, 0.8 * rain, 0).sum()
            heat = int((p.loc[days[-30:], "tmax"] > cp.loc["Wheat", "heat_threshold_c"]).sum()) if key == "Wheat" else None
            rows.append({"crop": crop, "sown": days[0].date(), "harvest": days[-1].date(), "crop_water_use_mm": round(etc.sum()),
                         "net_irrigation_mm": round(max(0.0, etc.sum() - eff - 50)), "heat_days": heat})
        s0, s1 = cc.window(r28["seedbed_sowing"], y)
        sown = s0 + (s1 - s0) / 2
        transplant = sown + pd.Timedelta(days=round(cc.mid(r28["seedling_age_days"])))
        mature = sown + pd.Timedelta(days=round(r28["duration_days_min"]))
        days = pd.date_range(transplant, mature - pd.Timedelta(days=1))
        etc = cc.kc_curve(len(days), tuple(cp.loc["Boro rice", ["kc_ini", "kc_mid", "kc_end"]])) * p.loc[days, "et0"].to_numpy()
        rain = p.loc[days, "rain"].sum()
        flower = mature - pd.Timedelta(days=30)
        fl = p.loc[flower - pd.Timedelta(days=7):flower + pd.Timedelta(days=7), "tmax"]
        rows.append({"crop": "Boro (BRRI dhan28)", "sown": transplant.date(), "harvest": mature.date(),
                     "crop_water_use_mm": round(etc.sum()),
                     "net_irrigation_mm": round(max(0.0, 150 + etc.sum() + cc.SEEPAGE * len(days) - rain)),
                     "heat_days": int((fl >= cp.loc["Boro rice", "heat_threshold_c"]).sum())})
    return aman, pd.DataFrame(rows)


def records(aman: pd.DataFrame, rabi: pd.DataFrame, brri: pd.DataFrame, srdi: dict, windows: dict) -> tuple[dict, dict]:
    """The engine's AmanRecord and RabiRecord shapes, as research/export/eden_release.py writes them for Tanore."""
    a_out = {}
    for v in er.AMAN:
        r = aman[aman["variety"] == v]
        a_out[v] = {"variety": v, "durationDays": [int(brri.loc[v, "duration_days_min"]), int(brri.loc[v, "duration_days_max"])],
                    "seedbedWindow": er.span(brri.loc[v, "seedbed_sowing"]), "transplant": er.typical(r["transplant"]),
                    "flowering": er.typical(r["flowering"]), "maturity": er.typical(r["maturity"]),
                    "fieldFree": er.typical(r["next_sowing"]), "rescueSeasons": int(r["needs_rescue_irrigation"].sum()),
                    "totalSeasons": int(len(r)), "rescueYears": [int(y) for y in r.loc[r["needs_rescue_irrigation"], "season"]],
                    "cropWaterUseMm": int(r["crop_water_use_mm"].median()),
                    "floweringNightTempC": round(float(r["night_c"].median()), 1),
                    "fieldDays": int((pd.to_datetime(r["maturity"]) - pd.to_datetime(r["transplant"])).dt.days.median())}
    r_out = {}
    for key, (label, _, heat_spec) in er.RABI.items():
        s = rabi[rabi["crop"] == label]
        exposure = None
        if heat_spec:
            _, stage, stage_bn, threshold, days = heat_spec
            exposure = {"stage": stage, "stageBangla": stage_bn, "thresholdC": threshold, "windowDays": days,
                        "hotDays": int(round(s["heat_days"].median()))}
        sow_window, source = windows[key]
        r_out[key] = {"key": key, "replayLabel": label, "sowing": er.typical(s["sown"]), "harvest": er.typical(s["harvest"]),
                      "sowingWindow": sow_window, "sowingWindowSource": source, "seasons": int(len(s)),
                      "netIrrigationMm": int(s["net_irrigation_mm"].median()),
                      "netIrrigationRangeMm": [int(s["net_irrigation_mm"].quantile(0.1)), int(s["net_irrigation_mm"].quantile(0.9))],
                      "pumpedM3PerHa": int(s["net_irrigation_mm"].median() * 10),
                      "fieldDays": int((pd.to_datetime(s["harvest"]) - pd.to_datetime(s["sown"])).dt.days.median()) + 1,
                      "cropWaterUseMm": int(s["crop_water_use_mm"].median()), "heat": exposure,
                      "fertilizer": srdi[key], "districtYieldTPerHa": None}
    return a_out, r_out


def main() -> None:
    brri = pd.read_csv(RESEARCH / "crops" / "brri_rice_varieties.csv").drop_duplicates("variety").set_index("variety")
    cp = pd.read_csv(RESEARCH / "crops" / "crop_parameters.csv").set_index("crop")
    srdi = er.srdi_doses()
    tech = pd.read_csv(RESEARCH / "crops" / "bari_production_technology.csv").set_index("crop_en")
    bw = pd.read_csv(RESEARCH / "crops" / "bwmri_wheat_maize_varieties.csv")
    wheat33 = bw[bw["variety_bn"].map(er.nfc) == er.nfc("বারি গম ৩৩")].iloc[0]
    windows = {"BARI Masur-8": (er.span(tech.loc["lentil", "sowing_windows"]), "BARI handbook"),
               "BARI Sarisha-14": (er.span(tech.loc["mustard", "sowing_windows"]), "BARI handbook"),
               "BARI Gom 33 (Early)": (er.span(wheat33["sowing_windows"]), "BWMRI variety page"),
               "BARI Gom 33 (Late)": (er.span(wheat33["sowing_windows"]), "BWMRI variety page"),
               "BRRI dhan28": (None, None)}
    st = pd.read_csv(RESEARCH / "sites" / "bmd_stations_gsod.csv")
    gsod = DATA / "stations" / "gsod"
    st["path"] = [next(iter(gsod.glob(f"{w}_*.parquet")), None) for w in st["wmo"]]
    st = st.dropna(subset=["path"]).reset_index(drop=True)
    gw = pd.read_csv(RESEARCH / "pilots" / "groundwater_trend.csv")
    gw = {norm(a[5:]): r for a, r in gw.set_index("area").iterrows() if a.startswith("ADM2_")}
    glw = {norm(r["district"]): float(r["cattle_per_km2"]) for _, r in pd.read_csv(RESEARCH / "crops" / "cattle_by_district_glw4.csv").iterrows()}
    glw.update({"nawabganj": glw.get("chapainawabganj", glw.get("nawabganj")), "netrakona": glw.get("netrokona", glw.get("netrakona")),
                "maulvibazar": glw.get("moulvibazar", glw.get("maulvibazar"))})
    sites = pd.read_csv(RESEARCH / "sites" / "districts.csv")

    out = {}
    for _, s in sites.iterrows():
        site = s["site_id"]
        if not (DATA / "power" / "daily" / f"{site}.parquet").exists():
            print(f"  {site}: no POWER cache, skipped")
            continue
        name = site[5:] if site.startswith("ADM2_") else s["name"]
        p, station = weather(site, float(s["lat"]), float(s["lon"]), st)
        aman, rabi = replay(p, brri, cp)
        a_rec, r_rec = records(aman, rabi, brri, srdi, windows)
        g = gw.get(norm(name))
        out[str(s["name"])] = {
            "id": site, "name": str(s["name"]), "lat": float(s["lat"]), "lon": float(s["lon"]), "station": station,
            "aman": a_rec, "rabi": r_rec,
            "conditions": {
                "groundwater": None if g is None else {"source": g["source"], "trendMmPerYear": float(g["annual_trend_per_year"]),
                                                       "changeMm": float(g["change_2003_07_to_2021_25"]), "period": "2003-07 to 2021-25"},
                "cattlePerKm2": glw.get(norm(s["name"])),
                "smap": None,
            },
        }
        d71, b = a_rec["BRRI dhan71"], r_rec["BRRI dhan28"]
        print(f"{s['name']:<16} dhan71 rescue {d71['rescueSeasons']:>2}/25, free {d71['fieldFree']}; Boro {b['netIrrigationMm']} mm; "
              f"station {station['name'] if station else '-'}")
    ups = pd.read_csv(RESEARCH / "sites" / "upazilas.csv")
    upazilas = [{"id": r["site_id"], "name": r["name"], "district": r["district"]} for _, r in ups.iterrows() if r["district"] in out]
    OUT.write_text(json.dumps({"generatedOn": f"{date.today()}", "seasons": "2001-2025", "districts": out, "upazilas": upazilas,
                               "method": __doc__.split("\n\n")[1].strip(),
                               "fertilizerNote": "SRDI Talanda card used as a stand-in until each upazila's card is added"},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} districts")


if __name__ == "__main__":
    main()
