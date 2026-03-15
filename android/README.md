# CaseTrace Waypoint Seed App

This module contains the Kotlin/Compose seed app (`com.casetrace.waypoint`) that populates deterministic Room/SQLite data for the CT-2026-001 case.

## Building & Testing

The project targets Compose with Room/SQLite and ships its own Gradle project.

1. Install a matching Gradle version (>= 8.0) if you do not already have `gradle` available in your `PATH`.
2. From `/android`, run `gradle :app:assembleDebug` to compile the APK and export the Room schema to `app/schemas/com.casetrace.waypoint/1.0.0-room-schema.json`.
3. Run `gradle :app:test` to exercise the `SeedProfileTest` unit tests, which verify the deterministic counts for `case_alpha`.

> There is no Gradle wrapper shipped in this repo, so the `gradle` CLI must be available on the workstation used for building. You can point `GRADLE_HOME` at your distribution to stick with a known version.

## Running in the Emulator

1. Launch the recommended emulator (`pixel7-api34-emulator`) and install the APK with `adb install -r android/app/build/outputs/apk/debug/app-debug.apk`.
2. Use the `Seed Device` button inside the app to clear Room and reseed every data table, including messages, calls, browser history, photos, and app events. The deterministic `case_alpha` seed is applied with a fixed random salt so the same artifact set is generated every time.
3. Use `Mutate + Delete` to force a WAL-worthy sequence (insert → update → delete). The action touches both the core and web databases while `JournalMode.WRITE_AHEAD_LOGGING` is enabled so the resulting `.db-wal` files contain the deleted rows referenced by the `recovered_record` artifacts.

The UI exposes six screens (Messages, Calls, Browser, Location, Photos, App Activity) inside the bottom navigation bar, and the top app bar surface shows the last seed and mutation timestamps. Snackbars confirm the actions.

## Artifact Extraction

After running the seed + mutate flows, grab the emulator data bundle with:

```bash
adb exec-out run-as com.casetrace.waypoint tar -cf - . > ct-2026-001-emulator.tar
```

Unpack this tarball and copy the following files into `cases/CT-2026-001/files/` so the artifact bundle matches the locked dataset:

- `databases/waypoint_core.db` and `waypoint_core.db-wal`
- `databases/waypoint_web.db` and `waypoint_web.db-wal`
- `exports/location_trace.json`
- `logs/app-events-20260312.jsonl`
- `media/IMG_20260312_*.jpg` (the generated photos with EXIF data)

After replacing the files, regenerate `cases/CT-2026-001/hash_manifest.json` with `python tools/validate_phase0.py` to refresh the SHA-256 entries.

## Screenshots

Sample screens live under `docs/screenshots/phase1/` once captured. Each image shows the UI for a different artifact category (messages, calls, browser, location, photos, app activity). These serve as stand-in documentation for what the seeded data looks like in-app.

## Layered Architecture Notes

- `domain/SeedUseCase` contains the deterministic logic for seeding Room tables, exporting the location trace + JSONL logs, and creating synthetic EXIF-backed photo files.
- `data/local` defines two Room databases with `@TypeConverters`, `JournalMode.WRITE_AHEAD_LOGGING`, and the DAOs the UI observes.
- `ui/viewmodel/MainViewModel` and the Compose screens stay thin; they only observe `Flow`s coming out of the repository and expose actions for the buttons in the top bar.

## Schema Export

Room schema artifacts are exported to `android/app/schemas/com.casetrace.waypoint/1.0.0-room-schema.json` every build. Keep this file in version control so downstream parsers can verify schema compatibility and migration safety.
