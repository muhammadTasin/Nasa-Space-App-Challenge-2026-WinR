# EDEN Farmer Android App

Native Android prototype for farmers, built with Kotlin, Jetpack Compose, Material 3, and Room. The latest Android work is on `codex/android-app-latest`; it has not been merged into `main`.

## Current scope

The prototype has four bottom-navigation tabs and one nested detail screen:

| Screen | What it demonstrates |
|---|---|
| **আজ — Today's advice** | Current rotation card, plot context, freshness/offline banner, and Bangla text-to-speech control |
| **পরিকল্পনা — Crop plan** | Crop-season timeline, alternative crop, and navigation to rotation details |
| **আগের পরামর্শ — Advice history** | Locally stored advice cards and replay controls |
| **আমার খামার — My farm** | Pilot farm profile, land/soil details, priorities, and consent presentation |
| **ফসল চক্রের বিস্তারিত — Rotation detail** | Sowing/harvest guidance, evidence notes, missing-value labels, and a demo confirmation action |

The source for screens and their ViewModels is under `app/src/main/java/org/projecteden/farmermobile/ui/`. Navigation is in `Navigation.kt`; shared screen data models are in `data/model/`.

## App architecture

```text
Compose screens
    ↓ events / StateFlow
Screen ViewModels
    ↓
FarmerRepository ───── EdenApiClient ───── services/api (HTTP :4000)
    ↓                                      GET /api/v1/overview
Room database                              POST /api/v1/advice
    ↑
Seeded prototype profile, advice, and history

BanglaTtsManager → Android system TextToSpeech
```

- **Presentation:** Compose screens collect screen state from ViewModels. Navigation keeps the four tabs in one scaffold and opens rotation detail as a separate destination.
- **Local data:** `EdenDatabase` and `FarmDao` store the farm profile, current advice, and advice history. The UI observes Room flows, so the cached advice is available without a network connection. The first-run seed in `AdviceModels.kt` mirrors the engine's farmer card; `npm test` (TEST 9) fails if they drift.
- **Remote data:** `EdenApiClient` uses Android's `HttpURLConnection` to call the shared Node API. The client defines overview and advice requests; farmer profile and advice history have no server endpoints yet.
- **Voice:** `BanglaTtsManager` uses the device's Bengali system TTS when available. If Bengali voice data is missing, it reports that state instead of playing fabricated audio. The progress display is an estimate based on a timer.
- **Recommendation ownership:** crop scoring remains in `packages/rotation-engine/` on the server side; the Android client does not implement scoring.

## Data and integration status

This branch is a reviewable demo, not a field-ready advice service. Treat the displayed farm, crop, dates, metrics, counts, provenance, and dashboard contacts as sample/pilot demonstration values until each is checked against its cited source and a real data release. Do not use the prototype as agricultural guidance.

Known gaps in this version:

- Room starts with seeded sample profile/advice/history. Farm profile edits and confirmed plans are saved on-device; the profile and confirmation do not sync to a server.
- The Today screen syncs when it opens and has a manual refresh action. `FarmerRepository.refreshAdvice()` maps the server's `farmer_card` into Room, and on failure keeps the cached advice and its last sync time. There is no background sync worker yet.
- Profile and history are local only; there are no `/api/v1/farmer-profile` or `/api/v1/advice-history` endpoints.
- The API already serves officer-verified advice (`POST /api/v1/advice` with `farmerId`), the IPM steps (`options[].ipmActions`) and English text, but the app does not show them yet; that is the next app step.
- There is no durable background sync worker, account/authentication flow, or production API configuration yet.
- The API address is currently `http://10.0.2.2:4000`, which is the Android emulator's route to the development host. A physical-device or deployed build needs an appropriate configurable API URL. Cleartext HTTP is enabled for local development and must be replaced with HTTPS before deployment.
- The debug APK is a build output and is ignored by Git. Share the APK separately if a tester needs to install it.
- Screen navigation, advice refresh, audio, profile saves, plan confirmations, and history playback emit privacy-safe event tags under `EDEN_APP` in Logcat. They do not log farm field values.

## Run locally

Start the API and dashboard from the repository root:

```bash
npm install
npm start
```

In a second terminal, build the Android app:

```bash
cd apps/farmer-mobile
./gradlew assembleDebug
```

The debug APK is written to `apps/farmer-mobile/app/build/outputs/apk/debug/app-debug.apk`. To install it on a connected Android device or emulator with ADB:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Run the existing local unit tests with:

```bash
./gradlew test
```

The app uses Gradle independently from the repository's npm workspaces. `local.properties`, Gradle caches, build outputs, APKs, and AABs should stay out of commits.
