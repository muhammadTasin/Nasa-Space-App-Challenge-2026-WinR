"""Monthly market prices in the pilot districts, from WFP's Bangladesh food price dataset on HDX (CC BY-IGO).

DAM's own report pages (market.dam.gov.bd: daily market report, commodity report) returned empty tables for
every market and date tried, 2020-2026, including Dhaka's Kawran Bazar from a browser (checked 27 Sep 2026).
WFP republishes DAM's market prices (with FAO GIEWS and its own collection) as one monthly file, updated
monthly: district markets from 2020, the division series before that. Mostly retail prices of what households
buy (coarse rice, lentils, flour, oil, potato, onion), so a food-cost and price-trend input, not farm-gate prices
(those are in research/bbs/harvest_prices.csv and monthly_prices.csv).

Output: research/pilots/wfp_market_prices.csv (pilot districts and Dhaka), raw file in research/data/wfp/
Usage : python research/acquire/wfp_prices.py
"""
from __future__ import annotations

import pandas as pd

from _common import RESEARCH, out_dir, session, write_provenance

PACKAGE = "https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-bangladesh"
DISTRICTS = ["Rajshahi", "Sunamganj", "Khulna", "Sirajganj", "Rangpur", "Dhaka"]  # pilots, and Dhaka for reference


def main() -> None:
    s = session()
    pkg = s.get(PACKAGE, timeout=60).json()["result"]
    res = next(r for r in pkg["resources"] if r["name"].endswith("Food Prices"))
    raw = out_dir("wfp") / "wfp_food_prices_bgd.csv"
    raw.write_bytes(s.get(res["url"], timeout=300).content)
    write_provenance(raw, source=f"WFP via HDX: {pkg['title']} ({pkg.get('dataset_source')})", url=res["url"],
                     license=pkg.get("license_title"), updated=res.get("last_modified"))
    d = pd.read_csv(raw, skiprows=[1], low_memory=False)  # row 2 holds HXL tags
    d = d[d["admin2"].isin(DISTRICTS)].drop(columns=["currency", "usdprice"])
    d = d.sort_values(["admin2", "market", "commodity", "pricetype", "date"])
    out = RESEARCH / "pilots" / "wfp_market_prices.csv"
    d.to_csv(out, index=False)
    write_provenance(out, source="WFP Bangladesh food prices (HDX), rows for the pilot districts and Dhaka",
                     url=res["url"], license=pkg.get("license_title"), rows=len(d))
    print(len(d), "rows ->", out.relative_to(RESEARCH.parent))
    print(d.groupby(["admin2", "market"])["date"].agg(["min", "max", "size"]).to_string())


if __name__ == "__main__":
    main()
