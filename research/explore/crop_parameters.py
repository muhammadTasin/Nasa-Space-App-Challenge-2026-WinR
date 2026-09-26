"""Assemble research/crops/crop_parameters.csv for the candidate rotation crops from the extracted sources.

Fills the columns of research/templates/crop_parameters_template.csv and adds a few more. Every value
comes from a table already in research/ (paths below); a blank means no source was found yet.

  varieties, duration, tolerances   crops/brri_rice_varieties.csv, crops/bari_field_crop_varieties.csv
  sowing and harvest windows        bbs/crop_calendar.csv (BBS Yearbook 2025, section 1.8)
  Kc ini / mid / end                crops/fao56_kc.csv (FAO-56 Table 12)
  national and Rajshahi yield       bbs/crop_district.csv, 2024-25 (BBS; rice is CLEAN rice, not paddy)
  harvest-time price                bbs/harvest_prices.csv, 2024-25 (DAM via BBS; paddy price for rice)
  cost and by-product value         bbs/census_costs.csv (Agriculture Census 2019 prices; HYV where split)

Usage: python research/explore/crop_parameters.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parents[1]
ACRE_PER_HA = 2.47105
PILOT_DISTRICT = "Rajshahi"

# template crop -> where to look in each source
SPEC = [
    dict(crop="Boro rice", season="Rabi (irrigated)", cal=("Boro Paddy", "HYV"), bbs=("Boro rice", "total"),
         price="Boro Paddy (Coarse)", census="HYV Boro", kc="Rice", varieties=("BRRI", "Boro",
         ["BRRI dhan28", "BRRI dhan81", "BRRI dhan88", "BRRI dhan89", "BRRI dhan92"]),
         sensitive="flowering (anthesis)", heat=35,
         heat_src="spikelet sterility above ~35 degC at anthesis (Yoshida 1981; Jagadish et al. 2007)"),
    dict(crop="T.Aman rice", season="Kharif-2 (rainfed)", cal=("Aman paddy", "HYV Transplant"),
         bbs=("Aman rice", "total"), price="Aman Paddy (Coarse)", census="HYV Amon", kc="Rice",
         varieties=("BRRI", "Aman", ["BRRI dhan49", "BRRI dhan71", "BRRI dhan75", "BRRI dhan87", "BRRI dhan103"]),
         sensitive="flowering (anthesis)", heat=35,
         heat_src="spikelet sterility above ~35 degC at anthesis (Yoshida 1981; Jagadish et al. 2007)"),
    dict(crop="Aus rice", season="Kharif-1", cal=("Aus paddy", "HYV Transplant"), bbs=("Aus rice", "total"),
         price="Aus Paddy (Coarse)", census="HYV Aus", kc="Rice",
         varieties=("BRRI", "Aus", ["BRRI dhan48", "BRRI dhan82", "BRRI dhan98", "BRRI dhan106"]),
         sensitive="flowering (anthesis)", heat=35,
         heat_src="spikelet sterility above ~35 degC at anthesis (Yoshida 1981; Jagadish et al. 2007)"),
    dict(crop="Wheat", season="Rabi", cal=("Wheat", ""), bbs=("Wheat", "all"), price="Wheat", census="Wheat",
         kc="Spring Wheat", varieties=None, sensitive="grain filling", heat=30,
         heat_src="grain-filling heat stress above ~30 degC (Wardlaw & Wrigley 1994); varieties now from BWMRI"),
    dict(crop="Maize", season="Rabi", cal=("Maize (Rabi)", ""), bbs=("Rabi Maize", "all"), price=None,
         census="Maize", kc="Maize, Field (grain) (field corn)", varieties=None, sensitive="tasselling/silking"),
    dict(crop="Mustard", season="Rabi", cal=("Rape Seed and Mustard", ""), bbs=("Rape and Mustard (Local+HYV)", "all"),
         price="Mustard", census=None, kc="Rapeseed, Canola",
         varieties=("BARI", "Mustard", ["BARI Mustard-14", "BARI Mustard-17", "BARI Mustard-18", "BARI Mustard-20"]),
         sensitive="flowering"),
    dict(crop="Potato", season="Rabi", cal=("Potato", ""), bbs=("Potato", "total"), price="Potato (Holand)",
         census="Potato", kc="Potato", varieties=("BARI", "Potato", ["BARI Potato-25", "BARI Potato-7", "BARI Potato-8"]),
         sensitive="tuber bulking"),
    dict(crop="Lentil", season="Rabi", cal=("Masur (Lentil)", ""), bbs=("Lentil (Masur)", "all"), price="Lentil (Masur)",
         census=None, kc="Lentil", varieties=("BARI", "Lentil", ["BARI Lentil-5", "BARI Lentil-6", "BARI Lentil-8"]),
         sensitive="flowering/pod fill", legume=True),
    dict(crop="Mungbean", season="Kharif-1", cal=("Mung bean", ""), bbs=("Green gram (Mug)", "all"),
         price="Green Gram (Mug)", census=None, kc="Green Gram and Cowpeas",
         varieties=("BARI", "Mungbean", ["BARI Mungbean-6", "BARI Mungbean-7", "BARI Mungbean-8"]),
         sensitive="flowering", legume=True),
    dict(crop="Grass pea (khesari)", season="Rabi (relay in Aman)", cal=("Kheshari", ""), bbs=("Kheshari", "all"),
         price="Grass pea (Kheshari)", census=None, kc="Peas - Dry/Seed", kc_note="proxy: FAO-56 has no grass pea",
         varieties=("BARI", "Grasspea", ["BARI Grasspea-3", "BARI Grasspea-5", "BARI Grasspea-6"]),
         sensitive="flowering", legume=True),
    dict(crop="Jute", season="Kharif-1", cal=("Jute", "Tossa (Olitorius)"), bbs=("Jute", "all"), price="Jute (tossa)",
         census="Jute", kc=None, kc_note="not in FAO-56 Table 12", varieties=None, sensitive=None,
         yield_note="BBS jute production is in bales, so no t/ha"),
    dict(crop="Dhaincha (green manure)", season="Kharif-1", cal=None, bbs=None, price=None, census=None, kc=None,
         varieties=None, sensitive=None, legume=True),
    dict(crop="Fodder (Rabi / Napier)", season="Rabi (Napier perennial)", cal=None, bbs=("Robi Fodder", "all"),
         price=None, census=None, kc="Sudan Grass hay (annual) - averaged cutting effects",
         kc_note="proxy: FAO-56 has no Napier grass", varieties=None, sensitive=None),
]


def main() -> None:
    cal = pd.read_csv(R / "bbs" / "crop_calendar.csv").fillna("")
    cd = pd.read_csv(R / "bbs" / "crop_district.csv")
    hp = pd.read_csv(R / "bbs" / "harvest_prices.csv")
    cc = pd.read_csv(R / "bbs" / "census_costs.csv")
    kc = pd.read_csv(R / "crops" / "fao56_kc.csv")
    brri = pd.read_csv(R / "crops" / "brri_rice_varieties.csv")
    bari = pd.read_csv(R / "crops" / "bari_field_crop_varieties.csv")
    rows = []
    for s in SPEC:
        r = {"crop": s["crop"], "season": s["season"]}
        src = []
        # varieties and duration
        if s.get("varieties"):
            who, season, names = s["varieties"]
            if who == "BRRI":
                v = brri[brri["variety"].isin(names) & brri["season"].str.contains(season, na=False)]
            else:
                v = bari[bari["variety"].isin(names)]
            r["variety_example"] = "; ".join(v["variety"])
            r["duration_days"] = f"{v['duration_days_min'].min():.0f}-{v['duration_days_max'].max():.0f}" \
                if v["duration_days_min"].notna().any() else None
            r["variety_yield_t_ha"] = f"{v['yield_t_ha_min'].min():g}-{v['yield_t_ha_max'].max():g}" \
                if v["yield_t_ha_min"].notna().any() else None
            src.append(f"{who} variety table")
        # sowing / harvest windows
        if s.get("cal"):
            c = cal[(cal["crop"] == s["cal"][0]) & (cal["type"] == s["cal"][1])]
            if len(c):
                r["sow_or_transplant_window"] = c.iloc[0]["sowing"]
                r["harvest_window"] = c.iloc[0]["harvest"]
                src.append("BBS crop calendar")
        # FAO-56 Kc
        if s.get("kc"):
            k = kc[kc["crop"] == s["kc"]]
            if len(k):
                r.update(kc_ini=k.iloc[0]["kc_ini"], kc_mid=k.iloc[0]["kc_mid"], kc_end=k.iloc[0]["kc_end"])
                src.append("FAO-56 Table 12" + (f" ({s['kc_note']})" if s.get("kc_note") else ""))
        elif s.get("kc_note"):
            src.append(s["kc_note"])
        r["sensitive_stage"] = s.get("sensitive")
        if s.get("heat"):
            r["heat_threshold_c"] = s["heat"]
            src.append(s["heat_src"])
        # tolerances from the variety tables
        if s.get("varieties") and s["varieties"][0] == "BRRI":
            season = s["varieties"][1]
            sea = brri[brri["season"].str.contains(season, na=False)]
            sub = sea[sea["submergence_tolerant"] == True]["variety"].tolist()  # noqa: E712
            salt = sea[sea["salt_tolerant"] == True]  # noqa: E712
            dro = sea[sea["drought_tolerant"] == True]["variety"].tolist()  # noqa: E712
            r["flood_submergence_tolerance"] = ("varieties: " + ", ".join(sub)) if sub else "none listed"
            r["salinity_tolerance_ds_m"] = (f"up to {salt['salt_tolerance_ds_m'].max():g} (seedling): "
                                            + ", ".join(salt["variety"])) if len(salt) else None
            r["drought_tolerant_varieties"] = ", ".join(dro) or None
        elif s.get("varieties"):
            crop_b = s["varieties"][1]
            b = bari[bari["crop"] == crop_b]
            r["salinity_tolerance_ds_m"] = ("tolerant: " + ", ".join(b[b["salt_tolerant"]]["variety"])) \
                if b["salt_tolerant"].any() else None
            r["drought_tolerant_varieties"] = ", ".join(b[b["drought_tolerant"]]["variety"]) or None
            r["fits_after_aman"] = ", ".join(b[b["fits_after_aman"]]["variety"]) or None
        r["n_fixing_legume"] = "yes" if s.get("legume") else "no"
        # yields: national and pilot district, 2024-25
        if s.get("bbs"):
            d = cd[(cd["crop"] == s["bbs"][0]) & (cd["variant"] == s["bbs"][1]) & (cd["year"] == "2024-25")]
            if len(d) and not s.get("yield_note"):
                r["typical_yield_t_ha"] = round(d["production_t"].sum() / d["area_ha"].sum(), 2)
                pil = d[d["district"] == PILOT_DISTRICT]
                if len(pil) and pil["area_ha"].sum() > 0:
                    r[f"yield_{PILOT_DISTRICT.lower()}_t_ha"] = round(pil["production_t"].sum() / pil["area_ha"].sum(), 2)
                r["national_area_ha"] = round(d["area_ha"].sum())
                r[f"{PILOT_DISTRICT.lower()}_area_ha"] = round(d.loc[d["district"] == PILOT_DISTRICT, "area_ha"].sum())
                src.append("BBS 2024-25 district tables" + (" (clean rice)" if "rice" in s["crop"] else ""))
            elif s.get("yield_note"):
                src.append(s["yield_note"])
        # price
        if s.get("price"):
            p = hp[hp["item"] == s["price"]]
            if len(p) and pd.notna(p.iloc[0]["2024-25"]):
                r["farmgate_price_bdt_kg"] = round(p.iloc[0]["2024-25"] / 100, 2)
                src.append(f"harvest-time price 2024-25 ({s['price']})")
        # census costs (2019 prices)
        if s.get("census"):
            c = cc[(cc["crop"] == s["census"]) & (cc["area"] == "Bangladesh")]
            if len(c):
                c = c.iloc[0]
                r["cost_bdt_ha"] = round(c["cost_tk_per_acre"] * ACRE_PER_HA)
                r["crop_value_bdt_ha"] = round(c["crop_value_tk_per_acre"] * ACRE_PER_HA)
                r["byproduct_value_bdt_ha"] = round(c["byproduct_value_tk_per_acre"] * ACRE_PER_HA)
                r["net_return_bdt_ha"] = round(c["net_return_tk_per_acre"] * ACRE_PER_HA)
                src.append("Agriculture Census 2019 costs (2019 taka)")
        r["source"] = "; ".join(src)
        rows.append(r)
    out = pd.DataFrame(rows)
    order = ["crop", "variety_example", "season", "sow_or_transplant_window", "harvest_window", "duration_days",
             "kc_ini", "kc_mid", "kc_end", "sensitive_stage", "heat_threshold_c", "flood_submergence_tolerance",
             "salinity_tolerance_ds_m", "drought_tolerant_varieties", "fits_after_aman", "n_fixing_legume",
             "variety_yield_t_ha", "typical_yield_t_ha", f"yield_{PILOT_DISTRICT.lower()}_t_ha", "national_area_ha",
             f"{PILOT_DISTRICT.lower()}_area_ha", "farmgate_price_bdt_kg", "cost_bdt_ha", "crop_value_bdt_ha",
             "byproduct_value_bdt_ha", "net_return_bdt_ha", "source"]
    out = out.reindex(columns=order)
    out.to_csv(R / "crops" / "crop_parameters.csv", index=False)
    print(out.drop(columns=["source"]).to_string(index=False))


if __name__ == "__main__":
    main()
