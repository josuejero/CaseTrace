# Synthetic Evidence Rules

CaseTrace uses synthetic evidence only. These rules prevent the project from drifting into realistic-looking but undocumented personal data.

## Identity and Contact Rules

- Use only synthetic human names created for the project.
- Do not use names of real coworkers, classmates, family members, or known public figures.
- Use only reserved or fictional phone numbers in the North American `555-01xx` range.
- Normalize people to canonical display names in parsed artifacts.

## Domain and Web Rules

- Use only reserved or test domains such as `.example`, `.test`, `.invalid`, `example.com`, `example.org`, or `localhost`.
- Do not include real business URLs, personal websites, or live tracking links.
- Browser content summaries may describe realistic actions, but the linked hostnames must remain synthetic.

## Location Rules

- Coordinates must describe synthetic public or commercial-style places such as transit halls, cafes, garages, hotels, markets, or terminals.
- Do not represent residences, apartment units, offices, classrooms, or workplaces.
- Labels should be generic and non-identifying even if the coordinates are urban and plausible.

## Media Rules

- Do not use real personal photos.
- Use placeholders or generated media only.
- Photo artifacts may carry synthetic EXIF-style metadata in later phases, but the media files in Phase 0 are placeholders.

## Deleted Data Rules

- Deleted evidence may originate only from seeded SQLite WAL content.
- Recovered deleted records must use the `recovered_record` artifact class.
- Recovered records must carry lower confidence than intact records and must be explicitly marked with `deleted_flag: true`.

## Documentation and Traceability Rules

- Every parsed record must be traceable to `raw_ref`.
- Every report statement must be defensible from normalized records that already resolve to a raw source.
- Any future parser heuristic that cannot resolve to a raw source stays out of the formal report.

## What Is Explicitly Out of Scope

- Real devices, real app backups, or real user media
- Real phone numbers, private addresses, or workplace-specific coordinates
- Cloud evidence, carrier records, or network packet capture in v1
- Recovery claims beyond the seeded app database and its seeded WAL files

