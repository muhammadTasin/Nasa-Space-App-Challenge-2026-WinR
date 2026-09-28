# Farmer Mobile App

This directory is reserved for EDEN's farmer-facing native Android app.

## Status

The Android application scaffold has not been created yet. Build it with Kotlin and Jetpack Compose; the target deliverable is an Android APK. Use the latest user-designated farmer Android screens, not superseded mobile exports in the design folder.

## Implementation boundaries

- Keep farmer-facing Compose screens, navigation, ViewModels, and device behavior in this directory.
- Call the shared backend in `services/api/` for crop advice and other server data.
- Reuse shared API types from `packages/contracts/`.
- Keep crop scoring in `packages/rotation-engine/`; do not reimplement it in the app.
- Use Room-backed local data as the read source for cached advice and farm data. Always show its last-updated time and a clear stale/offline state.
- Keep API, Room, and presentation responsibilities separate; expose screen state from ViewModels and use lifecycle-aware state collection.
- Keep the first release small and suitable for low-end Android devices. Avoid unnecessary SDKs, background polling, and large image assets.
- Do not commit APK/AAB build files or real farmer personal data.
