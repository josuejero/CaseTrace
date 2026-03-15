# Acquisition Placeholder

Later phases will add the repeatable acquisition workflow for the emulator case.

Locked Phase 0 acquisition assumptions:

- source path: `/data/user/0/com.casetrace.waypoint/`
- method: `adb exec-out run-as com.casetrace.waypoint tar -cf - .`
- device target: `pixel7-api34-emulator`
- ADB serial: `emulator-5554`

Planned responsibilities:

- acquire the synthetic app directory without modification
- package the case bundle under `cases/CT-2026-001/`
- produce `hash_manifest.json`

