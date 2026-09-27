"""NASA GIBS WMS snapshots of Bangladesh (no login) - for slides, the video, and the offline demo.

Each image is a stack: shaded-relief basemap + one NASA science layer + coastlines/borders.
Usage: python research/acquire/gibs_snapshots.py
"""
from __future__ import annotations

from _common import out_dir, session, write_provenance

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
BBOX = (20.4, 87.9, 26.8, 92.8)  # WMS 1.3.0 + EPSG:4326 -> lat_min, lon_min, lat_max, lon_max
SHOTS = [  # (file stem, science layer, date, caption)
    ("ndvi_viirs_noaa20_2026-02", "VIIRS_NOAA20_NDVI_8Day", "2026-02-18", "Boro season greenness, VIIRS NOAA-20 NDVI"),
    ("ndvi_viirs_noaa20_2025-10", "VIIRS_NOAA20_NDVI_8Day", "2025-10-16", "Aman season greenness, VIIRS NOAA-20 NDVI"),
    ("smap_l4_rootzone_2026-04", "SMAP_L4_Analyzed_Root_Zone_Soil_Moisture", "2026-04-15", "Pre-monsoon root-zone soil moisture, SMAP L4"),
    ("smap_l4_rootzone_2025-08", "SMAP_L4_Analyzed_Root_Zone_Soil_Moisture", "2025-08-15", "Monsoon root-zone soil moisture, SMAP L4"),
    ("imerg_2024-08-21", "IMERG_Precipitation_Rate", "2024-08-21", "IMERG rain rate during the Aug 2024 eastern floods"),
    # VIIRS flood layer only starts Jun 2025 in GIBS; MODIS flood covers 2023-07 onward
    ("flood_modis_2024-08-25", "MODIS_Combined_Flood_3-Day", "2024-08-25", "MODIS 3-day flood map, Aug 2024 eastern floods"),
]
# GIBS layers have date gaps: check <Dimension> values in WMTSCapabilities.xml before picking a date.
# A gap returns the basemap alone with HTTP 200, so eyeball every image.


def main() -> None:
    s = session()
    d = out_dir("gibs")
    w, h = 620, 800
    for stem, layer, day, caption in SHOTS:
        params = {"SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.3.0", "CRS": "EPSG:4326",
                  "LAYERS": f"BlueMarble_ShadedRelief,{layer},Coastlines_15m,Reference_Features_15m",
                  "STYLES": "", "BBOX": ",".join(map(str, BBOX)), "WIDTH": w, "HEIGHT": h,
                  "FORMAT": "image/png", "TIME": day, "TRANSPARENT": "FALSE"}
        r = s.get(WMS, params=params, timeout=180)
        ok = r.ok and r.headers.get("Content-Type", "").startswith("image/")
        path = d / f"{stem}.png"
        if ok:
            path.write_bytes(r.content)
            write_provenance(path, source="NASA GIBS WMS", url=r.url, layer=layer, date=day, caption=caption)
        print("ok " if ok else "ERR", stem, r.status_code, r.headers.get("Content-Type"), len(r.content), flush=True)


if __name__ == "__main__":
    main()
