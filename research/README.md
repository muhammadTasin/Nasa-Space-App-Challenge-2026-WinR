# Pre-event research: data access and a first look

This folder is **research, not the product.** The NASA Space Apps FAQ asks teams to start the actual
project work when the hackathon begins (Bangladesh local events 13–14 Nov 2026). Everything here
checks which data we can get, how, and whether it says what we think it says. Product code gets
written at the event. Disclose this folder, and any AI help with it, in `docs/AI_USE.md`.

## Challenge 07, as officially summarised

*Field Shift: Adapting Farms with NASA Data.* Build a decision-support tool that uses NASA Earth
observations, **local soil information, crop characteristics and farmer priorities** to help farmers
explore **crop-rotation strategies** that strengthen soil health and adapt to changing conditions.
The full statement and datasets are due 28 Oct 2026. Re-read it then.

## What is already downloaded (no login needed)

| Script | Source | What we have | Where |
|---|---|---|---|
| `acquire/boundaries.py` | geoBoundaries (CC BY 4.0) | 64 districts, 544 upazilas + centroids (5,160 unions available) | `data/boundaries/`, `sites/districts.csv` |
| `acquire/power.py` | NASA POWER daily (MERRA-2, CERES) | 16 variables, 1991 → yesterday, 64 districts + 5 pilot sites + 1 upstream point | `data/power/daily/*.parquet` |
| `acquire/power.py` | **GPM IMERG via POWER** (`IMERG_PRECTOT`) | daily rain at native 0.1°, 1998 → ~12 days ago | same files, column `IMERG_PRECTOT` |
| `acquire/power.py --hourly-years` | NASA POWER hourly | T, RH, wind, sun for 2023–2025 at the pilot sites (cattle THI) | `data/power/hourly/` |
| `acquire/ndvi_modis.py` | MODIS MOD13Q1 250 m NDVI (ORNL DAAC web service) | 2000 → Aug 2026, 9×9-pixel window per pilot site, QA-filtered | `data/ndvi/MOD13Q1/` |
| `acquire/soilgrids.py` | ISRIC SoilGrids 2.0 (CC BY 4.0) | SOC, N, pH, clay/sand/silt, CEC, bulk density; 3 depths; mean + 5–95% band | `data/soil/` |
| `acquire/gibs_snapshots.py` | NASA GIBS WMS | Bangladesh images: VIIRS NOAA-20 NDVI, SMAP L4 root zone, IMERG, MODIS flood | `data/gibs/` |

Every cached file has a `.provenance.json` sidecar (source, URL, parameters, retrieval time).

**Gotcha:** POWER returns `IMERG_PRECTOT` only with `time-standard=UTC`. With the default (LST) it
silently returns -999. The script makes two calls per site for this reason.

## What needs a free Earthdata Login (scripts ready, not yet run)

1. Each teammate creates an account at <https://urs.earthdata.nasa.gov/users/new>.
2. In the Earthdata profile, under *Applications → Authorized Apps*, approve **NASA GESDISC DATA ARCHIVE**
   (needed for any GES DISC download).
3. Copy `.env.example` to `.env` at the repo root and fill in the username and password. `.env` is gitignored.

| Script | Products | Why we want them |
|---|---|---|
| `acquire/appeears_points.py --preset core` | SMAP L3 enhanced 9 km soil moisture, **VIIRS NOAA-20 NDVI (VJ113A1)**, SMAP L4 carbon (soil organic carbon, GPP) | field workability and sowing windows; the MODIS successor; a NASA soil-carbon signal |
| `acquire/appeears_points.py --preset l4` | SMAP L4 surface + **root-zone** soil moisture and its percentile | crop water stress, irrigate/skip advice |
| `acquire/appeears_points.py --preset et` | MODIS ET/PET 500 m (MOD16A2GF) | crop water use per rotation |
| `acquire/grace_fo.py` | GRACE/GRACE-FO JPL mascon RL06.3 | regional groundwater decline (north-west). About 300 km resolution, so it is context, not a farm number |

`grace_fo.py` also needs `pip install earthaccess xarray netCDF4`.

## What has to be collected by hand

| Item | Source | Use |
|---|---|---|
| Daily station Tmax/Tmin/rain for Rajshahi, Sylhet, Khulna, Bogura, Rangpur | Bangladesh Meteorological Department (BMD) data request | **bias-correct POWER** (see below) and validate IMERG |
| Cropping patterns by district | BRRI: Nasim et al. 2017, *Distribution of crops and cropping patterns in Bangladesh*, Bangladesh Rice Journal 21(2) | the candidate-rotation library |
| Crop traits | FAO-56 crop coefficients; BRRI/BARI variety guides (duration, heat, salt and flood tolerance) | fill `templates/crop_parameters_template.csv` |
| Soil and salinity | SRDI upazila land and soil guides; BARC Fertilizer Recommendation Guide 2018 | local soil information |
| District yields; market prices | BBS Yearbook of Agricultural Statistics; DAM price bulletins | income side of the rotation score; labels for any yield model |
| Flood dates | BWDB Flood Forecasting and Warning Centre | hindcast the flash-flood trigger |

## First look (run `python explore/first_look.py`)

Exploratory only: one grid cell per site, and not yet checked against stations.

* **Reanalysis Tmax runs about 3 °C hot in Barind.** POWER's April mean Tmax at the Tanore cell is
  39.0 °C against BMD Rajshahi's 35.8 °C (1991–2020 normals). Crop heat thresholds (e.g. 35 °C at
  rice flowering) cannot be applied to raw POWER values; bias-correct first.
* **No robust shift in rainy-season onset** at any pilot site (Liebmann–Marengo method, 2001–12 vs
  2013–25, all p > 0.2). Year-to-year spread is 16–28 days, so timing advice has to follow each
  season's live data rather than a fixed "shifted calendar".
* **Monsoon rain at the Tanore cell fell about 18%** (Jun–Sep IMERG, 1,179 → 961 mm, p ≈ 0.05).
  Needs a station check, but it points the same way as the groundwater story.
* **Barind fields intensified from about 1.6 to 2.8 crop cycles a year** (MODIS NDVI peaks, 2001–05 vs
  2021–25). The other sites are mixed (Batiaghata 2.2 → 1.6, Ullahpara 2.2 → 1.8, Mithapukur 1.6 → 2.0,
  haor 2.0 → 2.0, where wetland greenness inflates the count). The peak counter is rough; check it against
  HLS 30 m and local knowledge before quoting anything beyond Tanore.
* **MERRA-2 root-zone wetness rose in the dry season at all five sites** (p < 0.03) while Rabi rain did not
  change. Treat modelled soil-moisture trends with suspicion and use SMAP (2015 onward) for current state.
* **Daily-mean cattle THI is ≥ 78 on about 170–210 days a year** at every site, so a daily alert would
  be permanently on. Use hourly THI and night-time relief instead. In April 2024 at Ullahpara, 16 of
  30 nights never dropped below THI 72, and the coolest hours were 02:00–05:00.
* **Upstream IMERG rain on the Meghalaya plateau** (Sohra) put 317 mm in 3 days ending 3 Apr 2017,
  the year the haor Boro harvest was lost. That ranks 5th of 27 pre-harvest seasons, so the trigger is
  plausible but needs a proper hindcast against BWDB flood dates.

## Continuity

Terra/Aqua MODIS are ending, and NASA stops delivering Suomi-NPP VIIRS data on 1 Nov 2026. Use MODIS
for the 2000–2025 baseline, and VIIRS on NOAA-20/21 (VJ113A1, VJ213A1) plus HLS 30 m for anything live.
