"""Shared helpers for the pre-event data research pulls: HTTP session, paths, site lists."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RESEARCH = Path(__file__).resolve().parents[1]  # research/
DATA = RESEARCH / "data"                        # gitignored cache
SITES = RESEARCH / "sites"


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET", "POST"))
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=8))
    s.headers["User-Agent"] = "WinR-FieldShift-research/0.1 (NASA Space Apps 2026)"
    return s


def load_sites(name: str) -> list[dict]:
    """Read research/sites/<name>.csv (columns: site_id, name, district, lat, lon, ...)."""
    with open(SITES / f"{name}.csv", newline="", encoding="utf-8") as f:
        return [{**r, "lat": float(r["lat"]), "lon": float(r["lon"])} for r in csv.DictReader(f)]


def out_dir(*parts: str) -> Path:
    p = DATA.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_provenance(path: Path, **fields) -> None:
    """Every cached file gets a sidecar saying where it came from and when."""
    fields.setdefault("retrieved_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    path.with_suffix(path.suffix + ".provenance.json").write_text(
        json.dumps(fields, indent=1, ensure_ascii=False), encoding="utf-8")


def load_dotenv(path: Path = RESEARCH.parent / ".env") -> None:
    """Minimal .env reader so the Earthdata scripts need no extra dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
