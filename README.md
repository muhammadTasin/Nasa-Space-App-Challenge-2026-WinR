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

The committed branch currently contains the research and design work. The architecture above describes where product modules belong; the native Android app has not been implemented yet. Check the active branch and working tree before changing files, and preserve any existing uncommitted work.

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
