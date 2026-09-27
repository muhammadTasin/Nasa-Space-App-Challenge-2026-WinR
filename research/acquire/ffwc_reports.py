"""FFWC (Bangladesh Water Development Board) annual flood reports and station list, from the public old website.

FFWC's data API (api.ffwc.gov.bd) refuses requests without its site security header, so it is not used. The
old website (old.ffwc.gov.bd) publishes the Annual Flood Report for each year 2008-2021 as a PDF with a text
layer: for every water-level station the danger level, the year's peak and its date, and the days above danger
level, plus chapters on the year's flash floods. Its home page lists every station with its id and danger level.
The new site (ffwc.gov.bd/app) shows the last 40 days of readings and monthly average and maximum levels for
2003-2026 by station; those are read in a browser, not downloaded here.

Output: research/data/ffwc/annualYY.pdf, research/data/ffwc/stations_old_site.csv
Usage : python research/acquire/ffwc_reports.py
"""
from __future__ import annotations

import html
import re

import pandas as pd

from _common import out_dir, session, write_provenance

OLD = "http://old.ffwc.gov.bd"
REPORTS = f"{OLD}/index.php/reports/annual-flood-reports"


def main() -> None:
    s = session()
    d = out_dir("ffwc")
    page = s.get(REPORTS, timeout=120).text
    links = sorted(set(re.findall(r'href="(/images/annual(\d\d)\.pdf)"', page)), key=lambda x: x[1])
    for href, yy in links:
        path = d / f"annual{yy}.pdf"
        if not path.exists():
            with s.get(OLD + href, stream=True, timeout=600) as r:
                if r.status_code == 404:  # the page links some years that are not on the server
                    print(path.name, "listed but not on the server")
                    continue
                r.raise_for_status()
                with open(path, "wb") as fh:
                    for block in r.iter_content(1 << 20):
                        fh.write(block)
            write_provenance(path, source=f"FFWC/BWDB Annual Flood Report 20{yy}", url=OLD + href)
        print(path.name, f"{path.stat().st_size / 1e6:.1f} MB", flush=True)
    # station list with danger levels (the home page's station links)
    home = s.get(f"{OLD}/", timeout=120).text
    rows = []
    for stid, text in re.findall(r'href="http://old\.ffwc\.gov\.bd/ffwc_charts/index\.php\?stid=(\d+)"[^>]*>(.*?)</a>', home, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", " ", text))
        m = re.search(r"^\s*(.+?)\s*Water Level\s*:\s*([\d.]+)\s*Danger Level\s*:\s*([\d.]+)", t)
        if m:
            rows.append({"stid": int(stid), "station": m.group(1).strip(), "danger_level_m": float(m.group(3))})
    st = pd.DataFrame(rows).drop_duplicates("stid").sort_values("stid")
    path = d / "stations_old_site.csv"
    st.to_csv(path, index=False)
    write_provenance(path, source="FFWC old website station list (id and danger level)", url=f"{OLD}/",
                     note="danger levels as listed on the site today; the annual reports give each year's")
    print(len(st), "stations ->", path.name)


if __name__ == "__main__":
    main()
