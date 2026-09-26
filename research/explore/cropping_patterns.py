"""Cropping patterns of Bangladesh from BRRI's national survey (every upazila, 2014-15):
Nasim M, Shahidullah SM, Saha A, Muttaleb MA, Aditya TL, Ali MA, Kabir MS (2017) Distribution of crops and
cropping patterns in Bangladesh. Bangladesh Rice Journal 21(2): 1-55. doi:10.3329/brj.v21i2.38195

Input : the paper's PDF (the team keeps it in "raw, collected datas/admin,+1-55.pdf"; open access on BanglaJOL)
Output: research/crops/
  cropping_patterns_bd.csv          Table 2: all 316 patterns, area (ha), % of net cropped area, districts, upazilas
  dominant_patterns_by_district.csv Tables 18-23: where the six most common patterns are, by district
  district_crop_diversity.csv       Table 25: patterns, crops, diversity indices, cropping intensity by district

Usage: python research/explore/cropping_patterns.py [path/to/pdf]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bbs_yearbook import district  # noqa: E402  (same 64-name district matching)

REPO = Path(__file__).resolve().parents[2]
PDF = REPO / "raw, collected datas" / "admin,+1-55.pdf"
OUT = REPO / "research" / "crops"
CITE = "Nasim et al. 2017, Bangladesh Rice Journal 21(2):1-55, doi:10.3329/brj.v21i2.38195"
DASH = r"\s*[−–-]\s*"
# BRRI abbreviations in the district column of Tables 18-25
SHORT = {"b.baria": "Brahamanbaria", "chapain.ganj": "Nawabganj", "coxbazar": "Cox's Bazar",
         "borguna": "Barguna", "jhenaidaha": "Jhenaidah", "moulvibazar": "Maulvibazar"}


def dist(name: str) -> str | None:
    return SHORT.get(name.strip().lower()) or district(name)


def season_split(pattern: str) -> dict:
    """'Boro−Fallow−T. Aman' -> Rabi / Kharif-1 / Kharif-2 slots. Two-crop patterns such as 'Boro−B.Aman'
    have a long crop spanning both kharif seasons; 4-crop patterns keep the extra crop in 'extra'."""
    parts = [p.strip() for p in re.split(DASH, pattern) if p.strip()]
    crops = [p for p in parts if p.lower() != "fallow"]
    rec = {"n_crops": len(crops), "fallow_slots": len(parts) - len(crops),
           "has_rice": any(re.search(r"boro|aus|aman", p, re.I) for p in parts),
           "has_legume": any(re.search(r"lentil|mungbean|grasspea|gram|pea|soybean|groundnut|felon|blackgram|"
                                       r"cowpea|chickpea|dhaincha", p, re.I) for p in parts)}
    if len(parts) == 3:
        rec.update(rabi=parts[0], kharif1=parts[1], kharif2=parts[2], extra=None)
    elif len(parts) == 2:
        rec.update(rabi=parts[0], kharif1=parts[1], kharif2=parts[1], extra=None)
    else:
        rec.update(rabi=parts[0], kharif1=parts[1] if len(parts) > 1 else None,
                   kharif2=parts[2] if len(parts) > 2 else None, extra="−".join(parts[3:]) or None)
    return rec


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    with pdfplumber.open(pdf_path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    OUT.mkdir(parents=True, exist_ok=True)

    # Table 2 (pages 16-23)
    pat = re.compile(r"^(\d{3})\s+(.+?)\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+)\s*$")
    rows = []
    for i in range(15, 23):
        for line in pages[i].splitlines():
            if m := pat.match(line.strip()):
                rows.append({"rank": int(m.group(1)), "pattern": re.sub(DASH, "−", m.group(2)).strip(),
                             "area_ha": int(m.group(3)), "pct_nca": float(m.group(4)),
                             "n_districts": int(m.group(5)), "n_upazilas": int(m.group(6))})
    cp = pd.DataFrame(rows).drop_duplicates("rank").sort_values("rank")
    cp = pd.concat([cp, cp["pattern"].apply(season_split).apply(pd.Series)], axis=1)
    cp["source"] = CITE
    cp.to_csv(OUT / "cropping_patterns_bd.csv", index=False)

    # Tables 18-23: district distribution of the six dominant patterns
    drows, current = [], None
    for i in range(43, 52):
        for line in pages[i].splitlines():
            if t := re.match(r"^Table (1[89]|2[0-3])\. Distribution of the .*?dominant\s+(.+?)\s+cropping pattern",
                             line.strip()):
                current = re.sub(DASH, "−", t.group(2)).strip()
                continue
            m = re.match(r"^(\d{2})\s+([A-Za-z.' ]+?)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$", line.strip())
            if m and current and dist(m.group(2)):
                drows.append({"pattern": current, "district": dist(m.group(2)), "area_ha": int(m.group(3)),
                              "pct_district_nca": float(m.group(4)), "pct_of_pattern_in_bd": float(m.group(5))})
    dp = pd.DataFrame(drows).drop_duplicates(["pattern", "district"])
    dp["source"] = CITE
    dp.to_csv(OUT / "dominant_patterns_by_district.csv", index=False)

    # Table 25: diversity and cropping intensity
    vrows = []
    for i in range(52, 55):
        for line in pages[i].splitlines():
            m = re.match(r"^(\d{2})\s+([A-Za-z.' ]+?)\s+(\d+)\s+(\d+)\s+(\d\.\d+)\s+(\d\.\d+)\s+(\d+)\s*$", line.strip())
            if m and dist(m.group(2)):
                vrows.append({"district": dist(m.group(2)), "n_patterns": int(m.group(3)), "n_crops": int(m.group(4)),
                              "pattern_diversity_index": float(m.group(5)), "crop_diversity_index": float(m.group(6)),
                              "cropping_intensity_pct": int(m.group(7))})
    dv = pd.DataFrame(vrows).drop_duplicates("district")
    dv["source"] = CITE
    dv.to_csv(OUT / "district_crop_diversity.csv", index=False)

    print(f"patterns: {len(cp)} (ranks {cp['rank'].min()}-{cp['rank'].max()}), area {cp['area_ha'].sum():,} ha, "
          f"{cp['pct_nca'].sum():.1f}% of NCA")
    print(f"dominant-pattern rows: {len(dp)} across {dp['pattern'].nunique()} patterns")
    print(f"district diversity rows: {len(dv)}")


if __name__ == "__main__":
    main()
