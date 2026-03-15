# Raw Files Mirror

This directory mirrors the acquired app path at `/data/user/0/com.casetrace.waypoint/`.

Run `python acquisition/extract_case.py` to refresh this folder. The script recreates the `databases/`, `exports/`, `logs/`, and `media/` subdirectories, streams the app files through `run-as com.casetrace.waypoint tar -cf - .`, and recomputes file integrity metadata. `README.md` stays in place so the documentation survives repeated captures.

The live case bundle contains the latest acquisition, which later phases parse and normalize; do not mutate the raw files directly.
