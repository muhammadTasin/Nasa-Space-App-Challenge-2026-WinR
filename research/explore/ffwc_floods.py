"""River flood statistics by station and year from FFWC's Annual Flood Reports 2010-2021
(research/acquire/ffwc_reports.py downloads them).

Every report compares the year's water levels at the main stations with past floods (Tables 3.1-3.4: previous
record, danger level, the year's peak, days above danger level) and lists each station's monsoon peak with its
date (Table 3.5). This reads both for every year and matches the station names (spelled differently from year
to year) to FFWC's station list. Levels are metres above the Public Works Datum (mPWD); the new FFWC site gives
them above mean sea level, 0.45 m lower (Sunamganj danger level 8.25 mPWD = 7.80 mMSL).

Those tables cover the monsoon. The haor Boro is lost to flash floods before mid-May, so the 2018-2021 reports'
pre-monsoon table for the Meghna basin (15 Mar-15 May: monsoon and pre-monsoon danger levels, the season's peak
for the report year and for the flash-flood years 2010 and 2017, days above each) is read separately, with every
report's sentences on pre-monsoon and flash floods, and a year-by-year haor table built from both.

Output: research/floods/ffwc_station_years.csv (monsoon, 2010-2021), ffwc_premonsoon_meghna.csv (15 Mar-15 May:
        2010, 2017-2021), ffwc_premonsoon_notes.csv (the reports' own sentences), haor_flash_flood_years.csv
Usage : python research/explore/ffwc_floods.py
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH  # noqa: E402

# report spellings -> the station list's names
ALIAS = {"serajgonj": "serajganj", "sirajganj": "serajganj", "sunamgonj": "sunamganj", "kaunias": "kaunia",
         "lorergarh": "lourergorh", "lorergorh": "lourergorh", "narayangonj": "narayanganj", "manurb": "manurb",
         "manurailybridge": "manurb", "manurlybr": "manurb", "rlybr": "manurb", "moulvibazar": "moulvibazar", "bbaria": "bbaria", "brahmanbaria": "bbaria",
         "meghnabridge": "meghnabr", "hardingebridge": "hardingerb", "gorairailbridge": "gorairb", "gorairb": "gorairb",
         "chakrahimpur": "chakrahimpur", "elasin": "elasinghat", "sureswar": "sureshswar", "rekabibazar": "rekabibazar",
         "chapainawabganj": "cnawabganj", "nawabganj": "cnawabganj", "mohadebpur": "mohadevpur",
         "sherpur": "sherpursylhet", "debiddar": "debidwar", "comilla": "comilla", "cumilla": "comilla",
         "bogura": "bogra", "sarighat": "sarighat", "bhairabbazar": "bhairabbazar", "hatboalia": "hatboalia"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


class Stations:
    """Find the station at the end of a 'river station' text."""

    def __init__(self, table: pd.DataFrame):
        self.names = {norm(n): n for n in table["station"]}
        self.ids = dict(zip(table["station"], table["stid"]))

    def match(self, text: str) -> str | None:
        words = text.replace("*", " ").split()
        for k in (3, 2, 1):  # the longest tail that is a station
            key = norm("".join(words[-k:]))
            key = ALIAS.get(key, key)
            if key in self.names:
                return self.names[key]
        key = ALIAS.get(norm(words[-1]), norm(words[-1])) if words else ""
        close = difflib.get_close_matches(key, list(self.names), n=1, cutoff=0.85)
        return self.names[close[0]] if close else None


def num(tok: str) -> float | None:
    tok = tok.strip("*")
    try:
        return float(tok)
    except ValueError:
        return None


def leading_values(toks: list[str]) -> list[str]:
    """The table cells of a row: numbers, '-' and 'NA' up to the first word (text after a table can run on)."""
    out = []
    for t in toks:
        if not re.fullmatch(r"\d+(\.\d+)?|-|NA", t):
            break
        out.append(t)
    return out


def premonsoon_rows(text: str, stations: Stations, report_year: int) -> list[dict]:
    """The Meghna-basin pre-monsoon table (15 Mar-15 May; 2018-2021 reports): monsoon and pre-monsoon danger
    levels, the season's peak for three years (the report year and the flash-flood years 2010 and 2017, in the
    order the header gives), days above the monsoon danger level for each, days above the pre-monsoon danger
    level for the report year."""
    m = re.search(r"(?m)^\s*((?:(?:19|20)\d\d\s+){6}(?:19|20)\d\d)\s*$", text)
    if not m:
        return []
    years = [int(y) for y in m.group(1).split()[:3]]
    out = []
    for row in rows_of(text[m.end():]):
        toks = [t.strip("*") for t in row.split()[1:]]
        k = next((i for i, t in enumerate(toks) if re.fullmatch(r"\d+\.\d+|-|NA", t)), None)
        if not k:
            continue
        name, vals = " ".join(toks[:k]), leading_values(toks[k:])
        if len(vals) < 8:
            continue
        mdl, pmdl = num(vals[0]), num(vals[1])
        for j, year in enumerate(years):
            peak = num(vals[2 + j])
            days_m = int(vals[5 + j]) if vals[5 + j].isdigit() else (0 if peak is not None and mdl and peak < mdl else None)
            days_p = None
            if year == report_year and len(vals) > 8 and vals[8].isdigit():
                days_p = int(vals[8])
            elif peak is not None and pmdl and peak < pmdl:
                days_p = 0
            out.append({"year": year, "name_in_report": name, "station": stations.match(name),
                        "monsoon_dl_mpwd": mdl, "premonsoon_dl_mpwd": pmdl, "peak_15mar_15may_mpwd": peak,
                        "days_above_monsoon_dl": days_m, "days_above_premonsoon_dl": days_p,
                        "report_year": report_year})
    return out


def rows_of(text: str) -> list[str]:
    """Join a table's lines into rows: a row starts with a serial number followed by a name."""
    rows = []
    for line in text.splitlines():
        if re.match(r"^\s*\d{1,3}\s+[A-Za-z*]", line):
            rows.append(line.strip())
        elif rows and line.strip() and not re.match(r"^\s*(\(|Table|Figure|\d\.\d)", line.strip()):
            rows[-1] += " " + line.strip()
    return rows


def comparison_rows(text: str, stations: Stations) -> list[dict]:
    """Tables 3.1-3.4: previous maximum, danger level, the year's peak and two comparison years' peaks, then days
    above danger level for the same three years. A full row has 8 values; blank cells shorten it, so the peaks
    (decimals, NA, -) run until the first whole number, which is the year's days above danger level."""
    out = []
    for row in rows_of(text):
        toks = [t.strip("*") for t in row.split()[1:]]
        k = next((i for i, t in enumerate(toks) if re.fullmatch(r"\d+\.\d+|-|NA", t)), None)
        if k is None or k == 0:
            continue
        name, vals = " ".join(toks[:k]), leading_values(toks[k:])
        if len(vals) < 3 or re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", " ".join(toks[k:k + 3])):
            continue  # not a comparison row (the peak-date table follows on the same page in some years)
        if len(vals) >= 8:
            days_tok = vals[5]
        else:
            j = next((i for i, v in enumerate(vals[2:], start=2) if v.isdigit()), None)
            days_tok = vals[j] if j is not None else None
        prev_max, dl, peak = num(vals[0]), num(vals[1]), num(vals[2])
        days = int(days_tok) if days_tok and days_tok.isdigit() else None
        if peak is not None and dl is not None and peak < dl:
            days = 0  # never reached danger level
        out.append({"name_in_report": name, "station": stations.match(name), "previous_max_mpwd": prev_max,
                    "danger_level_mpwd": dl, "peak_mpwd": peak, "days_above_dl": days})
    return out


def peak_date_rows(text: str, stations: Stations, year: int) -> list[dict]:
    """Table 3.5: 'n RIVER STATION peak dd/mm/yy'."""
    out = []
    for m in re.finditer(r"(?m)^\s*\d{1,3}\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$", text):
        yy = int(m.group(5))
        yy = yy + 2000 if yy < 100 else yy
        try:
            when = pd.Timestamp(yy, int(m.group(4)), int(m.group(3))).date()
        except ValueError:
            continue
        if yy != year:
            continue
        out.append({"station": stations.match(m.group(1)), "peak_date": when, "peak_in_date_table": float(m.group(2))})
    return out


# What each report says about flash floods in the north-east before mid-May (read from ffwc_premonsoon_notes.csv);
# the text is matched back to its sentence for the page number
HAOR_YEARS = {
    2010: ("yes", "late April and again early May",
           "pre-monsoon flash flood, in the last part of April and again the first part of May"),
    2014: ("no", None, "No flash flood experienced during pre-monsoon"),
    2015: ("not before mid-May", "June (monsoon)", "which led to flash flood in that North-Eastern part"),
    2017: ("yes", "very early April", "severe flash flood in very early April in the North East region"),
    2018: ("late", "second week of May (none in March-April)", "crossed and flowed above Pre-Monsoon Danger Levels"),
    2019: ("short", None, "Moderate to severe flash floods occurred in the North-Eastern"),
    2020: ("no", None, "No pre-monsoon flooding occurred this year"),
    2021: ("no", None, "No pre-monsoon flooding occurred this year"),
}


def haor_years(notes: pd.DataFrame, pre: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in range(2010, 2022):
        label, timing, quote = HAOR_YEARS.get(year, ("not stated", None, None))
        hit = notes[(notes["year"] == year) & notes["sentence"].str.contains(quote, regex=False)] if quote else notes[:0]
        rec = {"year": year, "flash_flood_before_15_may": label, "timing": timing,
               "ffwc_says": hit["sentence"].iloc[0] if len(hit) else None,
               "report_page": int(hit["page"].iloc[0]) if len(hit) else None}
        for st in ("Sunamganj", "Jariajanjail", "Kanaighat"):
            r = pre[(pre["station"] == st) & (pre["year"] == year)]
            key = st.lower()
            rec[f"{key}_peak_mpwd"] = r["peak_15mar_15may_mpwd"].iloc[0] if len(r) else None
            rec[f"{key}_premonsoon_dl_mpwd"] = r["premonsoon_dl_mpwd"].iloc[0] if len(r) else None
            rec[f"{key}_days_above_premonsoon_dl"] = r["days_above_premonsoon_dl"].iloc[0] if len(r) else None
        rows.append(rec)
    return pd.DataFrame(rows)


def main() -> None:
    d = DATA / "ffwc"
    stations = Stations(pd.read_csv(d / "stations_old_site.csv"))
    rows, pre, notes = [], [], []
    for path in sorted(d.glob("annual*.pdf")):
        year = 2000 + int(path.stem[-2:])
        pdf = pdfium.PdfDocument(str(path))
        texts = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
        comp, dates = [], []
        for i, t in enumerate(texts):
            for m in re.finditer(r"Comparison of Water Level|Comparative WL of Selected Stations", t, re.I):
                head = t[m.start():m.start() + 300]
                if re.search(r"Pre.?Monsoon|15 Mar", head, re.I):  # the haor flash-flood season
                    more = texts[i + 1] if i + 1 < len(texts) else ""  # the table can run onto the next page
                    pre += premonsoon_rows(t[m.start():] + "\n" + more, stations, year)
                    continue
                chunk = t[m.start():] + "\n" + texts[i + 1] if i + 1 < len(texts) else t[m.start():]
                chunk = re.split(r"\n\s*(?:\(\*|3\.\s?\d\s+[A-Z]|Comparative hydrograph|Figure|Table\s*\d)", chunk,
                                 maxsplit=1)[0]
                comp += [{**r, "page": i + 1} for r in comparison_rows(chunk, stations)]
            if re.search(r"Peak Water Level.{0,40}with Dates?", t, re.I) or (dates and re.search(r"Peak WL", t)):
                dates += peak_date_rows(t, stations, year)
            if i < 60:  # the report's own words on the year's pre-monsoon (flash) floods
                flat = re.sub(r"\s+", " ", t)
                for s in re.findall(r"[^.]*(?:flash flood|pre-monsoon|pre monsoon|premonsoon)[^.]*\.", flat, re.I):
                    if len(s) < 400 and not re.search(r"\.{4,}|Table \d|Figure \d", s):
                        notes.append({"year": year, "page": i + 1, "sentence": s.strip()})
        c = pd.DataFrame(comp)
        c = c[c["station"].notna()].drop_duplicates("station")
        dt = pd.DataFrame(dates)
        if len(dt):
            dt = dt[dt["station"].notna()].drop_duplicates("station")
            c = c.merge(dt, on="station", how="outer")
        c.insert(0, "year", year)
        rows.append(c)
        print(year, f"{len(comp)} table rows, {c['peak_mpwd'].notna().sum()} with a peak,",
              f"{c['days_above_dl'].notna().sum()} with days above DL, {len(dt)} peak dates", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out["stid"] = out["station"].map(stations.ids)
    cols = ["year", "station", "stid", "name_in_report", "danger_level_mpwd", "previous_max_mpwd", "peak_mpwd",
            "peak_date", "peak_in_date_table", "days_above_dl", "page"]
    out = out[cols].sort_values(["station", "year"])
    dest = RESEARCH / "floods"
    dest.mkdir(exist_ok=True)
    out.to_csv(dest / "ffwc_station_years.csv", index=False)
    print(len(out), "station-years,", out["station"].nunique(), "stations ->",
          (dest / "ffwc_station_years.csv").relative_to(RESEARCH.parent))
    p = pd.DataFrame(pre)
    p = p[p["station"].notna()]
    p["own_report"] = p["year"] == p["report_year"]  # a year's own report wins; else the latest report
    p = p.sort_values(["own_report", "report_year"], ascending=False).drop_duplicates(["station", "year"])
    p["stid"] = p["station"].map(stations.ids)
    p = p.drop(columns="own_report").sort_values(["station", "year"])
    p.to_csv(dest / "ffwc_premonsoon_meghna.csv", index=False)
    print(len(p), "pre-monsoon station-years, years", sorted(p["year"].unique()))
    n = pd.DataFrame(notes).drop_duplicates(["year", "sentence"])
    n.to_csv(dest / "ffwc_premonsoon_notes.csv", index=False)
    print(len(n), "sentences on pre-monsoon and flash floods")
    h = haor_years(n, p)
    h.to_csv(dest / "haor_flash_flood_years.csv", index=False)
    pd.set_option("display.width", 220)
    print(h[["year", "flash_flood_before_15_may", "timing", "report_page", "sunamganj_peak_mpwd",
             "jariajanjail_peak_mpwd", "jariajanjail_days_above_premonsoon_dl"]].to_string(index=False))


if __name__ == "__main__":
    main()
