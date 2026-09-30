# Project EDEN — Earth Data & Environment Navigator

NASA Space Apps Challenge 2026 · Team WinR

EDEN is a Bangla-first crop-rotation decision-support app. The target architecture keeps the SAAO desktop dashboard and farmer Android app in one repository, using a shared API and one authoritative crop-rotation engine. Research scripts and curated datasets stay alongside the product so recommendations can be traced to their evidence.

## Architecture and repository structure

This is the target structure for product code. Keep the desktop web app, native Android app, API, shared logic, research, and design assets in this repository; do not create a separate app repository.

```text
apps/
  saao-dashboard/       SAAO officers' desktop web app
  farmer-mobile/        Native Kotlin + Jetpack Compose app; Android APK target

services/
  api/                  API used by both the web and mobile apps

packages/
  contracts/            Shared request, response, and domain types
  rotation-engine/      Deterministic crop-rotation scoring and replay
  narration-core/       Advice narration and validation

research/               Data sources, acquisition scripts, and curated datasets
design/                 Stitch screens, previews, and design notes
```

The Node/TypeScript apps, services, and packages use npm workspaces. The Android app is a native Gradle/Kotlin module under `apps/farmer-mobile/`; it is not an npm package. Keep Android dependencies and build configuration in that module.

### Implementation status

The default `main` branch contains the research/data-source work and this architecture overview. The `codex/android-apk` branch contains the first prototype of the native farmer app, the SAAO dashboard, API, and shared TypeScript packages. The `demo/research-data` branch builds on it with the changes listed under [What changed on `demo/research-data`](#what-changed-on-demoresearch-data). Neither is merged into `main`. Treat the app and dashboard as a demo for the Talanda (Tanore) pilot only. The rotation numbers, dates, fertilizer doses and satellite conditions come from the research data release described below; farmer rows, the farm profile and the income scores are sample values, labelled as such on screen. Review [`apps/farmer-mobile/README.md`](apps/farmer-mobile/README.md) for the app's screens, build steps, and known integration gaps.

## Run the demo

```bash
npm install
npm test          # 10 engine tests + API, officer-desk and translation checks
npm start         # API and SAAO dashboard on http://localhost:4000
```

- **Language:** the বাংলা / EN buttons in the header switch the whole dashboard; the choice is remembered in the browser.
- **Krishi officer desk:** tab ৬ / 6. The demo access code is `talanda-demo` (set `EDEN_OFFICER_CODE` to change it). This is a demo gate, not real authentication. **Restore sample data** on the desk resets the sample farmers before a recording.
- **Android app:** see [`apps/farmer-mobile/README.md`](apps/farmer-mobile/README.md); the emulator reaches the API at `http://10.0.2.2:4000`.

A two-minute walkthrough for a demo video:

1. **Overview (১):** dated NASA values (SMAP root zone, 30-day IMERG rain checked against MERRA-2, GRACE-based groundwater trend, MODIS winter greenness), the late-Aman alert and field pest reports.
2. **Planner (২):** set "Aman in the field this season" to BRRI dhan49 and run. The planner says lentil and mustard miss their 14–15 Nov deadlines, and tags dhan49 → wheat as possible this season.
3. **Comparison (৩):** seven scored dimensions, each with its reason and a `sample` / `assumed` tag where the data is weak.
4. **Less pesticide (৫):** the recommended rotation against the usual Boro rotation: rice-pest cycle broken, 52% less urea, and sourced IPM steps.
5. **Officer desk (৬):** sign in, open the most urgent farmer, record a field observation (for example a pest), and watch that farmer's advice, queue position and the overview pest card update.
6. **Call delivery (৮):** press keypad 1 (water) and see mustard move to the top; press 9 and the call-back request lands on the officer desk.
7. Switch to **EN** at any point; the Bangla voice script gets an English translation underneath.

## What changed on `demo/research-data`

Changes made for the demo submission (September 2026), in three rounds.

### Round 1: numbers from the research, bugs fixed, app connected

| Area | Change | Files |
|---|---|---|
| One source of numbers | The engine's data file is **generated** from the WinR research tables by `research/export/eden_release.py` (research repo). Every screen reads it, and nothing is retyped by hand. | `packages/rotation-engine/src/data/tanore_replay_data.ts` (generated), `release_types.ts` |
| Corrected values | dhan71 needed rescue irrigation in 7 of 25 seasons (was 6), dhan87 in 6 (was 7); dhan87 frees the field on 6 Nov (was 15 Nov); Boro irrigation is 797 mm (was 745); late wheat 234 mm with 27 of 30 hot days (was 275 mm, 28); fertilizer comes from the SRDI Talanda card (lentil urea 54.3, not 45 kg/ha); SMAP on 10 Nov is 0.33 m³/m³ (not 0.24). | same |
| Boro scored as lentil (bug) | The plugins looked up `'BRRI dhan28'`, but the data key was `'BRRI dhan28 (Boro)'`, so every lookup fell back to lentil and the dashboard said Boro needs "198 mm". Crops now carry an explicit `season`, and the lookups throw instead of falling back. | `packages/contracts`, `data/lookup.ts`, all plugins |
| Weighting | Scores the farmer did not prioritise now weigh 0.05, so keypad 1 (water) really puts the lowest-water rotation first. | `engine.ts` |
| Unmodelled unions | A union without research data gets HTTP 422 instead of Talanda's advice under another name. | `engine.ts`, `server.ts` |
| Candidates | Five rotations: dhan71 → lentil, dhan71 → mustard, dhan49 → Boro (current practice), dhan49 → wheat on 20 Nov, dhan75 → wheat on 10 Dec. Their dates, timelines and actions come from the replay. | `engine.ts` |
| This season | Given the Aman already in the field, the engine reports which Rabi crops still meet their BARI/BWMRI deadlines (`this_season`) and the best rotation that starts from it (`this_season_option_id`). | `engine.ts` |
| Spoken script | Correct Bangla ("তালন্দ ইউনিয়নের", "১০ নভেম্বরের মধ্যে", Bangla digits, Bangla crop names); every number is read from the advice and checked by the dual gate. | `narration-core` |
| Honest labels | Removed the "LIVE FEED" badge, the 342 "active farmers", a named sample farmer, an invented SRDI card ID and NASADEM claims; soil is খিয়ার মাটি (SRDI card) everywhere; income is marked as a sample estimate; flood is marked "not modelled". | dashboard, plugins |
| Android app | It syncs the server's `farmer_card` on opening, keeps its cached advice when offline, and its seed shows dhan71 → lentil; the fake status bar is removed and screen texts come from the advice. | `apps/farmer-mobile` |

### Round 2: English, the Krishi officer desk, less pesticide

**Bangla / English toggle (dashboard).**

- Every static text has a `data-i18n` key. The Bangla stays in `index.html` and the English is in `apps/saao-dashboard/public/i18n.js`.
- Dynamic text is built in `app.js` with `tr(bangla, english)`. The engine and API now return English versions of actions, timelines, the "this season" note, alerts and the farmer summary.
- The farmer always hears Bangla. In EN mode the delivery screen adds an English translation of the script (`englishGloss`).
- `npm test` fails if any `data-i18n` key lacks an English string.

**Krishi officer desk (dashboard + API).** This is a separate channel between farmers and their SAAO:

- **Priority for the officer's knowledge:** an officer's field observation describes the farmer's land (land type, the Aman in the field, irrigation, pests seen, the farmer's priorities, a note). It takes priority over defaults whenever that farmer's advice is built, and the advice is marked `verification` (officer-verified).
- **Priority queue:** farmers are ranked by need, with the reasons in both languages. The rules are: a keypad-9 call-back request (+3); lentil and mustard both miss their deadline this season (+2); no Rabi crop fits on time (+1); a pest seen (+1, or +2 if severe); not yet checked in the field (+1).
- **Extra access:** after sign-in, officers get the call-back queue, the farmer register, the observation form and a reference pack farmers don't see. The pack holds the full SRDI card (gypsum, zinc, boric acid), the 25-season replay with rescue years, Rabi windows and heat exposure, data caveats and technical notes.
- **Farmer side:** pressing 9 in the IVR (or "call-back" in the companion mock-up) creates a call-back request on the desk.
- **Safety:** officer notes pass the same banned-word filter as farmer messages (no loans, no pesticide brands).
- **Storage:** sample farmers, observations and call-backs are kept in `services/api/.data/officer_store.json` (git-ignored). Tests use a throwaway file (`EDEN_OFFICER_STORE`).

**Less pesticide through rotation (IPM).** A seventh scoring plugin and a dashboard tab:

- `plugins/pest.ts` scores pest pressure from four transparent rules:
  - Host break: a non-rice Rabi crop breaks the rice-pest cycle; Boro after Aman keeps it going.
  - Nitrogen load: the SRDI urea total for the rotation.
  - Resistant varieties from the research tables: BWMRI lists BARI Gom 33 as blast and rust resistant.
  - Late sowing: sowing past the handbook deadline counts against the rotation.
- Confidence is `low` and the data is `assumed`, because there are no field pest counts yet. Officers' pest observations are the start of that data.
- `data/ipm_catalog.ts` holds IPM steps in Bangla and English, each with its source. They are non-chemical first, and no pesticide product is ever named.
- The **কম কীটনাশক (IPM)** tab compares the recommended rotation with the Boro baseline (lentil 90/100 vs Boro 31/100, 52% less urea), lists the IPM steps, ranks all rotations, shows officers' pest reports and gives spray-safety advice.
- Farmers can ask for this with keypad 4 ("কম কীটনাশক"); the dashboard has a matching priority slider.
- The app side of the officer desk and IPM is planned for later; the API already serves both.

### Round 3: more of the NASA data at work (early warnings, environment ledger)

The research release already held NASA results that the app did not use. Four of them now reach the dashboard, and all come from the same generated data file.

| Feature | What the officer sees | NASA data and method | Files |
|---|---|---|---|
| Haor flash-flood warning (Dharmapasha pilot) | New **early warnings** row on the overview. From 15 Mar to 15 May, 200 mm of rain in 3 days at Sohra (Cherrapunji, Meghalaya) raises a watch and 250 mm a warning; river gauges must confirm before any call goes out. A chart shows the largest 3-day spring rain for 2001–2025, coloured by FFWC flood years. Off season, the card shows when the trigger re-arms. | GPM IMERG daily rain at Sohra, checked against 25 springs of FFWC flood reports: the 200 mm rule caught 3 of 5 flood years (2004, 2010, 2017) with no false alarm in 3 no-flood years, and missed the small late floods of 2018–19. Eight labelled years test the thresholds; they do not calibrate a warning. A 250 mm burst caught BRRI dhan28 before harvest in 4 of 5 cases; BRRI dhan88, 81, 29, 89 and 92 in at most 1 of 5, and none when sown two weeks early. | `server.ts` (`earlyWarnings`, `haorStatus`), `app.js` (`renderWarnings`) |
| Warmer nights at Aman flowering | Card for officers: early Aman saves water but flowers into warmer nights, so watch for empty grains. | NASA POWER, corrected against BMD stations; Theil-Sen trend with a Kendall test. BRRI dhan71 flowering nights: +0.29 °C a decade (p 0.015); dhan49: +0.15 °C (not significant). Good news: hot days at grain filling for wheat sown on 20 Nov fell by 4.3 a decade. The heat plugin adds a caution when the trend is significant; the score does not change. | `plugins/heat.ts`, `server.ts`, `app.js` |
| Cattle heat stress (Tanore) | Card with a monthly chart: June to September have no night relief (THI stays above 72); in July 96% of hours are in the danger bands; the coolest hours are 02:00–05:00. | NASA POWER hourly temperature and humidity (2023–2025), temperature-humidity index (NRC 1971). | `server.ts`, `app.js` |
| Environment ledger | Table in the renamed **পরিবেশ ও কম কীটনাশক (Environment & less pesticide)** tab: groundwater pumped, flooded-rice days (a methane proxy, not a measurement), urea, legume or not, bare-soil days and the pest score for every rotation. Boro pumps 7,975 m³/ha; dhan71 → lentil 1,995. | Water from the 25-season POWER + IMERG replay; urea from the SRDI Talanda card. The engine rebuilds the research ledger exactly (TEST 11). | `engine.ts` (`ledger` on each option), `app.js` (`renderLedger`) |
| Soil carbon and a productivity check | Evidence tab: SMAP L4 soil organic carbon about 4,684 g/m² (2016–2025, +76 a year). The Aman productivity (GPP) did not drop in dry seasons (rho 0.26, 11 seasons), because farmers irrigate; so rescue water is counted as a cost, not a lost crop. | SMAP L4 carbon (SPL4CMDL). | `server.ts` (`soil_carbon`), `app.js` |

The generator (`research/export/eden_release.py`) now also writes `TANORE_ADVISORIES`, `HAOR_FLASH_FLOOD`, `TANORE_SOIL_CARBON` and `TANORE_LEDGER_RESEARCH`, plus `fieldDays` and `pumpedM3PerHa` on the replay records. The officer reference pack adds the cattle-heat months and the haor hindcast.

### API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/v1/overview` | Dated research conditions, alert, sample farmer rows (with this-season/next-season rotations), union-level pest reports |
| POST | `/api/v1/advice` | Ranked rotations; body `farmerId` applies that farmer's officer observation; `currentAmanCrop` adds the this-season check; 422 for unmodelled unions |
| POST | `/api/v1/narrate` | Checked Bangla script (+ `englishGloss`) for one option |
| POST | `/api/v1/channel-events` | Simulated IVR keypad: 1–4 re-rank by priority, 9 creates an officer call-back |
| GET | `/api/v1/data-release` | Datasets, periods, calibration and status (one pending: farm-gate prices) |
| GET | `/api/v1/officers` | Officers who can sign in (no secrets) |
| POST | `/api/v1/officer/login` | `{ officerId, accessCode }` → session token |
| GET | `/api/v1/officer/desk` | Queue, farmer register, observations, call-backs (Bearer token) |
| POST | `/api/v1/officer/observations` | Save a field observation; returns the farmer's updated advice |
| POST | `/api/v1/officer/callbacks/:id/resolve` | Mark a call-back done |
| GET | `/api/v1/officer/knowledge` | Officer reference pack |
| POST | `/api/v1/officer/reset` | Restore the sample farmers (demo) |
| GET | `/api/v1/haor/flash-flood` | Haor flash-flood trigger: the Sohra thresholds, the 25-season hindcast, variety escape and today's status |

`/api/v1/overview` also returns `early_warnings` (haor, warm nights, cattle heat) and `soil_carbon`.

### Tests

`npm test` runs `test_pipeline.ts` (engine) and `test_server.js` (API). They check:

- the ranking, feature flags and narration gates (a fake AI that invents "১২ টন" and a loan offer falls back to the template);
- that Boro is scored with Boro data, and that unmodelled unions are refused;
- that a stated priority leads the ranking;
- that the Android seed matches the engine;
- the pest score and the English fields;
- that the environment ledger matches the research ledger (TEST 11);
- that the overview carries the early warnings and the haor endpoint serves all 25 seasons;
- officer sign-in (including a wrong code), queue order, that an observation takes priority, the note filter, keypad-9 call-backs and the reference pack;
- that every dashboard text has an English translation.

The Android unit tests run with `./gradlew test` in `apps/farmer-mobile`.

### How to…

- **Add or change a dashboard text:** write the Bangla in `index.html` with a new `data-i18n="section.key"`, then add the English under the same key in `i18n.js`. The test lists anything missing.
- **Update the numbers:** re-run the generator (below), then `npm test`. If TEST 9 fails, refresh the Android seed (`AdviceModels.kt`) from the engine's `farmer_card`.
- **Add a scoring dimension:** write a plugin in `packages/rotation-engine/src/plugins/`, register it in `registry.ts`, add its name to `DIMENSIONS` in `app.js`, and add a bar colour in `styles.css`.
- **Change the officer access code:** set `EDEN_OFFICER_CODE` before `npm start`.

### Known limits

- Only the Talanda pilot is modelled; other unions return 422.
- Income is a team estimate until DAM farm-gate prices and farmer cost interviews are in.
- The pest score is rule-based until officers log pest counts.
- Floods are not modelled for Barind land.
- The haor warning shows the 25-season hindcast and the season status; a live trigger needs a daily IMERG Early feed (planned). Rotation advice is not modelled for the haor.
- Flooded-rice days stand in for methane; they are not a methane measurement.
- The officer sign-in is a shared demo code with in-memory sessions and a JSON file store; a real deployment needs proper accounts and a database.
- The Android app does not yet show the officer verification or the IPM steps; its API address works in the emulator only.

### Research data release

`packages/rotation-engine/src/data/tanore_replay_data.ts` is generated from the WinR research tables (25-season NASA POWER + IMERG replay, BMD-corrected heat windows, SRDI Talanda card, BRRI/BARI/BWMRI sowing windows, SMAP L4, GLDAS-2.2, MODIS, BBS, GLW4). Do not edit it by hand; from the research repository run:

```bash
python research/export/eden_release.py --out <project-eden>/packages/rotation-engine/src/data/tanore_replay_data.ts
```

Labels and the illustrative income figures live in `packages/rotation-engine/src/data/crop_catalog.ts`. `npm test` checks that the Boro baseline uses its own data, that unions without data are refused, and that the Android offline seed (`AdviceModels.kt`) matches the engine's advice.

### Where new code and data go

- Put SAAO dashboard UI and browser behavior in `apps/saao-dashboard/`.
- Put farmer-facing Android UI, navigation, and device-specific behavior in `apps/farmer-mobile/`, using Kotlin and Jetpack Compose. Keep screen state in ViewModels and expose immutable UI state to Compose.
- Make the Android app offline-first: use a local Room database as the read source for cached advice and farm data, show when that data was last updated, and sync changes only when connectivity permits. Use persistent background work only for sync that must survive app restarts. Do not imply live data when the app is offline.
- Put HTTP endpoints and server-side orchestration in `services/api/`. Both apps should use this API rather than duplicating backend behavior.
- Put shared request/response types in `packages/contracts/`.
- Keep crop scoring and historical replay deterministic in `packages/rotation-engine/`. Do not move scoring rules into either app or an LLM prompt.
- Keep generated advice wording and its validation in `packages/narration-core/`.
- Put data acquisition and analysis scripts, source notes, provenance, and small curated datasets in `research/`. The downloaded/generated cache under `research/data/` is ignored by Git; regenerate it with the scripts in `research/acquire/`.
- Put Stitch exports, screen previews, and design documentation in `design/`. These are design references; production UI code belongs in the relevant app.

Do not commit secrets, local environment files, dependency folders, generated APK/AAB files, or real farmer personal information. Add run/build commands to this README when the corresponding app modules are committed.

## Team

- muhammadTasin
- Anindya Shiddhartha
- Jarin Subah
- Mohammed Rayyanul Haque
- Safin Rahman
- Tasrif Ahmed
