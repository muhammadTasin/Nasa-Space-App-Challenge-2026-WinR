"""Download all editions of the BBS Yearbook of Agricultural Statistics (2012-2025) listed on
https://bbs.gov.bd/pages/static-pages/6922e0d6933eb65569e28cbf (links read 26 Sep 2026).
Stacked, the editions give a district-level area/yield/production series for ~2010-2025.
Usage: python research/acquire/bbs_yearbooks.py
"""
from __future__ import annotations

from _common import out_dir, session, write_provenance

BASE = "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-bbs/"
EDITIONS = {
    2025: "2026/5/cfb80ec8-1c7f-4632-8a59-7649b6ac7ffe.pdf",
    2024: "2024/12/58f325576f9a47cc91e7d227e336e40f.pdf",
    2023: "2024/12/d09f33a6167a46fd980e5797749de63d.pdf",
    2022: "2024/12/85216bc379fa443e837ffac3052a45dc.pdf",
    2021: "https://bbs.gov.bd/pages/files/6a7420f8112d0b7ffdd4f987",
    2020: "2024/12/4b0a4874dbbf461eb7aebb0a64348c1f.pdf",
    2019: "2024/12/2dd420c42e2544ea8b556b683d73fab3.pdf",
    2018: "2024/12/14091496465c4fc49d5adc56c459f057.pdf",
    2017: "2024/12/44df01e1fa7e442496cdc35cc9dae0ab.pdf",
    2016: "2024/12/2392443cc06247a0a01094c57cc0b46f.pdf",
    2015: "2024/12/f393ed9d22e94303ae27f41ff5ef05ad.pdf",
    2014: "2024/12/1aa452d6da76465cb14f36ab494c48a1.pdf",
    2013: "2024/12/ec3f36dfee9c4adf99cc82f248da2a4a.pdf",
    2012: "2024/12/11a0d621571a41bf85f5dbf66b2cff6f.pdf",
}
S = session()
S.headers["User-Agent"] = "Mozilla/5.0 (WinR research; NASA Space Apps)"


def main() -> None:
    d = out_dir("bbs")
    for year, path in EDITIONS.items():
        url = path if path.startswith("http") else BASE + path
        f = d / ("BBS_Yearbook_Agricultural_Statistics_2025.pdf" if year == 2025
                 else f"BBS_Yearbook_Agricultural_Statistics_{year}.pdf")
        if f.exists():
            print(f"{year}: cached ({f.stat().st_size / 1e6:.1f} MB)")
            continue
        try:
            r = S.get(url, timeout=600, verify=not url.startswith("https://bbs.gov.bd"))
        except Exception as e:  # bbs.gov.bd has certificate problems
            print(f"{year}: failed {type(e).__name__}")
            continue
        if not r.content.startswith(b"%PDF"):
            print(f"{year}: not a PDF (HTTP {r.status_code}, {r.headers.get('Content-Type')})")
            continue
        f.write_bytes(r.content)
        write_provenance(f, source=f"BBS Yearbook of Agricultural Statistics {year}", url=url)
        print(f"{year}: saved {len(r.content) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
