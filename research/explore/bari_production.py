"""Crop production technology from BARI's Krishi Projukti Hatboi (Handbook on Agro-technology), 10th ed., Dec 2024.

For every crop the handbook gives a "Drcv`b cÖhyw³" (utpadon projukti, production technology) section: soil, land
preparation, sowing time and method, seed rate, spacing, a fertilizer table, irrigation, weeding, harvest. This
script cuts those sections out (the table of contents gives each crop's page), converts the Bijoy text to Unicode
Bangla, splits the bold field labels, and pulls the numbers a rotation engine needs.

The PDF was laid out in Illustrator: every page's text layer also carries its neighbours' text frames, placed off
the page. Only characters inside the page box are kept, with their font, so English words set in Times New Roman
are not run through the Bijoy converter and bold (the field labels) is known.

Input : "raw, collected datas/krishiProjuktiHatboi_10.pdf" (also on bari.gov.bd)
Output: research/crops/bari_production_technology.csv (one row per crop section, numbers + key text)
        research/crops/bari_production_fields.csv (every labelled field, Unicode Bangla, for reading and for the
        advisory text)
Usage : python research/explore/bari_production.py
"""
from __future__ import annotations

import calendar
import datetime
import ctypes
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bijoy import to_unicode  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PDF = REPO / "raw, collected datas" / "krishiProjuktiHatboi_10.pdf"
CACHE = REPO / "research" / "data" / "brri" / "bari_hatboi10_runs.json"
CROPS = REPO / "research" / "crops"
CITE = "BARI Krishi Projukti Hatboi, 10th edition (Dec 2024), Akhond et al. (eds.) 2025"
PAGE_OFFSET = 24  # PDF page index = printed page + 24
BOLD_OPEN, BOLD_CLOSE = "⟦", "⟧"  # marks bold spans in the converted text


def N(s: str) -> str:
    """NFC, as the converter emits: text typed here must match its য় / ড় / ঢ় (base + nukta)."""
    return unicodedata.normalize("NFC", s)


PROD = N("উৎপাদন প্রযুক্তি")  # production technology


def page_runs(pdf_path: Path) -> list[list[list[str]]]:
    """Per page, the visible text as [kind, text] runs; kind 'b' Bijoy, 'B' Bijoy bold, 'I' Bijoy italic (photo
    captions, scientific names), 'l' any other font."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    pdf = pdfium.PdfDocument(str(pdf_path))
    buf, flags = ctypes.create_string_buffer(256), ctypes.c_int()
    l, r, b, t = (ctypes.c_double() for _ in range(4))
    pages = []
    for pno in range(len(pdf)):
        page = pdf[pno]
        w, h = page.get_size()
        tp = page.get_textpage()
        runs: list[list[str]] = []
        visible, kind = False, "l"
        for i in range(pdfium_c.FPDFText_CountChars(tp)):
            ch = chr(pdfium_c.FPDFText_GetUnicode(tp, i))
            if pdfium_c.FPDFText_IsGenerated(tp, i) == 1 or ch in "\r\n":
                if visible and ch != "\r":  # generated spaces and line breaks follow the character before them
                    runs.append([kind, ch])
                continue
            pdfium_c.FPDFText_GetCharBox(tp, i, l, r, b, t)
            cx, cy = (l.value + r.value) / 2, (b.value + t.value) / 2
            visible = 0 <= cx <= w and 0 <= cy <= h
            if not visible:
                continue
            n = pdfium_c.FPDFText_GetFontInfo(tp, i, buf, 256, flags)
            font = buf.value.decode("utf-8", "replace") if n else ""
            kind = ("B" if "Bold" in font else "I" if "Italic" in font else "b") if "MJ" in font else "l"
            runs.append([kind, ch])
        merged: list[list[str]] = []
        for k, c in runs:  # merge characters into runs of one kind; whitespace joins the run it sits in
            if merged and (merged[-1][0] == k or c.isspace()):
                merged[-1][1] += c
            else:
                merged.append([k, c])
        pages.append(merged)
    CACHE.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


HEADER = re.compile(N(r"^\s*(?:\d+\s*\|\s*)?কৃষি প্রযুক্তি হাতবই(?:\s*\|\s*\d+)?\s*$"))


def page_text(runs: list[list[str]]) -> str:
    """Unicode text of one page: bold Bijoy spans wrapped in BOLD_OPEN/BOLD_CLOSE; the running header (chapter
    name, page number) and lines set wholly in italic (photo captions) dropped."""
    lines: list[list[tuple[str, str]]] = [[]]
    for kind, text in runs:
        for k, piece in enumerate(text.split("\n")):
            if k:
                lines.append([])
            if piece:
                lines[-1].append((kind, piece))
    out = []
    for segs in lines:
        if segs and all(k == "I" or not s.strip() for k, s in segs):
            continue  # caption under a photo
        line = ""
        for kind, text in segs:
            if kind == "l":
                line += text
            elif kind == "B" and text.strip():
                lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
                line += f"{lead}{BOLD_OPEN}{to_unicode(text.strip())}{BOLD_CLOSE}{trail}"
            else:
                line += to_unicode(text)
        bare = line.replace(BOLD_OPEN, "").replace(BOLD_CLOSE, "").strip()
        if HEADER.match(bare) or bare in CHAPTERS:  # running header, wherever the page's text order puts it
            continue
        out.append(line)
    text = "\n".join(out)
    text = text.replace(BOLD_CLOSE + " " + BOLD_OPEN, " ").replace(BOLD_CLOSE + BOLD_OPEN, "")  # join split spans
    return re.sub(r"\n\s*\n+", "\n", text)


# chapter names as the running header prints them (first line of every page)
CHAPTERS = {N(x) for x in {"কন্দাল ফসল", "ডাল ফসল", "তেল ফসল", "সবজি ফসল", "ফল ফসল", "ফুল ফসল", "মসলা ফসল", "দানা ফসল",
            "কৃষি যন্ত্রপাতি", "সেচ ও পানি ব্যবস্থাপনা", "সমন্বিত বালাই দমন ব্যবস্থাপনা (আইপিএম)",
            "উদ্ভিদ রোগ ব্যবস্থাপনা", "শস্য সংগ্রহোত্তর প্রযুক্তি", "অনিষ্টকারী মেরুদণ্ডী প্রাণি ব্যবস্থাপনা",
            "অনিষ্টকারী মেরুদন্ডী প্রাণি ব্যবস্থাপনা", "বীজ প্রযুক্তি", "লাক্ষা ফসল", "পাহাড়ী কৃষি", "জীবপ্রযুক্তি",
            "উদ্ভিদ কৌলিসম্পদ", "সরেজমিন ও সিস্টেম গবেষণা", "সরেজমিন", "ডাল", "তেল", "সবজি", "মসলা", "দানা"}}
CROP_CHAPTERS = [N(x) for x in ["কন্দাল ফসল", "ডাল ফসল", "তেল ফসল", "সবজি ফসল", "ফল ফসল", "ফুল ফসল", "মসলা ফসল", "দানা ফসল"]]


def toc(runs) -> list[tuple[str, int]]:
    """(entry, printed page) from the table of contents, in order."""
    entries = []
    for p in range(7, 20):
        for line in page_text(runs[p]).split("\n"):
            m = re.match(r"^\s*(.+?)\s*_{3,}\s*(\d+)\s*$", line.replace(BOLD_OPEN, "").replace(BOLD_CLOSE, ""))
            if m:
                entries.append((m.group(1).strip(), int(m.group(2))))
    return entries


NOT_CROP = (N("অন্যান্য প্রযুক্তি"), N("নন-কমোডিটি প্রযুক্তি"))


def crop_sections(entries: list[tuple[str, int]]) -> list[dict]:
    """One dict per production-technology entry. The crop is the entry just before the block's last variety-list
    heading ('... জাত'), or, without one, the block's first entry; a block runs from the previous production-
    technology entry (or chapter heading) to this one. The section ends at the next entry's heading."""
    out, chapter, block = [], None, []
    for k, (name, page) in enumerate(entries):
        if name in CHAPTERS or any(name.startswith(N(c)) for c in ("কৃষি যন্ত্রপাতি", "সমন্বিত বালাই", "অনিষ্টকারী")):
            chapter, block = name, []
            continue
        if chapter in CROP_CHAPTERS and name != PROD and re.search(N(r"উৎপাদন(?: প্রযুক্তি)?$"), name):
            # a section named for itself ("শীতকালীন পেঁয়াজ উৎপাদন", "বাটিশাক ও চীনাশাকের উৎপাদন প্রযুক্তি")
            crop = re.sub(N(r"ে?র$"), "", re.sub(N(r"\s*উৎপাদন(?: প্রযুক্তি)?$"), "", name))
            nxt = next(((n, p) for n, p in entries[k + 1:] if n not in NOT_CROP), (None, None))
            out.append({"chapter": chapter, "crop_bn": crop, "crop_page": page, "prod_page": page,
                        "next_bn": nxt[0], "next_page": nxt[1], "heading": name})
            block = []
            continue
        if name != PROD:
            if name not in NOT_CROP:
                block.append((name, page))
            continue
        if chapter in CROP_CHAPTERS and block:
            hdr = next((i for i in range(len(block) - 1, -1, -1) if block[i][0].endswith(N("জাত"))), None)
            if hdr is None:
                crop, cpage = block[0]
            elif hdr > 0:
                crop, cpage = block[hdr - 1]
            else:  # only a variety-list heading: 'হাইব্রিড শসার জাত' -> 'হাইব্রিড শসা'
                crop, cpage = re.sub(N(r"ে?র$"), "", block[hdr][0][:-3].strip()), block[hdr][1]
            nxt = next(((n, p) for n, p in entries[k + 1:] if n not in NOT_CROP), (None, None))
            out.append({"chapter": chapter, "crop_bn": crop, "crop_page": cpage, "prod_page": page,
                        "next_bn": nxt[0], "next_page": nxt[1]})
        block = []
    return out


def section_text(runs, sec: dict) -> str:
    """Text from the bold 'উৎপাদন প্রযুক্তি' heading on the section's page to the next entry's heading."""
    p0 = sec["prod_page"] + PAGE_OFFSET
    p1 = (sec["next_page"] or sec["prod_page"] + 3) + PAGE_OFFSET
    pages = [page_text(runs[p]) for p in range(p0 - 1, min(p1, len(runs) - 1) + 1)]
    text = "\n".join(pages)
    first = len(pages[0]) + 1  # where page p0 starts
    # the heading, alone or after the crop name ("ডাঁটা উৎপাদন প্রযুক্তি"); self-named sections use their own
    head = re.escape(sec["heading"]).replace(r"\ ", r"\s*") if "heading" in sec else PROD
    starts = [m.start() for m in re.finditer(BOLD_OPEN + "[^" + BOLD_CLOSE + r"\n]{0,30}" + head, text)]
    # the heading on the listed page, else the one just before it (the book's contents are off by a page at
    # times), else the next one
    on_page = [s for s in starts if first <= s <= first + len(pages[1])]
    before, after = [s for s in starts if s < first], [s for s in starts if s > first + len(pages[1])]
    start = on_page[0] if on_page else before[-1] if before else after[0] if after else first
    end = len(text)
    if sec["next_bn"]:
        name = re.escape(sec["next_bn"].split(" (")[0])
        m = re.compile(BOLD_OPEN + r"\s*" + name + r"(?:\s*" + BOLD_CLOSE + r"|\s*\n)").search(text, start + 10)
        if m:
            end = m.start()
        else:  # heading not bold or spelled differently: stop at the start of the next entry's page
            end = max(start, len(text) - len(pages[-1])) if p1 > p0 else len(text)
    return text[start:end]


# field label -> key (first match wins)
FIELD_KEYS = [(k, re.compile(N(p))) for k, p in [
    ("seed_storage", r"বীজ সংরক্ষণ"),
    ("fertilizer_method", r"সার প্রয়োগ(?:ের)? পদ্ধতি|^প্রয়োগ পদ্ধতি"),
    ("fertilizer", r"সার(?:ের|\s|/|$)"),
    ("irrigation", r"সেচ|পানি ব্যবস্থাপনা"),
    ("seed_rate", r"বীজের হার|বীজ হার|বীজের পরিমাণ|চারার সংখ্যা|বীজ/চারার"),
    ("spacing", r"দূরত্ব"),
    ("pest_disease", r"রোগ|পোকা|বালাই|দমন|আক্রমণ|প্রতিকার|লক্ষণ|ক্ষতির|দাগ|পচা|ঝলসা|মোজাইক|মিলডিউ|ব্লাইট|মাছি|বিটল|থ্রিপস|মাকড়|ছত্রাক|ভাইরাস"),
    ("intercultural", r"মাটি তোলা|মাটি দেওয়া|মাটি দেয়া"),  # earthing up, before 'তোলা' (lifting) below
    ("sowing_time", r"(?:বপন|রোপণ|রোপন|লাগানো)[^:]{0,15}(?:সময়|মৌসুম)|মৌসুম|(?<!শেষ )চাষের সময়|^সময়$|আগাম চাষ|"
                    r"না[বভ][িী] চাষ"),
    ("harvest", r"সংগ্রহ|কাটা|(?<!মাটি )তোলা|উত্তোলন|পরিপক্ক"),
    ("sowing_method", r"বপন|রোপণ|রোপন|লাগানো|চারা|বংশ ?বিস্তার"),
    ("land_preparation", r"জমি"),
    ("soil_climate", r"মাটি|জলবায়ু|আবহাওয়া|এলাকা"),
    ("intercultural", r"পরিচর্যা|আগাছা|নিড়ান|মালচ|খুঁটি|মাচা|ছাঁটাই"),
    ("yield", r"ফলন"),
    ("pest_disease", r"ব্যবস্থাপনা"),
]]


def field_key(label: str) -> str:
    return next((k for k, p in FIELD_KEYS if p.search(label)), "other")


def split_fields(text: str) -> list[dict]:
    """Split a section into [{label, key, text}]: a bold span ending in ':' is a field label, any other bold span
    a heading whose following text is kept under the heading's name."""
    parts = re.split("(" + BOLD_OPEN + ".*?" + BOLD_CLOSE + r"\s*:?)", text, flags=re.S)
    fields: list[dict] = []
    for k in range(1, len(parts), 2):
        body = parts[k + 1] if k + 1 < len(parts) else ""
        span = parts[k].strip().strip(BOLD_OPEN + BOLD_CLOSE + ": \n")
        lines = [x.strip(" :") for x in re.split(r"\n", parts[k].replace(BOLD_OPEN, "").replace(BOLD_CLOSE, ""))]
        lines = [x for x in lines if x]
        label = lines[-1] if lines else span
        if label == PROD and not body.strip():
            continue
        body = re.sub(r"\s*\n\s*", " ", body).strip()
        if fields and fields[-1]["label"] == label:
            fields[-1]["text"] = (fields[-1]["text"] + " " + body).strip()
            continue
        fields.append({"label": label, "key": field_key(label), "text": body})
    return [f for f in fields if f["text"] or f["key"] != "other"]


# ---------------------------------------------------------------- numbers
NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"  # 10,000 or 2.5
RNG = NUM + r"(?:\s*(?:-|–|থেকে|হতে)\s*" + NUM + r")?"
BN = r"ঀ-৿"


def pair(m: re.Match, i: int = 1) -> tuple[float, float]:
    a = float(m.group(i).replace(",", ""))
    return a, float(m.group(i + 1).replace(",", "")) if m.group(i + 1) else a


GREG = {1: r"জানুয়ার[িী]", 2: r"ফেব্রু?য়ার[িী]", 3: r"মার্চ", 4: r"এপ্রিল", 5: r"(?<![" + BN + r"])মে(?![" + BN + r"\.])",
        6: r"জুন", 7: r"জুলাই", 8: r"আগস্ট|আগষ্ট|অগাস্ট|অগস্ট|আগাস্ট", 9: r"সেপ্টেম্বর", 10: r"অক্টোবর",
        11: r"নভেম্বর", 12: r"ডিসেম্বর"}
# Bangla calendar month -> (Gregorian month, day) it starts on (revised calendar, +-1 day)
BANGLA = {r"বৈশাখ": (4, 14), r"জ্যৈষ্ঠ|জৈষ্ঠ": (5, 15), r"আষাঢ়": (6, 15), r"শ্রাবণ": (7, 16), r"ভাদ্র": (8, 16),
          r"আশ্বিন": (9, 16), r"কার্তিক": (10, 17), r"অগ্রহায়ণ": (11, 16), r"পৌষ": (12, 16), r"মাঘ": (1, 15),
          r"ফাল্গুন": (2, 14), r"চৈত্র": (3, 15)}
QUAL = r"মধ্যে|মধ্য|মাঝামাঝি|মধ্যভাগ|শেষ|প্রথম|শুরু|1ম|১ম|2য়|২য়|দ্বিতীয়|3য়|৩য়|তৃতীয়|4র্থ|৪র্থ|চতুর্থ"
DAYS = {"mid": (15, 15), "end": (23, 30), "w1": (1, 7), "w2": (8, 14), "w3": (15, 21), "w4": (22, 28), "": (1, 30)}
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def qual_key(q: str | None) -> str:
    q = q or ""
    return ("mid" if re.search(N("মধ্য|মাঝামাঝি"), q) else "end" if N("শেষ") in q else
            "w1" if re.search(N("প্রথম|শুরু|1ম|১ম"), q) else "w2" if re.search(N("2য়|২য়|দ্বিতীয়"), q) else
            "w3" if re.search(N("3য়|৩য়|তৃতীয়"), q) else "w4" if re.search(N("4র্থ|৪র্থ|চতুর্থ"), q) else "")


def _month_re(names: str) -> re.Pattern:
    return re.compile(N(r"(?:(" + QUAL + r")[\s\-–]*)?(" + names + r")(?:ের|র|য়ের|\s*এর)?(?:\s*মাসের|\s*মাসে|\s*মাস)?"
                        r"(?:\s*(" + QUAL + r")\s*(?:সপ্তাহ|পক্ষ|ভাগ)?)?"))


GREG_RE = _month_re("|".join(f"(?:{v})" for v in GREG.values()))
BANGLA_RE = _month_re("|".join(f"(?:{v})" for v in BANGLA))
CONNECT = re.compile(N(r"থেকে|হতে|-|–|—|পর্যন্ত"))


def windows(text: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Date windows ((month, day), (month, day)) named in a text, in reading order. 'X থেকে Y' / 'X-Y' make one
    window, a lone month a whole month (a lone 'mid-X' a fortnight). Bangla calendar months are converted, except
    where the book gives the Gregorian equivalent next to them ("কার্তিক ... (মধ্য-অক্টোবর থেকে মধ্য-নভেম্বর)")."""
    greg_ms = list(GREG_RE.finditer(text))
    bangla_ms = [m for m in BANGLA_RE.finditer(text) if not any(abs(m.start() - g.start()) < 80 for g in greg_ms)]

    def when(m: re.Match, greg: bool, is_start: bool, alone: bool = False) -> tuple[int, int]:
        name = m.group(2)
        k = qual_key((m.group(1) or "") + " " + (m.group(3) or ""))
        days = (8, 22) if alone and k == "mid" else DAYS[k]
        if greg:
            mon = next(n for n, p in GREG.items() if re.fullmatch(N(p), name))
            return mon, min(days[0 if is_start else 1], calendar.monthrange(2025, mon)[1])
        mon, day = next(v for p, v in BANGLA.items() if re.fullmatch(N(p), name))
        off = {"mid": (7, 21) if alone else (15, 15), "end": (23, 29), "w1": (0, 6), "w2": (7, 13), "w3": (14, 20),
               "w4": (21, 27), "": (0, 29)}[k][0 if is_start else 1]
        d = datetime.date(2025, mon, day) + datetime.timedelta(days=int(off))
        return d.month, d.day

    found = []
    for ms, greg in ((greg_ms, True), (bangla_ms, False)):
        i = 0
        while i < len(ms):
            a = ms[i]
            gap = text[a.end():ms[i + 1].start()] if i + 1 < len(ms) else ""
            # 'X থেকে Y', 'X-Y', and for Bangla months also 'X Y' ("কার্তিক অগ্রহায়ণ")
            if i + 1 < len(ms) and len(gap) <= 40 and (CONNECT.search(gap) or (not greg and not gap.strip())):
                found.append((a.start(), (when(a, greg, True), when(ms[i + 1], greg, False))))
                i += 2
            else:
                found.append((a.start(), (when(a, greg, True, True), when(a, greg, False, True))))
                i += 1
    return [w for _, w in sorted(found)]


def fmt(ws) -> str | None:
    return "; ".join(f"{a[1]} {MON[a[0] - 1]}-{b[1]} {MON[b[0] - 1]}" for a, b in ws) or None


FERTS = {  # key -> Bangla names (longest first inside each alternation)
    "urea": r"ইউরিয়া", "tsp": r"টিএসপি|টি এস পি|ট্রিপল সুপার ফসফেট", "mop": r"এমওপি|এমও পি|এম ও পি|এমপি|মিউরেট অব পটাশ",
    "gypsum": r"জিপসাম", "zinc_sulphate": r"জিংক সালফেট|জিঙ্ক সালফেট|জিংক|দস্তা",
    "boron": r"বরিক এসিড|বোরিক এসিড|বোরিক এ্যাসিড|বরিক এ্যাসিড|সলুবর বোরন|বোরাক্স|বোরন|সোহাগা",
    "dap": r"ডিএপি|ডি এ পি", "magnesium_sulphate": r"ম্যাগনেসিয়াম সালফেট|ম্যাগনেশিয়াম সালফেট|ম্যাগনেসিয়াম",
    "cowdung": r"পচা গোবর|গোবর সার|গোবর|খামারজাত সার|কম্পোস্ট|জৈব সার", "lime": r"ডলোচুন|ডলোমাইট|চুন",
    "molybdenum": r"অ্যামোনিয়াম মলিবডেট|এমোনিয়াম মলিবডেট|মলিবডেনাম", "sulphur": r"সালফার|গন্ধক",
    "oil_cake": r"সরিষার খৈল|খৈল", "ash": r"ছাই"}
FERT_RE = re.compile(N(r"(?<![" + BN + r"])(" + "|".join(FERTS.values()) + r")\*?(?:\s*সার)?\s*(\([^)]{0,25}\))?"
                       r"\s*[:\-–]?\s*" + RNG + r"(?![\d.])\s*(কেজি|গ্রাম|মে\.?\s*টন|টন)?"
                       r"(?!\s*(?:কিস্তি|ভাগ|দিন|বার|%|সপ্তাহ|মাস|সেমি|মিলি|লিটার|বছর|টি(?![" + BN + r"])))"))
UNIT_KG = {N("কেজি"): 1.0, N("গ্রাম"): 0.001, N("টন"): 1000.0}


def fert_key(name: str) -> str:
    return next(k for k, p in FERTS.items() if re.fullmatch(N(p), name))


HECTARE = re.compile(N(r"হেক্টর|হেঃ|/হে(?![" + BN + "])"))
OTHER_BASES = [(k, re.compile(N(p))) for k, p in (
    ("decimal", r"শতাংশ|শতক"), ("bigha", r"বিঘা"), ("plant", r"গাছ|প্রতিটি গাছে|গাছপ্রতি"), ("pit", r"মাদা|গর্ত|পিট"),
    ("m2", r"বর্গমিটার|বর্গ মিটার"), ("acre", r"একর"))]


def basis(context: str) -> str:
    """Area or plant a dose or seed rate refers to, from one sentence."""
    if HECTARE.search(context):
        return "ha"
    return next((k for k, p in OTHER_BASES if p.search(context)), "ha?")


TABLE_HEAD = re.compile(N(r"সারের নাম|সারের পরিমাণ|সারের মাত্রা|মোট পরিমাণ"))


# smallest believable per-hectare dose; below it a figure is per plant, pit or decimal, or not a dose at all
MIN_PER_HA = {"urea": 10, "tsp": 10, "mop": 10, "gypsum": 10, "dap": 10, "magnesium_sulphate": 5, "zinc_sulphate": 1,
              "boron": 1, "lime": 50, "sulphur": 5, "molybdenum": 0.2, "oil_cake": 50, "cowdung": 1, "ash": 0.5}


def fertilizer_rows(text: str, default: str = "ha?") -> list[dict]:
    """Every '<fertilizer> [(unit)] X-Y [unit]' in the text. The basis comes from the table heading when there is
    one (the first unit column of the heading; else hectares if the lead-in mentions them, else `default`)."""
    rows = []
    for m in FERT_RE.finditer(text):
        a, b = pair(m, 3)
        unit = m.group(5) or m.group(2) or ""  # "এমওপি (গ্রাম) 1-3": the unit sits in the bracket
        unit = "t" if N("টন") in unit else "g" if N("গ্রাম") in unit else "kg"
        ctx = text[max(0, m.start() - 350): m.start()]
        heads = list(TABLE_HEAD.finditer(ctx))
        heading = ctx[heads[0].start():] if heads else ""
        tail = re.match(r"\s*/?\s*[^\d\s]{0,12}", text[m.end():]).group(0)  # the unit right after the number
        # a heading with several unit columns ("কেজি/হেক্টর কেজি/বিঘা কেজি/শতক"): the first column is the first number
        found = [(mm.start(), k) for k, p in [("ha", HECTARE), *OTHER_BASES] for mm in [p.search(heading)] if mm]
        own = [k for k, p in [("ha", HECTARE), *OTHER_BASES] if p.search(m.group(0) + tail)]
        base = own[0] if own else min(found)[1] if found else "ha" if HECTARE.search(ctx) else default
        key = fert_key(m.group(1))
        if key == "cowdung" and unit == "kg" and a >= 500:  # "গোবর 10,000" kg/ha
            a, b, unit = a / 1000, b / 1000, "t"
        per_ha = base in ("ha", "ha?") and unit == ("t" if key in ("cowdung", "ash") else "kg") \
            and max(a, b) >= MIN_PER_HA.get(key, 0)
        rows.append({"fertilizer": key, "dose_min": a, "dose_max": b, "unit": unit, "basis": base,
                     "plausible_per_ha": per_ha, "snippet": re.sub(r"\s+", " ", m.group(0)).strip()})
    return rows


PER_HA = {"ha": 1, "ha?": 1, "decimal": 247.105, "bigha": 7.475, "acre": 2.471, "m2": 10000}


def seed_rate(text: str) -> tuple[float, float, str] | None:
    """(min, max) kg/ha: the first 'X-Y কেজি/টন' in a sentence that names its area (grams only per decimal or
    square metre, so a clove or seed weight is not read as a rate); a '(কেজি/হেক্টর)' table heading followed by
    figures gives its first figure."""
    for sent in re.split(N(r"[।\n]"), text):
        area = basis(sent)
        if area not in PER_HA or N("মাতৃ") in sent:  # mother bulbs/tubers for seed production are not a seed rate
            continue
        for m in re.finditer(N(RNG + r"\s*(কেজি|গ্রাম|টন)"), sent):
            if m.group(3) == N("গ্রাম") and area not in ("decimal", "m2"):
                continue
            a, b = pair(m)
            k = UNIT_KG[m.group(3)] * PER_HA[area]
            return round(a * k, 2), round(b * k, 2), sent.strip()[:200]
        head = re.search(N(r"\(কেজি\s*/\s*হেক্টর\)[^\d]{0,60}?" + RNG), sent)
        if head:
            a, b = pair(head)
            return a, b, sent.strip()[:200]
    return None


LEN_UNIT = N(r"(সেমি|সেন্টিমিটার|সে\.\s*মি\.?|মিটার|মি\.?)")


def _cm(v: str, unit: str | None) -> float:
    metres = unit is not None and N("সে") not in unit and re.match(N(r"মি"), unit) is not None
    return float(v) * (100 if metres else 1)


def spacing(text: str) -> tuple[float | None, float | None]:
    """(row, plant) spacing in cm: 'সারি থেকে সারির দূরত্ব X' / 'গাছ (চারা, কন্দ, কোয়া) থেকে ... দূরত্ব Y', else
    'X × Y সেমি'. A range gives its lower end."""
    row = re.search(N(r"সারি\s*(?:থেকে|হতে)\s*সারির?\s*দূরত্ব\s*(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*") + LEN_UNIT, text)
    plant = re.search(N(r"(?:গাছ|চারা|কন্দ|কোয়া|গুছি|বীজ)\s*(?:থেকে|হতে)\s*(?:গাছ|চারা|কন্দ|কোয়া|গুছি|বীজ)(?:ে?র)?\s*"
                        r"দূরত্ব\s*(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*") + LEN_UNIT, text)
    if row or plant:
        return (_cm(row.group(1), row.group(2)) if row else None, _cm(plant.group(1), plant.group(2)) if plant else None)
    m = re.search(N(r"(\d+(?:\.\d+)?)\s*(?:সেমি|সে\.?\s*মি\.?|মিটার|মি\.?)?\s*[x×X]\s*(\d+(?:\.\d+)?)\s*") + LEN_UNIT, text)
    return (_cm(m.group(1), m.group(3)), _cm(m.group(2), m.group(3))) if m else (None, None)


ORDINALS = [(1, r"প্রথম|1ম|১ম|একবার|এক বার|একটি"), (2, r"দ্বিতীয়|2য়|২য়|দুইবার|দুই বার|দু'বার|দুটি|দুইটি"),
            (3, r"তৃতীয়|3য়|৩য়|তিনবার|তিন বার|তিনটি"), (4, r"চতুর্থ|4র্থ|৪র্থ|চারবার|চার বার|চারটি"),
            (5, r"পঞ্চম|5ম|৫ম|পাঁচবার|পাঁচটি")]


def irrigation_count(text: str) -> tuple[int | None, int | None]:
    """How many irrigations the text asks for: an explicit 'X-Y বার/টি সেচ', else the highest ordinal."""
    m = re.search(N(RNG + r"\s*(?:টি|বার)\s*(?:হালকা\s*)?(?:সেচ|পানি)"), text) or \
        re.search(N(r"সেচ[^।]{0,40}?" + RNG + r"\s*(?:টি|বার)"), text)
    if m:
        a, b = pair(m)
        if a <= 15:
            return int(a), int(b)
    hi = max((n for n, p in ORDINALS if re.search(N(r"(?:" + p + r")[^।]{0,25}?সেচ|সেচ[^।]{0,10}?(?:" + p + r")"),
                                                  text)), default=None)
    return (hi, hi) if hi else (None, None)


def days_after(text: str) -> tuple[float, float] | None:
    """Days from sowing/planting to harvest: the first 'X-Y দিন' in a sentence not about flowering or about the
    interval between pickings ('20-25 দিন পর পর')."""
    for sent in re.split(N(r"[।\n]"), text):
        if re.search(N(r"ফুল আস|ফুল ফোট|ফুল ধর|ফল ধর|ফল আস|পর পর|পরপর|অন্তর"), sent):
            continue
        m = re.search(N(RNG + r"\s*দিন"), sent)
        if m:
            return pair(m)
    return None


def yield_t_ha(text: str) -> tuple[float, float] | None:
    for sent in re.split(N(r"[।\n]"), text):
        if N("ফলন") not in sent:
            continue
        m = re.search(N(RNG + r"\s*(টন|কেজি|মে\.?\s*টন)"), sent)
        if m and basis(sent) in ("ha", "ha?"):
            a, b = pair(m)
            k = 0.001 if m.group(3) == N("কেজি") else 1.0
            return round(a * k, 3), round(b * k, 3)
    return None


# ---------------------------------------------------------------- output
GROUP = dict(zip(CROP_CHAPTERS, ["tuber", "pulse", "oilseed", "vegetable", "fruit", "flower", "spice", "grain"]))
EN = {N(k): v for k, v in {
    "আলু": "potato", "মিষ্টি আলু": "sweet potato", "মেটেআলু": "yam", "কচু": "water taro (panikochu)",
    "সাহেবীকচু": "tannia (Xanthosoma)", "মুখীকচু": "taro (mukhikochu)", "ওলকচু": "elephant foot yam",
    "কাসাভা": "cassava", "খেসারী": "grass pea", "মসুর": "lentil", "ছোলা": "chickpea", "মাসকলাই": "black gram",
    "মুগ": "mung bean", "ফেলন": "cowpea", "মটর": "field pea", "অড়হর": "pigeon pea", "সরিষা": "mustard",
    "তিল": "sesame", "চীনাবাদাম": "groundnut", "সূর্যমুখী": "sunflower", "সয়াবিন": "soybean", "গর্জন তিল": "niger",
    "তিসি": "linseed", "টমেটো": "tomato", "বারি হাইব্রিড টমেটো-4 (গ্রীষ্মকালীন)": "summer hybrid tomato",
    "বেগুন": "brinjal", "বিটি বেগুন": "Bt brinjal", "মিষ্টিমরিচ": "sweet pepper", "মুলা": "radish",
    "শিম": "hyacinth bean", "ঝাড় শিম": "bush bean", "কামরাঙ্গা শিম": "winged bean", "বরবটি": "yardlong bean",
    "মটরশুঁটি": "garden pea", "লেটুস": "lettuce", "ডাঁটা": "stem amaranth", "ফুলকপি": "cauliflower",
    "বাঁধাকপি": "cabbage", "ব্রোকলি": "broccoli", "লালশাক": "red amaranth", "পালংশাক": "spinach",
    "পুঁইশাক": "Malabar spinach", "সবুজ ডাঁটা শাক": "green amaranth", "গীমাকলমি": "water spinach", "ঢেঁড়স": "okra",
    "কুমড়াজাতীয় সবজি": "cucurbits (general)", "লাউ": "bottle gourd", "চিচিঙ্গা": "snake gourd",
    "করলা": "bitter gourd", "চালকুমড়া": "ash gourd", "বারি পটল-2": "pointed gourd", "স্কোয়াশ": "squash",
    "ধুন্দুল": "sponge gourd", "হাইব্রিড ধুন্দুল": "hybrid sponge gourd", "ঝিঙ্গা": "ridge gourd",
    "সজিনা": "drumstick (moringa)", "হাইব্রিড শসা": "hybrid cucumber", "আম": "mango", "কাঁঠাল": "jackfruit",
    "কলা": "banana", "পেঁপে": "papaya", "আনারস": "pineapple", "পেয়ারা": "guava", "কুল": "jujube", "লিচু": "litchi",
    "নারিকেল": "coconut", "কমলা": "mandarin", "মাল্টা": "sweet orange (malta)", "জারা লেবু": "jara lemon",
    "কাগজীলেবু": "lime (kagzi)", "মিষ্টিলেবু": "sweet lime", "বাতাবিলেবু": "pomelo", "সাতকরা": "satkara (Citrus macroptera)",
    "আমড়া": "hog plum", "জামরুল": "wax apple", "সফেদা": "sapodilla", "কামরাঙ্গা": "carambola",
    "তৈকর": "tikoi (Garcinia)", "লটকন": "Burmese grape (latkan)", "আমলকি": "Indian gooseberry", "আঁশফল": "longan",
    "রাম্বুতান": "rambutan", "স্ট্রবেরি": "strawberry", "বিলাতি গাব": "velvet apple", "কদবেল": "wood apple",
    "বেল": "bael", "জলপাই": "Indian olive", "নাশপাতি": "pear", "প্যাশন ফল": "passion fruit", "তেঁতুল": "tamarind",
    "এ্যাভোকেডো": "avocado", "তরমুজ": "watermelon", "ফলসা": "phalsa", "আতা": "custard apple", "জাম": "black plum (jamun)",
    "পানি ফল": "water chestnut", "গ্লাডিওলাস": "gladiolus", "অর্কিড": "orchid", "চন্দ্রমল্লিকা": "chrysanthemum",
    "রজনীগন্ধা": "tuberose", "জারবেরা": "gerbera", "এ্যানথুরিয়াম": "anthurium", "ডালিয়া": "dahlia", "লিলি": "lily",
    "এলপিনিয়া": "alpinia", "গাঁদা": "marigold", "লিলিয়াম": "lilium", "জিপসোফিলা": "gypsophila", "ক্যাকটাস": "cactus",
    "বাগান বিলাস": "bougainvillea", "সাকুলেন্ট": "succulents", "শীতকালীন পেঁয়াজ": "onion, winter (rabi)",
    "গ্রীষ্ম/খরিফ পেঁয়াজ": "onion, summer (kharif)", "পাতা পেঁয়াজ": "leaf onion",
    "বাটিশাক ও চীনাশাক": "pak choi and Chinese cabbage",
    "নেগি অনিয়ন": "Welsh (bunching) onion", "মরিচ": "chilli", "অর্নামেন্টাল মরিচ": "ornamental chilli", "রসুন": "garlic",
    "আদা": "ginger", "হলুদ": "turmeric", "ধনিয়া": "coriander", "মেথী": "fenugreek", "কালোজিরা": "black cumin (nigella)",
    "জিরা": "cumin", "মৌরি": "fennel", "ফিরিঙ্গি": "firingi (spice)", "শলুক": "dill (shaluk)", "গোল মরিচ": "black pepper",
    "চুইঝাল": "chui jhal (Piper chaba)", "পান": "betel leaf", "দারুচিনি": "cinnamon", "তেজপাতা": "Indian bay leaf",
    "আলুবোখারা": "plum (alubokhara)", "একাঙ্গী": "aromatic ginger (Kaempferia)", "চিভ": "chives", "পুদিনা": "mint",
    "সুপারি": "areca nut", "বার্লি": "barley", "চিনা": "proso millet", "কাউন": "foxtail millet", "চিয়ার": "chia",
    "জোয়ার": "sorghum", "রাঘী": "finger millet", "ওট": "oat", "ঢেমশী": "buckwheat", "কিনোয়া": "quinoa"}.items()}
OUTLINED = {188: "broccoli", 217: "pointed gourd"}  # printed pages whose text was turned into outlines


def keytext(fields: list[dict], *keys: str, labels: bool = False) -> str:
    return " ".join((f["label"] + ": " if labels else "") + f["text"] for f in fields if f["key"] in keys)


def mid(lo: float | None, hi: float | None) -> float | None:
    return None if lo is None else round((lo + hi) / 2, 2)


def main() -> None:
    runs = page_runs(PDF)
    secs = crop_sections(toc(runs))
    rows, field_rows, fert_rows = [], [], []
    for s in secs:
        text = section_text(runs, s)
        fields = split_fields(text)
        crop_en = EN.get(s["crop_bn"])
        base = {"crop_group": GROUP[s["chapter"]], "crop_en": crop_en, "crop_bn": s["crop_bn"], "page": s["prod_page"]}
        for f in fields:
            field_rows.append({**base, "field": f["key"], "label_bn": f["label"], "text_bn": f["text"]})
        flat = re.sub(r"\s+", " ", text.replace(BOLD_OPEN, "").replace(BOLD_CLOSE, ""))
        sow_txt = keytext(fields, "sowing_time") or keytext(fields, "sowing_method")
        ws = windows(sow_txt)
        sr = seed_rate(keytext(fields, "seed_rate")) or seed_rate(keytext(fields, "sowing_method", "sowing_time"))
        row_cm, plant_cm = spacing(keytext(fields, "spacing", "sowing_method", "seed_rate", "sowing_time",
                                           "land_preparation"))
        if row_cm is None and plant_cm is None:
            row_cm, plant_cm = spacing(flat)
        default = "plant?" if base["crop_group"] == "fruit" else "ha?"  # fruit-tree doses go by tree age
        ferts = fertilizer_rows(keytext(fields, "fertilizer", "fertilizer_method", "land_preparation", "other",
                                        labels=True), default)
        if not ferts:
            ferts = fertilizer_rows(flat, default)
        for k, f in enumerate(ferts):
            fert_rows.append({**base, "occurrence": k, **f})
        first: dict[str, dict] = {}
        for f in ferts:
            if f["plausible_per_ha"]:
                first.setdefault(f["fertilizer"], f)
        irr_txt = keytext(fields, "irrigation") or " ".join(x for x in re.split(N("।"), flat) if N("সেচ") in x)
        irr = irrigation_count(irr_txt)
        hv_txt = keytext(fields, "harvest")
        hd = days_after(hv_txt) if hv_txt else None
        yd = yield_t_ha(keytext(fields, "yield", "harvest"))

        def dose(name: str, unit: str = "kg") -> float | None:
            f = first.get(name)
            return mid(f["dose_min"], f["dose_max"]) if f else None

        note = f"text outlined in the PDF (no text layer); read page {s['prod_page']}" if s["prod_page"] in OUTLINED else None
        rows.append({
            **base, "sowing_windows": fmt(ws),
            "sow_start": f"{ws[0][0][0]:02d}-{ws[0][0][1]:02d}" if ws else None,
            "sow_end": f"{ws[0][1][0]:02d}-{ws[0][1][1]:02d}" if ws else None,
            "seed_rate_kg_ha_min": sr[0] if sr else None, "seed_rate_kg_ha_max": sr[1] if sr else None,
            "row_spacing_cm": row_cm, "plant_spacing_cm": plant_cm,
            "urea_kg_ha": dose("urea"), "tsp_kg_ha": dose("tsp"), "mop_kg_ha": dose("mop"), "gypsum_kg_ha": dose("gypsum"),
            "zinc_sulphate_kg_ha": dose("zinc_sulphate"), "boron_kg_ha": dose("boron"), "cowdung_t_ha": dose("cowdung", "t"),
            "irrigations_min": irr[0], "irrigations_max": irr[1],
            "harvest_days_min": hd[0] if hd else None, "harvest_days_max": hd[1] if hd else None,
            "harvest_windows": fmt(windows(hv_txt)), "yield_t_ha_min": yd[0] if yd else None,
            "yield_t_ha_max": yd[1] if yd else None, "n_fields": len(fields),
            "sowing_time_bn": sow_txt[:700] or None, "seed_rate_bn": keytext(fields, "seed_rate")[:500] or None,
            "fertilizer_method_bn": keytext(fields, "fertilizer_method")[:700] or None,
            "irrigation_bn": keytext(fields, "irrigation")[:700] or None, "harvest_bn": hv_txt[:500] or None,
            "note": note, "source": CITE})
    wide, long, ferts = pd.DataFrame(rows), pd.DataFrame(field_rows), pd.DataFrame(fert_rows)
    CROPS.mkdir(parents=True, exist_ok=True)
    wide.to_csv(CROPS / "bari_production_technology.csv", index=False, encoding="utf-8-sig")
    long.to_csv(CROPS / "bari_production_fields.csv", index=False, encoding="utf-8-sig")
    ferts.to_csv(CROPS / "bari_fertilizer_doses.csv", index=False, encoding="utf-8-sig")
    print(f"{len(wide)} crop sections, {len(long)} fields, {len(ferts)} fertilizer rows")
    print("filled:", {c: int(wide[c].notna().sum()) for c in ["sow_start", "seed_rate_kg_ha_min", "row_spacing_cm",
                                                              "urea_kg_ha", "tsp_kg_ha", "mop_kg_ha", "irrigations_min",
                                                              "harvest_days_min", "yield_t_ha_min"]})


if __name__ == "__main__":
    main()
