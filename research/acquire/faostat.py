"""FAOSTAT crops and livestock production (QCL), Bangladesh only, 1961 to the latest year.

Source: FAO. FAOSTAT Crops and livestock products, bulk file Production_Crops_Livestock_E_Asia.zip
(https://bulks-faostat.fao.org/production/). FAO's statistical data are CC BY 4.0.
Output: research/crops/faostat_bangladesh.csv (item, element, year, value, unit; long format) and a wide
summary of area/yield/production for the rotation crops. Usage: python research/acquire/faostat.py
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from _common import RESEARCH, out_dir, session, write_provenance

URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Asia.zip"
ITEMS = ["Rice", "Wheat", "Maize (corn)", "Potatoes", "Lentils, dry", "Mustard seed", "Rape or colza seed",
         "Sesame seed", "Groundnuts, excluding shelled", "Jute, raw or retted", "Onions and shallots, dry (excluding dehydrated)",
         "Chick peas, dry", "Peas, dry", "Sweet potatoes", "Garlic", "Soya beans", "Sunflower seed", "Cattle",
         "Buffalo", "Goats", "Raw milk of cattle", "Meat of cattle with the bone, fresh or chilled"]


def main() -> None:
    d = out_dir("faostat")
    z = d / "Production_Crops_Livestock_E_Asia.zip"
    if not z.exists():
        s = session()
        s.headers["User-Agent"] = "Mozilla/5.0 (WinR research; NASA Space Apps)"
        z.write_bytes(s.get(URL, timeout=600).content)
        write_provenance(z, source="FAOSTAT QCL bulk (Asia)", url=URL, license="CC BY 4.0")
    with zipfile.ZipFile(z) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv") and "Normalized" in n) if any(
            "Normalized" in n for n in zf.namelist()) else next(n for n in zf.namelist() if n.endswith(".csv")
                                                                  and "Flags" not in n and "Area" not in n)
        raw = pd.read_csv(io.BytesIO(zf.read(name)), encoding="latin-1")
    bd = raw[raw["Area"] == "Bangladesh"]
    if "Year" not in bd.columns:  # wide file: Y1961, Y1962 ... -> long
        ycols = [c for c in bd.columns if c.startswith("Y") and c[1:].isdigit()]
        bd = bd.melt(id_vars=["Item", "Element", "Unit"], value_vars=ycols, var_name="Year", value_name="Value")
        bd["Year"] = bd["Year"].str[1:].astype(int)
    long = bd[["Item", "Element", "Year", "Value", "Unit"]].dropna(subset=["Value"])
    long.columns = ["item", "element", "year", "value", "unit"]
    out = RESEARCH / "crops" / "faostat_bangladesh.csv"
    long.to_csv(out, index=False)
    sel = long[long["item"].isin(ITEMS) & long["element"].isin(["Area harvested", "Production", "Yield", "Stocks"])]
    wide = sel.pivot_table(index=["item", "year"], columns="element", values="value").reset_index()
    wide.to_csv(RESEARCH / "crops" / "faostat_bangladesh_rotation_crops.csv", index=False)
    print(f"{len(long):,} rows, {long['item'].nunique()} items, {long['year'].min()}-{long['year'].max()}")
    missing = sorted(set(ITEMS) - set(long["item"]))
    if missing:
        print("item names not found (FAOSTAT naming):", missing)


if __name__ == "__main__":
    main()
