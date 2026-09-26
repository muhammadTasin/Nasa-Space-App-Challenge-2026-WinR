"""FAO-56 crop coefficients (Table 12) and growth-stage lengths (Table 11).

Allen RG, Pereira LS, Raes D, Smith M (1998) Crop evapotranspiration - Guidelines for computing crop water
requirements. FAO Irrigation and Drainage Paper 56, Chapter 6. https://www.fao.org/4/x0490e/x0490e0b.htm

Output: research/crops/fao56_kc.csv, research/crops/fao56_stage_lengths.csv
  * footnote marks (<SUP>n</SUP>) are removed before parsing; '0.75<SUP>4</SUP>' was read as 0.754
  * Kc ini is printed once per crop group; crops without their own value inherit the group's
  * sub-rows such as 'Peas / - Dry' become 'Peas - Dry'
Stage lengths are from other climates (California, Mediterranean...): use their proportions, scaled to the
local variety duration (BRRI/BARI), not their day counts. Usage: python research/explore/fao56.py
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
URL = "https://www.fao.org/4/x0490e/x0490e0b.htm"
CACHE = REPO / "research" / "data" / "fao56_ch6.htm"
OUT = REPO / "research" / "crops"
CITE = "FAO-56 (Allen et al. 1998), Chapter 6, Tables 11-12"


def get_html() -> str:
    if not CACHE.exists():
        r = requests.get(URL, timeout=120, headers={"User-Agent": "Mozilla/5.0 (WinR research)"})
        r.raise_for_status()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(r.text, encoding="utf-8")
    html = CACHE.read_text(encoding="utf-8")
    return re.sub(r"(?i)<sup>\s*\d+\s*</sup>", "", html)  # footnote numbers only; keeps 1<sup>st</sup>


def rng(v) -> tuple[float | None, float | None]:
    """'1.0-1.15' -> (1.0, 1.15); '0.60-0.35' (end Kc for early vs late harvest) -> (0.35, 0.60)."""
    s = str(v).strip()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)] if s not in ("", "nan") else []
    if not nums:
        return None, None
    return min(nums), max(nums)


def names(df: pd.DataFrame) -> pd.DataFrame:
    """Column 0 = crop (repeated in col 1 by colspan); group header rows start with 'a.', 'b.' ...;
    sub-rows start with '- '."""
    out, group, parent = [], None, None
    for _, r in df.iterrows():
        a, b = str(r.iloc[0]).strip(), str(r.iloc[1]).strip()
        name = b if a in ("nan", "") else a
        if re.match(r"^[a-z]\.\s", name):
            group = re.sub(r"^[a-z]\.\s*", "", name)
            out.append(("group", group, None))
            continue
        if name.startswith("-") or (a in ("nan", "") and b.startswith("-")):
            out.append(("crop", group, f"{parent} {name}".strip()))
            continue
        parent = name
        out.append(("crop", group, name))
    df = df.copy()
    df["_kind"], df["group"], df["crop"] = zip(*out)
    return df


def kc_table(t12: pd.DataFrame) -> pd.DataFrame:
    t = names(t12.iloc[1:])
    t.columns = ["c0", "c1", "kc_ini_raw", "kc_mid_raw", "kc_end_raw", "height_raw", "_kind", "group", "crop"]
    group_kc = {}
    rows = []
    for _, r in t.iterrows():
        ini = rng(r.kc_ini_raw)[0]
        if r._kind == "group":
            group_kc[r.group] = ini
            continue
        mid_lo, mid_hi = rng(r.kc_mid_raw)
        end_lo, end_hi = rng(r.kc_end_raw)
        if mid_lo is None and end_lo is None:
            continue  # parent line of sub-rows ('Peas', 'Onions')
        rows.append({"crop": r.crop, "group": r.group, "kc_ini": ini if ini is not None else group_kc.get(r.group),
                     "kc_ini_from_group": ini is None, "kc_mid": mid_hi, "kc_mid_low": mid_lo,
                     "kc_end": end_hi, "kc_end_low": end_lo, "max_height_m": rng(r.height_raw)[1],
                     "kc_mid_printed": str(r.kc_mid_raw), "kc_end_printed": str(r.kc_end_raw)})
    df = pd.DataFrame(rows)
    df["source"] = CITE
    return df


def stage_table(t11: pd.DataFrame) -> pd.DataFrame:
    t = names(t11.iloc[1:])
    t.columns = ["c0", "c1", "l_ini", "l_dev", "l_mid", "l_late", "total", "plant_date", "region", "_kind", "group",
                 "crop"]
    rows = []
    for _, r in t[t._kind == "crop"].iterrows():
        vals = [rng(r[c])[0] for c in ("l_ini", "l_dev", "l_mid", "l_late")]
        if None in vals:
            continue
        tot = sum(vals)
        rows.append({"crop": r.crop, "group": r.group, "l_ini": vals[0], "l_dev": vals[1], "l_mid": vals[2],
                     "l_late": vals[3], "total_days": tot, "plant_date": r.plant_date, "region": r.region,
                     **{f"frac_{k}": round(v / tot, 3) for k, v in zip(("ini", "dev", "mid", "late"), vals)}})
    df = pd.DataFrame(rows)
    df["source"] = CITE
    return df


def main() -> None:
    html = get_html()
    tabs = pd.read_html(io.StringIO(html))
    t11 = next(t for t in tabs if t.shape[1] == 9 and "Init" in t.astype(str).to_string()[:2000])
    t12 = next(t for t in tabs if t.shape[1] == 6 and "Kc mid" in t.astype(str).to_string()[:2000])
    kc, st = kc_table(t12), stage_table(t11)
    OUT.mkdir(parents=True, exist_ok=True)
    kc.to_csv(OUT / "fao56_kc.csv", index=False)
    st.to_csv(OUT / "fao56_stage_lengths.csv", index=False)
    print(f"Kc rows: {len(kc)} | stage-length rows: {len(st)}")


if __name__ == "__main__":
    main()
