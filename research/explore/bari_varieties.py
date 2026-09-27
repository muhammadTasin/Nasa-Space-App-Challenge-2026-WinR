"""Field-crop varieties from BARI's Krishi Projukti Hatboi (Handbook on Agro-technology), 10th edition, Dec 2024.

Input : the handbook PDF (the team keeps it in "raw, collected datas/krishiProjuktiHatboi_10.pdf";
        also on bari.gov.bd). Cite as: Akhond et al. (eds.) 2025, Krishi Projukti Hatboi, 10th ed., BARI.
Output: research/crops/bari_field_crop_varieties.csv, one row per variety of the rotation crops.

The Bangla is typed in the legacy Bijoy/SutonnyMJ encoding, so the text layer reads as ASCII look-alikes
("RxebKvj" = jibonkal, growth duration; "djb" = fholon, yield; "Ub" = ton; "w`b" = days). The PDF was
built in Illustrator and neighbouring pages carry copies of each other's text, so every variety appears
several times; the most complete description is kept. Each row keeps the description it was parsed from.

Usage: python research/explore/bari_varieties.py [path/to/pdf]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

REPO = Path(__file__).resolve().parents[2]
PDF = REPO / "raw, collected datas" / "krishiProjuktiHatboi_10.pdf"
OUT = REPO / "research" / "crops" / "bari_field_crop_varieties.csv"
CITE = "BARI Krishi Projukti Hatboi, 10th edition (Dec 2024), Akhond et al. (eds.) 2025"

# Bijoy spelling in the variety name -> crop (field crops that fit rice-based rotations)
CROPS = {"Avjy": "Potato", "wgwóAvjy": "Sweet potato", "wgwó Avjy": "Sweet potato", "mwilv": "Mustard",
         "gmyi": "Lentil", "†Qvjv": "Chickpea", "gyM": "Mungbean", "gvm": "Blackgram", "†Lmvix": "Grasspea",
         "†Lmvwi": "Grasspea", "gUi": "Field pea", "†djb": "Cowpea (felon)", "Aoni": "Pigeon pea",
         "wZj": "Sesame", "Pxbvev`vg": "Groundnut", "mqvweb": "Soybean", "m~h©gyLx": "Sunflower",
         "evwj©": "Barley", "KvDb": "Foxtail millet", "wPbv": "Proso millet", "†cuqvR": "Onion", "imyb": "Garlic",
         "gwiP": "Chili", "fyÆv": "Maize", "Mg": "Wheat"}
NUM = r"(\d+(?:[.,]\d+)?)"
RNG = NUM + r"(?:\s*[-–]\s*" + NUM + r")?"
TOL = r"[^|।\n]{0,40}?(?:mnbkxj|mwnòy|mn¨)"
TRAITS = {"drought_tolerant": r"Liv" + TOL, "salt_tolerant": r"jeYv³Zv" + TOL + r"|jeY" + TOL,
          "heat_tolerant": r"(?:Zvc|D”P ZvcgvÎv)" + TOL, "waterlogging_tolerant": r"Rjve×Zv" + TOL,
          "cold_tolerant": r"(?:kxZ|VvÛv)" + TOL,
          "fits_after_aman": r"Avgb\s*avb\s*(?:KvUvi|†Zvjvi|msMÖ‡ni)\s*ci",
          "short_duration": r"¯^í\s*†gqv`x|¯^íKvjxb|AvMvg"}


def num(s: str | None) -> float | None:
    return None if s is None else float(s.replace(",", ""))


def load_text(pdf_path: Path) -> str:
    pdf = pdfium.PdfDocument(str(pdf_path))
    text = "\n".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"evwi\s*\n\s*", "evwi ", text)  # 'evwi\nMUi-2' -> 'evwi MUi-2'


def heading_re() -> re.Pattern:
    words = "|".join(sorted((re.escape(w) for w in CROPS), key=len, reverse=True))
    return re.compile(r"(?m)^\s*(evwi\s+(?:nvBweªW\s+)?(" + words + r")\s*[-–]\s*(\d{1,3}))\s*(\([^)\n]{0,40}\))?\s*$")


def parse(desc: str) -> dict:
    flat = re.sub(r"\s+", " ", desc)
    rec: dict = {}
    # release year: the year nearest BEFORE the approval wording ('1984 brought from ICARDA ... 1993 approved');
    # explicit approval words first, weaker 'named as'/'as a variety' only if none
    rec["release_year"] = None
    for words in (r"Aby‡gv`b|Aby‡gvw`Z|QvoKiY|Aegy³|gyw³ †`qv|wbeÜb", r"RvZ wn‡m‡e|bv‡g"):
        for a in re.finditer(words, flat):
            yrs = re.findall(r"((?:19|20)\d\d)\s*mv‡j", flat[max(0, a.start() - 160): a.start()])
            if yrs:
                rec["release_year"] = int(yrs[-1])
                break
        if rec["release_year"]:
            break
    if rec["release_year"] is None and (yr := re.search(r"((?:19|20)\d\d)\s*mv‡j", flat)):
        rec["release_year"] = int(yr.group(1))
    # duration: 'RxebKvj', 'w¯’wZKvj' (duration), 'cwic°Zvi mgq' (time to maturity), 'X-Y w`‡b cv‡K' (ripens in)
    d = (re.search(r"(?:RxebKvj|Rxeb Kvj|w¯’wZKvj|cwic°Zvi mgq|cvKv ch©šÍ|†_‡K cvKv|†_‡K dmj msMÖn)\D{0,40}?"
                   + RNG + r"\s*w`", flat)
         or re.search(RNG + r"\s*w`‡b\s*(?:cv‡K|cwic°|msMÖn|dmj|†Zvjv)", flat))
    if d:
        a, b = num(d.group(1)), num(d.group(2)) or num(d.group(1))
        if 40 <= a <= 400:
            rec["duration_days_min"], rec["duration_days_max"] = a, b
    # yield: t/ha or kg/ha, first figure after 'djb'/'†n±i'
    y = re.search(r"(?:djb|†n±i|†n±‡i)\D{0,60}?" + RNG + r"\s*(Ub|†KwR|†g\.\s*Ub)", flat)
    if y:
        a, b, unit = num(y.group(1)), num(y.group(2)) or num(y.group(1)), y.group(3)
        k = 1000.0 if unit == "†KwR" else 1.0
        if 0.2 <= a / k <= 80:
            rec["yield_t_ha_min"], rec["yield_t_ha_max"] = round(a / k, 3), round(b / k, 3)
    h = re.search(r"D”PZv\D{0,15}?" + RNG + r"\s*(?:†mwg|†m.wg|‡mwg)", flat)
    if h:
        rec["plant_height_cm"] = num(h.group(1))
    oil = re.search(r"†Z‡ji\s*cwigvY\D{0,20}?" + RNG + r"\s*(?:%|fvM)", flat)
    if oil:
        rec["oil_pct"] = num(oil.group(1))
    rec.update({k: bool(re.search(p, flat)) for k, p in TRAITS.items()})
    return rec


PLAUSIBLE = {  # (days min, days max, t/ha min, t/ha max) for sanity-checking a parsed description
    "Potato": (55, 130, 10, 60), "Sweet potato": (90, 170, 10, 60), "Mustard": (70, 120, 0.8, 3.5),
    "Lentil": (90, 135, 0.8, 3), "Chickpea": (90, 150, 0.8, 3), "Mungbean": (50, 90, 0.6, 2.5),
    "Blackgram": (55, 90, 0.6, 2.5), "Grasspea": (90, 140, 0.6, 3), "Field pea": (70, 120, 0.8, 3),
    "Cowpea (felon)": (60, 120, 0.6, 3), "Pigeon pea": (120, 300, 0.6, 3), "Sesame": (70, 110, 0.6, 2.5),
    "Groundnut": (90, 170, 1, 4), "Soybean": (85, 125, 1, 3.5), "Sunflower": (85, 120, 1, 3.5),
    "Barley": (85, 125, 1.5, 4.5), "Foxtail millet": (70, 120, 1, 3.5), "Proso millet": (60, 100, 1, 3.5),
    "Onion": (80, 150, 8, 35), "Garlic": (100, 170, 5, 20), "Chili": (90, 240, 1, 30),
    "Maize": (90, 160, 6, 14), "Wheat": (90, 125, 3, 7)}


def score(crop: str, name_bits: tuple[str, str], desc: str, rec: dict) -> float:
    """Pick the best of the several copies of a description: own name mentioned, fields filled, plausible."""
    flat = re.sub(r"\s+", " ", desc)
    s = 3.0 if re.search(re.escape(name_bits[0]) + r"\s*[-–]\s*" + name_bits[1] + r"(?!\d)", flat[:600]) else 0.0
    s += sum(rec.get(k) is not None for k in ("release_year", "duration_days_min", "yield_t_ha_min", "plant_height_cm"))
    d0, d1, y0, y1 = PLAUSIBLE.get(crop, (0, 999, 0, 999))
    if rec.get("duration_days_min") is not None:
        s += 2 if d0 <= rec["duration_days_min"] <= d1 else -6
    if rec.get("yield_t_ha_min") is not None:
        s += 1 if y0 <= rec["yield_t_ha_min"] <= y1 else -4
    return s - len(flat) / 5000  # mild preference for the tighter copy


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    text = load_text(pdf_path)
    hre = heading_re()
    words = "|".join(sorted((re.escape(w) for w in CROPS), key=len, reverse=True))
    # a description ends at the next variety heading, the crop's cultivation section, the next crop, or one of
    # the older non-BARI varieties listed among them (Tori-7, T-6, Dhaka-1, DG-2, ACC-12, DM-1, DS-1, PB-1, G-2)
    local = r"(?:Uwi|wU)\s*[-–]\s*\d+\s*$|[^\n]{1,25}\((?:XvKv|wWwR|Gwmwm|wWGg|wW Gm|wcwe|wR)\s*[-–]\s*\d+\)\s*$"
    stop = re.compile(r"(?m)^\s*(?:Drcv`b cÖhyw³|Pvlvev` c×wZ|evwi\s+\S+\s*[-–]\s*\d{1,3}\s*(?:\([^)\n]*\))?\s*$|"
                      r"(?:" + words + r")(?:i RvZ| Pv‡li)?\s*$|" + local + ")")
    best: dict[str, dict] = {}
    for m in hre.finditer(text):
        start = m.end()
        nxt = stop.search(text, start)
        desc = text[start: nxt.start() if nxt else start + 2500][:3000]
        crop, n = CROPS[m.group(2)], str(int(m.group(3)))
        name = f"BARI {crop}-{n}"
        rec = parse(desc)
        sc = score(crop, (m.group(2), n), desc, rec)
        if sc > best.get(name, {}).get("score", -99):
            best[name] = {"variety": name, "crop": crop, "bijoy_name": m.group(1),
                          "alias": (m.group(4) or "").strip("() ") or None, "desc": desc, "rec": rec, "score": sc}
    rows = [{**{k: v for k, v in b.items() if k not in ("desc", "rec", "score")}, **b["rec"],
             "description_bijoy": re.sub(r"\s+", " ", b["desc"]).strip()[:1500]} for b in best.values()]
    df = pd.DataFrame(rows)
    df["source"] = CITE
    num_key = df["variety"].str.extract(r"-(\d+)$")[0].astype(int)
    df = df.assign(_n=num_key).sort_values(["crop", "_n"]).drop(columns="_n")
    cols = ["crop", "variety", "alias", "release_year", "duration_days_min", "duration_days_max", "yield_t_ha_min",
            "yield_t_ha_max", "plant_height_cm", "oil_pct", *TRAITS, "bijoy_name", "description_bijoy", "source"]
    df = df.reindex(columns=cols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} varieties of {df['crop'].nunique()} crops -> {OUT.relative_to(REPO)}")
    print("filled:", {c: int(df[c].notna().sum()) for c in ["release_year", "duration_days_min", "yield_t_ha_min",
                                                             "plant_height_cm"]})
    print(df.groupby("crop").size().to_dict())


if __name__ == "__main__":
    main()
