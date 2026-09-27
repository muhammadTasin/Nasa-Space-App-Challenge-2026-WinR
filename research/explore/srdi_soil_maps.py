"""Soil fertility classes for every upazila and pilot site, read from SRDI's Soil Fertility Atlas 2020 maps.

The atlas (SRDI 2020; built from the Upazila Nirdeshika soil data) prints 12 national maps as images: soil pH,
organic matter, P, K and S (each for upland crops and for wetland rice), Zn, B, Ca and Mg, in fertility
classes (Very Low ... Very High; pH from Very Strongly Acidic to Very Strongly Alkaline). This script
  1. georeferences the map frame (all 12 maps share it): the maps are in BUTM (Bangladesh Transverse
     Mercator), so a scale and offset per axis, fitted by maximising the overlap between the map's coloured land
     and the geoBoundaries outline of Bangladesh;
  2. reads each map's legend swatches and classifies every pixel to the nearest legend colour;
  3. takes the majority class inside each upazila polygon (and in a 5 x 5 pixel window at each pilot site).
A map pixel is about 0.8 km, and the maps are generalised, so these are upazila-scale classes, not field tests.

Input : research/data/soil/SRDI_Soil_Fertility_Atlas_Bangladesh_2020.pdf, research/data/boundaries/*.geojson
Output: research/soil/srdi_fertility_upazila.csv, research/soil/srdi_fertility_pilots.csv,
        research/data/soil/srdi_georef_check.png (district lines drawn on the pH map, to eyeball the fit)
Usage : python research/explore/srdi_soil_maps.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pyproj import Transformer
from rasterio import features
from rasterio.transform import Affine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acquire"))
from _common import DATA, RESEARCH, load_sites  # noqa: E402

PDF = DATA / "soil" / "SRDI_Soil_Fertility_Atlas_Bangladesh_2020.pdf"
OUT = RESEARCH / "soil"
BUTM = ("+proj=tmerc +lat_0=0 +lon_0=90 +k=0.9996 +x_0=500000 +y_0=-2000000 +a=6377276.345 +b=6356075.4131 "
        "+units=m +no_defs")  # Bangladesh Transverse Mercator (Everest 1830)
TO_BUTM = Transformer.from_crs("EPSG:4326", BUTM, always_xy=True)
FERTILITY = ["Very Low", "Low", "Medium", "Optimum", "High", "Very High"]
PH = ["Very Strongly Acidic", "Strongly Acidic", "Slightly Acidic", "Neutral", "Slightly Alkaline",
      "Strongly Alkaline", "Very Strongly Alkaline"]
MAPS = {7: ("ph", PH), 8: ("organic_matter", FERTILITY), 9: ("p_upland", FERTILITY), 10: ("p_wetland_rice", FERTILITY),
        11: ("k_upland", FERTILITY), 12: ("k_wetland_rice", FERTILITY), 13: ("s_upland", FERTILITY),
        14: ("s_wetland_rice", FERTILITY), 15: ("zn", FERTILITY), 16: ("b", FERTILITY), 17: ("ca", FERTILITY),
        18: ("mg", FERTILITY)}
# Two page layouts. Per layout: graticule label positions for the starting guess (x of 88 and 92 E, y of 26 and
# 20 N), the page furniture that is coloured but not land (legend, class table, logo, title, scale bar) and the
# legend swatch column. The Mg map (page 18) is drawn larger, with its frame running to 93 E.
LAYOUTS = {"a": ((60, 620, 128, 896), [(0, 655, 240, 940), (240, 690, 460, 940), (455, 790, 665, 940),
                                       (120, 20, 640, 200)], (690, 900, 50, 70)),
           "b": ((45, 518, 105, 918), [(0, 715, 240, 940), (240, 760, 460, 940), (455, 800, 665, 940),
                                       (110, 15, 645, 185)], (745, 900, 36, 50))}
PAGE_LAYOUT = {page: ("b" if page == 18 else "a") for page in MAPS}


def map_images() -> dict[int, np.ndarray]:
    pdf = pdfium.PdfDocument(str(PDF))
    out = {}
    for page in MAPS:
        img = next(o for o in pdf[page].get_objects() if o.type == 3).get_bitmap(render=False).to_pil()
        out[page] = np.asarray(img.convert("RGB").resize((665, 940)), dtype=np.int16)
    return out


def land_mask(rgb: np.ndarray, boxes: list) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    coloured = (mx - mn > 60) & (mx > 60)          # saturated: the class colours
    sea = (b > 180) & (b > r + 40) & (g > 150)       # light blue: sea and major rivers
    m = coloured & ~sea
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = False
    return m


def bd_polygons(level: str) -> list[dict]:
    j = json.loads((DATA / "boundaries" / f"BGD_{level}_simplified.geojson").read_text(encoding="utf-8"))
    return j["features"]


def project(geom: dict) -> dict:
    def ring(coords):
        x, y = TO_BUTM.transform([c[0] for c in coords], [c[1] for c in coords])
        return list(zip(x, y))
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [ring(r) for r in geom["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[ring(r) for r in poly] for poly in geom["coordinates"]]}


def fit_frame(mask: np.ndarray, country: list[dict], layout: str) -> tuple[Affine, float]:
    """Pixel -> BUTM affine (no rotation) maximising IoU between the map's land and Bangladesh."""
    (px88, px92, py26, py20), boxes, _ = LAYOUTS[layout]  # starting guess from the graticule labels
    (x88, x92), _ = TO_BUTM.transform([88, 92], [24, 24])
    _, (y26, y20) = TO_BUTM.transform([90, 90], [26, 20])
    sx, sy = (x92 - x88) / (px92 - px88), (y26 - y20) / (py20 - py26)
    x0, y0 = x88 - px88 * sx, y26 + py26 * sy
    # Bangladesh on a 250 m grid in BUTM, looked up for every map pixel
    res, (gx0, gy1) = 250.0, (x0 - 50000, y0 + 50000)
    nx, ny = int(700000 / res), int(1000000 / res)
    grid_t = Affine(res, 0, gx0, 0, -res, gy1)
    bd = features.rasterize([(project(f["geometry"]), 1) for f in country], out_shape=(ny, nx), transform=grid_t,
                            dtype="uint8")
    rows, cols = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    valid = np.ones_like(mask)
    for x_0, y_0, x_1, y_1 in boxes:
        valid[y_0:y_1, x_0:x_1] = False
    cols_v, rows_v, m_v = cols[valid] + 0.5, rows[valid] + 0.5, mask[valid]

    def iou(p):
        ax, ay, bx, by = p
        gx = ((ax + cols_v * bx) - gx0) / res
        gy = (gy1 - (ay - rows_v * by)) / res
        ok = (gx >= 0) & (gx < nx) & (gy >= 0) & (gy < ny)
        inside = np.zeros_like(m_v)
        inside[ok] = bd[gy[ok].astype(int), gx[ok].astype(int)] == 1
        return (m_v & inside).sum() / max((m_v | inside).sum(), 1)

    best = np.array([x0, y0, sx, sy])
    score = iou(best)
    for step_off, step_sc, n in ((6000, 0.02, 4), (1500, 0.005, 4), (400, 0.0015, 3), (100, 0.0005, 3)):
        improved = True
        while improved:
            improved = False
            for k in range(4):
                for sign in (-1, 1):
                    for mult in range(1, n + 1):
                        cand = best.copy()
                        cand[k] += sign * mult * (step_off if k < 2 else step_sc * best[k])
                        s = iou(cand)
                        if s > score + 1e-6:
                            best, score, improved = cand, s, True
    ax, ay, bx, by = best
    return Affine(bx, 0, ax, 0, -by, ay), score


def legend_colours(rgb: np.ndarray, n: int, layout: str) -> list[np.ndarray]:
    """The first n colour swatches of the legend, top to bottom, from the layout's swatch column."""
    y0, y1, x0, x1 = LAYOUTS[layout][2]
    col = rgb[y0:y1, x0:x1]
    colours, run, last = [], [], None
    for y in range(col.shape[0]):
        row = col[y]
        uniform = row.std(axis=0).max() < 12 and (row.max(axis=1) - row.min(axis=1)).mean() > 40
        c = row.mean(axis=0)
        if uniform and (last is None or np.abs(c - last).max() < 25):
            run.append(c)
            last = c
        else:
            if len(run) >= 6:
                colours.append(np.mean(run, axis=0))
            run, last = ([c], c) if uniform else ([], None)
    if len(run) >= 6:
        colours.append(np.mean(run, axis=0))
    return colours[:n]


def classify(rgb: np.ndarray, colours: list[np.ndarray], max_dist: float = 45.0) -> np.ndarray:
    d = np.stack([np.sqrt(((rgb - c) ** 2).sum(axis=2)) for c in colours])
    cls = d.argmin(axis=0)
    cls[d.min(axis=0) > max_dist] = -1
    return cls


def main() -> None:
    imgs = map_images()
    country = bd_polygons("ADM2")
    frames = {}
    for layout, page in (("a", 7), ("b", 18)):
        frames[layout], score = fit_frame(land_mask(imgs[page], LAYOUTS[layout][1]), country, layout)
        print(f"layout {layout} frame fit: IoU {score:.3f}, pixel = {frames[layout].a:.0f} x {-frames[layout].e:.0f} m")
    frame_t = frames["a"]
    to_px = ~frame_t

    # eyeball check: district lines on the pH map
    check = Image.fromarray(imgs[7].astype(np.uint8))
    draw = ImageDraw.Draw(check)
    for f in country:
        g = project(f["geometry"])
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            draw.line([to_px * xy for xy in poly[0]], fill=(0, 0, 255), width=1)
    check.save(DATA / "soil" / "srdi_georef_check.png")

    upz = bd_polygons("ADM3")
    upz_px = {layout: [features.rasterize([(project(f["geometry"]), 1)], out_shape=(940, 665), transform=t,
                                          dtype="uint8") == 1 for f in upz] for layout, t in frames.items()}
    pilots = load_sites("pilot_sites")
    pil_px = {layout: [tuple(int(v) for v in (~t * TO_BUTM.transform(p["lon"], p["lat"]))) for p in pilots]
              for layout, t in frames.items()}

    up_rows = [{"upazila": f["properties"]["shapeName"], "shape_id": f["properties"]["shapeID"]} for f in upz]
    pi_rows = [{"site_id": p["site_id"]} for p in pilots]
    for page, (name, classes) in MAPS.items():
        layout = PAGE_LAYOUT[page]
        colours = legend_colours(imgs[page], len(classes), layout)
        if len(colours) != len(classes):
            raise ValueError(f"page {page}: found {len(colours)} legend swatches for {len(classes)} classes")
        cls = classify(imgs[page], colours)
        for row, inside in zip(up_rows, upz_px[layout]):
            v = cls[inside & (cls >= 0)]
            if len(v):
                counts = np.bincount(v, minlength=len(classes))
                row[name] = classes[counts.argmax()]
                row[f"{name}_share"] = round(counts.max() / len(v), 2)
            else:
                row[name], row[f"{name}_share"] = None, None
        for row, (x, y) in zip(pi_rows, pil_px[layout]):
            v = cls[max(y - 2, 0):y + 3, max(x - 2, 0):x + 3].ravel()
            v = v[v >= 0]
            row[name] = classes[np.bincount(v).argmax()] if len(v) else None
        print(f"{name:16s} legend {len(colours)} classes; upazilas classified {sum(r[name] is not None for r in up_rows)}")
    OUT.mkdir(parents=True, exist_ok=True)
    src = "SRDI Soil Fertility Atlas of Bangladesh 2020 (maps from Upazila Nirdeshika data), read by colour"
    pd.DataFrame(up_rows).assign(source=src).to_csv(OUT / "srdi_fertility_upazila.csv", index=False)
    pd.DataFrame(pi_rows).assign(source=src).to_csv(OUT / "srdi_fertility_pilots.csv", index=False)


if __name__ == "__main__":
    main()
