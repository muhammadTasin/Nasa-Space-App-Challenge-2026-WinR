"""One data card per pilot site, joining every table in research/ for its upazila and district.

Output: research/pilots/<site_id>.md (+ pilots.json). Run after the extraction scripts
(bbs_yearbook.py, bbs_panel.py, regional_patterns.py, livestock_glw4.py). Usage: python research/explore/pilot_cards.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parents[1]
PILOTS = {  # site -> (upazila as in the BRRI regional papers, district as in sites/districts.csv)
    "RAJ_TANORE": ("Tanor", "Rajshahi"), "SUN_DHARMAPASHA": ("Dharampasha", "Sunamganj"),
    "KHU_BATIAGHATA": ("Batiaghata", "Khulna"), "SIR_ULLAHPARA": ("Ullapara", "Sirajganj"),
    "RAN_MITHAPUKUR": ("Mithapukur", "Rangpur")}
KEY_CROPS = [("Boro rice", "total"), ("Aman rice", "total"), ("Aus rice", "total"), ("Wheat", "all"),
             ("Potato", "total"), ("Rabi Maize", "all"), ("Lentil (Masur)", "all"), ("Rape and Mustard (Local+HYV)", "all"),
             ("Green gram (Mug)", "all"), ("Jute", "all")]


def read(path: str) -> pd.DataFrame:
    p = R / path
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def main() -> None:
    land, top, div = read("crops/upazila_land_use.csv"), read("crops/upazila_top_patterns.csv"), read("crops/upazila_diversity.csv")
    hold, cattle, irr = read("bbs/holdings.csv"), read("crops/cattle_by_district_glw4.csv"), read("bbs/irrigation.csv")
    cd, panel, dmg = read("bbs/crop_district.csv"), read("bbs/crop_district_panel.csv"), read("bbs/damage.csv")
    out_dir = R / "pilots"
    out_dir.mkdir(exist_ok=True)
    cards = {}
    for site, (upz, dist) in PILOTS.items():
        c: dict = {"site": site, "upazila": upz, "district": dist}
        L = []
        L.append(f"# {upz} upazila, {dist} district ({site})\n")
        u = land[land["upazila"].str.lower() == upz.lower()]
        if len(u):
            r = u.iloc[0]
            c["land_use_2014_15"] = r[["net_cropped_ha", "single_cropped_ha", "double_cropped_ha", "triple_cropped_ha",
                                       "cropping_intensity_pct"]].to_dict()
            L.append("## Land use, 2014-15 (BRRI regional survey)\n")
            L.append(f"Net cropped area {r['net_cropped_ha']:,.0f} ha: single-cropped {r['single_cropped_ha']:,.0f}, "
                     f"double {r['double_cropped_ha']:,.0f}, triple {r['triple_cropped_ha']:,.0f} ha; "
                     f"cropping intensity {r['cropping_intensity_pct']:.0f}%.\n")
        t = top[top["upazila"].str.lower() == upz.lower()].sort_values("area_ha", ascending=False)
        if len(t):
            c["top_patterns"] = t[["pattern", "area_ha", "pct_upazila_nca"]].to_dict("records")
            L.append("## Where the region's dominant rotations sit in this upazila\n")
            L.append("| Rotation | Area (ha) | % of upazila cropland |\n|---|---|---|")
            L += [f"| {x.pattern} | {x.area_ha:,.0f} | {x.pct_upazila_nca:.1f} |" for x in t.itertuples()]
            L.append("")
        dv = div[div["upazila"].str.lower() == upz.lower()]
        if len(dv):
            r = dv.iloc[0]
            L.append(f"Crop diversity: {r['n_patterns']} rotations and {r['n_crops']} crops recorded; crop diversity "
                     f"index {r['crop_diversity_index']:.2f}.\n")
        h = hold[hold["district"] == dist]
        if len(h):
            r = h.iloc[0]
            c["farms"] = {"farm_holdings": int(r["farm_holdings"]), "small_farm_share": float(r["small_farm_share"]),
                          "tenancy_share": float(r["tenancy_share"]), "agri_labour_holdings": int(r["agri_labour_holdings"])}
            L.append("## Farms and cattle (district)\n")
            L.append(f"{r['farm_holdings']:,.0f} farm holdings, {r['small_farm_share']:.0%} small (under 2.5 acres); "
                     f"{r['tenancy_share']:.0%} of owner-operators rent some land; {r['agri_labour_holdings']:,.0f} "
                     f"farm-labour households (Agriculture Census 2019).")
        ct = cattle[cattle["district"] == dist]
        if len(ct):
            r = ct.iloc[0]
            c["cattle_2015"] = int(r["cattle_head_2015"])
            L.append(f" About {r['cattle_head_2015']:,.0f} cattle ({r['cattle_per_km2']:.0f} per km²; FAO GLW4, 2015).\n")
        ir = irr[(irr["district"] == dist) & (irr["year"] == "2022-23")]
        if len(ir):
            r = ir.iloc[0]
            c["irrigated_000acre_2022_23"] = {k: r[k] for k in ("aman", "boro", "wheat", "potato", "vegetables", "total")}
            L.append(f"Irrigated area 2022-23: {r['total']:.0f} thousand acres, of which Boro {r['boro']:.0f}, "
                     f"Aman {r['aman']:.0f}, wheat {r['wheat'] if pd.notna(r['wheat']) else 0:.0f}, "
                     f"potato {r['potato'] if pd.notna(r['potato']) else 0:.0f}.\n")
        L.append("## Yields (district, BBS)\n")
        L.append("| Crop | Area 2024-25 (ha) | Yield 2024-25 (t/ha; jute bales/ha) | Earliest season in panel | Yield then |")
        L.append("|---|---|---|---|---|")
        ylds = []
        for crop, var in KEY_CROPS:
            now = cd[(cd["crop"] == crop) & (cd["variant"] == var) & (cd["district"] == dist) & (cd["year"] == "2024-25")]
            if not len(now) or not now.iloc[0]["area_ha"]:
                continue
            first = panel[(panel["crop"] == crop) & (panel["variant"] == var) & (panel["district"] == dist)
                          & panel["yield_t_ha"].notna() & (panel["area_ha"] > 0)].sort_values("year") if len(panel) else pd.DataFrame()
            f0 = first.iloc[0] if len(first) else None
            ylds.append({"crop": crop, "area_ha_2024_25": now.iloc[0]["area_ha"], "yield_2024_25": now.iloc[0]["yield_t_ha"],
                         "first_season": None if f0 is None else f0["year"],
                         "yield_first": None if f0 is None else f0["yield_t_ha"]})
            unit = " bales/ha" if crop == "Jute" else ""  # BBS counts jute in bales
            then_season = "" if f0 is None else f0["year"]
            then_yield = "" if f0 is None else f"{f0['yield_t_ha']:.2f}"
            L.append(f"| {crop} | {now.iloc[0]['area_ha']:,.0f} | {now.iloc[0]['yield_t_ha']:.2f}{unit} | "
                     f"{then_season} | {then_yield} |")
        c["yields"] = ylds
        L.append("\nRice yields are clean rice. Minor-crop yields are derived from area and production.\n")
        d = dmg[(dmg["district"] == dist)]
        if len(d):
            ev = d.groupby("event")["production_loss_t"].sum().sort_values(ascending=False)
            c["damage_events"] = {k: float(v) for k, v in ev.items()}
            L.append("## Recorded crop losses (BBS damage tables)\n")
            L += [f"- {k}: {v:,.0f} t lost (all crops)" for k, v in ev.items()]
            L.append("")
        L.append("Sources: research/crops/*.csv and research/bbs/*.csv (see research/README.md).")
        (out_dir / f"{site}.md").write_text("\n".join(L), encoding="utf-8")
        cards[site] = c
        print(f"{site}: {len(L)} lines")
    (out_dir / "pilots.json").write_text(json.dumps(cards, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
