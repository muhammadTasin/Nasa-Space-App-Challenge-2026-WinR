"""BRRI's regional cropping-system papers (Bangladesh Rice Journal 21(2), 2017, open access on BanglaJOL).

The national paper (Nasim et al.) lists patterns for the whole country; these 14 regional companions give
the patterns district by district and upazila by upazila. Downloads the PDFs to research/data/brri/regional/
and caches their text. Usage: python research/acquire/brri_regional_papers.py
"""
from __future__ import annotations

import json
import re

import pypdfium2 as pdfium

from _common import out_dir, session, write_provenance

ISSUE = "https://www.banglajol.info/index.php/BRJ/issue/view/2135"
S = session()
S.headers["User-Agent"] = "Mozilla/5.0 (WinR research; NASA Space Apps)"


def main() -> None:
    d = out_dir("brri", "regional")
    html = S.get(ISSUE, timeout=60).text
    arts = {}
    for aid, title in re.findall(r'href="https://www\.banglajol\.info/index\.php/BRJ/article/view/(\d+)"[^>]*>\s*'
                                 r'([^<]{5,200}?)\s*</a>', html):
        arts.setdefault(aid, re.sub(r"\s+", " ", title).strip())
    index = []
    for aid, title in arts.items():
        page = S.get(f"https://www.banglajol.info/index.php/BRJ/article/view/{aid}", timeout=60).text
        gal = re.search(rf"/BRJ/article/view/{aid}/(\d+)", page)
        doi = re.search(r"https?://doi\.org/(10\.\d+/[^\s\"<]+)", page)
        if not gal:
            print("no PDF link:", aid, title)
            continue
        url = f"https://www.banglajol.info/index.php/BRJ/article/download/{aid}/{gal.group(1)}"
        slug = re.sub(r"[^A-Za-z0-9]+", "_", title)[:60].strip("_")
        path = d / f"{aid}_{slug}.pdf"
        if not path.exists():
            r = S.get(url, timeout=180)
            if not r.content.startswith(b"%PDF"):
                print("not a PDF:", aid, r.status_code)
                continue
            path.write_bytes(r.content)
        pdf = pdfium.PdfDocument(str(path))
        text = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
        path.with_suffix(".json").write_text(json.dumps(text, ensure_ascii=False), encoding="utf-8")
        index.append({"article": aid, "title": title, "pdf": path.name, "pages": len(text), "url": url,
                      "doi": doi.group(1) if doi else None})
        print(f"{aid} {len(text):3d} pages  {title}")
    (d / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    write_provenance(d / "index.json", source="Bangladesh Rice Journal 21(2), 2017 (BanglaJOL)", url=ISSUE,
                     papers=len(index))


if __name__ == "__main__":
    main()
