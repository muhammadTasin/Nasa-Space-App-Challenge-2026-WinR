"""Write the research numbers behind the EDEN app (Tanore pilot, Talanda union) as one generated TypeScript module.

The EDEN rotation engine, API, SAAO dashboard and Android app (repo project-eden-earth-data-environment-navigator)
carried hand-copied numbers that drifted from these tables. This script reads the research outputs and writes
packages/rotation-engine/src/data/tanore_replay_data.ts, so every screen shows the same traceable values.

  Aman replay (explore/connect_check.py): seasons needing rescue irrigation at flowering, typical dates, water use
  Rabi replay (connect_check.py): net irrigation after 50 mm of residual soil water, sowing and harvest dates
  Heat (explore/heat_windows.py, BMD-corrected): hot days at Boro flowering and wheat grain filling
  SRDI union card (acquire/srdi_frs.py): Talanda, medium-high land, Kharia soil; fertilizer in kg/ha
  BRRI / BARI / BWMRI handbooks: seedbed and sowing windows
  Current conditions: SMAP L4 root zone (latest day) and 30-day rain (IMERG Late cross-checked, rain_vs_normal.py)
  Context: GLDAS-2.2 groundwater trend, MODIS winter greenness, upazila land use, BBS yields, GLW4 cattle
  Advisories: warming nights and hot days at sensitive stages (heat_trends.py), cattle heat by month (cattle_heat.py)
  Haor early warning: IMERG 3-day rain at Sohra against FFWC flood years, Boro varieties that escape (flash floods)
  Soil and checks: SMAP L4 carbon (soil organic carbon, GPP check), and the environment ledger rows for the app's tests

Only research outputs go in here. Crop labels, fodder classes and the illustrative income figures stay in the
engine's hand-written crop catalog, marked as team estimates.

Usage : python research/export/eden_release.py --out <project-eden>/packages/rotation-engine/src/data/tanore_replay_data.ts
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "explore"))
from signals_common import NEAREST_BMD  # noqa: E402
from _common import DATA, RESEARCH  # noqa: E402
from connect_check import window  # noqa: E402

SITE = "RAJ_TANORE"
PILOTS = RESEARCH / "pilots"

AMAN = ["BRRI dhan71", "BRRI dhan87", "BRRI dhan103", "BRRI dhan49", "BRRI dhan75"]
NIGHT_COLUMN = {"BRRI dhan71": "aman71_night_c", "BRRI dhan49": "aman49_night_c"}

# engine key: (row in connect_tanore_rabi.csv, SRDI crop group, heat column, stage, threshold C, window days)
RABI = {
    "BARI Masur-8": ("Lentil (BARI Masur-8)", ("মসুর", None), None),
    "BARI Sarisha-14": ("Mustard (BARI Sarisha-14)", ("সরিষা", "১৪"), None),
    "BARI Gom 33 (Early)": ("Wheat (BARI Gom 33), sown 20 Nov", ("গম (সেচসহ)", None),
                            ("wheat_20nov_days_gt30", "grain filling", "দানা পুষ্ট হওয়ার সময়", 30, 30)),
    "BARI Gom 33 (Late)": ("Wheat (BARI Gom 33), sown 10 Dec", ("গম (সেচসহ)", None),
                           ("wheat_10dec_days_gt30", "grain filling", "দানা পুষ্ট হওয়ার সময়", 30, 30)),
    "BRRI dhan28": ("Boro (BRRI dhan28)", ("বোরো", "ধান-২৮"),
                    ("boro_days_ge35", "flowering", "ফুল আসার সময়", 35, 15)),
}
BBS_YIELD = {"BARI Masur-8": "Lentil (Masur)", "BARI Sarisha-14": "Rape and Mustard (Local+HYV)",
             "BARI Gom 33 (Early)": "Wheat", "BARI Gom 33 (Late)": "Wheat", "BRRI dhan28": "Boro rice"}


def nfc(text: object) -> str:
    return unicodedata.normalize("NFC", str(text))


def span(text: str) -> list[str]:
    """Handbook window as ['MM-DD', 'MM-DD']; only the first of several ('23 Oct-14 Nov; 23 Nov-30 Nov')."""
    start, end = window(text.split(";")[0], 2001)
    return [start.strftime("%m-%d"), end.strftime("%m-%d")]


def typical(series: pd.Series) -> str:
    """Most common calendar day of a date column, as 'MM-DD' (dates repeat each season in the replay)."""
    return pd.to_datetime(series).dt.strftime("%m-%d").mode().iloc[0]


def srdi_doses() -> dict[str, dict]:
    d = pd.read_csv(RESEARCH / "soil" / "srdi_frs_doses.csv")
    d = d[d["site_id"] == SITE].copy()
    for c in ("crop_bn", "land_type_bn", "soil_type_bn", "union"):
        d[c] = d[c].map(nfc)
    d = d[d["land_type_bn"] == nfc("মাঝারি উঁচু জমি")]

    def pick(prefix: str, must: str | None) -> dict:
        rows = d[d["crop_bn"].str.startswith(nfc(prefix))]
        if must:
            rows = rows[rows["crop_bn"].str.contains(nfc(must), regex=False)]
        if len(rows) != 1:
            raise SystemExit(f"SRDI card: expected one row for {prefix} {must}, found {len(rows)}")
        r = rows.iloc[0]
        return {"cropGroupBangla": r["crop_bn"].split("(")[0].strip(), "ureaKgHa": float(r["urea_kg_ha"]),
                "tspKgHa": float(r["tsp_kg_ha"]), "mopKgHa": float(r["mop_kg_ha"]),
                "gypsumKgHa": float(r["gypsum_kg_ha"]), "zincSulphateKgHa": float(r["zinc_sulphate_kg_ha"]),
                "boricAcidKgHa": float(r["boric_acid_kg_ha"])}

    card = {"soilTypeBangla": d["soil_type_bn"].iloc[0], "unionBangla": d["union"].iloc[0],
            "landTypeBangla": nfc("মাঝারি উঁচু জমি"), "aman": pick("আমন রোপা", "৭১")}
    for key, (_, (prefix, must), _) in RABI.items():
        card[key] = pick(prefix, must)
    return card


def aman_records() -> dict[str, dict]:
    a = pd.read_csv(PILOTS / "connect_tanore_aman.csv")
    brri = pd.read_csv(RESEARCH / "crops" / "brri_rice_varieties.csv").drop_duplicates("variety").set_index("variety")
    heat = pd.read_csv(PILOTS / "heat_windows.csv")
    heat = heat[heat["site_id"] == SITE]
    out = {}
    for v in AMAN:
        r = a[a["variety"] == v]
        seedbed = brri.loc[v, "seedbed_sowing"]
        night = heat[NIGHT_COLUMN[v]].median() if v in NIGHT_COLUMN else None
        out[v] = {
            "variety": v,
            "durationDays": [int(brri.loc[v, "duration_days_min"]), int(brri.loc[v, "duration_days_max"])],
            "seedbedWindow": span(seedbed),
            "transplant": typical(r["transplant"]),
            "flowering": typical(r["flowering"]),
            "maturity": typical(r["maturity"]),
            "fieldFree": typical(r["next_sowing"]),
            "rescueSeasons": int(r["needs_rescue_irrigation"].sum()),
            "totalSeasons": int(len(r)),
            "rescueYears": [int(y) for y in r.loc[r["needs_rescue_irrigation"], "season"]],
            "cropWaterUseMm": int(r["crop_water_use_mm"].median()),
            "floweringNightTempC": None if night is None else round(float(night), 1),
            # days in the field, transplanting to maturity (environment_ledger.py's method)
            "fieldDays": int((pd.to_datetime(r["maturity"]) - pd.to_datetime(r["transplant"])).dt.days.median()),
        }
    return out


def rabi_records(srdi: dict, yields: dict[str, float]) -> dict[str, dict]:
    r = pd.read_csv(PILOTS / "connect_tanore_rabi.csv")
    heat = pd.read_csv(PILOTS / "heat_windows.csv")
    heat = heat[heat["site_id"] == SITE]
    tech = pd.read_csv(RESEARCH / "crops" / "bari_production_technology.csv").set_index("crop_en")
    bwmri = pd.read_csv(RESEARCH / "crops" / "bwmri_wheat_maize_varieties.csv")
    wheat33 = bwmri[bwmri["variety_bn"].map(nfc) == nfc("বারি গম ৩৩")].iloc[0]
    windows = {"BARI Masur-8": (span(tech.loc["lentil", "sowing_windows"]), "BARI handbook"),
               "BARI Sarisha-14": (span(tech.loc["mustard", "sowing_windows"]), "BARI handbook"),
               "BARI Gom 33 (Early)": (span(wheat33["sowing_windows"]), "BWMRI variety page"),
               "BARI Gom 33 (Late)": (span(wheat33["sowing_windows"]), "BWMRI variety page"),
               "BRRI dhan28": (None, None)}
    out = {}
    for key, (label, _, heat_spec) in RABI.items():
        s = r[r["crop"] == label]
        if s.empty:
            raise SystemExit(f"connect_tanore_rabi.csv has no rows for {label}")
        exposure = None
        if heat_spec:
            column, stage, stage_bn, threshold, days = heat_spec
            exposure = {"stage": stage, "stageBangla": stage_bn, "thresholdC": threshold, "windowDays": days,
                        "hotDays": int(round(heat[column].median()))}
        sow_window, window_source = windows[key]
        out[key] = {
            "key": key,
            "replayLabel": label,
            "sowing": typical(s["sown"]),
            "harvest": typical(s["harvest"]),
            "sowingWindow": sow_window,
            "sowingWindowSource": window_source,
            "seasons": int(len(s)),
            "netIrrigationMm": int(s["net_irrigation_mm"].median()),
            "netIrrigationRangeMm": [int(s["net_irrigation_mm"].quantile(0.1)),
                                     int(s["net_irrigation_mm"].quantile(0.9))],
            "pumpedM3PerHa": int(s["net_irrigation_mm"].median() * 10),
            "fieldDays": int((pd.to_datetime(s["harvest"]) - pd.to_datetime(s["sown"])).dt.days.median()) + 1,
            "cropWaterUseMm": int(s["crop_water_use_mm"].median()),
            "heat": exposure,
            "fertilizer": srdi[key],
            "districtYieldTPerHa": yields.get(BBS_YIELD[key]),
        }
    return out


def conditions() -> dict:
    site = pd.read_csv(RESEARCH / "sites" / "pilot_sites.csv").set_index("site_id").loc[SITE]
    pilot = json.loads((PILOTS / "pilots.json").read_text(encoding="utf-8"))[SITE]
    rain = pd.read_csv(PILOTS / "rain_vs_normal.csv")
    rain = rain[(rain["site_id"] == SITE) & (rain["window"] == "last 30 days")].iloc[0]
    moist = pd.read_csv(PILOTS / "soil_moisture_rotation.csv").set_index("site_id").loc[SITE]
    gw = pd.read_csv(PILOTS / "groundwater_trend.csv")
    gw = gw[(gw["area"] == SITE) & gw["source"].str.startswith("GLDAS")].iloc[0]
    cycles = pd.read_csv(PILOTS / "field_cycles.csv")
    cycles = cycles[cycles["site_id"] == SITE].dropna(subset=["cycles_nov_oct"])
    early, late = cycles.head(5), cycles.tail(5)
    glw = pd.read_csv(RESEARCH / "crops" / "cattle_by_district_glw4.csv").set_index("district").loc["Rajshahi"]
    station, km = NEAREST_BMD[SITE]
    top = pilot["top_patterns"][0]

    smap_path = DATA / "appeears" / "l4" / "smap_l4_daily.parquet"
    smap = None
    if smap_path.exists():
        s = pd.read_parquet(smap_path)
        s = s[s["ID"] == SITE].assign(t=lambda x: pd.to_datetime(x["t"])).set_index("t").sort_index()
        rz = s["SPL4SMGP_008_Geophysical_Data_sm_rootzone"]
        last = rz.index.max()
        same_day = {y: rz[(rz.index >= last.replace(year=y) - pd.Timedelta(days=3)) &
                          (rz.index <= last.replace(year=y) + pd.Timedelta(days=3))].mean()
                    for y in range(2023, last.year)}
        nov10 = rz[(rz.index.month == 11) & rz.index.day.isin(range(8, 13))]
        smap = {"date": last.strftime("%Y-%m-%d"), "rootZoneM3M3": round(float(rz.iloc[-1]), 3),
                "sameDatePastYears": [{"year": y, "rootZoneM3M3": round(float(v), 3)}
                                      for y, v in same_day.items() if pd.notna(v)],
                "nov10TypicalM3M3": round(float(nov10.mean()), 3),
                "nov10Years": sorted({int(y) for y in nov10.index.year})}

    return {
        "siteId": SITE, "lat": float(site["lat"]), "lon": float(site["lon"]),
        "bmdStation": station.replace("_", " "), "bmdStationKm": km,
        "smap": smap,
        "rainLast30Days": {"from": rain["from"], "to": rain["to"], "imergLateMm": float(rain["imerg_late_mm"]),
                           "lateFinalRatio": float(rain["late_final_ratio"]),
                           "pctOfNormal": {"imergLate": int(rain["imerg_late_pct_of_normal"]),
                                           "imergAdjusted": int(rain["imerg_adj_pct_of_normal"]),
                                           "merra2": int(rain["merra2_pct_of_normal"])},
                           "verdict": rain["verdict"]},
        "rootZoneGldasMm": {"oct20": int(moist["20_oct_median_mm"]), "nov10": int(moist["10_nov_median_mm"]),
                            "nov19": int(moist["19_nov_median_mm"]),
                            "lostNov10To19": float(moist["lost_10_to_19_nov_median_mm"]),
                            "smapSpearman": float(moist["smap_spearman"])},
        "groundwater": {"source": gw["source"], "trendMmPerYear": float(gw["annual_trend_per_year"]),
                        "changeMm": float(gw["change_2003_07_to_2021_25"]), "period": "2003-07 to 2021-25"},
        "winterGreenness": {"product": "MODIS MOD13Q1 NDVI, 250 m",
                            "early": {"years": f"{early['crop_year'].iloc[0]} to {early['crop_year'].iloc[-1]}",
                                      "peakNdvi": round(float(early["winter_peak_ndvi"].mean()), 2),
                                      "cyclesPerYear": round(float(early["cycles_nov_oct"].mean()), 1)},
                            "recent": {"years": f"{late['crop_year'].iloc[0]} to {late['crop_year'].iloc[-1]}",
                                       "peakNdvi": round(float(late["winter_peak_ndvi"].mean()), 2),
                                       "cyclesPerYear": round(float(late["cycles_nov_oct"].mean()), 1)}},
        "landUse": {"year": "2014-15", "croppingIntensityPct": float(pilot["land_use_2014_15"]["cropping_intensity_pct"]),
                    "topPattern": top["pattern"], "topPatternPct": float(top["pct_upazila_nca"])},
        "cattlePerKm2": float(glw["cattle_per_km2"]),
    }


def advisories() -> dict:
    """Warming nights and hot days at sensitive stages (heat_trends.py), and cattle heat by month (cattle_heat.py)."""
    trends = pd.read_csv(PILOTS / "heat_trends.csv")
    trends = trends[trends["site_id"] == SITE]
    cattle = pd.read_csv(PILOTS / "cattle_heat.csv")
    cattle = cattle[cattle["site_id"] == SITE].sort_values("month")
    return {
        "heatTrends": [{"measure": r["measure"], "mean1991to2005": round(float(r["mean_1991_2005"]), 2),
                        "mean2011to2025": round(float(r["mean_2011_2025"]), 2),
                        "trendPerDecade": round(float(r["trend_per_decade"]), 2), "kendallP": round(float(r["kendall_p"]), 3)}
                       for _, r in trends.iterrows()],
        "cattleHeat": [{"month": int(r["month"]), "meanThi": round(float(r["mean_thi"]), 1),
                        "dangerShare": round(float(r["share_danger_79_83"] + r["share_emergency_84"]), 3),
                        "emergencyShare": round(float(r["share_emergency_84"]), 3),
                        "nightsWithoutReliefPct": round(float(r["nights_without_relief_pct"]), 1),
                        "coolestHours": str(r["coolest_hours"]).split()}
                       for _, r in cattle.iterrows()],
        "cattleSource": "NASA POWER hourly temperature and humidity 2023-2025, THI (NRC 1971); explore/cattle_heat.py",
    }


def haor() -> dict:
    """Flash-flood trigger for the Sunamganj haors from IMERG rain at Sohra, and which Boro varieties escape it."""
    hind = pd.read_csv(RESEARCH / "floods" / "flash_flood_hindcast.csv")
    thr = pd.read_csv(RESEARCH / "floods" / "flash_flood_thresholds.csv")
    esc = pd.read_csv(RESEARCH / "floods" / "boro_flood_escape.csv")
    sites = pd.concat([pd.read_csv(RESEARCH / "sites" / f) for f in ("pilot_sites.csv", "upstream_points.csv")])
    sites = sites.drop_duplicates("site_id").set_index("site_id")
    label = {1.0: "flood", 0.0: "no flood"}
    return {
        "window": ["03-15", "05-15"],
        "sohra": {"lat": float(sites.loc["UP_SOHRA", "lat"]), "lon": float(sites.loc["UP_SOHRA", "lon"])},
        "dharmapasha": {"lat": float(sites.loc["SUN_DHARMAPASHA", "lat"]), "lon": float(sites.loc["SUN_DHARMAPASHA", "lon"])},
        "watchMm": 200,
        "warningMm": 250,
        "source": "GPM IMERG daily rain at Sohra (Meghalaya), 3-day totals 15 Mar-15 May; flood years from FFWC annual reports",
        "seasons": [{"year": int(r["year"]), "sohraMax3Mm": round(float(r["sohra_max3_mm"]), 1),
                     "sohraMax3End": r["sohra_max3_end"],
                     "label": label.get(r["flash_flood"], "unlabelled"),
                     "first200mm": None if pd.isna(r["first_burst_200mm"]) else r["first_burst_200mm"]}
                    for _, r in hind.iterrows()],
        "skill": [{"thresholdMm": int(r["threshold_mm"]), "floodYearsCaught": r["flood_years_caught"],
                   "noFloodYearsFlagged": r["no_flood_years_flagged"], "seasonsFlagged": r["seasons_flagged"]}
                  for _, r in thr.iterrows()],
        "escape": [{"variety": r["variety"], "sowing": r["sowing"], "medianHarvest": r["median_harvest"],
                    "burstsBeforeHarvest": int(r["burst_before_harvest"]), "bursts": int(r["seasons_with_burst"]),
                    "caughtYears": [] if pd.isna(r["caught_years"]) else [int(y) for y in str(r["caught_years"]).split()]}
                   for _, r in esc[esc["burst_mm"] == 250].iterrows()],
    }


def soil_and_productivity() -> dict:
    """SMAP L4 carbon: soil organic carbon, and whether GPP confirms the replay's dry seasons (productivity_check.py)."""
    soc = pd.read_csv(PILOTS / "soil_carbon.csv").set_index("site_id").loc[SITE]
    prod = pd.read_csv(PILOTS / "productivity_check.csv")
    tan = prod[prod["site_id"] == SITE].dropna(subset=["aman_gpp_pct", "tanore_dhan49_dry_days"])
    both = prod.dropna(subset=["aman_gpp_pct", "rain_jun_oct_pct"])
    return {
        "soilCarbonGm2": int(soc["soc_g_m2_2016_2025"]),
        "soilCarbonTrendGm2PerYear": round(float(soc["trend_g_m2_per_year"]), 1),
        "dryDaysVsAmanGppRho": round(float(tan["tanore_dhan49_dry_days"].corr(tan["aman_gpp_pct"], method="spearman")), 2),
        "dryDaysVsAmanGppSeasons": int(len(tan)),
        "monsoonRainVsAmanGppRho": round(float(both["rain_jun_oct_pct"].corr(both["aman_gpp_pct"], method="spearman")), 2),
        "source": "SMAP L4 carbon (SPL4CMDL) GPP and soil organic carbon, 2015-2025",
    }


def ledger_check() -> list[dict]:
    """The research ledger's rows, so the app's tests can check that the engine reproduces them."""
    led = pd.read_csv(PILOTS / "environment_ledger_tanore.csv")
    return [{"rotation": r["rotation"], "pumpedM3PerHa": int(r["groundwater_pumped_m3_per_ha"]),
             "floodedRiceDays": int(r["flooded_rice_days"]), "ureaKgHa": int(r["urea_kg_per_ha"]),
             "bareDays": int(r["bare_days"])} for _, r in led.iterrows()]


def research_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(RESEARCH), "describe", "--always", "--dirty"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path, help="path of tanore_replay_data.ts in the EDEN repo")
    args = ap.parse_args()

    pilot = json.loads((PILOTS / "pilots.json").read_text(encoding="utf-8"))[SITE]
    yields = {y["crop"]: round(float(y["yield_2024_25"]), 2) for y in pilot["yields"]}
    srdi = srdi_doses()
    today = date.today()
    release = {
        "id": f"tanore-{today:%Y.%m.%d}",
        "generatedOn": today.isoformat(),
        "researchCommit": research_commit(),
        "generator": "research/export/eden_release.py (WinR research repo)",
        "pilot": "Talanda union, Tanore upazila, Rajshahi (research site RAJ_TANORE)",
        "seasons": "2001-2025",
    }
    srdi_card = {"siteId": SITE, "unionBangla": srdi.pop("unionBangla"), "soilTypeBangla": srdi.pop("soilTypeBangla"),
                 "landTypeBangla": srdi.pop("landTypeBangla"), "aman": srdi.pop("aman"),
                 "source": "SRDI Fertilizer Recommendation System union card (frs.srdi.gov.bd)"}

    blocks = [
        ("RELEASE", "ReleaseInfo", release),
        ("TANORE_AMAN_REPLAY", "Record<string, AmanRecord>", aman_records()),
        ("TANORE_RABI_REPLAY", "Record<string, RabiRecord>", rabi_records(srdi, yields)),
        ("TALANDA_SRDI", "SrdiCard", srdi_card),
        ("TANORE_CONDITIONS", "PilotConditions", conditions()),
        ("TANORE_ADVISORIES", "PilotAdvisories", advisories()),
        ("HAOR_FLASH_FLOOD", "HaorFlashFlood", haor()),
        ("TANORE_SOIL_CARBON", "SoilAndProductivity", soil_and_productivity()),
        ("TANORE_LEDGER_RESEARCH", "LedgerCheckRow[]", ledger_check()),
    ]
    body = "\n".join(f"export const {name}: {kind} = {json.dumps(value, ensure_ascii=False, indent=2)};\n"
                     for name, kind, value in blocks)
    header = (f"// GENERATED by research/export/eden_release.py from the WinR research repo "
              f"(commit {release['researchCommit']}) on {release['generatedOn']}.\n"
              "// Do not edit by hand. Re-run the script so the engine, dashboard and app keep the research numbers.\n"
              "import type { AmanRecord, HaorFlashFlood, LedgerCheckRow, PilotAdvisories, PilotConditions, RabiRecord, "
              "ReleaseInfo, SoilAndProductivity, SrdiCard } from './release_types.ts';\n\n")
    args.out.write_text(header + body, encoding="utf-8")
    print(f"wrote {args.out} ({release['id']}, research {release['researchCommit']})")


if __name__ == "__main__":
    main()
