"""Parse BRRI rice-variety factsheets into one table.

Two sources, one schema:
  * factsheets with a text layer: Bangla typed in the legacy Bijoy/SutonnyMJ encoding, so the
    extracted text is ASCII look-alikes (e.g. "RxebKvj" = jibonkal, growth duration). Parsed here
    with patterns on those codes.
  * scanned factsheets (image only): read by eye from rendered pages and entered in
    research/crops/brri_manual_entries.csv with the same columns. This script merges them.

Output: research/crops/brri_rice_varieties.csv (one row per variety, source file kept).
Usage: python research/explore/brri_varieties.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

CROPS = RESEARCH / "crops"
# Bijoy spellings seen in the factsheets (several have variants or typos); applied inside date brackets only
MONTHS = {"Rvbyqvwi": "Jan", "Rvbyqvix": "Jan", "Jani": "Jan", "†deªæqvwi": "Feb", "gvP©": "Mar", "GwcÖj": "Apr",
          "Gwcªj": "Apr", "†g": "May", "‡g": "May", "Ryb": "Jun", "Rb": "Jun", "RyjvB": "Jul", "AvvMó": "Aug",
          "AvMó": "Aug", "AvM÷": "Aug", "†m‡Þ¤^i": "Sep", "†m‡Þ¤¦i": "Sep", "A‡±vei": "Oct", "b‡f¤^i": "Nov",
          "b‡f¤¦i": "Nov", "wW‡m¤^i": "Dec", "wW‡m¤¦i": "Dec",
          "†_‡K": "-", "‡_‡K": "-", "ga¨": "mid", "cÖ_g mßvn": "1st week"}
NUM = r"(\d+(?:\.\d+)?)"
RANGE = NUM + r"(?:\s*[-–]\s*" + NUM + r")?"
TOL = r"\S*\s*(?:mnbkxj|mwnòy|mn¨)"  # "...tolerant" / "can tolerate"
TRAITS = {  # a hazard word only counts when "tolerant" follows it ("if drought comes, irrigate" must not)
    "salt_tolerant": r"jeY" + TOL,
    "submergence_tolerant": r"RjgMœ" + TOL + r"|Wz‡e\s*_vK‡jI",
    "drought_tolerant": r"Liv" + TOL,
    "cold_tolerant": r"(?:kxZ|VvÛv)" + TOL,
}


def variety_name(fname: str) -> str | None:
    f = fname.split("__")[-1].lower().replace("_", " ").replace("-", " ")
    for pat, fmt in ((r"hy(?:brid)?\s*dhan\s*(\d+)|hybriddhan\s*(\d+)", "BRRI hybrid dhan{}"),
                     (r"brri\s*d(?:han)?\s*(\d+)|brridhan\s*(\d+)", "BRRI dhan{}"), (r"\bbr\s*(\d+)", "BR{}")):
        m = re.search(pat, f)
        if m:
            n = int(next(g for g in m.groups() if g))
            # BR1-BR26 kept the BR name; from 27 on the same varieties are called BRRI dhan
            return f"BRRI dhan{n}" if fmt == "BR{}" and n >= 27 else fmt.format(n)
    return None


def first_range(pattern: str, text: str, lo: float, hi: float) -> tuple[float | None, float | None]:
    for m in re.finditer(pattern, text, re.S):
        a = float(m.group(1)); b = float(m.group(2)) if m.group(2) else a
        if lo <= a <= hi and lo <= b <= hi:
            return a, b
    return None, None


def dates_in(line: str) -> str | None:
    """Gregorian dates on a calendar line. Most sheets put them in brackets after the Bangla dates,
    '(15 Jun-15 Jul)'; some put them first, '20 Nov - 16 Dec A_©vr <Bangla dates>' (A_©vr = 'that is')."""
    m = re.search(r"\(([^)]*)\)", line)
    if m:
        s = m.group(1)
    else:
        m = re.search(r"[:t]\s*([^:]*?)\s*A_©vr", line)
        if not m:
            return None
        s = m.group(1)
    for k, v in MONTHS.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    return s if re.search(r"[A-Z][a-z]{2}", s) else None


def parse_text(t: str) -> dict:
    d0, d1 = first_range(r"RxebKvj\D{0,40}?" + RANGE + r"\s*w`b", t, 70, 200)
    # "7.0 Ub †_‡K 7.5 Ub" (7.0 to 7.5 t) first, then "5.5-6.0 Ub"
    y0, y1 = first_range(r"djb.{0,120}?" + NUM + r"\s*Ub\s*[†‡]_‡K\s*" + NUM, t, 1.5, 12)
    if y0 is None:
        y0, y1 = first_range(r"djb.{0,120}?" + RANGE + r"\s*Ub", t, 1.5, 12)
    h0, _ = first_range(r"D.PZv\D{0,20}?" + RANGE, t, 50, 200)
    yr = re.search(r"(19[6-9]\d|20[0-2]\d)\s*mv‡j", t)
    seed_age = re.search(r"Pvivi eqm\s*[:t]?\s*(\d+)\s*[-–]\s*(\d+)", t)
    lines = t.splitlines()
    # seedbed sowing ("exR Zjvq") or, for direct-seeded Aus, "1. exR ecb" (seed sowing)
    sow = next((dates_in(l) for l in lines
                if re.search(r"exR\s*Zjvq|exRZjvq|^\s*1\.\s*exR\s*ecb", l) and dates_in(l)), None)
    harvest = next((dates_in(l) for l in lines if "KvUv" in l and dates_in(l)), None)
    zinc = re.search(r"wRsK.{0,40}?" + NUM + r"\s*wgwjMÖvg", t, re.S)
    salt = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*wWGm/", t)]
    rec = {"duration_days_min": d0, "duration_days_max": d1, "yield_t_ha_min": y0, "yield_t_ha_max": y1,
           "plant_height_cm": h0, "release_year": int(yr.group(1)) if yr else None,
           "seedling_age_days": f"{seed_age.group(1)}-{seed_age.group(2)}" if seed_age else None,
           "seedbed_sowing": sow, "harvest": harvest,
           "zinc_mg_kg": float(zinc.group(1)) if zinc else None, "aromatic": bool(re.search(r"myMwÜ", t)),
           "salt_tolerance_ds_m": max(salt) if salt else None}
    rec.update({k: bool(re.search(p, t)) for k, p in TRAITS.items()})
    text_seasons = {s for s, code in (("Aman", "Avgb"), ("Boro", "†ev‡iv"), ("Aus", "AvDk")) if code in t}
    rec["seasons_in_text"] = ";".join(sorted(text_seasons))
    return rec


COLUMNS = ["variety", "season", "release_year", "duration_days_min", "duration_days_max", "yield_t_ha_min",
           "yield_t_ha_max", "plant_height_cm", "seedbed_sowing", "seedling_age_days", "harvest",
           "salt_tolerant", "salt_tolerance_ds_m", "submergence_tolerant", "drought_tolerant", "cold_tolerant", "aromatic",
           "zinc_mg_kg", "notes", "source", "source_file", "url"]


def main() -> None:
    idx = json.loads((DATA / "brri" / "index.json").read_text(encoding="utf-8"))
    rows = []
    for r in idx:
        if "error" in r or r.get("chars", 0) < 50:
            continue
        t = (DATA / "brri" / "pdf" / r["file"]).with_suffix(".txt").read_text(encoding="utf-8")
        rec = parse_text(t)
        folder_season = next((s for s in ("Aman", "Boro", "Aus") if f"Module_2_{s}" in r["file"]), None)
        # season pages first; the training-manual folder names are sometimes wrong (dhan59 sits in "Aman")
        seasons = r["seasons"] or ([folder_season] if folder_season else [])
        season = ";".join(sorted(seasons)) or rec.pop("seasons_in_text")
        rec.pop("seasons_in_text", None)
        rows.append({"variety": variety_name(r["file"]), "season": season, **rec, "notes": None,
                     "source": "text layer (Bijoy encoding)", "source_file": r["file"], "url": r["url"]})
    auto = pd.DataFrame(rows, columns=COLUMNS)
    # one row per variety: keep the factsheet that yielded the most fields
    auto["filled"] = auto[COLUMNS[2:11]].notna().sum(axis=1)
    auto = auto.sort_values("filled", ascending=False).drop_duplicates("variety").drop(columns="filled")
    manual_path = CROPS / "brri_manual_entries.csv"
    manual = pd.read_csv(manual_path) if manual_path.exists() else pd.DataFrame(columns=COLUMNS)
    manual["source"] = "read from scanned factsheet"
    table = pd.concat([manual.reindex(columns=COLUMNS), auto[~auto["variety"].isin(manual["variety"])]],
                      ignore_index=True)
    key = lambda v: (0 if v.startswith("BR") and not v.startswith("BRRI") else 1 if "hybrid" in v else 2,
                     int(re.findall(r"\d+", v)[-1]))
    table = table.sort_values("variety", key=lambda s: s.map(key)).reset_index(drop=True)
    CROPS.mkdir(parents=True, exist_ok=True)
    table.to_csv(CROPS / "brri_rice_varieties.csv", index=False)
    cols = ["duration_days_min", "yield_t_ha_min", "plant_height_cm", "release_year", "seedbed_sowing", "harvest"]
    from_text = table["source"].str.startswith("text").sum()
    print(f"{len(table)} varieties ({from_text} parsed from text, {len(table) - from_text} read from scans)")
    print("fields filled:", {c: int(table[c].notna().sum()) for c in cols})


if __name__ == "__main__":
    main()
