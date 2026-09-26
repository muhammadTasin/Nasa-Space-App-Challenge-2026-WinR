# BBS Yearbook of Agricultural Statistics 2025: extracted tables

Source: Bangladesh Bureau of Statistics, *Yearbook of Agricultural Statistics of Bangladesh 2025* (June 2026).
Listed at <https://bbs.gov.bd/pages/static-pages/6922e0d6933eb65569e28cbf>; PDF:
<https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-bbs/2026/5/cfb80ec8-1c7f-4632-8a59-7649b6ac7ffe.pdf>

Rebuild with `python research/explore/bbs_yearbook.py` (downloads nothing; expects the PDF in `research/data/bbs/`).
`page` columns are PDF pages (printed page number + 15). District names follow `research/sites/districts.csv`.

| File | Book section | Notes |
|---|---|---|
| `crop_district.csv` | Ch. 3, every district table | Major crops (Aus, Aman, Boro, wheat, jute, potato): 2023-24 and 2024-25, area in acres and hectares, yield t/ha. Minor crops: 2022-23 to 2024-25, area in acres and production; yield derived. District sums match the national totals for rice and wheat. 33 Aus-hybrid 2023-24 yields are recomputed (see `note`). Jute production is in bales. |
| `crop_district_tables.csv` | | the book's title and pages for each crop table |
| `crop_calendar.csv` | 1.8 | sowing/transplanting and harvest windows, seed rate |
| `census_costs.csv` | 8.2-8.6 (Agriculture Census 2019) | per acre: yield (t), cost, crop value, by-product value; net return computed |
| `harvest_prices.csv` | 10.5.1 (DAM) | harvest-time price, Tk per quintal, 2021-22 to 2024-25; one flagged typo |
| `irrigation.csv` | 7.7 | irrigated area by crop, '000 acres; wrapped rows rebuilt from row sums |
| `intensity.csv` | 5.2.1 | net and gross cropped area; intensity recomputed (the printed column is misaligned) |
| `damage.csv` | 4.2.x | district crop damage for 8 floods and cyclones, 2017-2024; the book repeats some Noakhali 2024 rows under two crops |
| `holdings.csv` | 8.1 (Agriculture Census 2019) | farm holdings by district: small/medium/large, owner/tenant, farm-labour and fisheries households; two typo rows recomputed (`note`); sums to the national total |
| `wages.csv` | 7.5 | daily farm wage (Tk) by district and month, Jan 2024 - Dec 2025, men and women, with 1/2/3 meals or without food (column order inferred from the values: more meals, lower cash wage); 0 printed = not reported |
| `bmd_monthly.csv` | 6.1.2-6.3.3 | BMD station monthly rain, Tmax, Tmin, humidity, 2023-2025 (33-45 stations); rows with an unmarked missing month are skipped |
| `bmd_annual_rain.csv` | 6.1.1 | BMD annual rainfall 2016-2024, 39 stations |
| `crop_district_panel.csv` | all editions 2012-2025 | built by `bbs_panel.py`: rotation crops by district and season, ~2009-10 to 2024-25; the latest edition wins where editions overlap; rice totals missing from the 2015-2018 books are derived from their local/HYV/hybrid tables (`note`) |
