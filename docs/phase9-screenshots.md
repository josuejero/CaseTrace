# Phase 9 Screenshots

Collecting polished screenshots is part of the recruiter signal. Capture six panels (overview, timeline, artifacts, entity graph, search, report) after the backend and frontend are running.

1. Start the backend and frontend as described in `docs/phase9-investigator-ui.md`.
2. Open each tab and let the data settle (chips show hit counts, graph renders, report frame loads).
3. Use your preferred macOS/Windows shortcut (e.g., `Cmd+Shift+4` or `Win+Shift+S`) or `npx playwright screenshot http://localhost:5173 --path docs/screenshots/phase9/<name>.png` to grab a clean frame.
4. Name files to match the tab (`overview.png`, `timeline.png`, etc.) and drop them under `docs/screenshots/phase9/`.
5. Mention the screenshot locations in your portfolio readme so maintainers know where to find them.
