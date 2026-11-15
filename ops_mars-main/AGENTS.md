# AGENTS.md

## Project state

- The source archive mentions an initial commit; this extracted copy has no .git metadata. Do not assume a repository exists. There is no CI or task runner; backend tests live in `backend/tests/`.
- `frontend/` has the Mission Control UI and a 2D Mars Explorer map. The map renders real NASA Mars Trek WMTS mosaics (HiRISE and CTX of Jezero) through OpenLayers and the backend. Mission telemetry, targets, risks and events remain simulated.
- `backend/` is a FastAPI app exposing `GET /api/health`, the Mars catalog under `/api/v1/mars/`, and verified/live WMTS capabilities. Root `README.md` is the project doc; `docs/data_sources.md` records provenance.

## Layout

- `frontend/` — Vite + React 19 + JavaScript (JSX). Entry: `src/main.jsx` -> `src/App.jsx`.
- `backend/` — FastAPI app factory in `app/main.py`, versioned routers under `app/api/v1/`, schemas in `app/schemas/`, static data in `app/services/`, config in `app/core/config.py`, tests in `tests/`. On this Windows workspace use the local `.venv/` (Python 3.12.16); no checked-in venv was included.
- `mars_ml/` — empty, intended ML workspace.
- `docs/` — data provenance in `data_sources.md`.

## Frontend

Run commands from `frontend/`. Dependencies are already installed; commit
`package-lock.json` with changes.

- `npm run dev` — Vite dev server on `http://localhost:5173`
- `npm run lint` — ESLint (JS/JSX)
- `npm run build` — `vite build`; there is no TypeScript typecheck step
- `npm run preview` — serve the production build

Verify changes with `npm run lint && npm run build` before finishing. Run npm run test:terrain; for runtime confidence, serve the build and check the rendered
DOM (headless Chrome is available).

Source layout:

- `src/components/layout/` — app shell, sidebar, header.
- `src/components/dashboard/` — overview panels and stat cards.
- `src/components/charts/` — Chart.js wrappers; register new chart types in `chartSetup.js`.
- `src/components/map/` — `MarsMap` (OpenLayers), layer selector, controls, info, legend and attribution.
- `src/pages/` — one page per route; `MarsExplorer.jsx` owns the map state and API calls.
- `src/services/` — `navigation.js` (nav + sections), `missionData.js` (all demo data) and `marsApi.js` (the only API client).
- `src/hooks/` — shared hooks (`useClock`).
- `src/styles/` — `global.css` (palette tokens), `layout.css`, `dashboard.css`, `pages.css`, `map.css`.

Routes: `/`, `/explorer`, `/terrain`, `/routes`, `/targets`, `/ai`, plus a 404.
When adding a section, update both `src/App.jsx` and
`src/services/navigation.js`; every nav item must have a page.

This is a JSX-only app: ESLint targets `js/jsx`, there is no `tsconfig`, and
`vite.config.ts` only registers the React plugin. Do not add TypeScript source
files without migrating the lint/build setup.

All telemetry, progress, risks, targets, and events live in
`src/services/missionData.js` and are simulated. Keep the `SimulationNotice`
and `SIMULATED` labels; never present these values as real measurements or claim
an active human mission at Jezero Crater. The Mars Explorer map is the exception:
its HiRISE/CTX tiles and WMTS metadata are real NASA products. UI copy is
English; project docs are Spanish.

`src/services/marsApi.js` is the only API client. It defaults to
`http://127.0.0.1:8000` and reads `VITE_API_BASE_URL`. The map expects the
backend catalog/capabilities endpoints; keep loading, error and retry states
when changing it. OpenLayers uses the Mars projection `IAU2000:104905` in
degrees and streams tiles directly from `trek.nasa.gov`; do not proxy or cache
tiles in the backend.

Use the CSS variables in `src/styles/global.css` instead of hardcoded palette
values, and keep new UI responsive (the sidebar becomes a drawer under 900px).

`cesium` is declared as a dependency but is not imported or configured anywhere
yet. Do not add Cesium until the dedicated 3D map stage: it needs static-asset /
`CESIUM_BASE_URL` setup.

## Backend

Use the existing local Windows .venv created during stage 0:

- `backend/.venv/Scripts/python.exe`, `backend/.venv/Scripts/pip.exe` (Python 3.12.16)
- Install: `uv pip install --python backend/.venv/Scripts/python.exe -r backend/requirements.txt`

Run from `backend/`:

- ` .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` — dev server on `127.0.0.1:8000`
- ` .venv/Scripts/python.exe -m pytest -q` — backend tests (no external network calls)
- ` .venv/Scripts/python.exe -m compileall app tests` — quick syntax check
- Health check is `GET /api/health`; versioned routes live under `/api/v1/mars/`; docs are at `/docs`, `/redoc`, and `/openapi.json`.
- `GET /api/v1/mars/layers/{layer_id}/capabilities` returns the verified WMTS snapshot; add `?live=true` to fetch GetCapabilities from NASA Mars Trek (502 on upstream failure). The catalog has eight layers; only the two Jezero mosaics are `visualizable`.
- Provenance and bounding boxes are documented in `docs/data_sources.md`.

`fastapi`, `uvicorn`, `pydantic`, `httpx`, `python-dotenv`, and `pytest` are
installed. Config loads from `backend/.env` (see `.env.example`); CORS defaults
include `http://localhost:5173`, `http://127.0.0.1:5173`,
`http://localhost:4173`, and `http://127.0.0.1:4173`. Add future endpoints as
routers in `app/api/v1/`, with schemas in `app/schemas/` and static or external
data logic in `app/services/`. Do not reintroduce Flask or `run.py`. NASA
metadata must stay source-referenced and must not fabricate measurements,
acquisition dates, projections, or bounding boxes; tests must not depend on
external NASA services. WMTS metadata lives in `app/services/mars_wmts.py`.

## Workspace stage rules
Read ../AGENTS.md, ../docs/PROJECT_SPEC.md, ../docs/IMPLEMENTATION_STATUS.md and the supplied stage prompt first. Stages 1–3 are implemented; stage 4 authorizes georeferencing and scientific services only. Preserve manual routes/viewer; do not implement A* or the definitive hazard UI. See ../docs/stages/04-ciencia-prompt.md. Preserve MapaMarteN.glb in the parent workspace; never use Untitled1.glb. Existing 2D imagery is retained during preparation; do not add flat overlays to the future 3D terrain. Preserve simulated demo labels until real data or explicit unavailable states replace them in an authorized stage. Historical ZIP instructions about Git/installed environments are not evidence of their current availability.

Terrain: run npm run prepare:terrain before first build on a new checkout with output-stage1 available; run npm run test:terrain after input/camera changes. Keep original GLB coordinates and local-orientation disclaimer. Three.js is loaded on demand; do not add a second3D engine.

