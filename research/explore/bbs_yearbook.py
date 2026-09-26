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


def crop_tables(pages: list[str]) -> pd.DataFrame:
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
            for k, y in enumerate(years[-2:] if len(years) >= 2 else ["2023-24", "2024-25"]):
                a_ac, a_ha, _, y_tha, prod = v[5 * k: 5 * k + 5]
                note = None
                # the printed t/ha column has typos (Aus hybrid 2023-24): trust production / area instead
                if a_ha and prod and y_tha is not None and abs(prod / a_ha - y_tha) > 0.05 * (prod / a_ha) + 0.05 \
                        and "jute" not in title.lower():
                    y_tha, note = round(prod / a_ha, 3), "yield recomputed as production/area (printed t/ha inconsistent)"
                rows.append({"table": title, "page": p, "district": d, "year": y, "area_acre": a_ac,
                             "area_ha": a_ha, "yield_t_ha": y_tha, "production_t": prod, "note": note})
        else:  # minor crops: 3 seasons x (acre, t); yield derived
            for k, y in enumerate(years[:3] if len(years) >= 3 else ["2022-23", "2023-24", "2024-25"]):
                a_ac, prod = v[2 * k: 2 * k + 2]
                rows.append({"table": title, "page": p, "district": d, "year": y, "area_acre": a_ac,
                             "area_ha": None if a_ac is None else round(a_ac * ACRE_HA, 1),
                             "yield_t_ha": round(prod / (a_ac * ACRE_HA), 3) if a_ac and prod is not None else None,
                             "production_t": prod})

    for p in range(66, 425):
        t = pages[p - 1]
        head = "\n".join(t.splitlines()[:3])
        m = re.search(r"^(Table[^\n]*?(?:Estimat|Area and Production)[^\n]*)", head, re.I | re.M)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        elif re.search(r"Introduction|National estimate", head):
            title = None  # narrative page between tables
        if not title:
            continue
        years = title_years(title) or list(dict.fromkeys(season(y) for y in re.findall(r"20\d\d\s*-\s*\d{2,4}", t[:500])))
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
               "irrigation": irrigation(pages), "intensity": intensity(pages), "damage": damage(pages)}
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
