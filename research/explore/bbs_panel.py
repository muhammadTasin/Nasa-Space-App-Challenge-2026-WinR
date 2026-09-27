"""District crop panel from every BBS yearbook edition (research/acquire/bbs_yearbooks.py downloads them).

Each edition reports 2-3 seasons; stacking them gives district area, yield and production for ~2013-14 to
2024-25. Editions before ~2015 report 23 old 'agricultural regions' instead of the 64 districts; those rows
do not match a district and are dropped. Where editions overlap, the latest edition wins (BBS revises), and the
overlap is used to report how much the editions disagree.

Output: research/bbs/crop_district_panel.csv (+ crop_district_panel_editions.csv, the edition-level rows)
Usage: python research/explore/bbs_panel.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bbs_yearbook import DATA, OUT, crop_tables  # noqa: E402

BBS = DATA / "bbs"


def chapter3_bounds(pdf_path: Path) -> tuple[int, int]:
    """First and last PDF page of Chapter 3, found from the fast pdfium text (cached: the scan is slow)."""
    cache = pdf_path.with_suffix(".ch3bounds.json")
    if cache.exists():
        return tuple(json.loads(cache.read_text()))
    first, last = _scan_bounds(pdf_path)
    cache.write_text(json.dumps([first, last]))
    return first, last


def _scan_bounds(pdf_path: Path) -> tuple[int, int]:
    doc = pdfium.PdfDocument(str(pdf_path))
    texts = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    start = next((i for i, t in enumerate(texts) if i > 30 and re.search(r"(?i)estimat\w* of (aus|local aus)", t)), 40)
    end = next((i for i, t in enumerate(texts) if i > start + 60 and re.search(
        r"(?i)estimates? of crop damage|damage of different crops|land utili[sz]ation|intensity of cropping", t)),
        int(len(texts) * 0.7))
    return start + 1, end + 1


def edition_pages(pdf_path: Path, first: int, last: int) -> list[str]:
    cache = pdf_path.with_suffix(".ch3.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    pages = [""] * (last + 5)
    with pdfplumber.open(pdf_path) as pdf:
        for p in range(first, min(last, len(pdf.pages) + 1)):
            pages[p - 1] = pdf.pages[p - 1].extract_text() or ""
    cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def main() -> None:
    frames = []
    for f in sorted(BBS.glob("BBS_Yearbook_Agricultural_Statistics_*.pdf")):
        edition = int(re.search(r"(\d{4})\.pdf$", f.name).group(1))
        first, last = chapter3_bounds(f)
        df = crop_tables(edition_pages(f, first, last), first, last, edition)
        df["edition"] = edition
        frames.append(df)
        print(f"{edition}: pages {first}-{last}, {len(df):6,d} rows, {df['district'].nunique()} districts, "
              f"seasons {sorted(df['year'].unique())}", flush=True)
    allr = pd.concat(frames, ignore_index=True)
    key = ["crop", "variant", "district", "year"]
    # Some editions (2015-2018) print no 'total' rice table, only local/HYV/hybrid: derive the total as their sum
    # within the same edition, and check the method where a printed total exists.
    rice = allr[allr["crop"].isin(["Aus rice", "Aman rice", "Boro rice"])]
    parts = rice[rice["variant"] != "total"].groupby(["edition", "crop", "district", "year"])[
        ["area_acre", "area_ha", "production_t"]].sum(min_count=1).reset_index()
    parts["variant"] = "total"
    parts["yield_t_ha"] = (parts["production_t"] / parts["area_ha"]).where(parts["area_ha"] > 0).round(3)
    printed = rice[rice["variant"] == "total"].set_index(["edition", "crop", "district", "year"])["production_t"]
    both = parts.set_index(["edition", "crop", "district", "year"])["production_t"].to_frame("derived").join(
        printed.rename("printed"), how="inner").dropna()
    both = both[both["printed"] > 0]
    agree = ((both["derived"] - both["printed"]).abs() / both["printed"]).describe(percentiles=[0.5, 0.9])
    print(f"derived vs printed rice totals ({int(agree['count'])} cells): median diff {agree['50%']:.2%}, "
          f"90th pct {agree['90%']:.2%}")
    have = set(map(tuple, rice[rice["variant"] == "total"][["edition", "crop", "district", "year"]].values))
    parts = parts[[t not in have for t in map(tuple, parts[["edition", "crop", "district", "year"]].values)]]
    parts["note"] = "total derived as the sum of the edition's local/HYV/hybrid (and broadcast/transplant) tables"
    allr = pd.concat([allr, parts], ignore_index=True)
    allr.to_csv(DATA / "bbs" / "crop_district_panel_editions.csv", index=False)  # 33 MB: kept out of git
    # disagreement between editions on the same crop/district/season (major crops, production)
    both = allr.dropna(subset=["production_t"]).groupby(key)["production_t"].agg(["min", "max", "count"])
    both = both[(both["count"] > 1) & (both["max"] > 0)]
    rel = ((both["max"] - both["min"]) / both["max"]).describe(percentiles=[0.5, 0.9])
    panel = allr.sort_values("edition").drop_duplicates(key, keep="last").drop(columns=["table", "page"], errors="ignore")
    panel.to_csv(DATA / "bbs" / "crop_district_panel_all_crops.csv", index=False)
    # committed version: the crops a rotation can use, rounded, so the file stays small
    keep = ["Aus rice", "Aman rice", "Boro rice", "Wheat", "Potato", "Jute", "Rabi Maize", "Kharif Maize",
            "Maize (Rabi & Kharif)", "Lentil (Masur)", "Green gram (Mug)", "Kheshari", "Black gram (Mashkalai)", "Gram",
            "Rape and Mustard (Local+HYV)", "Sesame Till (Rabi & Kharif)", "Groundnut (Rabi & kharif)", "Sunflower (Surjamukhi)",
            "Onion", "Garlic", "Robi Fodder", "Bhadoi Fodder", "Sweet Potato"]
    # seasons before 2012-13 come from books that report major crops by 23 old regions: incomplete, so cut
    small = panel[panel["crop"].isin(keep) & (panel["year"] >= "2012-13")].round(
        {"area_acre": 0, "area_ha": 0, "yield_t_ha": 3, "production_t": 0})
    small.to_csv(OUT / "crop_district_panel.csv", index=False)
    print(f"committed panel: {len(small):,} rows, {small['crop'].nunique()} crops")
    rice = panel[(panel["crop"].str.contains("rice")) & (panel["variant"] == "total")]
    print(f"panel: {len(panel):,} rows; total-rice seasons per district: "
          f"{rice.groupby(['crop', 'district'])['year'].nunique().median():.0f} (median)")
    print(f"editions disagree on production for {int(rel['count'])} overlapping cells: median "
          f"{rel['50%']:.1%}, 90th pct {rel['90%']:.1%}")


if __name__ == "__main__":
    main()
