"""BRRI rice-variety factsheets (Bangladesh Rice Knowledge Bank) -> PDFs + extracted text.

Collects every factsheet PDF linked from the variety pages, tags each with the season page(s)
that list it (Boro / Aman / Aus), downloads it, and stores the extracted text next to it.
Parsing the text into a variety table is done by explore/brri_varieties.py.

Usage: python research/acquire/brri_factsheets.py
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
from urllib.parse import unquote, urljoin

import pdfplumber

from _common import out_dir, session, write_provenance

PAGES = {"all": "https://knowledgebank-brri.org/brri-rice-varieties/",
         "Boro": "https://knowledgebank-brri.org/brri-rice-varieties/boro-rice-varieties/",
         "Aman": "https://knowledgebank-brri.org/brri-rice-varieties/aman-rice-varieties/",
         "Aus": "https://knowledgebank-brri.org/brri-rice-varieties/aus-rice-varieties/"}
S = session()
S.headers["User-Agent"] = "Mozilla/5.0 (WinR research; NASA Space Apps)"


def links() -> dict[str, list[str]]:
    found: dict[str, set[str]] = {}
    for season, url in PAGES.items():
        html = S.get(url, timeout=60).text
        for h in re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.I):
            u = urljoin(url, h).replace("http://", "https://")
            found.setdefault(u, set())
            if season != "all":
                found[u].add(season)
    return {u: sorted(s) for u, s in found.items()}


def fetch(item: tuple[str, list[str]]) -> dict:
    url, seasons = item
    d = out_dir("brri", "pdf")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(url.split("/")[-1]))
    # a few file names repeat across folders; keep them apart
    folder = re.sub(r"[^A-Za-z0-9]+", "_", url.split("knowledgebank-brri.org/")[-1].rsplit("/", 1)[0])[-40:]
    path = d / f"{folder}__{name}"
    rec = {"url": url, "seasons": seasons, "file": path.name}
    if not path.exists():
        r = S.get(url, timeout=180)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return {**rec, "error": f"HTTP {r.status_code}"}
        path.write_bytes(r.content)
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            rec["pages"] = len(pdf.pages)
    except Exception as e:
        return {**rec, "error": f"unreadable: {type(e).__name__}"}
    path.with_suffix(".txt").write_text(text, encoding="utf-8")
    rec["chars"] = len(text)
    return rec


def main() -> None:
    items = links()
    with cf.ThreadPoolExecutor(3) as ex:
        recs = list(ex.map(fetch, items.items()))
    d = out_dir("brri")
    (d / "index.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
    write_provenance(d / "index.json", source="BRRI Bangladesh Rice Knowledge Bank", url=PAGES["all"],
                     files=len([r for r in recs if "error" not in r]))
    bad = [r for r in recs if "error" in r]
    empty = [r for r in recs if r.get("chars", 1) < 50]
    print(f"{len(recs) - len(bad)} PDFs saved, {len(bad)} failed, {len(empty)} with no extractable text")
    for r in bad:
        print("  failed:", r["file"], r["error"])


if __name__ == "__main__":
    main()
