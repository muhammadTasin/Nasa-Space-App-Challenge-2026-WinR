# Pre-event research: data access and a first look

This folder is **research, not the product.** The NASA Space Apps FAQ asks teams to start the actual
project work when the hackathon begins (Bangladesh local events 13–14 Nov 2026 per the local guide; the global
FAQ gives 14–15 Nov, so confirm with the organisers). Everything here
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
| `acquire/boundaries.py` | geoBoundaries (CC BY 4.0) | 64 districts, 544 upazilas and 5,160 unions (`--levels ADM4`) + centroids | `data/boundaries/`, `sites/districts.csv`, `sites/adm4_centroids.csv` |
| `acquire/power.py` | NASA POWER daily (MERRA-2, CERES) | 16 variables, 1991 → yesterday, 64 districts + 5 pilot sites + 1 upstream point | `data/power/daily/*.parquet` |
| `acquire/power.py` | **GPM IMERG via POWER** (`IMERG_PRECTOT`) | daily rain at native 0.1°, 1998 → ~12 days ago | same files, column `IMERG_PRECTOT` |
| `acquire/power.py --hourly-years` | NASA POWER hourly | T, RH, wind, sun for 2023–2025 at the pilot sites (cattle THI) | `data/power/hourly/` |
| `acquire/ndvi_modis.py` | MODIS MOD13Q1 250 m NDVI (ORNL DAAC web service) | 2000 → Aug 2026, 9×9-pixel window per pilot site, QA-filtered | `data/ndvi/MOD13Q1/` |
| `acquire/soilgrids.py` | ISRIC SoilGrids 2.0 (CC BY 4.0) | SOC, N, pH, clay/sand/silt, CEC, bulk density; 3 depths; mean + 5–95% band | `data/soil/` |
| `acquire/gibs_snapshots.py` | NASA GIBS WMS | Bangladesh images: VIIRS NOAA-20 NDVI, SMAP L4 root zone, IMERG, MODIS flood | `data/gibs/` |
| `acquire/gsod.py` | NOAA GSOD: BMD's own daily station reports via WMO | 41 stations, 186,165 station-days of Tmax/Tmin/rain/wind, 1981 → 24 Aug 2025, converted to °C and mm | `data/stations/gsod/`, `sites/bmd_stations_gsod.csv` |
| `acquire/brri_factsheets.py` + `explore/brri_varieties.py` | BRRI Rice Knowledge Bank factsheets | 178 PDFs → **127 rice varieties** (135 variety-season rows): duration, yield, height, release year, sowing and harvest windows (129 rows), salt/flood/drought/cold tolerance, zinc; for the 12 newest two-page sheets also spacing, seedlings per hill, weed-free days and **fertilizer doses per bigha with timing** | PDFs in `data/brri/`; table in `crops/brri_rice_varieties.csv` |
| `explore/bbs_yearbook.py` | BBS Yearbook of Agricultural Statistics 2025 (684 pages; PDF in `data/bbs/`) | `bbs/crop_district.csv` (124 crop tables × 64 districts, 2022-23 to 2024-25; district sums match national totals), `crop_calendar.csv`, `census_costs.csv` (cost and return per acre by division), `harvest_prices.csv` (70 items), `irrigation.csv`, `intensity.csv`, `damage.csv` (8 flood/cyclone events by district), **`monthly_prices.csv`** (national wholesale and retail prices by month, 2024 and 2025, ~260 items: paddy and rice by season and grade, pulses, oilseeds, potato, onion, jute, vegetables, beef, milk, fertilizer) and **`livestock_census.csv`** (Agriculture Census 2019: holdings keeping cows, buffalo, goats, sheep, chickens, ducks, pigeons and head counts, by farm size, national/rural/urban) | `research/bbs/` |
| `explore/cropping_patterns.py` | Nasim et al. 2017, BRRI national cropping-pattern survey (PDF in `raw, collected datas/`) | all 316 patterns with area; district tables for the top 6; crop diversity and intensity by district | `research/crops/` |

| `explore/bari_varieties.py` | BARI Krishi Projukti Hatboi, 10th ed. (650 pages, Bijoy-encoded; PDF in `raw, collected datas/`) | **167 varieties of 21 field crops** (potato, mustard, lentil, chickpea, mungbean, grass pea, sesame, groundnut ...): release year, days to maturity, yield, height, drought/salt/heat tolerance, fits after Aman | `crops/bari_field_crop_varieties.csv` |
| `explore/bari_production.py` (+ `explore/bijoy.py`) | the same handbook, "উৎপাদন প্রযুক্তি" (production technology) sections | **147 crop sections** (tubers, pulses, oilseeds, spices, grains, vegetables, fruits, flowers): sowing windows as dates, seed rate kg/ha, row and plant spacing, fertilizer doses kg/ha (urea, TSP, MoP, gypsum, zinc, boron, cowdung), number of irrigations, days to harvest; every labelled field as **Unicode Bangla text** (2,372 fields: soil, land preparation, sowing, fertilizer timing, weeding, irrigation, harvest, pests and diseases); 597 fertilizer rows with unit and basis | `crops/bari_production_technology.csv`, `crops/bari_production_fields.csv`, `crops/bari_fertilizer_doses.csv` |
| `explore/fao56.py` | FAO-56 Chapter 6, Tables 11-12 (link in `raw, collected datas/sitelink.txt`) | crop coefficients Kc ini/mid/end for 124 crops, growth-stage lengths (165 rows); footnote marks removed | `crops/fao56_kc.csv`, `crops/fao56_stage_lengths.csv` |
| `explore/crop_parameters.py` | all of the above | **the rotation engine's crop table**: 13 candidate crops with varieties, duration, sowing/harvest window, Kc, heat threshold, tolerant varieties, national and Rajshahi yield, price, cost, by-product value; every row lists its sources | `crops/crop_parameters.csv` |

| `acquire/brri_regional_papers.py` + `explore/regional_patterns.py` | BRRI's 14 regional cropping-system papers (Bangladesh Rice Journal 21(2), 2017, open access) | **upazila level, 2014-15**: land use and cropping intensity for 461 upazilas, 1,662 region-level rotation rows, where each region's top rotations sit (1,665 upazila rows), crop diversity; 97% of upazilas matched to map locations and districts | `crops/upazila_*.csv`, `crops/regional_patterns.csv` |
| `acquire/bbs_yearbooks.py` + `explore/bbs_panel.py` | 13 editions of the BBS yearbook (2012-2025; the 2021 link is broken) | **district panel, 23 rotation crops × 64 districts × 13 seasons (2012-13 to 2024-25)**, 25,735 rows; latest edition wins where they overlap. Checks: national rice area within 1-3% of FAOSTAT every season; editions agree on every overlapping cell; rice totals the 2015-2018 books omit are derived from their local/HYV/hybrid tables (matching printed totals, median diff 0.00%); the 2015 book's minor-crop tables use a 2-season layout (acre, kg/acre, t), detected from the column header. Mustard is missing 2015-16 and 2016-17 | `bbs/crop_district_panel.csv` |
| `acquire/faostat.py` | FAOSTAT crops and livestock (CC BY 4.0) | Bangladesh 1961-2024, 138 items: the long-run "field shift" (maize ×100 since 2000, wheat −63%) | `crops/faostat_bangladesh*.csv` |
| `acquire/livestock_glw4.py` | FAO Gridded Livestock of the World v4, cattle 2015 (CC0) | cattle per district (23.8 million nationally, matching the official estimate) | `crops/cattle_by_district_glw4.csv` |
| `explore/bbs_yearbook.py` (holdings) | Agriculture Census 2019, via the yearbook | farm holdings by district: small/medium/large, tenancy, farm-labour households; sums to the national total | `bbs/holdings.csv` |
| `explore/pilot_cards.py` | all of the above | one card per pilot site with its local rotations, land use, farms, cattle, irrigation, yields and recorded losses | `pilots/*.md` |

**Existing government services we must position against (checked 26 Sep 2026).** DAE's BAMIS portal
(<https://www.bamis.gov.bd>, with BMD) publishes district and upazila agromet bulletins, runs automatic rain
gauges, and lists two services close to ours, both not working today: an **IVR advisory** page showing only an
"Under construction / Coming soon" poster (uploaded Jan 2024), and **IRAS**, a satellite-based irrigation
advisory "under maintenance" while DAE improves it "over Barind and Haor regions", which are our two main
pilots. Pitch it as complementary: rotation choice, cattle and voice delivery that could plug into BAMIS.

**Not reachable from here:** BARC's *Fertilizer Recommendation Guide 2018* (ministry server times out, BARC
portal retired, the Fertilizer Association copy is gone) and FFWC's daily river data (its API is locked; the
annual flood reports are used instead, see `ffwc_floods.py`). Try the ministry link from a Bangladeshi network,
or request both from BARC and BWDB.

**About the BARI table.** The PDF was built in Illustrator and neighbouring pages carry copies of each other's
text, so each variety appears several times. The parser scores every copy (does it name its own variety; are
the days and yield plausible for that crop) and keeps the best; the Bijoy text it parsed is kept in
`description_bijoy`. Wheat and maize varieties now come from BWMRI and are not described in this handbook.

**About the BARI production-technology tables.** `bari_production.py` keeps only the characters that fall inside
each page (dropping the neighbours' copies), notes each character's font, and converts the Bijoy text to Unicode
Bangla with `bijoy.py` (text set in Times New Roman, such as scientific names, is left alone). Bold spans are the
field labels ("মাটি:", "বপনের সময়:", "সারের পরিমাণ:"), photo captions are the lines set wholly in italic and are
dropped, and the table of contents gives each crop's page. Checked against the printed pages: mustard urea
250-300, TSP 170-180, MoP 85-100 kg/ha, sow mid-Oct to mid-Nov; potato 325-350 / 200-220 / 250-300 kg/ha;
lentil sown late Oct to the 2nd week of Nov, harvested 110-115 days after sowing. Things to know:
* Dates are the book's; where it gives only Bangla-calendar months they are converted (Kartik = 17 Oct - 15 Nov).
  `sowing_windows` lists every window in reading order (the first is usually the main one; sesame, mung bean
  and groundnut list one per season).
* Dose columns in the summary are **midpoints of the printed range**, per hectare, and only where the value is
  believable per hectare; `bari_fertilizer_doses.csv` has every row with its unit (kg, g, t) and basis (ha,
  bigha, decimal, plant, pit). Fruit trees are dosed per plant by age, so their summary doses are blank.
* The book gives one recommendation for most pulses (urea 40-45, TSP 80-90, MoP 40-45, gypsum 50-55 kg/ha), so
  lentil, chickpea, mung bean, black gram and field pea share figures. Coriander prints TSP "15 kg/ha" (probably
  150); garlic's table lists only cowdung, ash, TSP and MoP.
* The summer-onion section also covers onion seed production (mother-bulb planting in Oct-Dec). Two pages
  (broccoli p.188, pointed gourd p.217) are printed as outlines with no text layer and are not extracted.
* Not every field is filled: 115 of 147 sections give sowing dates, 54 a seed rate, 64 an MoP dose, 44 days to
  harvest. The Bangla text of every field is in `bari_production_fields.csv` for reading and for the advisory
  wording (cite BARI).

**About FAO-56 stage lengths.** They are for California, the Mediterranean and similar climates (lentil
150-170 days there, 105-115 in Bangladesh). Use their proportions, scaled to the local variety duration.

**About the BRRI table.** The factsheets are in Bangla. 65 PDFs have a text layer typed in the legacy
Bijoy font encoding, which `brri_varieties.py` decodes with patterns (50 varieties). The other 113 are
scanned images; those 77 varieties were read by eye and entered in `crops/brri_manual_entries.csv`, which
the script merges. Every row keeps its source file and URL. Figures are BRRI's own (yield under good
management), and blanks mean the sheet did not state the value. Page 2 of the 12 two-page scans (BRRI dhan79,
91, 101, 104, 108, 110-112, 115-118) adds harvest dates, spacing, weed-free period and the fertilizer table
(kg per bigha of 33 decimals, as farmers use; × 7.475 for kg/ha) with split timing; the BRRI dhan51 scan
duplicates a text factsheet. Spot-check a few scanned rows against their PDFs before quoting them.

Every cached file has a `.provenance.json` sidecar (source, URL, parameters, retrieval time).

**Gotcha:** POWER returns `IMERG_PRECTOT` only with `time-standard=UTC`. With the default (LST) it
silently returns -999. The script makes two calls per site for this reason.

## Live feeds and local layers (added 27 Sep 2026)

| Script | Source | What we have | Where |
|---|---|---|---|
| `acquire/forecast.py [--skill]` | ECMWF IFS/ENS and NOAA GFS via [Open-Meteo](https://open-meteo.com) (CC BY 4.0; NASA's GEOS-FP servers did not answer from here) | for the 5 pilots, the upstream Meghalaya point and 64 district centroids: 16-day hourly and daily forecast (T, RH, rain, wind, sun, FAO ET0, cattle THI); 51-member ensemble probabilities for 15 days (rain >= 20/50/100 mm, Tmax >= 36/38/40 C); 6-month seasonal outlook by month; with `--skill`, archived ECMWF runs at 1-7 days' lead since Jan 2024 (Tanore Tmax error 0.8 C a day ahead, 1.5 C a week ahead) | `data/forecast/<date>/` (run daily) |
| `acquire/imerg_nrt.py [--days 120]` / `--baseline 2001 2025` | NASA GPM IMERG V07 daily, Late run (Early for the newest day), GES DISC OPeNDAP, a 0.1 deg window over Bangladesh and Meghalaya; the baseline from GES DISC's Giovanni time-series service | **rain to yesterday** (POWER lags ~12 days): 30 May - 26 Sep 2026 on the grid and at 70 sites; identical to POWER's values where they overlap (r = 1.00). `--baseline`: the Late run 2001-2025 at the same 70 cells, one call per site (~5 s for 25 years; cutting the days out over OPeNDAP took ~10 min a year; the two agree to 0.000002 mm). POWER's 1998-2025 history is the gauge-adjusted Final run (r = 1.000), and **the Late run has drifted dry against it**: Jun-Sep Late/Final stayed within 0.8-1.2 in 2001-2022, then fell to 0.84, 0.64, 0.58 at Tanore (2023-2025) and 0.73-0.92 at the other pilots. So even Late against Late overstates dryness now; see `rain_vs_normal.py` | `data/imerg_nrt/` |
| `explore/rain_vs_normal.py` | the IMERG Late feed and baseline, POWER's IMERG Final and MERRA-2 | **rain so far against normal** at 70 sites (since 1 Jun, by month, last 30 days) from three estimates (Late vs Late; Late scaled by the site's 2023-2025 Late/Final ratio vs Final; MERRA-2) and a `verdict` that says dry/wet/normal only when all three agree. As of 22 Sep 2026 they disagree on the season (Tanore since 1 Jun: 50%, 71%, 107% of normal; ERA5 from Open-Meteo, checked by hand, 75%), and agree that the **last 30 days were dry** at Batiaghata, Mithapukur and Dharmapasha. BMD gauges would settle the season (see the hand-collection table) | `pilots/rain_vs_normal.csv` |
| `acquire/srdi_frs.py` | SRDI's online fertilizer recommendation card ([frs-bd.com](http://frs-bd.com), SRDI with Katalyst; searched only, nothing entered but the choices) | **union-level fertilizer doses by soil type, land type, season and crop** for each pilot's union (Talanda, Tanore; Selborash, Dharmapasha; Batiaghata; Ullapara; Durgapur, Mithapukur): urea (with/without DAP), TSP/DAP, MoP, gypsum, zinc sulphate, boric acid, lime, with timing, per acre as printed and per hectare. **The doses are local**: no two pilot unions get the same card for a crop, season and land type (Boro, medium-high land: urea 80 kg/acre at Ullapara, 132 at Batiaghata and Selborash, 185 at Talanda; lime at Talanda and Selborash; no zinc at Selborash). The form returns cards for every land type it lists crops for (the haor union gets high-land cards too), so which land types a union has comes from `landtype_proxy_*.csv`, not from here. The pilot points: Dharmapasha's lies 0.3 km over the Mohanganj border and Ullapara's in the town, so their nearest rural unions inside the upazila are used | `soil/srdi_frs_cards.csv`, `soil/srdi_frs_doses.csv` |
| `acquire/wfp_prices.py` | WFP Bangladesh food prices on HDX (CC BY-IGO; republishes DAM's market prices, monthly) | monthly market prices in the pilot districts and Dhaka: division series 2004/2006-2020, district markets 2020-Jul 2026 (Rajshahi, Godagari, Khulna, Dumuria, Rangpur, Mithapukur, Sirajganj, Sunamganj). Mostly retail household items (coarse rice, lentils, flour, oil, potato, onion): food cost and price trends, not farm-gate prices | `pilots/wfp_market_prices.csv` |
| `explore/srdi_soil_maps.py` | SRDI *Soil Fertility Atlas of Bangladesh 2020* (built from the Upazila Nirdeshika data; PDF in `data/soil/`) | **soil fertility class for every upazila** (and 5 x 5 pixels at each pilot): pH, organic matter, P, K and S (upland and wetland rice), Zn, B, Ca, Mg. The 12 map images are georeferenced to BUTM by fitting Bangladesh's outline (91-93% overlap; district lines land on the map's own), each pixel is classed by the nearest legend colour and each upazila takes its majority class (`*_share` = how dominant). Upazila shares match the atlas's national tables (pH strongly/very strongly acidic 44% vs 46%; Zn low 84% vs 79%). A map pixel is ~0.85 km: upazila-scale classes, not field tests | `soil/srdi_fertility_upazila.csv`, `soil/srdi_fertility_pilots.csv` |
| `acquire/landtype_proxy.py` | NASA NASADEM elevation (Planetary Computer) + JRC Global Surface Water 1984-2021 | **a land-type proxy for every upazila and pilot**: elevation p10/median/p90, share of land never seen as water, water in >= 10% / >= 50% of clear Landsat views, water >= 3 / 6 months in 2021. The wettest upazilas are the haor (Khaliajuri, Itna, Mithamain, Austagram, Sulla, Jamalganj, Dharampasha) and char areas. Landsat misses floods under monsoon cloud, so this marks land that stays wet into the dry season, not flood depth | `soil/landtype_proxy_upazila.csv`, `soil/landtype_proxy_pilots.csv` |
| `explore/fao_ky.py` | FAO Irrigation and Drainage Paper 66, Table 1 (FAO-33 values) | seasonal yield-response factor Ky for 21 crops (maize 1.25, spring wheat 1.15, potato and onion 1.1, groundnut 0.7 ...); no rice, lentil, mustard or jute in the table | `crops/fao_ky_seasonal.csv` |
| `acquire/bwmri_varieties.py` + `explore/bwmri_varieties.py` | BWMRI variety pages (bwmri.gov.bd; the page text is Unicode Bangla, the leaflets are scans) | **14 wheat and 30 maize varieties**: release year, days to maturity, height, 1000-grain weight, yield, sowing window, seed rate, heat/salt/drought/blast/rust traits, suitable areas. All current wheat varieties are heat tolerant; BARI Gom 25 and BWMRI Gom 4 take 8-10 dS/m salinity; BARI Gom 33 is blast resistant and zinc-rich; BARI Hybrid Maize 13 is the drought-tolerant Barind maize (8.1-8.5 t/ha with one irrigation) | `crops/bwmri_wheat_maize_varieties.csv` |
| `acquire/dls_livestock.py` + `explore/dls_livestock.py` | DLS *Livestock Economy at a glance* 2015-16 to 2025-26 | national cattle, buffalo, goat, sheep, chicken and duck numbers and milk, meat and egg production by year (cattle 23.8 to 25.3 million; milk 7.3 to 15.8 million t). DLS's own yearly estimates, which differ from the census head count | `livestock/dls_livestock_economy.csv` |
| `acquire/ffwc_reports.py` + `explore/ffwc_floods.py` | FFWC/BWDB *Annual Flood Report* 2010-2021 (old.ffwc.gov.bd; 2008-09 are linked but not on the server) and FFWC's station list | **river floods by station and year**: 948 station-years at 95 stations (danger level, previous record, the year's monsoon peak and its date, days above danger level; the peak agrees with the report's own peak-date table 98% of the time, the rest are typos in the reports). **Haor flash floods**: the 15 Mar-15 May table of the 2018-2021 reports for 15 Meghna-basin stations (monsoon and pre-monsoon danger levels, season peak, days above each) for 2010 and 2017-2021, the reports' 91 sentences on pre-monsoon floods, and a year table: flash floods before mid-May in 2010 (late April, early May), 2017 (very early April), 2018 (mid-May) and 2019 (short; Jariajanjail 6 days above its pre-monsoon danger level), none in 2014, 2020, 2021. Levels in mPWD (0.45 m above the new site's mMSL) | `floods/ffwc_station_years.csv`, `floods/ffwc_premonsoon_meghna.csv`, `floods/ffwc_premonsoon_notes.csv`, `floods/haor_flash_flood_years.csv` |

**Not reachable or not ours to take:** FFWC's data API refuses requests without a site security header, and the
new site (ffwc.gov.bd/app) only shows its data: the last 40 days of readings, May-Oct hydrographs for 2022-2026
and monthly average and maximum levels for 2003-2026, as charts with image export only. Daily levels, and the
2022-2026 pre-monsoon record (the 2022 flash flood is after the last report), need a formal request to BWDB/FFWC.
BWDB groundwater well data needs registration and is sold by the record. DAM's report pages (market.dam.gov.bd daily market report and commodity report, incl. growers' prices)
returned empty tables for every market and date tried, 2020-2026, even Kawran Bazar from a browser (27 Sep 2026);
`wfp_prices.py` takes DAM's prices as WFP republishes them.

**Faster ways to NASA data (checked 27 Sep 2026).** Time goes on how many files NASA's server opens, not on
how much we download: a day of IMERG is one global file even when we keep 3,250 cells of it. For a point series
use the **Giovanni time-series service** (`imerg_nrt.py --baseline`; CMR lists it for IMERG, GLDAS and more;
it refused the SMAP L4 name we tried), for a gridded cut-out **Harmony** (listed for IMERG Late, Final and monthly),
and AppEEARS only for MODIS/VIIRS/SMAP points, where jobs queue for hours. NASA's official **Earthdata MCP
server** (<https://cmr.earthdata.nasa.gov/mcp/v1>, tools `get_collections`, `get_granules`, `get_services`,
`get_variables` ...) only searches the catalogue; it finds these services but downloads nothing.

## NASA signals behind the rotation scores (added 28 Sep 2026)

One command rebuilds them from the cache: `python research/run_analyses.py` (after `acquire/gldas_da.py`, which
pulls GLDAS through Giovanni in about 12 minutes for 70 sites). Each row turns a NASA dataset into something a
rotation choice depends on.

| Script | NASA data | Informs | Result | Output |
|---|---|---|---|---|
| `acquire/gldas_da.py` + `explore/groundwater.py` | GRACE/GRACE-FO mascons; GLDAS-2.2 groundwater with GRACE data assimilation (daily, 25 km, 2003 to Jun 2026) | the water ledger | Bangladesh's water storage falls 0.40 cm a year (p 0.002), the north-west Barind's is 7 cm lower than in 2003-07. Groundwater under Tanore falls 7.4 mm a year (147 mm since 2003-07); it falls significantly in 50 of 64 districts, fastest in Naogaon, Nawabganj, Thakurgaon, Rajshahi and Natore. The haor's is not falling | `pilots/groundwater_trend.csv` |
| `explore/soil_moisture.py` | GLDAS-2.2 root-zone moisture 2003-2025, checked against SMAP L4 (Spearman 0.86-0.96 over 1,008 days) | sowing and relay crops after Aman | the top metre holds about 290 mm at Tanore on 10 November; harvesting nine days earlier keeps 8-16 mm more (median by pilot), small next to the sowing window and heat | `pilots/soil_moisture_rotation.csv` |
| `explore/heat_windows.py` | POWER daily, corrected by month against each pilot's nearest BMD station | the heat score | days at 35 C or more around Boro flowering: about 10 of 15 at Tanore and Batiaghata, 2 at Mithapukur and Dharmapasha. Nights at Aman flowering warm 0.24-0.43 C a decade (significant at every pilot for BRRI dhan71). Wheat sown on 10 December meets two to three times the hot days of wheat sown on 20 November. Mithapukur's April correction is large (+4.9 C against Rangpur) | `pilots/heat_windows.csv`, `heat_trends.csv` |
| `explore/flash_flood_hindcast.py` | IMERG Final at Sohra (Meghalaya), Sunamganj and Dharmapasha, with FFWC's flood years | the haor flood trigger and the Boro variety | 200 mm or more in 3 days at Sohra (15 Mar-15 May) flags 2004, 2010 and 2017 and no labelled no-flood year (8 of 25 springs), and misses the small late floods of 2018-19. At 250 mm, BRRI dhan28 was still in the field for 4 of 5 bursts, BRRI dhan88, 81 and 89 for 1 (2017), and for none when sown two weeks early | `floods/flash_flood_hindcast.csv`, `flash_flood_thresholds.csv`, `boro_flood_escape.csv` |
| `explore/field_cycles.py` | MODIS MOD13Q1 NDVI (9 x 9 pixels) | what the fields do; targeting and the soil ledger | crops a year, 2001-05 to 2020-24: Tanore 1.8 to 2.8, Batiaghata 2.0 to 1.6. Winter greenness (15 Jan-15 Mar): Batiaghata 0.33 to 0.44, still mostly fallow; Tanore 0.53 to 0.82 | `pilots/field_cycles.csv` |
| `explore/cattle_heat.py` | POWER hourly 2023-2025 | the cows inside the rotation | from June to September no night cools below THI 72 at any pilot; 60-76% of hours fall in the danger band for crossbred cows; the coolest hours are 02:00-05:00 | `pilots/cattle_heat.csv` |
| `explore/productivity_check.py` | SMAP L4 carbon: GPP and soil organic carbon, 2015-2025 | checking the replay; the soil ledger | does **not** confirm the replay's dry-at-flowering seasons at Tanore (rho +0.26, n 11): Barind farmers likely irrigate, so the ledger counts rescue water as a cost, not a lost crop. Wetter monsoons cut Aman productivity (rho -0.56 across pilots). Soil carbon 4,320 g/m2 (Batiaghata) to 5,389 (Dharmapasha) | `pilots/productivity_check.csv`, `soil_carbon.csv` |
| `explore/environment_ledger.py` | all of the above | the ledger per rotation | Tanore: BRRI dhan49 then Boro pumps 7,975 m3/ha a winter, keeps rice flooded 182 days and takes 595 kg/ha of urea; BRRI dhan71 then lentil 1,995 m3/ha, 80 days, 283 kg/ha and a legume; BRRI dhan71 then mustard 1,140 m3/ha | `pilots/environment_ledger_tanore.csv` |

Not used yet, because they need new downloads or methods: HLS 30 m field maps, Sentinel-1, OPERA and NISAR radar,
ECOSTRESS and land-surface temperature, FIRMS fires and NASA's GEOS-S2S seasonal outlooks. The SMAP L4 archive
(NSIDC) is not in Giovanni, so its long record needs AppEEARS or Harmony; GLDAS stands in for it here.

## What needs a free Earthdata Login

Status 27 Sep 2026: all downloaded. MODIS ET/PET (`--preset et`, 5 sites × 1,196 composites, 2000-2025),
GRACE-FO, **SMAP L4** (`--preset l4`, 5 sites × 8,736 three-hourly steps, 27 Sep 2023 - 22 Sep 2026; daily means
in `data/appeears/l4/smap_l4_daily.parquet`) and the **`core` job** (`data/appeears/core/`): SMAP L3 enhanced
soil moisture 1 Apr 2015 - 23 Sep 2026, SMAP L4 carbon (GPP, soil organic carbon) 1 Apr 2015 - 21 Sep 2026,
VIIRS NOAA-20 NDVI 2018 - 6 Sep 2026, all at the 5 pilots.

**Core job checks:** VIIRS NDVI (pixel reliability 0-3, 1,425 of 2,000 composites) tracks MODIS NDVI on the same
dates, r = 0.80 overall (0.53-0.87 by site) with a median offset within ±0.04, so it can take over when MODIS
ends. SMAP L4 GPP is complete and shows the two rice seasons (peaks Mar-May for Boro and Sep-Oct for Aman,
lows in Dec-Jan and at Aman transplanting in July). SMAP L3 soil moisture is noisy here: a retrieval on 41% of
days, "recommended quality" on only 13% (open water and dense crops in the 9 km pixel), wetter than L4 (median
0.31-0.38 vs 0.18-0.32) and correlating 0.34-0.79 with it. Use L4 as the soil-moisture signal; L3 only as an
independent cross-check.

**National jobs, submitted 27 Sep 2026 01:10, not waited for:** `--preset ndvi_national --sites adm3_centroids`
(MODIS 2000- and VIIRS 2018- NDVI at all 544 upazila centroids, task `51baeb90-b315-4bdc-b28f-6ffab21daf32`) and
`--preset l4_national --sites districts` (SMAP L4 surface and root-zone soil moisture for the last year at the
64 district centroids, task `11a5220e-608b-47d6-a10a-07a163cc333c`). After 10.5 hours NDVI was at 18% of its
download step and L4 had sat at 74% for 5 hours (AppEEARS opens every file that covers the points: 26 years of
16-day tiles from two sensors, 2,920 global three-hourly SMAP files), so the watchers were stopped; the tasks stay on AppEEARS and
`--resume <task_id>` fetches them if they finish. One pixel per centroid, so they were only context layers for
maps: the pilots already have their NDVI and SMAP series, and the district and upazila context comes from the
BBS and BRRI tables.

**SMAP L4 checks:** root-zone moisture 0.13-0.55 m³/m³; correlates 0.85-0.92 with POWER's MERRA-2 root-zone
wetness at all five sites; rises ~0.01-0.02 m³/m³ the day after >20 mm of IMERG rain; driest in April, wettest
Aug-Oct. **Do not use the `sm_rootzone_pctl` field as delivered:** it is missing on a third of days and its median
over 2023-2026 is 13.5, not ~50, so it is not a simple climatological percentile. Compute percentiles ourselves
from `sm_rootzone` (or from POWER GWETROOT, which goes back to 1981).

**MODIS ET caveat:** at Tanore it reads only ~1-1.5 mm/day in the Boro months, far below irrigated rice. The
model does not see irrigation, so use FAO-56 Kc × ET0 (from POWER weather) for crop water need, and MODIS ET
only as regional context.

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
| **Station rain, Jun-Sep 2026** (needed) | BMD monthly rainfall for Rajshahi, Ishurdi or Bogura, Rangpur, Khulna, Sylhet or Sunamganj: BMD's monthly bulletins, BAMIS, or the [BMD data portal](https://dataportal.bmd.gov.bd/web/) (sells the last 3 months); BMD's reports stopped reaching NOAA on 24 Aug 2025 | the satellite and model estimates disagree on whether this monsoon was dry (`pilots/rain_vs_normal.csv`); gauges decide it and calibrate the Late run |
| Cropping patterns by district | BRRI: Nasim et al. 2017, *Distribution of crops and cropping patterns in Bangladesh*, Bangladesh Rice Journal 21(2) | the candidate-rotation library |
| Crop traits | done: FAO-56, BRRI and BARI tables above (`crops/crop_parameters.csv` does not yet use the BARI production tables) | the rotation engine's crop table |
| Soil and salinity | SRDI upazila land and soil guides (soil test values, land-type areas) and salinity data; BARC Fertilizer Recommendation Guide 2018 (the SRDI atlas classes, the land-type proxy and the SRDI fertilizer cards for the pilot unions stand in) | field-level soil information |
| District farm-gate prices over time | DAM district offices or growers' price records (DAM's web reports are empty; we have national monthly and harvest prices from the yearbook and retail prices by district from WFP) | income side of the rotation score |
| Daily river levels, 2022-2026 flood dates | BWDB Flood Forecasting and Warning Centre (formal request; the public API is locked). 2010-2021 flood statistics and haor flash-flood years are in `floods/` from the annual reports | hindcast the flash-flood trigger (7 labelled years so far: 2010, 2014, 2017-2021) |
| Groundwater levels, Barind | BWDB groundwater wells (registration, paid) or BMDA | local proof of the falling water table (GRACE-FO is ~300 km) |
| Farmer priorities | 5-10 farmers and 1 SAAO per pilot | the fourth input the challenge names |

## First look (run `python explore/first_look.py`)

Exploratory only: one grid cell per site. `python explore/station_check.py` compares each pilot site
with its nearest BMD station (GSOD copy) on the same days, 2011 → Aug 2025.

* **IMERG rain agrees with the gauges.** Monthly totals are within about 10% of the nearest gauge
  (IMERG/gauge 0.93–1.11) with correlations of 0.93–0.96, over 87–91 complete months per site. The haor
  site reads 1.65× its nearest gauge, but that gauge is 60 km away in drier Mymensingh.
* **Confirmed with BMD's official monthly figures for 2023-2025** (yearbook Chapter 6, `bbs/bmd_monthly.csv`):
  IMERG monthly rain vs the Rajshahi, Khulna and Rangpur gauges correlates 0.87-0.95, reading 11-18% high over
  May-October; POWER's April Tmax is 1.6-2.8 °C hot while its annual mean bias is within ±0.7 °C.
* **POWER Tmax needs a seasonal correction.** Same-day comparison: in April POWER runs +1.8 °C (Tanore),
  +1.9 (Batiaghata), +2.0 (Ullahpara) and +3.8 (Mithapukur) hotter than the station; in July it runs
  1.2–1.6 °C cooler. Against the 1991–2020 BMD normals the April gap at Tanore looks like +3.2 °C, because
  POWER's April Tmax also varies by decade (40.1 °C in the 1990s, 37.7 in the 2010s). Correct month by
  month over overlapping recent years, and use station data, not POWER, for any "it is getting hotter" claim.
  Crop heat thresholds (e.g. 35 °C at rice flowering) cannot be applied to raw POWER values.
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
