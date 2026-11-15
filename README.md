# Bridges Mavors

**Bridges Mavors** is an interactive platform for exploring Martian terrain and supporting the planning of hypothetical missions in the Jezero region. It brings together NASA orbital maps, a 3D terrain model, scientific data, and analysis tools in an interface inspired by a mission control center.

[**Open the application**](https://agusbianchi-ui.github.io/NasaSpaceAppsChallenge-BridgesMavors/) · [API documentation](https://bridges-mavors-api.onrender.com/docs) · [Sources and attribution](SOURCES.md)

## Features

- **Explore Mars in 2D:** browse orbital mosaics and Mars Trek layers, along with their metadata and sources.
- **Navigate the terrain in 3D:** explore a voxelized regional model, inspect points, and create or import a reference route.
- **Plan routes:** define mission conditions, compare alternatives calculated with A*, view elevation profiles, and export or import a mission as JSON.
- **Inspect scientific data:** explore elevation, slope, aspect, roughness, and other available variables, together with their provenance and limitations. Apparent TES thermal inertia for daytime and nighttime is available for location-based queries.
- **Analyze aeolian dynamics:** browse catalogs and analyze observations when suitable local images, masks, and metadata are available.
- **Organize a mission:** use a task board and an assistant that responds with information available in the system.

To try the main workflow, open **Mars Explorer** and select **Load 3D terrain**, **Import preliminary route**, **Use endpoints only**, and **Calculate routes**. The model loads progressively and downloads approximately 52 MiB on first use.

## Data and scope

The 2D map retrieves imagery from NASA Mars Trek. The scientific terrain uses an HRSC/MOLA elevation model resampled to 250 m and its derived products; the 3D model's height is visually exaggerated by a factor of three. Route planning uses the scientific samples rather than the exaggerated visual height. A coarse-resolution historical regional dust scenario for Mars Year 36 is also included.

Telemetry, events, mission progress, and some targets shown in the interface are **simulated**. Planning conditions and thresholds are editable assumptions; the system does not certify traversability or replace scientific and safety assessments for a real mission. Missing data is shown as unavailable.

The current assistant uses deterministic responses based on system information and does not require an AI provider key. The aeolian module does not include a trained and validated predictive model or all the imagery needed to run independent analyses. Server-side results and tasks are held in memory and may be lost on restart.

See the [scientific limitations](docs/SCIENTIFIC_LIMITATIONS.md), [data dictionary](docs/DATA_DICTIONARY.md), and [sources](SOURCES.md) for the scope of each product.

## Technologies

- **Frontend:** React, Vite, React Router, Three.js, and OpenLayers.
- **Backend:** Python, FastAPI, and Uvicorn.
- **Scientific analysis:** NumPy, SciPy, Rasterio, and the `mars_ml` package.
- **Hosting:** GitHub Pages for the frontend and Render for the API.

## Run locally

### Requirements

- Node.js 22 and npm.
- Python 3.14 and Git.
- The terrain and scientific data files included in the repository. If any are missing, see the [deployment guide](docs/DEPLOYMENT.md).

### 1. Set up and run the API

From the project root:

```bash
python -m venv .venv
```

Activate the virtual environment, then run:

```bash
python -m pip install -r WebApp/backend/requirements.txt
cd WebApp/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

### 2. Set up and run the frontend

In another terminal:

```bash
cd WebApp/frontend
npm ci
npm run dev
```

Open the URL shown by Vite, normally `http://localhost:5173`. By default, the frontend connects to the local API on port 8000. Configuration examples are available in [`WebApp/frontend/.env.example`](WebApp/frontend/.env.example) and [`WebApp/backend/.env.example`](WebApp/backend/.env.example).

On Windows, you can also run `Start-BridgesMavors.ps1` from the project root to start the local services. The script serves the latest frontend build; run `npm run build` in `WebApp/frontend` after making frontend changes.

## Repository structure

```text
WebApp/
├── frontend/          Interface, maps, 3D viewer, and planning
├── backend/           API, scientific queries, and services
└── mars_ml/           Aeolian analysis and research tools
data/                  Additional scientific products
output-stage4/         Derived regional data for queries and routes
docs/                  Architecture, sources, limitations, and deployment
recursosU/             Historical terrain sources and materials
```

The active application is in `WebApp/`. The root-level `backend/` and `ops_mars-main/` directories are historical copies, not the main servers. The historical `reorganize.py` and `consolidate.py` scripts move or delete files and are not needed to run the application.

## Testing and deployment

From `WebApp/frontend`:

```bash
npm run lint
npm run build
npm run test:terrain
```

To run the backend and `mars_ml` tests, include `WebApp` and `WebApp/backend` in `PYTHONPATH`, then run `python -m pytest tests ../mars_ml/tests -q` from `WebApp/backend`.

The published application uses Render's free plan, so the backend may take time to respond after a period of inactivity. To set up another deployment, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Do not put credentials in code or in `VITE_*` variables, which are exposed in the frontend.
