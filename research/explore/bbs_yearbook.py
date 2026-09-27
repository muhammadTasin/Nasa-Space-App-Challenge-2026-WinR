"""Extract the tables we need from the BBS Yearbook of Agricultural Statistics 2025 (684 pages).

Input : research/data/bbs/BBS_Yearbook_Agricultural_Statistics_2025.pdf  (download link in README)
Output: research/bbs/*.csv  (small, committed)

  crop_district.csv     every Chapter 3 district table: crop, variant, district, year, area, yield, production
  crop_calendar.csv     Section 1.8: sowing/transplanting and harvest windows, seed rate, for ~50 crops
  census_costs.csv      Agriculture Census 2019 (Ch. 8): yield, cost, crop and by-product value per acre, by division
  harvest_prices.csv    Table 10.5.1: harvest-time market price, Tk per quintal, 2021-22 to 2024-25
  irrigation.csv        Table 7.7: irrigated area by crop and district ('000 acres)
  intensity.csv         Table 5.2.1: net and gross cropped area by district; intensity recomputed
  damage.csv            Tables 4.2.x: district crop damage from named floods and cyclones

District names are matched to the 64 geoBoundaries names used elsewhere in research/ (sites/districts.csv).
Page numbers below are PDF pages (printed page + 15). Usage: python research/explore/bbs_yearbook.py
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH, SITES  # noqa: E402

PDF = DATA / "bbs" / "BBS_Yearbook_Agricultural_Statistics_2025.pdf"
CACHE = DATA / "bbs" / "yearbook_2025_pages.json"
OUT = RESEARCH / "bbs"
SOURCE = "BBS Yearbook of Agricultural Statistics of Bangladesh 2025"
ACRE_HA = 0.404686
NUMTOK = r"(?:\d[\d,]*\.?\d*|-|\.\.)"

# yearbook spelling -> geoBoundaries name (sites/districts.csv)
ALIASES = {"barishal": "Barisal", "bogura": "Bogra", "brahmanbaria": "Brahamanbaria",
           "brahmmanbaria": "Brahamanbaria", "chattogram": "Chittagong", "cumilla": "Comilla",
           "coxsbazar": "Cox's Bazar", "jashore": "Jessore", "jhallokati": "Jhalokati", "jhalokathi": "Jhalokati",
           "jhalakati": "Jhalokati", "khagrachari": "Khagrachhari", "moulvibazar": "Maulvibazar",
           "netrokona": "Netrakona", "chapainawabganj": "Nawabganj", "chapai": "Nawabganj",
           "chapainababganj": "Nawabganj", "panchagar": "Panchagarh", "narshingdi": "Narsingdi",
           "laxmipur": "Lakshmipur", "lakhsmipur": "Lakshmipur", "jhenaidaha": "Jhenaidah", "jhinaidah": "Jhenaidah",
           "moulvibazer": "Maulvibazar", "maulavibazar": "Maulvibazar", "chuadenga": "Chuadanga",
           "munsiganj": "Munshiganj", "nilphamary": "Nilphamari", "kishorganj": "Kishoreganj",
           "gopalgonj": "Gopalganj", "narayangonj": "Narayanganj", "sherpore": "Sherpur", "barguna": "Barguna"}


def canon_map() -> dict[str, str]:
    names = pd.read_csv(SITES / "districts.csv")["name"].tolist()
    m = {re.sub(r"[^a-z]", "", n.lower()): n for n in names}
    m.update(ALIASES)
    return m


CANON = canon_map()


def district(name: str) -> str | None:
    key = re.sub(r"[^a-z]", "", name.lower()).replace("gonj", "ganj")
    if key in CANON:
        return CANON[key]
    if "division" in key or key in ("bangladesh", "total") or len(key) < 4:
        return None
    close = difflib.get_close_matches(key, list(CANON), n=1, cutoff=0.85)
    return CANON[close[0]] if close else None


def season(label: str) -> str:
    """'2024-2025', '2022-223', '2024-25' -> '2024-25' (the book has typos in its year headers)."""
    y = int(re.match(r"(20\d\d)", label).group(1))
    return f"{y}-{(y + 1) % 100:02d}"


def num(tok: str) -> float | None:
    tok = tok.replace(",", "")
    if tok in ("-", "..", ""):
        return None
    try:
        return float(tok)
    except ValueError:
        return None


def load_pages() -> list[str]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    with pdfplumber.open(PDF) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    CACHE.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


# ---------------------------------------------------------------- Chapter 3: crop tables by district
def major_err(v: list) -> float:
    """Major-crop row = 2 x (acre, ha, maund/acre, t/ha, t). Relative mismatch between the area columns
    (1 acre = 0.4047 ha); used only to choose where a split number belongs."""
    err = 0.0
    for k in (0, 5):
        a_ac, a_ha = v[k], v[k + 1]
        if a_ac and a_ha:
            err += abs(a_ha - a_ac * ACRE_HA) / max(a_ha, 1)
    return err


def fix_tokens(toks: list[str]) -> list[float | None] | None:
    """Return 6 or 10 numbers. A stray space can split one number in two ('2.3 56' for 2.356), so for one
    extra token try each merge and keep the one whose acre and hectare columns agree best."""
    if len(toks) in (6, 10):
        return [num(x) for x in toks]
    if len(toks) == 11:
        cands = ([num(x) for x in toks[:i] + [toks[i] + toks[i + 1]] + toks[i + 2:]] for i in range(10))
        return min(cands, key=major_err)
    if len(toks) == 7:
        for i in range(6):
            if "." in toks[i] and "." not in toks[i + 1]:
                return [num(x) for x in toks[:i] + [toks[i] + toks[i + 1]] + toks[i + 2:]]
    return None


def title_years(title: str) -> list[str]:
    ys = [int(re.match(r"(20\d\d)", y).group(1)) for y in re.findall(r"20\d\d\s*-\s*\d{2,4}", title)]
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(min(ys), max(ys) + 1)] if ys else []


def seasons_for(found: list[str], n: int, edition: int) -> list[str]:
    """The n seasons a row covers: the last n of those named in the title/header; if fewer are named,
    count back from the latest one named (or from the edition year)."""
    found = sorted(set(found))
    if len(found) >= n:
        return found[-n:]
    end = int(found[-1][:4]) if found else edition - 1
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(end - n + 1, end + 1)]


def crop_tables(pages: list[str], first: int = 66, last: int = 425, edition: int = 2025) -> pd.DataFrame:
    """Chapter 3 district tables between PDF pages first..last-1 (defaults: the 2025 edition)."""
    rows, title = [], None
    full = re.compile(r"^\s*(?:\d{1,2}\s+)?([A-Za-z][A-Za-z .'’()-]*?)\s+((?:" + NUMTOK + r"\s+){5,10}" + NUMTOK
                      + r")\s*$")
    name_only = re.compile(r"^\s*\d{1,2}\s+([A-Za-z][A-Za-z .'’()-]*?)\s*$")  # numbered, so never a division
    nums_only = re.compile(r"^\s*((?:" + NUMTOK + r"\s+){5,10}" + NUMTOK + r")\s*$")

    def emit(p: int, name: str, toks: list[str], years: list[str]) -> None:
        d, v = district(name), fix_tokens(toks)
        if not d or v is None:
            return
        if len(v) == 10:  # major crops: 2 seasons x (acre, ha, maund/acre, t/ha, t)
            for k, y in enumerate(seasons_for(years, 2, edition)):
                a_ac, a_ha, _, y_tha, prod = v[5 * k: 5 * k + 5]
                note = None
                # the printed t/ha column has typos (Aus hybrid 2023-24): trust production / area instead
                if a_ha and prod and y_tha is not None and abs(prod / a_ha - y_tha) > 0.05 * (prod / a_ha) + 0.05 \
                        and "jute" not in title.lower():
                    y_tha, note = round(prod / a_ha, 3), "yield recomputed as production/area (printed t/ha inconsistent)"
                rows.append({"table": title, "page": p, "district": d, "year": y, "area_acre": a_ac,
                             "area_ha": a_ha, "yield_t_ha": y_tha, "production_t": prod, "note": note})
        elif layout["yield_cols"]:
            # 2015 edition: header 'Area | Yield per acre (KG) | Production' -> 2 seasons x (acre, kg/acre, t)
            for k, y in enumerate(seasons_for(years, 2, edition)):
                a_ac, _, prod = v[3 * k: 3 * k + 3]
                rows.append({"table": title, "page": p, "district": d, "year": y, "area_acre": a_ac,
                             "area_ha": None if a_ac is None else round(a_ac * ACRE_HA, 1),
                             "yield_t_ha": round(prod / (a_ac * ACRE_HA), 3) if a_ac and prod is not None else None,
                             "production_t": prod, "note": "2-season layout: acre, kg/acre, t"})
        else:  # minor crops: 3 seasons x (acre, t); yield derived
            for k, y in enumerate(seasons_for(years, 3, edition)):
                a_ac, prod = v[2 * k: 2 * k + 2]
                rows.append({"table": title, "page": p, "district": d, "year": y, "area_acre": a_ac,
                             "area_ha": None if a_ac is None else round(a_ac * ACRE_HA, 1),
                             "yield_t_ha": round(prod / (a_ac * ACRE_HA), 3) if a_ac and prod is not None else None,
                             "production_t": prod})

    layout = {"yield_cols": False}  # decided from each table's column header; continuation pages keep it
    for p in range(first, min(last, len(pages) + 1)):
        t = pages[p - 1]
        head = "\n".join(t.splitlines()[:3])
        hdr = t[:500]
        if re.search(r"Area", hdr) and re.search(r"P\s?roduction", hdr):
            layout["yield_cols"] = bool(re.search(r"(?i)yield\s*per", hdr))
        m = re.search(r"^(Table[^\n]*?(?:Estimat|Area and Production)[^\n]*)", head, re.I | re.M)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        elif re.search(r"Introduction|National estimate", head):
            title = None  # narrative page between tables
        if not title:
            continue
        years = sorted(set(title_years(title)) | {season(y) for y in re.findall(r"20\d\d\s*-\s*\d{2,4}", t[:500])})
        # data values can look like seasons ('2030 -31'): keep only the few seasons before this edition
        years = [y for y in years if edition - 8 <= int(y[:4]) <= edition - 1]
        pend_name = pend_nums = None
        for line in t.splitlines():
            line = re.sub(r"(\d)\.\.(\d)", r"\1.\2", line)  # '1114..00' typo
            if (r := full.match(line)) and district(r.group(1)):
                emit(p, r.group(1), r.group(2).split(), years)
                pend_name = pend_nums = None
            elif r := name_only.match(line):
                if pend_nums:
                    emit(p, r.group(1), pend_nums, years)
                    pend_nums = None
                else:
                    pend_name = r.group(1)
            elif r := nums_only.match(line):
                if pend_name:
                    emit(p, pend_name, r.group(1).split(), years)
                    pend_name = None
                else:
                    pend_nums = r.group(1).split()
            elif line.strip() and not re.fullmatch(r"\d+", line.strip()):
                pend_nums = None  # a division label or text breaks the pairing
    df = pd.DataFrame(rows)
    df["crop"] = df["table"].map(crop_name)
    df["variant"] = df["table"].map(variant_name)
    df = df.drop_duplicates(["crop", "variant", "district", "year"], keep="first")
    return df[["crop", "variant", "district", "year", "area_acre", "area_ha", "yield_t_ha", "production_t",
               "note", "table", "page"]]


def crop_name(title: str) -> str:
    t = title.lower()
    for key, name in (("aus", "Aus rice"), ("aman", "Aman rice"), ("bona", "Aman rice"), ("boro", "Boro rice"),
                      ("potato", "Potato"), ("wheat", "Wheat"), ("jute", "Jute")):
        if re.search(rf"\b{key}\b", t) and not (key == "potato" and "sweet" in t):
            return name
    m = re.search(r"(?:area and production of|estimates? of)\s+(.*?)\s*(?:by district|,|\d{4})", title, re.I)
    return (m.group(1) if m else title).strip(" ,.")


def variant_name(title: str) -> str:
    t = title.lower()
    if not re.search(r"\b(aus|aman|bona|boro|potato)\b", t) or "sweet" in t:
        return "all"  # e.g. 'Rape and Mustard (Local+HYV)' is one table, not the HYV part
    for key, v in (("total", "total"), ("hybrid", "hybrid"), ("hyv", "HYV"), ("high yielding", "HYV"),
                   ("local", "local"), ("bona", "broadcast"), ("broadcast", "broadcast"), ("transplant", "transplant")):
        if key in t:
            return v
    return "all"


# ---------------------------------------------------------------- Section 1.8: crop calendar
def crop_calendar() -> pd.DataFrame:
    rows, crop = [], None
    with pdfplumber.open(PDF) as pdf:
        for p in (39, 40, 41):
            for tab in pdf.pages[p - 1].extract_tables():
                for r in tab:
                    r = [re.sub(r"\s+", " ", c or "").strip() for c in r]
                    if not any(r) or r[0] in ("Crop", "1") or len(r) < 3:
                        continue
                    name, sow, harv = r[0], r[1], r[2]
                    seed = r[3] if len(r) > 3 else ""
                    if re.match(r"^\d+\.", name):
                        crop = re.sub(r"^\d+\.\s*", "", name).strip(" :")
                        if not sow and not harv:
                            continue
                        rows.append({"crop": crop, "type": "", "sowing": sow, "harvest": harv, "seed_per_acre": seed})
                    elif re.match(r"^\(\w\)", name) or not name:
                        rows.append({"crop": crop, "type": re.sub(r"^\(\w\)\s*", "", name), "sowing": sow,
                                     "harvest": harv, "seed_per_acre": seed})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Chapter 8: costs and returns (Census 2019)
def census_costs(pages: list[str]) -> pd.DataFrame:
    rows = []
    for p in range(553, 558):
        crop = None
        for line in pages[p - 1].splitlines():
            m = re.match(r"^(Bangladesh|[A-Z][a-z]+ Division)\s+(" + NUMTOK + r")\s+(" + NUMTOK + r")\s+(" + NUMTOK
                         + r")\s+(" + NUMTOK + r")\s*$", line)
            if m and crop:
                y, cost, val, by = (num(m.group(i)) for i in range(2, 6))
                rows.append({"crop": crop, "area": m.group(1), "yield_t_per_acre": y, "cost_tk_per_acre": cost,
                             "crop_value_tk_per_acre": val, "byproduct_value_tk_per_acre": by,
                             "net_return_tk_per_acre": None if None in (cost, val, by) else val + by - cost,
                             "page": p})
            elif re.match(r"^(Local|HYV|Hybrid|Wheat|Maize|Potato|Onion|Jute|Deshi|Tossa|Local Bona|Local Ropa|"
                          r"B\.|T\.|Transplant|Broadcast)[A-Za-z .()&-]*$", line.strip()) and len(line) < 45:
                crop = line.strip()
            elif re.match(r"^8\.\d .*of ([A-Za-z]+)", line):
                section = re.search(r"of ([A-Za-z]+)", line).group(1)
                crop = None if section.lower() in ("aus", "amon", "aman", "boro") else section
    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------- 8.1: farm holdings by district (Census 2019)
def holdings(pages: list[str]) -> pd.DataFrame:
    cols = ["all_holdings", "non_farm_holdings", "farm_holdings", "small_farms", "medium_farms", "large_farms",
            "owner", "owner_cum_tenant", "tenant", "agri_labour_holdings", "fisheries_holdings"]
    rows = []
    for p in range(550, 554):
        lines = pages[p - 1].splitlines()
        for i, line in enumerate(lines):
            m = re.match(r"^\s*\d{2}\s*-\s*([A-Za-z][A-Za-z .'’-]*?)\s+((?:\d+\s+){10}\d+)\s*$", line)
            if not m and re.match(r"^\s*\d{2}\s*-\s*$", line) and i + 2 < len(lines):
                # '70-' / numbers / 'Chapainababganj' on three lines
                nums = re.match(r"^\s*((?:\d+\s+){10}\d+)\s*$", lines[i + 1])
                if nums and district(lines[i + 2].strip()):
                    m = re.match(r"(.*)\|(.*)", f"{lines[i + 2].strip()}|{nums.group(1)}")
            if m and district(m.group(1)):
                v = [int(x) for x in m.group(2).split()]
                rec = {"district": district(m.group(1)), **dict(zip(cols, v)), "note": None, "page": p}
                # the book has typos (Rajshahi small farms '3251111' for 325111): farm = small + medium + large
                if abs(rec["small_farms"] + rec["medium_farms"] + rec["large_farms"] - rec["farm_holdings"]) > 200:
                    rec["small_farms"] = rec["farm_holdings"] - rec["medium_farms"] - rec["large_farms"]
                    rec["note"] = "small_farms recomputed as farm - medium - large (printed value inconsistent)"
                rows.append(rec)
    df = pd.DataFrame(rows).drop_duplicates("district")
    df["small_farm_share"] = (df["small_farms"] / df["farm_holdings"]).round(3)
    df["tenancy_share"] = ((df["owner_cum_tenant"] + df["tenant"]) / (df["owner"] + df["owner_cum_tenant"]
                                                                     + df["tenant"])).round(3)
    return df


# ---------------------------------------------------------------- Chapter 6: BMD station weather
def bmd_weather(pages: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """6.1.2-6.1.4 monthly rain, 6.2.4-6.2.9 monthly Tmax/Tmin, 6.3.x humidity (2023-2025), and 6.1.1 annual rain
    2016-24. Missing values print as '*', '***' or '-'. Rows with fewer tokens than columns are ambiguous
    (which month is missing?) and are skipped."""
    monthly, annual = [], []
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    tok = r"(?:\d+(?:\.\d+)?|\*+|-)"
    for p in range(462, 478):
        t = pages[p - 1]
        head = t[:300]
        var = ("rain_mm" if "Rainfall" in head else "tmax_c" if "Maximum Temperature in" in head else
               "tmin_c" if "Minimum Temperature in" in head else "rh_pct" if "Humidity" in head else
               "tmean_c" if "Maximum + Minimum" in head else None)
        yr = re.search(r"(20\d\d)\s*(?:by|\(|$)|of\s*-?\s*(20\d\d)", head)
        year = int(next(g for g in yr.groups() if g)) if yr else None
        for line in t.splitlines():
            if p == 462:
                m = re.match(r"^([A-Z][A-Za-z'’ .]+?)\s+((?:" + tok + r"\s+){8}" + tok + r")\s*$", line.strip())
                if m:
                    vals = m.group(2).split()
                    annual += [{"station": m.group(1).strip(), "year": y, "rain_mm": num(v)}
                               for y, v in zip(range(2016, 2025), vals)]
                continue
            m = re.match(r"^([A-Z][A-Za-z'’ .]+?)\s+((?:" + tok + r"\s+){11,12}" + tok + r")\s*$", line.strip())
            if m and var and year and not re.match(r"^(Station|Name)", m.group(1)):
                vals = m.group(2).split()
                monthly += [{"station": m.group(1).strip(), "year": year, "month": i + 1, "variable": var,
                             "value": None if re.fullmatch(r"\*+|-", v) else float(v)}
                            for i, v in enumerate(vals[:12])]
    return pd.DataFrame(monthly), pd.DataFrame(annual)


# ---------------------------------------------------------------- 7.5: farm labour wages by district
def wages(pages: list[str]) -> pd.DataFrame:
    """Daily wage, Tk. Column order read from the values (more meals provided -> lower cash wage): one meal M/F,
    two meals M/F, three meals M/F, without food M/F. 0 = not reported."""
    cols = ["one_meal_m", "one_meal_f", "two_meals_m", "two_meals_f", "three_meals_m", "three_meals_f",
            "no_food_m", "no_food_f"]
    rows = []
    mon = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                            "Nov", "Dec"])} | {"Agu": 8, "Sept": 9, "June": 6, "July": 7}  # book typos
    for p in range(490, 538):
        mo = re.search(r"\b([A-Z][a-z]{2,3})-(20\d\d)\b", pages[p - 1][:400])
        if not mo or mo.group(1) not in mon:
            continue
        month = f"{mo.group(2)}-{mon[mo.group(1)]:02d}"
        for line in pages[p - 1].splitlines():
            m = re.match(r"^([A-Z][A-Za-z'’ .]+?)\s+((?:\d+\s+){7}\d+)\s*$", line.strip())
            if m and district(m.group(1)):
                v = [int(x) for x in m.group(2).split()]
                rows.append({"month": month, "district": district(m.group(1)),
                             **{c: (x or None) for c, x in zip(cols, v)}})
    return pd.DataFrame(rows).drop_duplicates(["month", "district"])


# ---------------------------------------------------------------- Table 10.5.1: harvest-time prices
def harvest_prices(pages: list[str]) -> pd.DataFrame:
    """Table 10.5.1 only (DAM prices, 70 items, PDF 653-656); it ends at its 'Source:' line."""
    rows, done = [], False
    for p in range(653, 668):
        for line in pages[p - 1].splitlines():
            if line.startswith("Source") and rows:
                done = True
                break
            m = re.match(r"^\s*(\d{1,3})\s+(.+?)\s+(" + NUMTOK + r")\s+(" + NUMTOK + r")\s+(" + NUMTOK + r")\s+("
                         + NUMTOK + r")\s*$", line)
            if m:
                item = re.sub(r"\s*[^\x00-\x7F].*$|\(cid:\d+\)", "", m.group(2)).strip()
                rows.append({"item": item, "2021-22": num(m.group(3)), "2022-23": num(m.group(4)),
                             "2023-24": num(m.group(5)), "2024-25": num(m.group(6)),
                             "unit": "Tk per quintal (100 kg); fruit per 100 pieces", "page": p})
        if done:
            break
    df = pd.DataFrame(rows).drop_duplicates("item")
    df["note"] = None
    df.loc[(df["item"] == "Black Gram (Mashkalai)"), "note"] = "2022-23 value 1761 looks like a typo in the book (neighbours ~7,700-8,900)"
    return df


# ---------------------------------------------------------------- 10.1-10.4: monthly wholesale and retail prices
PRICE_TABLES = [("10.1", "wholesale", 2024, 616, 622), ("10.2", "wholesale", 2025, 623, 629),
                ("10.3", "retail", 2024, 630, 636), ("10.4", "retail", 2025, 637, 652)]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DITTO = re.compile(r"^(?:,,|‘’|“”|\"\"|''|”|“|‘|’)\s*")
PRICE_HEADER = re.compile(r"(?i)^(?:sl no|name of|january|year-|measur|ement|\(per|source|note|10\.\d)")


def monthly_prices(pages: list[str]) -> pd.DataFrame:
    """National monthly average prices (DAM): wholesale Tk per quintal, retail Tk per kg (the 2025 tables print a
    'measurement' column, kept as printed). Long names wrap: in the 2025 tables the extra lines follow the row; in
    the 2024 tables the row's figures sit mid-cell, so name lines come before it (a new name, ditto mark or capital)
    and after it (a lower-case word, a bracket, or the rest of an open bracket). The 2024 tables also abbreviate
    repeated names with ditto marks: `item_full` fills them from the category above (heuristic). Values more than 3x
    off the row median are listed in `suspect_months` (e.g. '300' printed among ~3,000s)."""
    val = r"(?:\.?\d[\d,]*(?:\.\d*)?\.?|-)"  # the book has stray dots: "57.74.", ".36.72"
    rows = []
    for table, market, year, p0, p1 in PRICE_TABLES:
        measurement, last, head, serial_head = None, None, [], None
        recs = []
        for p in range(p0, p1 + 1):
            for line in pages[p - 1].splitlines():
                line = line.strip()
                if not line or PRICE_HEADER.match(line):
                    continue
                # print glitches: '571.02-' (a dash glued on), '--', '####' (a spreadsheet overflow)
                line = re.sub(r"(?<=\d)-(?=\s|$)", " -", line.replace("####", "-"))
                line = re.sub(r"(?<=\s)--(?=\s|$)", "- -", line)
                m = re.match(r"^(?:(\d{1,3})\s+)?(.*?)\s*((?:" + val + r"\s+){12}" + val + r")$", line)
                short = None
                if not m:  # one month missing: 11 months + average; taken as Jan-Nov
                    m = short = re.match(r"^(?:(\d{1,3})\s+)?(.*?)\s*((?:" + val + r"\s+){11}" + val + r")$", line)
                    if m and not re.search(r"[A-Za-z]", m.group(2)) and not m.group(1):
                        m = short = None
                if m and (m.group(1) or serial_head):
                    serial = int(m.group(1)) if m.group(1) else serial_head[0]
                    core = m.group(2).strip() if m.group(1) else f"{serial_head[1]} {m.group(2)}".strip()
                    serial_head = None
                    toks = m.group(3).split()
                    if short:
                        toks = toks[:11] + ["-"] + toks[11:]
                    last = {"serial": serial, "head": head, "core": core, "tail": [], "toks": toks, "page": p,
                            "note": "11 months printed; read as Jan-Nov" if short else None}
                    recs.append(last)
                    head = []
                    continue
                s = re.match(r"^(\d{1,3})\s+(\D.*)$", line)
                if s:  # serial and the start of a name; the figures come on the next line ("44 Dal Black gram")
                    serial_head = (int(s.group(1)), s.group(2).strip())
                    continue
                if re.search(r"\d{3,}", line) or last is None and year == 2025:
                    continue
                name_so_far = " ".join(last["head"] + [last["core"]] + last["tail"]) if last else ""
                is_tail = last is not None and (year == 2025 or line[:1] in "(" or line[:1].islower()
                                               or name_so_far.count("(") > name_so_far.count(")"))
                (last["tail"] if is_tail else head).append(line)
        category, prev = None, 0
        for r in recs:
            if r["serial"] < prev - 50:  # the 2025 tables number 217-219 as 117-119
                r["note"] = "; ".join(x for x in (r["note"], f"serial printed as {r['serial']}") if x)
                r["serial"] += 100
            prev = r["serial"]
            name = " ".join(r["head"] + [r["core"]] + r["tail"]).strip()
            meas = re.search(r"\s*(1\s?quintal|\d+\s?[Pp]i?ces?|,,)(?=\s|$)", name) if year == 2025 else None
            if meas:
                measurement = measurement if meas.group(1) == ",," else meas.group(1).replace(" ", "")
                name = (name[:meas.start()] + name[meas.end():]).strip()
            ditto = bool(DITTO.match(name)) or (name[:1].islower() and category is not None)
            bare = re.sub(r"\s+", " ", DITTO.sub("", name)).strip()
            if ditto and category:
                full = f"{category} {bare}"
            else:
                full = bare
                words = bare.split()
                category = " ".join(words[:2]) if words and words[0] in ("Paddy", "Rice") else (words[0] if words else None)
            vals = [num(t.strip(".")) for t in r["toks"]]
            months = dict(zip(MONTHS, vals[:12]))
            good = [v for v in vals[:12] if v]
            med = float(pd.Series(good).median()) if good else None
            suspect = [k for k, v in months.items() if v and med and (v < med / 3 or v > med * 3)]
            rows.append({"table": table, "market": market, "year": year, "serial": r["serial"], "item": name,
                         "item_full": full, "measurement": measurement if year == 2025 else None,
                         "unit": "Tk per quintal" if market == "wholesale" else "Tk per kg", **months,
                         "average_printed": vals[12], "suspect_months": ";".join(suspect) or None,
                         "note": r["note"], "page": r["page"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 9.1.1: livestock and poultry by holding size
HOLDING_CLASSES = ["all", "no_operated_land", "no_cultivated_land", "cultivated_0.01-0.04ac", "small_0.05-2.49ac",
                   "medium_2.50-7.49ac", "large_7.50ac+", "farm_total"]
ANIMALS = {"cow": "cow", "buffalo": "buffalo", "goat": "goat", "sheep": "sheep", "cock;hen": "chicken",
           "cocks;hens": "chicken", "duck": "duck", "pigeon": "pigeon"}


def livestock_census(pages: list[str]) -> pd.DataFrame:
    """Agriculture Census 2019 (Table 9.1.1): holdings keeping each animal and head counts, by area (Bangladesh,
    rural, urban) and holding class. Rows are rebuilt where the text wraps a label or a number onto the next line.
    Counts obey all = the three non-farm classes + farm total, and farm total = small + medium + large; a count
    broken by a line wrap is recomputed from them (`note`). Average per holding is recomputed from the counts (the
    book prints 134.04 for urban small-farm poultry, 13.04 by the counts)."""
    text = "\n".join(pages[p - 1] for p in range(560, 564))
    lines = [l.strip() for l in text.splitlines()]
    area, recs, pending = None, {}, None
    numrow = re.compile(r"^((?:[\d.]+\s+){7}[\d.]+)$")
    for i, line in enumerate(lines):
        if line in ("BANGLADESH", "RURAL", "URBAN"):
            area = line.title()
            continue
        m = re.match(r"^([A-Za-z;() ]+?)\s+((?:[\d.]+\s+){7}[\d.]+)$", line)
        label, nums = (m.group(1), m.group(2)) if m else (None, None)
        if not m and numrow.match(line):
            nums = line
            if pending:  # "Holdings reporting buffalo" / numbers on the next line
                label = pending
            else:  # numbers first, label after ("29752874 ... 16048594" / "All holdings")
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                label = nxt if re.match(r"^[A-Za-z][A-Za-z;() ]*$", nxt) else None
        elif not m:
            if re.match(r"^Holdings reporting", line):
                pending = line  # label alone; its numbers come on the next line
            continue
        if nums is None or label is None or area is None:
            continue
        v = [float(x) for x in nums.split()]
        # a number broken by a line wrap: '... 39501 515266 ...' then '16' on the next line
        wrap = lines[i + 1] if i + 1 < len(lines) and re.fullmatch(r"\d{1,3}", lines[i + 1]) else None
        low = label.lower()
        if low.startswith("all holdings"):
            recs[(area, "all_holdings")] = v, None
        elif low.startswith("holdings reporting"):
            recs[(area, "holdings", ANIMALS.get(low.split("reporting")[-1].strip(), low))] = v, wrap
        elif low.startswith("number of"):
            recs[(area, "number", ANIMALS.get(low.split("number of")[-1].strip(), low))] = v, wrap
        elif low.startswith("percentage of corresponding"):
            last_animal = next((k[2] for k in reversed(recs) if k[0] == area and len(k) == 3), None)
            recs[(area, "pct_reporting", last_animal)] = v, None
        pending = None
    rows = []
    for (key, (v, wrap)) in recs.items():
        if key[1] not in ("holdings", "number"):
            continue
        note = None
        v = list(v)
        if abs(v[0] - (v[1] + v[2] + v[3] + v[7])) > 2:  # repair the class the wrap broke
            fixed = v[0] - v[1] - v[3] - v[7]
            note = f"no_cultivated_land printed {v[2]:.0f}{'|' + wrap if wrap else ''}; recomputed from the row total"
            v[2] = fixed
        recs[key] = v, note
    for area_ in ("Bangladesh", "Rural", "Urban"):
        allh = recs.get((area_, "all_holdings"), (None, None))[0]
        for animal in ("cow", "buffalo", "goat", "sheep", "chicken", "duck", "pigeon"):
            h, hn = recs.get((area_, "holdings", animal), (None, None))
            n, nn = recs.get((area_, "number", animal), (None, None))
            pct = recs.get((area_, "pct_reporting", animal), (None, None))[0]
            if h is None or n is None:
                continue
            for k, cls in enumerate(HOLDING_CLASSES):
                fixes = [f"{what} {x}" for what, x in (("holdings:", hn), ("head:", nn)) if x]
                rows.append({"area": area_, "animal": animal, "holding_class": cls,
                             "all_holdings": allh[k] if allh else None, "holdings_keeping": h[k], "head": n[k],
                             "pct_of_holdings_keeping": pct[k] if pct else None,
                             "head_per_keeping_holding": round(n[k] / h[k], 2) if h[k] else None,
                             "note": "; ".join(fixes) if fixes and cls == "no_cultivated_land" else None})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Table 7.7: irrigation by crop
def irrigation(pages: list[str]) -> pd.DataFrame:
    """The 2022-23 half of Table 7.7 wraps badly: the total can sit on the name line and 'Other' can drop
    to the next line. Collect a district's 9 numbers across lines, then take as the total the one value
    that equals the sum of the other eight; the rest keep their column order."""
    cols = ["aman", "boro", "wheat", "sugarcane", "cotton", "potato", "vegetables", "other"]
    rows, year, cur = [], None, None

    def close() -> None:
        if not cur or len(cur["toks"]) != 9:
            return
        v = [num(t) or 0.0 for t in cur["toks"]]
        for i in range(9):
            if abs(v[i] - (sum(v) - v[i])) <= 2:
                rest = [t for j, t in enumerate(cur["toks"]) if j != i]
                rows.append({"district": cur["district"], "year": year, **{c: num(t) for c, t in zip(cols, rest)},
                             "total": v[i], "page": cur["page"]})
                return

    for p in range(542, 547):
        for line in pages[p - 1].splitlines():
            if y := re.search(r"Year:\s*(20\d\d-\d\d)", line):
                close(); cur = None
                year = y.group(1)
                continue
            m = re.match(r"^\s*\d{1,2}\s+([A-Za-z][A-Za-z .'’-]*?)((?:\s+" + NUMTOK + r")*)\s*$", line)
            if m and district(m.group(1)):
                close()
                cur = {"district": district(m.group(1)), "toks": m.group(2).split(), "page": p}
            elif cur and re.fullmatch(r"(?:\s*" + NUMTOK + r")+\s*", line) and len(cur["toks"]) < 9:
                cur["toks"] += line.split()
            elif line.strip():
                close(); cur = None
        close(); cur = None
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Table 5.2.1: cropping intensity
def intensity(pages: list[str]) -> pd.DataFrame:
    rows = []
    for p in (458, 459):
        for line in pages[p - 1].splitlines():
            m = re.match(r"^\s*\d{1,2}\s+([A-Za-z][A-Za-z .'’-]*?)\s+((?:" + NUMTOK + r"\s+){6}" + NUMTOK + r")\s*$", line)
            if m and district(m.group(1)):
                v = [num(x) for x in m.group(2).split()]
                rows.append({"district": district(m.group(1)), "total_area_000acre": v[0],
                             "net_cropped_000acre_2021_22": v[1], "net_cropped_000acre_2022_23": v[2],
                             "gross_cropped_000acre_2021_22": v[3], "gross_cropped_000acre_2022_23": v[4],
                             "intensity_pct_2022_23": round(100 * v[4] / v[2]) if v[2] else None, "page": p})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Tables 4.2.x: event damage by district
HEADER_WORDS = re.compile(r"(?i)name of|area|damage|fully|partial|percentag|crops\b|region|district|ton\b|acre|"
                          r"caused|col\.|terms|under|yield|production|loss|^d$|^\)$|^e of")


def damage(pages: list[str]) -> pd.DataFrame:
    """Tables 4.2.x, one per event. 2017 table: fully, partially, % partial, full-equivalent, total, kg/acre,
    loss t. Later tables add 'area under crop' first and put 'fully' after the full-equivalent column."""
    rows, event, crop, cont, table_no = [], None, None, False, None
    for p in range(431, 450):
        for line in pages[p - 1].splitlines():
            s = line.strip()
            if e := re.match(r"^Table:?\s*(4\.2\.\d+)\s*(.*)", s):
                if e.group(1) != table_no:  # a repeated header on a continuation page keeps the current crop
                    table_no, crop = e.group(1), None
                    event = re.sub(r"\s+", " ", e.group(2)).strip()
                    cont = not re.search(r"(19|20)\d\d", event)  # title wraps: '... Month of' / 'April to June 2022.'
                else:
                    cont = not re.search(r"(19|20)\d\d", s)
                    if cont:
                        cont = "skip"
                continue
            if cont == "skip":
                cont = False
                continue
            if cont:
                event = f"{event} {s}".strip()
                cont = False
                continue
            m = re.match(r"^([A-Za-z][A-Za-z .'’()-]*?)\s+((?:" + NUMTOK + r"\s+){6,7}" + NUMTOK + r")\s*$", s)
            if m and event:
                d = district(m.group(1)) or ("Bangladesh" if m.group(1).strip() == "Bangladesh" else None)
                v = [num(x) for x in m.group(2).split()]
                if not d:
                    continue
                if len(v) == 7:
                    rec = dict(area_under_crop_acre=None, fully_damaged_acre=v[0], partially_damaged_acre=v[1],
                               pct_partial_damage=v[2], total_damaged_acre=v[4], yield_kg_per_acre=v[5],
                               production_loss_t=v[6])
                else:
                    rec = dict(area_under_crop_acre=v[0], partially_damaged_acre=v[1], pct_partial_damage=v[2],
                               fully_damaged_acre=v[4], total_damaged_acre=v[5], yield_kg_per_acre=v[6],
                               production_loss_t=v[7])
                rows.append({"event": event.rstrip("."), "crop": crop, "district": d, **rec, "page": p})
                continue
            if s and len(s) < 45 and not re.search(r"\d", s) and not district(s) and s[0].isupper() \
                    and not HEADER_WORDS.search(s):
                crop = s
    df = pd.DataFrame(rows)
    group = lambda c: next((g for k, g in (("seed", "Aman seedbed"), ("aus", "Aus rice"), ("aman", "Aman rice"),
                                           ("amon", "Aman rice"), ("boro", "Boro rice"), ("jute", "Jute"))
                            if k in str(c).lower()), c)
    df.insert(2, "crop_group", df["crop"].map(group))
    return df


def main() -> None:
    pages = load_pages()
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {"crop_district": crop_tables(pages), "crop_calendar": crop_calendar(),
               "census_costs": census_costs(pages), "harvest_prices": harvest_prices(pages),
               "irrigation": irrigation(pages), "intensity": intensity(pages), "damage": damage(pages),
               "holdings": holdings(pages), "wages": wages(pages), "monthly_prices": monthly_prices(pages),
               "livestock_census": livestock_census(pages)}
    outputs["bmd_monthly"], outputs["bmd_annual_rain"] = bmd_weather(pages)
    # the long table titles go to a lookup file instead of repeating on 21,000 rows
    cd = outputs["crop_district"]
    titles = cd.groupby(["crop", "variant", "table"]).page.agg(lambda s: f"{s.min()}-{s.max()}").reset_index()
    titles.rename(columns={"page": "pdf_pages"}).to_csv(OUT / "crop_district_tables.csv", index=False)
    outputs["crop_district"] = cd.drop(columns="table")
    for name, df in outputs.items():
        if name != "crop_district":
            df.insert(0, "source", SOURCE)
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:15s} {len(df):6,d} rows")


if __name__ == "__main__":
    main()
