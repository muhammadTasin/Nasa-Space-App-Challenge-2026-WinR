"""SRDI's online fertilizer recommendation card (সার সুপারিশ কার্ড, http://frs-bd.com) for the pilot unions.

The service (SRDI with Katalyst) turns a union's soil test results, by soil type and land type, into doses for
a crop using the Fertilizer Recommendation Guide. This walks the form (division > district > upazila > union >
soil type > season > land type > crop group > crop) for the rotation crops and keeps every card. It only
searches: the farmer, village and mobile boxes stay empty and nothing is added. One request a second.

A land type whose first card is empty is skipped for that season. The doses are local (for the same crop, season
and land type, no two pilot unions get the same card), but the form returns cards for every land type it lists
crops for (the haor union gets high-land cards too), so it does not say which land types a union has: use
research/soil/landtype_proxy_*.csv for that.

Output: research/soil/srdi_frs_cards.csv (one row per fertilizer line: kg per acre as printed, kg per hectare)
        research/soil/srdi_frs_doses.csv  (one row per card: urea, TSP, MoP, gypsum, zinc, boron, lime in kg/ha)
        research/data/srdi_frs/<site_id>.json (raw cards)
Usage : python research/acquire/srdi_frs.py [--sites RAJ_TANORE ...] [--force]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import unicodedata
from datetime import date

import pandas as pd
import requests

from _common import RESEARCH, out_dir, write_provenance

URL = "http://frs-bd.com/"
P = "ctl00$ContentPlaceHolder1$"
ACRE_PER_HA = 2.4710538
# pilot -> the union the pilot point lies in, or the nearest one inside the upazila (Dharmapasha's point is
# 0.3 km over the Mohanganj border; Ullapara's is in the town, so its rural namesake union)
UNIONS = {
    "RAJ_TANORE": ("রাজশাহী", "রাজশাহী", "তানোর", "তালন্দ"),
    "SUN_DHARMAPASHA": ("সিলেট", "সুনামগঞ্জ", "ধর্মপাশা", "সেলবরষ"),
    "KHU_BATIAGHATA": ("খুলনা", "খুলনা", "বটিয়াঘাটা", "বটিয়াঘাটা"),
    "SIR_ULLAHPARA": ("রাজশাহী", "সিরাজগঞ্জ", "উল্লাপাড়া", "উল্লাপাড়া"),
    "RAN_MITHAPUKUR": ("রংপুর", "রংপুর", "মিঠাপুকুর", "দুর্গাপুর"),
}
SEASONS = {"1": "Kharif-1", "2": "Kharif-2", "3": "Rabi"}
# the rotation engine's crops and the other field crops of the pilot areas (matched inside the form's names)
CROPS = ["বোরো", "আমন", "আউশ", "গম", "ভুট্টা", "সরিষা", "আলু", "মসুর", "মুগ", "খেসারি", "পাট", "ধৈঞ্চা",
         "ছোলা", "তিল", "সূর্যমুখী", "পেঁয়াজ", "রসুন", "চীনাবাদাম", "মাসকলাই", "ঘাস"]
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def norm(s: str) -> str:
    """NFC, no spaces, and the spelling variants the form mixes (ূ/ু in ভুট্টা, ী/ি in খেসারি)."""
    s = unicodedata.normalize("NFC", s).replace(" ", "")
    return s.replace("ভূট্টা", "ভুট্টা").replace("খেসারী", "খেসারি")


def wanted(name: str) -> bool:
    n = norm(name)
    return any(norm(k) in n for k in CROPS) and "পাটশাক" not in n


class Form:
    """The page's form state; each change of a list posts the page back, as the browser does."""

    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 (research; NASA Space Apps 2026 team WinR)"
        self.t = self.s.get(URL, timeout=120).text
        self.sticky: dict = {}

    def fields(self) -> dict:
        f = {}
        for m in re.finditer(r"<input[^>]*>", self.t):
            name, typ = re.search(r'name="([^"]+)"', m.group(0)), re.search(r'type="([^"]+)"', m.group(0))
            if name and (typ is None or typ.group(1) in ("hidden", "text")):
                val = re.search(r'value="([^"]*)"', m.group(0))
                f[html.unescape(name.group(1))] = html.unescape(val.group(1)) if val else ""
        for sel in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', self.t, re.S):
            opts = re.findall(r'<option([^>]*)value="([^"]*)"', sel.group(2))
            if opts:  # an empty list posts nothing (a value would fail the page's event validation)
                chosen = [v for attrs, v in opts if "selected" in attrs]
                f[html.unescape(sel.group(1))] = html.unescape((chosen or [opts[0][1]])[0])
        return f

    def options(self, name: str) -> list[tuple[str, str]]:
        sel = re.search(r'<select[^>]*name="' + re.escape(P + name) + r'"[^>]*>(.*?)</select>', self.t, re.S)
        return [] if not sel else [
            (v, html.unescape(re.sub(r"<[^>]+>", "", x)).strip())
            for v, x in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', sel.group(1), re.S) if v]

    def pick(self, name: str, label: str) -> str:
        opts = self.options(name)
        hit = [v for v, x in opts if norm(x) == norm(label)] or [v for v, x in opts if norm(label) in norm(x)]
        if not hit:
            raise LookupError(f"{name}: {label!r} not in {[x for _, x in opts]}")
        return hit[0]

    def post(self, control: str, **values) -> None:
        f = self.fields()
        f.update({P + k: v for k, v in {**self.sticky, **values}.items()})
        f.update({"__EVENTTARGET": P + control, "__EVENTARGUMENT": "",
                  P + "txtFarmer": "", P + "txtVillage": "", P + "txtMobile": ""})
        for attempt in range(4):
            time.sleep(1.0)
            try:
                r = self.s.post(URL, data=f, timeout=120)
                r.raise_for_status()
                self.t = r.text
                return
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(15 * (attempt + 1))

    def card(self) -> list[dict]:
        """The result table: one dict per fertilizer line; `option` 2 marks the line after 'অথবা' (or)."""
        i = self.t.find("পুষ্টি উপাদান")
        if i < 0:
            return []
        table = self.t[self.t.rfind("<table", 0, i):self.t.find("</table>", i)]
        rows, alt = [], False
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) == 2 and "অথবা" in cells[1]:
                alt = True
                continue
            if len(cells) == 5 and cells[1]:
                rows.append({"line": cells[0].translate(BN_DIGITS) or None, "option": 2 if alt else 1,
                             "nutrient_bn": cells[1], "fertilizer_bn": cells[2], "amount_bn": cells[3],
                             "method_bn": cells[4]})
                alt = False
        return rows


def kg(amount: str) -> float | None:
    """'১২৩ কেজি ৪৩৭ গ্রাম' -> 123.437; 'প্রয়োজন নেই' (not needed) -> 0; 'প্রয়োজন মত' (as needed) -> None."""
    a = amount.translate(BN_DIGITS)
    if "নেই" in a:
        return 0.0
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*(টন|কেজি|গ্রাম)", a)
    if not parts:
        return None
    return round(sum(float(n) * {"টন": 1000.0, "কেজি": 1.0, "গ্রাম": 0.001}[u] for n, u in parts), 3)


def walk(site_id: str, log) -> list[dict]:
    division, district, upazila, union = UNIONS[site_id]
    f = Form()
    f.post("ddlDivision", ddlDivision=f.pick("ddlDivision", division))
    f.post("ddlDistrict", ddlDistrict=f.pick("ddlDistrict", district))
    f.post("ddlUpazila", ddlUpazila=f.pick("ddlUpazila", upazila))
    f.post("ddlUnion", ddlUnion=f.pick("ddlUnion", union))
    cards = []
    for phys, phys_bn in f.options("ddlSoilPhysiography"):
        f.sticky = {"ddlSoilPhysiography": phys}
        for season, season_en in SEASONS.items():
            f.post("ddlSeason", ddlSeason=season)
            for lt, lt_bn in f.options("ddlLandType"):
                f.post("ddlLandType", ddlLandType=lt)
                tried = 0
                for cat, cat_bn in f.options("ddlCropCategory"):
                    if any(norm(g) in norm(cat_bn) for g in ("ফল", "ফুল", "চিনি")):  # fruit, flowers, sugarcane
                        continue
                    f.post("ddlCropCategory", ddlCropCategory=cat)
                    for crop, crop_bn in [c for c in f.options("ddlCrop") if wanted(c[1])]:
                        f.post("ddlCrop", ddlCrop=crop)
                        f.post("btnSearch", txtDecimal="100")
                        rows = f.card()
                        tried += 1
                        cards.append({"site_id": site_id, "division": division, "district": district,
                                      "upazila": upazila, "union": union, "soil_type_bn": phys_bn,
                                      "season": season_en, "land_type_bn": lt_bn, "crop_group_bn": cat_bn,
                                      "crop_bn": crop_bn, "crop_code": crop, "lines": rows})
                        log(f"{site_id} {phys_bn} {season_en} {lt_bn} {crop_bn[:40]}: {len(rows)} lines")
                        if tried == 1 and not rows:  # no soil data for this land type
                            break
                    if tried == 1 and not cards[-1]["lines"]:
                        break
    return cards


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=list(UNIONS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    raw = out_dir("srdi_frs")
    log = lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)
    for site_id in args.sites:
        path = raw / f"{site_id}.json"
        if path.exists() and not args.force:
            continue
        try:
            cards = walk(site_id, log)
        except LookupError as e:  # a name spelled differently in the form: print the choices and go on
            log(f"{site_id}: {e}")
            continue
        path.write_text(json.dumps({"queried_on": str(date.today()), "url": URL, "cards": cards},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    lines, doses = [], []
    for path in sorted(raw.glob("*.json")):
        got = json.loads(path.read_text(encoding="utf-8"))
        for c in got["cards"]:
            if not c["lines"]:
                continue
            head = {k: v for k, v in c.items() if k != "lines"} | {"queried_on": got["queried_on"]}
            for r in c["lines"]:
                k = kg(r["amount_bn"])
                lines.append({**head, **r, "kg_per_acre": k,
                              "kg_per_ha": None if k is None else round(k * ACRE_PER_HA, 1)})
            first = {}
            for r in c["lines"]:  # the first option of each fertilizer (urea without DAP, TSP, zinc hepta ...)
                fert = norm(r["fertilizer_bn"].split("(")[0])  # the name; the brackets hold the condition
                for key, pat in [("urea", "ইউরিয়া"), ("tsp", "টিএসপি"), ("dap", "ডিএপি"), ("mop", "এমওপি"),
                                 ("gypsum", "জিপসাম"), ("zinc_sulphate", "জিংকসালফেট"), ("boric_acid", "বরিকএসিড"),
                                 ("lime", "চুন")]:
                    if norm(pat) in fert and key not in first:
                        k = kg(r["amount_bn"])
                        first[key] = None if k is None else round(k * ACRE_PER_HA, 1)
            first.setdefault("lime", 0.0)  # a card has a lime line only where the soil needs liming
            doses.append({**{k: c[k] for k in ("site_id", "union", "soil_type_bn", "season", "land_type_bn",
                                               "crop_bn")}, **{f"{k}_kg_ha": first.get(k) for k in
                                                               ("urea", "tsp", "dap", "mop", "gypsum",
                                                                "zinc_sulphate", "boric_acid", "lime")}})
    soil = RESEARCH / "soil"
    if lines:
        pd.DataFrame(lines).to_csv(soil / "srdi_frs_cards.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(doses).to_csv(soil / "srdi_frs_doses.csv", index=False, encoding="utf-8-sig")
        write_provenance(soil / "srdi_frs_cards.csv", source="SRDI fertilizer recommendation card service "
                         "(frs-bd.com, SRDI and Katalyst), searched for 100 decimals (1 acre)", url=URL,
                         note="kg_per_ha = printed kg per acre x 2.471; 'as needed' left empty")
        print(len(doses), "cards,", len(lines), "lines")


if __name__ == "__main__":
    main()
