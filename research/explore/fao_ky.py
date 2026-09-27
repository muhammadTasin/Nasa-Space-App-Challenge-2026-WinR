"""Seasonal yield response factors (Ky) from FAO Irrigation and Drainage Paper 66 (Steduto et al. 2012), Table 1,
which reprints the FAO-33 values (Doorenbos & Kassam 1979).

Ky links relative yield loss to relative evapotranspiration deficit: 1 - Ya/Yx = Ky (1 - ETa/ETx). Ky > 1: the
crop loses more than proportionally when water-stressed. Table 1 has no rice, lentil, mustard, chickpea or jute;
FAO-66 Table 2 (p. 12) gives stage-by-stage values for 9 crops against IAEA trials, which differ widely, so treat
any single Ky as a planning figure, not a site calibration.

Input : research/data/fao/FAO66_crop_yield_response_to_water.pdf (https://www.fao.org/4/i2800e/i2800e.pdf)
Output: research/crops/fao_ky_seasonal.csv
Usage : python research/explore/fao_ky.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

PDF = DATA / "fao" / "FAO66_crop_yield_response_to_water.pdf"
CITE = "FAO Irrigation and Drainage Paper 66 (Steduto et al. 2012), Table 1, from FAO-33 (Doorenbos & Kassam 1979)"


def main() -> None:
    pdf = pdfium.PdfDocument(str(PDF))
    page = next(i for i in range(15, 40) if "Table 1 Seasonal Ky values" in pdf[i].get_textpage().get_text_range())
    text = pdf[page].get_textpage().get_text_range().replace("\r\n", "\n")
    body = text.split("Table 1 Seasonal Ky values", 1)[1].split("\n", 2)[2]  # skip title and header lines
    rows = []
    for name, lo, hi in re.findall(r"([A-Z][a-z]+(?: [a-z]+)?)\s+(\d[.,]\d+)(?:-(\d[.,]\d+))?", body):
        lo = float(lo.replace(",", "."))  # the table prints "Peas 1,15"
        rows.append({"crop": name, "ky_min": lo, "ky_max": float(hi.replace(",", ".")) if hi else lo})
    df = pd.DataFrame(rows).sort_values("crop")
    df["source"] = f"{CITE}, PDF page {page + 1}"
    out = RESEARCH / "crops" / "fao_ky_seasonal.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} crops -> {out.relative_to(RESEARCH.parent)}")
    print(df[["crop", "ky_min", "ky_max"]].to_string(index=False))


if __name__ == "__main__":
    main()
