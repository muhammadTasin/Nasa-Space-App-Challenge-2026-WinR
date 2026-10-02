"""Shared pieces for the NASA signal analyses: the pilots, each pilot's nearest long-record BMD station, NASA POWER
temperatures corrected against that station, and crop dates from the BRRI factsheets."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH, load_sites  # noqa: E402
from connect_check import mid, window  # noqa: E402

PILOTS = [s["site_id"] for s in load_sites("pilot_sites")]
# nearest BMD station with years of daily records (NOAA GSOD file) and its distance from the pilot point, km
NEAREST_BMD = {"RAJ_TANORE": ("41895_ShahMokhdum", 21), "SUN_DHARMAPASHA": ("41886_Mymensingh", 60),
               "KHU_BATIAGHATA": ("41947_Khulna", 7), "SIR_ULLAHPARA": ("41907_Ishurdi", 56),
               "RAN_MITHAPUKUR": ("41859_Rangpur", 21)}
BRRI = pd.read_csv(RESEARCH / "crops" / "brri_rice_varieties.csv").drop_duplicates("variety").set_index("variety")


def power(site_id: str) -> pd.DataFrame:
    p = pd.read_parquet(DATA / "power" / "daily" / f"{site_id}.parquet")
    p.index = pd.to_datetime(p.index)
    return p


def corrected_power(site_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """NASA POWER daily with tmax/tmin shifted by their mean monthly difference from the nearest BMD station, and
    rain from IMERG (the gauge-adjusted Final run for past years). Returns the frame and the monthly bias table."""
    p = power(site_id)
    g = pd.read_parquet(DATA / "stations" / "gsod" / f"{NEAREST_BMD[site_id][0]}.parquet")
    g.index = pd.to_datetime(g.index)
    both = p.join(g[["tmax_c", "tmin_c"]], how="inner")
    bias = both.groupby(both.index.month).apply(lambda d: pd.Series({
        "tmax": (d["T2M_MAX"] - d["tmax_c"]).mean(), "tmin": (d["T2M_MIN"] - d["tmin_c"]).mean(), "days": len(d)}))
    p["tmax"] = p["T2M_MAX"] - p.index.month.map(bias["tmax"]).to_numpy()
    p["tmin"] = p["T2M_MIN"] - p.index.month.map(bias["tmin"]).to_numpy()
    p["rain"] = p["IMERG_PRECTOT"]
    return p, bias


def brri_dates(variety: str, year: int, shift_days: int = 0) -> dict:
    """Seedbed sowing (window midpoint), transplanting, flowering (30 days before maturity) and maturity for a BRRI
    variety whose seedbed window opens in `year`; `shift_days` moves sowing earlier (negative) or later."""
    r = BRRI.loc[variety]
    s0, s1 = window(r["seedbed_sowing"], year)
    sown = s0 + (s1 - s0) / 2 + pd.Timedelta(days=shift_days)
    mature = sown + pd.Timedelta(days=round(mid(r["duration_days_min"], r["duration_days_max"])))
    return {"sown": sown, "transplant": sown + pd.Timedelta(days=round(mid(r["seedling_age_days"]))),
            "flowering": mature - pd.Timedelta(days=30), "maturity": mature}


def around(p: pd.DataFrame, centre: pd.Timestamp, half: int = 7) -> pd.DataFrame:
    return p.loc[centre - pd.Timedelta(days=half):centre + pd.Timedelta(days=half)]
