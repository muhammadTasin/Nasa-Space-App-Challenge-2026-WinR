"""Does NASA's own productivity record agree with the replay? SMAP Level-4 carbon (SPL4CMDL: 9 km daily gross primary
production, GPP, April 2015 on) at the five pilots, season by season.

  Aman season GPP (15 Aug - 15 Nov) and Boro season GPP (1 Feb - 30 Apr), as % of each pilot's 2015-2025 mean
  checked against June-October rain (IMERG Final via POWER), the replay's dry days at Aman flowering at Tanore
  (connect_tanore_aman.csv, BRRI dhan49) and hot days at Boro flowering (heat_windows.csv)

SMAP L4 carbon is itself a model, driven by MODIS greenness, SMAP soil moisture and NASA GEOS weather. It shares
some inputs with the replay but not the IMERG rain or the BRRI calendars, so agreement is a consistency check, not
proof, and eleven seasons per pilot are few. Boro-season GPP also rises with how much land grows Boro. The same
product's soil organic carbon gives each pilot's soil-carbon level for the soil ledger.

Output: research/pilots/productivity_check.csv (pilot x season), research/pilots/soil_carbon.csv
Usage : python research/explore/productivity_check.py  (after connect_check.py and heat_windows.py)
"""
from __future__ import annotations

import pandas as pd
from scipy import stats

from signals_common import PILOTS, RESEARCH, power
from _common import DATA

GPP = "SPL4CMDL_008_GPP_gpp_mean"
SOC = "SPL4CMDL_008_SOC_soc_mean"


def main() -> None:
    c = pd.read_csv(next((DATA / "appeears" / "core").glob("*SPL4CMDL*results.csv")), usecols=["ID", "Date", GPP, SOC])
    c["Date"] = pd.to_datetime(c["Date"])
    heat = pd.read_csv(RESEARCH / "pilots" / "heat_windows.csv").set_index(["site_id", "season"])
    aman = pd.read_csv(RESEARCH / "pilots" / "connect_tanore_aman.csv")
    dry49 = aman[aman["variety"] == "BRRI dhan49"].set_index("season")["dry_days_at_flowering"]
    rows, soc = [], []
    for sid in PILOTS:
        g = c[c["ID"] == sid].set_index("Date")
        rain = power(sid)["IMERG_PRECTOT"]
        for y in range(2015, 2026):
            rows.append({"site_id": sid, "season": y,
                         "aman_gpp_g_m2": round(g.loc[f"{y}-08-15":f"{y}-11-15", GPP].sum(), 1),
                         "boro_gpp_g_m2": round(g.loc[f"{y}-02-01":f"{y}-04-30", GPP].sum(), 1) if y >= 2016 else None,
                         "rain_jun_oct_mm": round(rain.loc[f"{y}-06-01":f"{y}-10-31"].sum()),
                         "boro_days_ge35": heat.loc[(sid, y), "boro_days_ge35"],
                         "tanore_dhan49_dry_days": dry49.get(y) if sid == "RAJ_TANORE" else None})
        s = g[SOC].resample("YE").mean()
        ts = stats.theilslopes(s.values, s.index.year)
        soc.append({"site_id": sid, "soc_g_m2_2016_2025": round(s.loc["2016":"2025"].mean()),
                    "trend_g_m2_per_year": round(ts.slope, 1)})
    d = pd.DataFrame(rows)
    for col in ("aman_gpp_g_m2", "boro_gpp_g_m2", "rain_jun_oct_mm"):
        d[col.replace("_g_m2", "").replace("_mm", "") + "_pct"] = (
            100 * d[col] / d.groupby("site_id")[col].transform("mean")).round()
    out = RESEARCH / "pilots"
    d.to_csv(out / "productivity_check.csv", index=False)
    pd.DataFrame(soc).to_csv(out / "soil_carbon.csv", index=False)

    def rho(a, b, frame):
        f = frame[[a, b]].dropna()
        r = stats.spearmanr(f[a], f[b])
        return f"rho {r.statistic:+.2f} (p {r.pvalue:.2f}, n {len(f)})"

    t = d[d["site_id"] == "RAJ_TANORE"]
    print("Aman GPP vs June-October rain, all pilots:", rho("aman_gpp_pct", "rain_jun_oct_pct", d))
    print("Tanore Aman GPP vs replay dry days at dhan49 flowering:", rho("aman_gpp_pct", "tanore_dhan49_dry_days", t))
    print("Boro GPP vs hot days at Boro flowering, all pilots:", rho("boro_gpp_pct", "boro_days_ge35", d))
    for sid, g in d.groupby("site_id"):
        print(f"  {sid}: Aman GPP vs rain {rho('aman_gpp_pct', 'rain_jun_oct_pct', g)}; "
              f"Boro GPP vs heat {rho('boro_gpp_pct', 'boro_days_ge35', g)}")
    print(t[["season", "aman_gpp_pct", "rain_jun_oct_pct", "tanore_dhan49_dry_days", "boro_gpp_pct", "boro_days_ge35"]]
          .to_string(index=False))
    print(pd.DataFrame(soc).to_string(index=False))


if __name__ == "__main__":
    main()
