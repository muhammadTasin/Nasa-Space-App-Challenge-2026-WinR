"""Tidy the DLS "Livestock Economy at a glance" series (research/acquire/dls_livestock.py downloads it).

Tables 1 and 3 of the two latest editions cover 2015-16 to 2025-26: livestock and poultry numbers (lakh = 100,000
head) and milk, meat (lakh tonnes) and egg (crore = 10 million) production; the latest edition wins where they
overlap. DLS numbers are the department's own yearly estimates (cattle grow a steady ~0.6% a year), so they differ
from the Agriculture Census 2019 head count (bbs/livestock_census.csv: 29.5 million cows in all holdings).

Output: research/livestock/dls_livestock_economy.csv (long: year, item, value, unit)
Usage : python research/explore/dls_livestock.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

ITEMS = {"Cattle": "lakh head", "Buffalo": "lakh head", "Sheep": "lakh head", "Goat": "lakh head",
         "Chicken": "lakh head", "Duck": "lakh head", "Milk": "lakh tonnes", "Meat": "lakh tonnes", "Egg": "crore"}


def parse(path: Path) -> pd.DataFrame:
    pdf = pdfium.PdfDocument(str(path))
    text = re.sub(r"\s+", " ", " ".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf))))
    years = re.findall(r"20\d\d-\d\d", text.split("Table 1", 1)[1].split("Cattle", 1)[0])
    rows = []
    for item, unit in ITEMS.items():
        m = re.search(item + r"(?: Lakh Metric Ton| Crore number)?\s+((?:[\d.,]+\s+){%d})" % len(years), text)
        if not m:
            continue
        vals = [float(v.replace(",", "")) for v in m.group(1).split()]
        rows += [{"year": y, "item": item.lower(), "value": v, "unit": unit} for y, v in zip(years, vals)]
    return pd.DataFrame(rows).assign(edition=path.stem.rsplit("_", 1)[1])


def main() -> None:
    files = sorted((DATA / "dls").glob("livestock_economy_20*.pdf"))[-2:]  # the two latest editions
    df = pd.concat([parse(f) for f in files], ignore_index=True)
    df = df.sort_values("edition").drop_duplicates(["year", "item"], keep="last").sort_values(["item", "year"])
    df["source"] = "DLS, Livestock Economy at a glance (edition " + df["edition"] + ")"
    out = RESEARCH / "livestock" / "dls_livestock_economy.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns="edition").to_csv(out, index=False)
    print(df.pivot(index="year", columns="item", values="value").to_string())


if __name__ == "__main__":
    main()
