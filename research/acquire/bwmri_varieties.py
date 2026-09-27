"""Wheat and maize variety booklets from BWMRI (Bangladesh Wheat and Maize Research Institute), bwmri.gov.bd.

Wheat and maize varieties moved from BARI to BWMRI, so the BARI handbook no longer describes them. The site has
one page per variety (menu "উদ্ভাবিত জাতসমূহ"), each linking a PDF booklet and/or a leaflet image, and a
"maize varieties at a glance" page with release years and special traits.

Output: research/data/bwmri/<variety>/*.pdf|jpg (+ index.json), research/data/bwmri/maize_at_a_glance.html
Usage : python research/acquire/bwmri_varieties.py
"""
from __future__ import annotations

import base64
import html
import json
import re

import requests

from _common import out_dir, session, write_provenance

BASE = "https://bwmri.gov.bd"
STORE = r"https://objectstorage\.ap-dcc-gazipur-1\.oraclecloud15\.com/n/axvjbnqprylg/b/V2Ministry/o/office-bwmri/[^\s\"'<>]+"


def main() -> None:
    s = session()
    s.verify = False  # the gov.bd certificate chain does not validate here
    requests.packages.urllib3.disable_warnings()
    home = s.get(BASE + "/", timeout=60).text
    pages = {}
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', home, flags=re.S):
        label = html.unescape(re.sub(r"<.*?>", "", label)).strip()
        if re.search(r"(গম|ভুট্টা)\s*[০-৯]+$", label) or label in ("এক নজরে ভুট্টার জাতসমূহ", "খৈ ভুট্টা"):
            pages[label] = href if href.startswith("http") else BASE + href
    d = out_dir("bwmri")
    index = []
    for label, url in pages.items():
        raw = s.get(url, timeout=60).text
        body = raw.split("rt-renderer", 1)[1] if "rt-renderer" in raw else ""  # skip the site header's logos
        body = body.split("SocialContentShareWidget", 1)[0]
        # the page text itself is base64-encoded HTML in an `encoded-content` attribute (Unicode Bangla)
        enc = re.search(r'encoded-content="([^"]+)"', body)  # itself HTML-escaped (&#43; for +)
        content = base64.b64decode(html.unescape(enc.group(1))).decode("utf-8", "replace") if enc else ""
        content = re.sub(r'src="data:[^"]+"', 'src=""', content)  # drop inline images
        files = sorted(set(u.strip() for u in re.findall(STORE, body)))
        sub = out_dir("bwmri", re.sub(r"\s+", "_", label))
        (sub / "page_text.txt").write_text(
            re.sub(r"\n\s*\n+", "\n", html.unescape(re.sub(r"<(?:br|/p|/tr|/li|/h\d)[^>]*>", "\n", content))
                   .replace("\xa0", " ")).replace("\r", ""), encoding="utf-8")
        (sub / "page_text.txt").write_text(re.sub(r"<[^>]+>", " ", (sub / "page_text.txt").read_text(encoding="utf-8")),
                                           encoding="utf-8")
        saved = []
        for f in files:
            path = sub / f.rsplit("/", 1)[1]
            if not path.exists():
                r = s.get(f, timeout=180)
                r.raise_for_status()
                path.write_bytes(r.content)
            saved.append(path.name)
        if label == "এক নজরে ভুট্টার জাতসমূহ":
            (d / "maize_at_a_glance.html").write_text(raw, encoding="utf-8")
        index.append({"variety": label, "page": url, "files": saved})
        print(f"{label:40s} {len(saved)} files")
    (d / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    write_provenance(d / "index.json", source="BWMRI variety pages, bwmri.gov.bd", url=BASE, pages=len(index))


if __name__ == "__main__":
    main()
