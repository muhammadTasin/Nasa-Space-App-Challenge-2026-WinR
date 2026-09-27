"""Wheat and maize varieties from BWMRI's variety pages (research/acquire/bwmri_varieties.py saves the page text).

Each variety page carries its description as Unicode Bangla (the site stores it base64-encoded), so this parses
the text: release year, days to maturity, plant height, 1000-grain weight, yield, sowing window, seed rate and
traits (heat, salt, drought, blast, rust, zinc). The "maize varieties at a glance" page adds release years (and
special-trait lists) for the older maize varieties without a page. BARI Hybrid Maize 16 and BWMRI Hybrid Maize
3 have only images and are listed with what the at-a-glance page gives.

Output: research/crops/bwmri_wheat_maize_varieties.csv
Usage : python research/explore/bwmri_varieties.py
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402
from bari_production import GREG, N, fmt, windows  # noqa: E402

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
RNG = r"(\d+(?:\.\d+)?)(?:\s*[-–]\s*(\d+(?:\.\d+)?))?"
TRAITS = {
    "heat_tolerant": r"তাপ\s*সহিষ্ণু|তাপসহিষ্ণু|তাপ\s*সহনশীল|তাপসহনশীল",
    "salt_tolerant": r"লবণাক্ততা\s*(?:সহিষ্ণু|সহনশীল)",
    "drought_tolerant": r"খরা\s*(?:সহিষ্ণু|সহনশীল)",
    "blast_resistant": r"ব্লাস্ট\s*রোগ\s*প্রতিরোধী|ব্লাস্ট\s*প্রতিরোধী",
    "blast_tolerant": r"ব্লাস্ট\s*রোগ\s*সহনশীল",
    "rust_resistant": r"মরিচা\s*রোগ\s*প্রতিরোধী",
    "zinc_enriched": r"জিংক\s*সমৃদ্ধ",
    "lodging_resistant": r"হেলে\s*পড়ে\s*না",
    "fodder": r"গো-?\s*খাদ্য",
}


def clean(raw: str) -> str:
    t = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=\s]+", " ", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).translate(BN_DIGITS)
    return N(re.sub(r"[ \t\xa0]+", " ", t))


def first(pattern: str, text: str, span: int = 1):
    m = re.search(N(pattern), text)
    if not m:
        return None, None
    a = float(m.group(span))
    b = float(m.group(span + 1)) if m.group(span + 1) else a
    return a, b


def day_windows(text: str) -> list:
    """'নভেম্বর মাসের 15 থেকে 30' / 'ডিসেম্বর মাসের 15-20 তারিখ': explicit days inside one month."""
    out = []
    months = "|".join(f"(?:{v})" for v in GREG.values())
    for m in re.finditer(N(r"(" + months + r")(?:ের|র)?\s*(?:মাসের)?\s*(\d{1,2})\s*(?:থেকে|হতে|-|–)\s*(\d{1,2})"), text):
        mon = next(n for n, pat in GREG.items() if re.fullmatch(N(pat), m.group(1)))
        out.append(((mon, int(m.group(2))), (mon, int(m.group(3)))))
    for m in re.finditer(N(r"(\d{1,2})\s*(?:থেকে|হতে|-|–)\s*(\d{1,2})\s*(" + months + ")"), text):  # "15-30 নভেম্বর"
        mon = next(n for n, pat in GREG.items() if re.fullmatch(N(pat), m.group(3)))
        out.append(((mon, int(m.group(1))), (mon, int(m.group(2)))))
    return out


# fields the variety page leaves out, read from the variety's leaflet (PDF) or field-sign photo
LEAFLET_YEARS = {N("বিডাব্লিউএমআরআই গম ২"): 2020, N("বিডাব্লিউএমআরআই গম ৩"): 2020, N("বিডাব্লিউএমআরআই গম ৪"): 2022}
LEAFLET_DAYS = {N("বারি গম ২৫"): (102, 110), N("বারি গম ২৬"): (104, 110), N("বারি গম ২৯"): (105, 110)}


def parse(name: str, text: str) -> dict:
    crop = "wheat" if N("গম") in name else "maize"
    flat = re.sub(r"\s+", " ", text)
    rec = {"variety_bn": name, "crop": crop}
    # the last year written before the word for "released" (earlier years are crosses and trials)
    year = None
    for a in re.finditer(N(r"অবমুক্ত|অনুমোদন লাভ"), flat):
        ys = re.findall(r"((?:19|20)\d\d)", flat[max(0, a.start() - 160):a.start()])
        if ys:
            year = int(ys[-1])
            break
    tag = re.search(N(r"অবমুক্তির\s*(?:বছর|সাল)\s*:?\s*((?:19|20)\d\d)"), flat)
    rec["release_year"] = int(tag.group(1)) if tag else year or LEAFLET_YEARS.get(N(name))
    rec["note"] = "release year from the leaflet or field sign" if not tag and not year and N(name) in LEAFLET_YEARS \
        else None
    d = first(r"(?:জীবনকাল|বোনা থেকে পাকা পর্যন্ত|পাকা পর্যন্ত)\D{0,15}?" + RNG + r"\s*দিন", flat)
    if d[0] is None and N(name) in LEAFLET_DAYS:
        d = LEAFLET_DAYS[N(name)]
        rec["note"] = "days to maturity from the leaflet"
    rec["duration_days_min"], rec["duration_days_max"] = d
    h = first(r"উচ্চতা\D{0,25}?" + RNG + r"\s*(?:সেমি|সে\.\s*মি|সেন্টিমিটার)", flat)
    rec["plant_height_cm_min"], rec["plant_height_cm_max"] = h
    g = first(r"হাজার দানার ওজন\D{0,12}?" + RNG + r"\s*গ্রাম", flat)
    rec["thousand_grain_g_min"], rec["thousand_grain_g_max"] = g
    y = re.search(N(r"ফলন\D{0,60}?" + RNG + r"\s*(টন|কেজি)"), flat)
    if y:
        k = 0.001 if y.group(3) == N("কেজি") else 1.0
        a = float(y.group(1)) * k
        rec["yield_t_ha_min"], rec["yield_t_ha_max"] = round(a, 2), round((float(y.group(2)) * k if y.group(2) else a), 2)
    sow = re.search(N(r"বপনের\s*(?:উপযুক্ত\s*)?সময়[^:।]{0,5}:?([^।]*।[^।]*।?)"), flat)
    sow_txt = sow.group(1) if sow else ""
    ws = day_windows(sow_txt) or windows(sow_txt)
    rec["sowing_windows"] = fmt(ws) if ws else None
    sr = re.search(N(r"হেক্টর\S*\s*(?:প্রতি)?\s*(\d+(?:\.\d+)?)(?:\s*[-–]\s*\d+)?\s*কেজি\s*(?:\S+\s*){0,3}?বীজ"), flat) or \
        re.search(N(r"বীজ\s*হার\s*:?\s*(\d+(?:\.\d+)?)\s*কেজি\s*/\s*হে"), flat)
    rec["seed_rate_kg_ha"] = float(sr.group(1)) if sr else None
    salt = re.search(N(r"(\d+)\s*[-–]\s*(\d+)\s*ডিএস"), flat)
    rec["salt_tolerance_ds_m"] = f"{salt.group(1)}-{salt.group(2)}" if salt else None
    rec.update({k: bool(re.search(N(p), flat)) for k, p in TRAITS.items()})
    area = re.search(N(r"(?:উপযোগিতা|উপযোগী এলাকা)\s*:?\s*([^।]*।)"), flat)
    rec["suitability_bn"] = area.group(1).strip() if area else None
    rec["description_bn"] = flat[:1500]
    return rec


def at_a_glance(text: str) -> list[dict]:
    flat = re.sub(r"\s+", " ", text)
    rows = []
    for m in re.finditer(N(r"\d+\s+((?:বারি|বিডাব্লিউএমআরআই)[^\d]+?\d+|বর্ণালি|শুভ্রা|খই ভুট্টা|মোহর)\s+((?:19|20)\d\d)"), flat):
        rows.append({"variety_bn": m.group(1).strip(), "crop": "maize", "release_year": int(m.group(2))})
    return rows


def main() -> None:
    base = DATA / "bwmri"
    rows = []
    for f in sorted(base.glob("*/page_text.txt")):
        name = f.parent.name.replace("_", " ")
        text = clean(f.read_text(encoding="utf-8"))
        if N("এক নজরে") in name:
            rows += [{**r, "source": "BWMRI maize varieties at a glance"} for r in at_a_glance(text)]
            continue
        if not text.strip():
            rows.append({"variety_bn": name, "crop": "maize" if N("ভুট্টা") in name else "wheat",
                         "source": "BWMRI page (image only)"})
            continue
        rows.append({**parse(name, text), "source": "BWMRI variety page, bwmri.gov.bd"})
    df = pd.DataFrame(rows)
    # one row per variety: the variety's own page wins over the at-a-glance list
    df["_own"] = df["source"].str.startswith("BWMRI variety page")
    df["_key"] = (df["variety_bn"].str.translate(BN_DIGITS).str.replace(r"\s+", "", regex=True)
                  .str.replace(N("খই"), N("খৈ")))  # popcorn is spelled both ways
    df = df.sort_values("_own", ascending=False).drop_duplicates("_key").drop(columns=["_own", "_key"])
    df = df.sort_values(["crop", "variety_bn"])
    out = RESEARCH / "crops" / "bwmri_wheat_maize_varieties.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    show = ["variety_bn", "release_year", "duration_days_min", "duration_days_max", "plant_height_cm_min",
            "yield_t_ha_min", "yield_t_ha_max", "sowing_windows", "seed_rate_kg_ha", "heat_tolerant", "salt_tolerant",
            "drought_tolerant", "blast_resistant"]
    pd.set_option("display.width", 250)
    print(df[show].to_string(index=False))
    print(len(df), "rows ->", out.relative_to(RESEARCH.parent))


if __name__ == "__main__":
    main()
