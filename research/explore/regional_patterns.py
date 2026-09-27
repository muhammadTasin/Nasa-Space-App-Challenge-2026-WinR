"""Upazila-level land use and cropping patterns from BRRI's 14 regional papers (Bangladesh Rice Journal 21(2),
2017; survey year 2014-15). Run research/acquire/brri_regional_papers.py first.

Output: research/crops/
  upazila_land_use.csv      Table 1 of each paper: single/double/triple-cropped area, NCA, cropping intensity
  regional_patterns.csv     every pattern listed for each region, with area and number of upazilas
  upazila_top_patterns.csv  where each region's 5-6 dominant patterns are, upazila by upazila
  upazila_diversity.csv     patterns, crops, diversity indices and cropping intensity per upazila
Upazilas are matched to geoBoundaries ADM3 names (fuzzy) and given a district and centroid, so they can be
joined to the NASA data. Usage: python research/explore/regional_patterns.py
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH, SITES  # noqa: E402

REG = DATA / "brri" / "regional"
OUT = RESEARCH / "crops"
N = r"(\d[\d,]*\.?\d*)"
ABBR = [(r"\bF\b", "Fallow"), (r"\bVeg(?:etab|tab|et)?\b", "Vegetable"), (r"\bWht\b", "Wheat"),
        (r"\bMung\b", "Mungbean"), (r"\bB\.\s?gram\b", "Blackgram"), (r"\bS\.\s?Potato\b", "Sweet potato"),
        (r"\bT\.Aman\b", "T. Aman"), (r"\bB\.Aman\b", "B. Aman")]


def clean_pattern(p: str) -> str:
    p = re.sub(r"\s*[−–-]\s*", "-", p.strip())  # plain hyphen: opens cleanly in Excel
    for a, b in ABBR:
        p = re.sub(a, b, p)
    return p


def num(s: str) -> float:
    return float(s.replace(",", ""))


# ---------------------------------------------------------------- upazila -> district, centroid
def point_in_poly(x: float, y: float, ring: list) -> bool:
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def upazila_lookup() -> pd.DataFrame:
    up = pd.read_csv(SITES / "adm3_centroids.csv")
    gj = json.loads((DATA / "boundaries" / "BGD_ADM2_simplified.geojson").read_text(encoding="utf-8"))
    polys = []
    for f in gj["features"]:
        g = f["geometry"]
        rings = [p[0] for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]])]
        polys.append((f["properties"]["shapeName"], rings))
    def which(lon, lat):
        return next((n for n, rings in polys if any(point_in_poly(lon, lat, r) for r in rings)), None)
    up["district"] = [which(lo, la) for lo, la in zip(up["lon"], up["lat"])]
    up["key"] = up["name"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    return up[["name", "district", "lat", "lon", "key"]]


SHORT = {"b.baria": "brahmanbaria", "com.": "comilla ", "gaiba.": "gaibandha", "matlab.n": "matlab uttar",
         "matlab.s": "matlab dakshin", "chuadnga": "chuadanga", "manikgnj": "manikganj", "nrayangnj": "narayanganj",
         "joyprhat": "joypurhat", "coxbazar": "cox's bazar", "dharmapasha": "dharampasha", "dhormapasha": "dharampasha",
         "chapainawabganj": "chapai nababganj sadar", "barisal sadar": "barisal sadar kotwali"}


def match(name: str, up: pd.DataFrame) -> dict:
    n = name.lower().strip()
    for a, b in SHORT.items():
        n = n.replace(a, b)
    key = re.sub(r"[^a-z]", "", n.replace("sodar", "sadar"))
    base = key.replace("sadar", "")
    for cand in (key, base, base + "sadar", key.replace("pur", "por")):
        hit = up[up["key"] == cand]
        if len(hit):
            return hit.iloc[0].to_dict()
    close = difflib.get_close_matches(key, up["key"].tolist(), n=1, cutoff=0.8)
    return up[up["key"] == close[0]].iloc[0].to_dict() if close else {}


# ---------------------------------------------------------------- parse one paper
def parse_paper(pages: list[str], region: str) -> dict[str, list]:
    out = {"land": [], "patterns": [], "top": [], "div": []}
    table, kind = None, None
    for line in "\n".join(p.replace("\r", "") for p in pages).splitlines():
        s = line.strip()
        t = re.match(r"^Table\s+(\d+)\.\s+(.*)", s)
        # narrative sentences also start 'Table 3. The rest ...': only real titles switch the table
        if t and re.search(r"(?i)land (use|utili)|distribution of|diversity|cropping pattern|cropping system|"
                           r"crops? (and|with)", t.group(2)) and not re.search(r"(?i)\bthe rest\b", t.group(2)):
            title = t.group(2)
            table = title
            kind = ("land" if re.search(r"(?i)land (use|utili)", title) else
                    "top" if re.search(r"(?i)distribution of", title) else
                    "div" if re.search(r"(?i)diversity", title) else
                    "patterns" if re.search(r"(?i)cropping pattern|cropping system|crops? (and|with)", title) else None)
            top_pattern = None
            if kind == "top":
                m = re.search(r"dominant\s+(.+?)\s+cropping pattern", title, re.I)
                top_pattern = clean_pattern(m.group(1)) if m else None
                rank = re.search(r"(\d)(?:st|nd|rd|th)\s+dominant", title)
                top_rank = int(rank.group(1)) if rank else 1
            continue
        if not kind:
            continue
        if kind == "land" and (m := re.match(r"^\d{1,2}\s+([A-Za-z][A-Za-z .'()-]*?)\s+((?:" + N + r"\s+){8}" + N
                                             + r")\s*$", s)):
            v = [num(x) for x in m.group(2).split()]
            out["land"].append({"region": region, "upazila": m.group(1).strip(), "area_ha": v[0],
                                "annual_crop_ha": v[1], "single_cropped_ha": v[2], "double_cropped_ha": v[3],
                                "triple_cropped_ha": v[4], "quadruple_cropped_ha": v[5], "other_ha": v[6],
                                "net_cropped_ha": v[7], "cropping_intensity_pct": v[8]})
        elif kind == "patterns" and (m := re.match(r"^\d{1,3}\s+(.+?[−–-].+?)\s+" + N + r"\s+" + N + r"\s+(\d+)\s*$", s)):
            out["patterns"].append({"region": region, "table": table, "pattern": clean_pattern(m.group(1)),
                                    "area_ha": num(m.group(2)), "pct_nca": num(m.group(3)),
                                    "n_upazilas": int(m.group(4))})
        elif kind == "top" and top_pattern and (m := re.match(r"^\d{1,2}\s+([A-Za-z][A-Za-z .'()-]*?)\s+" + N + r"\s+"
                                                              + N + r"\s+" + N + r"\s*$", s)):
            out["top"].append({"region": region, "rank_in_region": top_rank, "pattern": top_pattern,
                               "upazila": m.group(1).strip(), "area_ha": num(m.group(2)),
                               "pct_upazila_nca": num(m.group(3)), "pct_of_pattern_in_region": num(m.group(4))})
        elif kind == "div" and (m := re.match(r"^\d{1,2}\s+([A-Za-z][A-Za-z .'()-]*?)\s+(\d+)\s+(\d+)\s+(\d?\.\d+)\s+"
                                              r"(\d?\.\d+)\s+(\d+)\s*$", s)):
            out["div"].append({"region": region, "upazila": m.group(1).strip(), "n_patterns": int(m.group(2)),
                               "n_crops": int(m.group(3)), "pattern_diversity_index": float(m.group(4)),
                               "crop_diversity_index": float(m.group(5)), "cropping_intensity_pct": int(m.group(6))})
    return out


def main() -> None:
    idx = json.loads((REG / "index.json").read_text(encoding="utf-8"))
    up = upazila_lookup()
    frames = {"land": [], "patterns": [], "top": [], "div": []}
    for paper in idx:
        if paper["article"] == "38195":
            continue  # national paper: see cropping_patterns.py
        region = re.sub(r"(?i).*\bin\s+|.*\bof\s+|\s*region.*|:.*", "", paper["title"]).strip() or paper["title"]
        pages = json.loads((REG / paper["pdf"]).with_suffix(".json").read_text(encoding="utf-8"))
        res = parse_paper(pages, region)
        for k, rows in res.items():
            for r in rows:
                r["source"] = f"Bangladesh Rice Journal 21(2) 2017, '{paper['title']}'" + (
                    f", doi:{paper['doi']}" if paper.get("doi") else "")
            frames[k].extend(rows)
        print(f"{region:22s} land {len(res['land']):3d} | patterns {len(res['patterns']):3d} | "
              f"top {len(res['top']):3d} | diversity {len(res['div']):3d}")
    names = {"land": "upazila_land_use", "patterns": "regional_patterns", "top": "upazila_top_patterns",
             "div": "upazila_diversity"}
    for k, rows in frames.items():
        df = pd.DataFrame(rows)
        if "upazila" in df:
            m = df["upazila"].apply(lambda n: match(n, up))
            df["adm3_name"] = m.apply(lambda d: d.get("name"))
            df["district"] = m.apply(lambda d: d.get("district"))
            df["lat"] = m.apply(lambda d: d.get("lat"))
            df["lon"] = m.apply(lambda d: d.get("lon"))
            print(f"{names[k]}: {df['adm3_name'].notna().mean():.0%} of upazila names matched to ADM3")
        df.to_csv(OUT / f"{names[k]}.csv", index=False)
        print(f"  -> {names[k]}.csv {len(df)} rows")


if __name__ == "__main__":
    main()
