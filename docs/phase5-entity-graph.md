# Phase 5 Entity Graph

The Phase 5 workstream stitches normalized artifacts into an explainable evidence graph. The builder reads `case.db`, treats each actor, phone channel, device, app account, location, photo, URL, keyword, and file as a node, and records eight edge types (`messaged`, `called`, `visited`, `captured_at`, `located_at`, `references`, `stored_in`, `linked_to_case`) so every relationship points back to a concrete `record_id` / `raw_ref`.

## Node taxonomy

- **person** – every actor and counterparty seeded into `entities`.
- **phone number** – call channels that describe who Jordan called and what label the record uses.
- **device** – the acquisition device metadata from `case.json`.
- **app account** – the Waypoint seed account aggregated from the case metadata and mapped back to the subject.
- **location** – cells built from `artifacts_locations` (and photo locations) with lat/long and labels.
- **photo** – a node per photo record that hooks into its capture location.
- **URL** – browser visits emit nodes labeled with the visited url and domain.
- **keyword** – app events are distilled into keyword nodes so analysts can see common triggers and the supporting evidence.
- **file** – every source file path (including `case.json`) becomes a node so downstream views can call out storage provenance.

## Edge taxonomy

- `messaged` – links actors via the parsed message table.
- `called` – connects actors to phone-channel nodes derived from call records.
- `visited` – ties actors to visited URLs.
- `captured_at` – connects photo nodes to their capture locations.
- `located_at` – shows where persons/respective nodes appear via GPS fixes and media.
- `references` – highlights descriptive connections such as keywords pointing at the subject or app account metadata.
- `stored_in` – traces every actor/location/keyword node back to the file that houses it.
- `linked_to_case` – bonds every file node to the case metadata entry so the graph stays anchored to `case.json`.

## Running the builder

```bash
python tools/build_graph.py --case-dir cases/CT-2026-001
```

Output files appear under `cases/CT-2026-001/reports`:

- `graph.html` – PyVis renders the NetworkX graph (nodes grouped by type and edges labeled with their verbs).
- `analysis/graph-data.json` – serialized nodes/edges for downstream views.
- `analysis/entity-detail.html` – a lightweight HTML page that fetches `graph-data.json` and lists every person along with each traced edge’s `record_id` and `raw_ref`.

If the builder cannot find `case.db`, re-run the parser (`python tools/parse_case.py`) first.

## Debug & explorer hints

- Open `reports/graph.html` from a static server (`python -m http.server` inside `cases/CT-2026-001/reports`) so browsers can load the generated JSON/HTML without cross-origin restrictions.
- The detail view groups edges per person so you can cite the raw evidence behind each relationship without hunting through the SQLite tables.
