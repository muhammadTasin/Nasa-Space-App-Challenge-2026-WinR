"""DLS "Livestock Economy at a glance", 2015-16 to 2025-26 (Department of Livestock Services, dls.gov.bd).

One or two pages a year: livestock and poultry numbers, milk, meat and egg production against demand, per-capita
availability, the sector's GDP share. National figures only.

Output: research/data/dls/livestock_economy_<year>.pdf|doc (+ provenance)
Usage : python research/acquire/dls_livestock.py
"""
from __future__ import annotations

import html
import re

import requests

from _common import out_dir, session, write_provenance

PAGE = "https://dls.gov.bd/pages/static-pages/6922de4d933eb65569e19b16"


def main() -> None:
    s = session()
    s.verify = False  # the gov.bd certificate chain does not validate here
    requests.packages.urllib3.disable_warnings()
    raw = s.get(PAGE, timeout=60).text
    body = raw.split("rt-renderer", 1)[1].split("SocialContentShareWidget", 1)[0]
    d = out_dir("dls")
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, flags=re.S):
        label = html.unescape(re.sub(r"<.*?>", "", label)).strip()
        m = re.search(r"(20\d\d)\s*-\s*(?:20)?(\d\d)", label)
        if not m or "objectstorage" not in href:
            continue
        year = f"{m.group(1)}-{m.group(2)}"
        path = d / f"livestock_economy_{year}{href[href.rfind('.'):]}"
        if not path.exists():
            r = s.get(href, timeout=180)
            r.raise_for_status()
            path.write_bytes(r.content)
            write_provenance(path, source=f"DLS, {label}", url=href, page=PAGE)
        print(year, path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
