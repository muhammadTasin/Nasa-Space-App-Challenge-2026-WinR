"""Rebuild the research tables from the cached data, in dependency order, and report what each step wrote.

  signals   (default) the NASA signal analyses behind the rotation scores, a few minutes
  documents the tables read from PDFs and web pages (BRRI, BARI, BWMRI, BBS, SRDI, FFWC ...), slower
  all       documents, then signals

The acquire/ scripts that fill research/data/ are not run here: several need an Earthdata Login and some take
hours; research/README.md lists them.

Usage : python research/run_analyses.py [signals|documents|all]
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

EXPLORE = Path(__file__).resolve().parent / "explore"
DOCUMENTS = ["fao56.py", "fao_ky.py", "brri_varieties.py", "bari_varieties.py", "bari_production.py",
             "bwmri_varieties.py", "bbs_yearbook.py", "bbs_panel.py", "cropping_patterns.py", "regional_patterns.py",
             "dls_livestock.py", "srdi_soil_maps.py", "ffwc_floods.py", "crop_parameters.py", "pilot_cards.py",
             "first_look.py"]
SIGNALS = ["rain_vs_normal.py", "connect_check.py", "heat_windows.py", "flash_flood_hindcast.py", "field_cycles.py",
           "cattle_heat.py", "productivity_check.py", "groundwater.py", "soil_moisture.py", "environment_ledger.py"]


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "signals"
    steps = {"signals": SIGNALS, "documents": DOCUMENTS, "all": DOCUMENTS + SIGNALS}[which]
    failed = []
    for script in steps:
        t0 = time.time()
        r = subprocess.run([sys.executable, str(EXPLORE / script)], cwd=EXPLORE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        ok = r.returncode == 0
        print(f"{'ok  ' if ok else 'FAIL'} {script:28s} {time.time() - t0:6.1f} s", flush=True)
        if not ok:
            failed.append(script)
            print("\n".join(r.stderr.strip().splitlines()[-6:]))
    print(f"\n{len(steps) - len(failed)} of {len(steps)} steps ran" + (f"; failed: {', '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
