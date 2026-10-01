"""An environment ledger for four real rotation choices at Tanore (medium-high land, Talanda union), built only from
the numbers the other analyses already computed.

  water: winter irrigation beyond rain (FAO-56 on NASA POWER and IMERG, connect_tanore_rabi.csv) and how often the
         Aman needed a rescue irrigation (connect_tanore_aman.csv); set against the GLDAS groundwater fall under Tanore
  flooded-rice days: days a rice field stands flooded, from transplanting to two weeks before harvest; flooded
         paddies emit methane, so fewer days means less methane (a proxy, not a measurement)
  urea: SRDI's card for each crop on this land (srdi_frs_doses.csv); the legume fixes its own nitrogen
  bare days: days in the year with no crop in the field (median dates), when soil carbon and structure suffer
  heat: hot days at Boro flowering or wheat grain filling (heat_windows.csv, BMD-corrected)

Medians over the seasons in the source tables (2001-2025). Kharif-1 (March-June) is left bare in all four; a mungbean
or jute crop there would add to the lentil and mustard rows.

Output: research/pilots/environment_ledger_tanore.csv
Usage : python research/explore/environment_ledger.py  (after connect_check.py, heat_windows.py, groundwater.py)
"""
from __future__ import annotations

import unicodedata

import pandas as pd

from signals_common import RESEARCH

SITE = "RAJ_TANORE"
ROTATIONS = [  # name, Aman variety, winter crop in connect_tanore_rabi.csv, SRDI crop key (digits appear in the card name)
    ("BRRI dhan49 then Boro (BRRI dhan28)", "BRRI dhan49", "Boro (BRRI dhan28)", ("বোরো", "২৮")),
    ("BRRI dhan49 then wheat, sown 20 Nov", "BRRI dhan49", "Wheat (BARI Gom 33), sown 20 Nov", ("গম (সেচসহ)", None)),
    ("BRRI dhan71 then lentil", "BRRI dhan71", "Lentil (BARI Masur-8)", ("মসুর", None)),
    ("BRRI dhan71 then mustard", "BRRI dhan71", "Mustard (BARI Sarisha-14)", ("সরিষা", "১৪")),
]
nfc = lambda s: unicodedata.normalize("NFC", s)


def urea(cards: pd.DataFrame, season: str, name: str, digit: str | None) -> float:
    c = cards[(cards["season"] == season) & cards["crop_bn"].map(nfc).str.contains(nfc(name), regex=False)]
    if digit:
        c = c[c["crop_bn"].str.contains(digit, regex=False)]
    return float(c["urea_kg_ha"].iloc[0])


def main() -> None:
    aman = pd.read_csv(RESEARCH / "pilots" / "connect_tanore_aman.csv", parse_dates=["transplant", "maturity"])
    rabi = pd.read_csv(RESEARCH / "pilots" / "connect_tanore_rabi.csv", parse_dates=["sown", "harvest"])
    heat = pd.read_csv(RESEARCH / "pilots" / "heat_windows.csv")
    heat = heat[heat["site_id"] == SITE]
    gw = pd.read_csv(RESEARCH / "pilots" / "groundwater_trend.csv").set_index("area").loc[SITE]
    frs = pd.read_csv(RESEARCH / "soil" / "srdi_frs_doses.csv")
    cards = frs[(frs["site_id"] == SITE) & frs["land_type_bn"].map(nfc).str.startswith(nfc("মাঝারি উঁচু"))]
    aman_urea = urea(cards, "Kharif-2", "আমন রোপা", "৭১")  # BRRI dhan49 and 71 share this card
    rows = []
    for name, variety, winter, (crop_bn, digit) in ROTATIONS:
        a = aman[aman["variety"] == variety]
        w = rabi[rabi["crop"] == winter]
        a_days = int((a["maturity"] - a["transplant"]).dt.days.median())
        w_days = int((w["harvest"] - w["sown"]).dt.days.median()) + 1
        is_rice = winter.startswith("Boro")
        flooded = (a_days - 14) + ((w_days - 14) if is_rice else 0)
        if is_rice:
            heat_note = f"{heat['boro_days_ge35'].median():.0f} of 15 days at 35 C or more around Boro flowering"
        elif winter.startswith("Wheat"):
            heat_note = f"{heat['wheat_20nov_days_gt30'].median():.0f} days above 30 C at grain filling"
        else:
            heat_note = "flowers in January-February, before the heat"
        rows.append({"rotation": name, "aman_rescue_seasons": f"{int(a['needs_rescue_irrigation'].sum())} of {len(a)}",
                     "winter_irrigation_mm": int(w["net_irrigation_mm"].median()),
                     "groundwater_pumped_m3_per_ha": int(w["net_irrigation_mm"].median() * 10),
                     "flooded_rice_days": flooded,
                     "urea_kg_per_ha": round(aman_urea + urea(cards, "Rabi", crop_bn, digit)),
                     "legume": "yes" if "lentil" in name else "no",
                     "bare_days": 365 - a_days - w_days,
                     "heat": heat_note})
    d = pd.DataFrame(rows)
    d.to_csv(RESEARCH / "pilots" / "environment_ledger_tanore.csv", index=False)
    pd.set_option("display.width", 220)
    print(d.to_string(index=False))
    print(f"for scale: GLDAS groundwater under Tanore falls {abs(gw['annual_trend_per_year'])} mm a year "
          f"({gw['change_2003_07_to_2021_25']} mm since 2003-07), averaged over the 25 km cell")


if __name__ == "__main__":
    main()
