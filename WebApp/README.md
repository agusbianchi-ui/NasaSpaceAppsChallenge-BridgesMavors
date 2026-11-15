# MARS OPS

Plataforma de operaciones para el proyecto **MARS OPS**, inspirada en centros de
control de misiones espaciales. La aplicación representa la exploración y
navegación de futuras misiones humanas en Marte, con **Jezero Crater** como
región inicial de estudio.

Esta versión incluye la infraestructura base, la interfaz Mission Control y una
API FastAPI con el endpoint de salud, un catálogo de fuentes y capas NASA,
metadatos WMTS y análisis histórico de migración de dunas mediante `mars_ml`.
Mars Explorer muestra mosaicos orbitales reales de Jezero Crater (HiRISE y CTX),
MOLA global y un mosaico CTX preliminar servidos por NASA Mars Trek y
renderizados con OpenLayers. El Route Planner superpone una ruta simulada sobre
esas capas para visualización; no permite editar rutas ni analiza el terreno. El
backend no descarga mosaicos: el navegador solicita los tiles directamente al
servicio de NASA.

El análisis eólico reutiliza el pipeline independiente de `mars_ml` sobre
imágenes y máscaras locales aportadas por el usuario. No hay píxeles, etiquetas
por duna ni checkpoints incluidos. Todavía no se implementan CesiumJS, edición
u optimización de rutas, modelos de ML entrenados ni predicción de migración; el
endpoint de predicción responde `501 not_implemented`. La telemetría, el
progreso, los riesgos, los objetivos y los eventos de la interfaz son **datos
simulados**, al igual que la ruta superpuesta por el Route Planner. Solo el mapa
orbital, los metadatos NASA y los análisis ejecutados sobre datos locales son
reales.

## Arquitectura general

```
bridges_mavors/
├── frontend/    # React 19 + JavaScript (JSX) + Vite (interfaz de usuario)
├── backend/     # FastAPI + Pydantic + Uvicorn (API REST)
├── mars_ml/     # espacio independiente para modelos y experimentos
└── docs/        # documentación adicional
```

El frontend consume la API mediante `src/services/marsApi.js`. La API expone el
health check bajo `/api` y los recursos versionados bajo `/api/v1`. El mapa
requiere el backend en ejecución; si no está disponible, la página muestra los
estados de error y reintento sin romper el resto del dashboard.

Estructura del frontend:

```
frontend/
├── src/
│   ├── App.jsx            # rutas de React Router
│   ├── main.jsx           # entrypoint y estilos globales
│   ├── components/        # layout, dashboard, gráficos, mapa y eólico
│   │   ├── aeolian/       # catálogo, formulario y resultados eólicos
│   │   └── map/           # OpenLayers: mapa, capas, controles y leyenda
│   ├── pages/             # una página por sección de navegación
│   ├── services/          # navegación, datos simulados y cliente API
│   ├── hooks/             # hooks compartidos (reloj de interfaz)
│   └── styles/            # tema, layout, dashboard, páginas, mapa y eólico
├── .env.example           # VITE_API_BASE_URL del cliente API
└── vite.config.ts
```

Secciones disponibles: Mission Overview, Mars Explorer, Terrain Analysis, Route
Planner, Scientific Targets, AI Systems y Aeolian Dynamics. La ruta desconocida
muestra una página 404; no hay enlaces rotos.

Estructura del backend:

```
backend/
├── app/
│   ├── main.py                 # create_app, CORS, errores y routers
│   ├── core/
│   │   └── config.py           # Settings desde variables de entorno
│   ├── api/
│   │   └── v1/
│   │       ├── health.py       # GET /api/health
│   │       ├── mars.py         # GET /api/v1/mars/*
│   │       └── aeolian.py      # /api/v1/aeolian/*
│   ├── schemas/
│   │   ├── common.py           # APIResponse, errores y health
│   │   ├── mars.py             # fuentes, capas, ubicaciones y WMTS
│   │   └── aeolian.py          # solicitudes y resultados eólicos
│   └── services/
│       ├── mars_data_service.py # catálogo y fetch de capacidades
│       ├── mars_wmts.py         # snapshot WMTS verificado y parser
│       └── aeolian_service.py   # integración con mars_ml
├── tests/
│   ├── conftest.py
│   ├── test_aeolian.py
│   ├── test_health.py
│   ├── test_mars.py
│   └── test_wmts.py
├── .env.example
├── requirements.txt
└── README.md
```

## Requisitos

- Node.js 20 o superior y npm
- Python 3.14 (el repositorio incluye `backend/.venv` con esta versión)
- Git

## Instalación del frontend

```bash
cd frontend
npm install
```

Las dependencias ya están instaladas en este entorno; `npm install` solo es
necesario si se agregan o actualizan paquetes. El frontend usa React Router,
Lucide React, Chart.js, react-chartjs-2 y OpenLayers. CesiumJS está declarado
como dependencia, pero todavía no se importa ni configura.

## Instalación del backend

El repositorio incluye un entorno virtual ya creado en `backend/.venv`.

```bash
cd backend
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps -e ../mars_ml
cp .env.example .env   # opcional: ajustar CORS y timeout
```

> `backend/.venv/` y los archivos `.env` están excluidos por `.gitignore`.
> La instalación editable de `mars_ml` es necesaria para importar el paquete
> científico; no se usan `PYTHONPATH` ni inserciones de `sys.path`. Verificá que
> `uvicorn` se ejecute desde el mismo entorno donde instalaste `mars_ml`.

## Ejecutar los servicios

Abrir dos terminales.

Backend (desde `backend/`):

```bash
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La API queda disponible en `http://127.0.0.1:8000`. La documentación interactiva
está en `http://127.0.0.1:8000/docs` y `http://127.0.0.1:8000/redoc`.

Frontend (desde `frontend/`):

```bash
npm run dev
```

La interfaz queda disponible en `http://localhost:5173`. El resto del dashboard
funciona sin backend, pero Mars Explorer necesita la API para cargar el catálogo
de capas y los metadatos WMTS. Los tiles se solicitan directamente a
`trek.nasa.gov` con CORS habilitado por NASA.

## Endpoints

| Método | Ruta                               | Descripción                            |
| ------ | ---------------------------------- | -------------------------------------- |
| GET    | `/api/health`                      | Salud de la API                        |
| GET    | `/api/v1/mars/sources`             | Fuentes NASA del catálogo              |
| GET    | `/api/v1/mars/layers`              | Capas disponibles                      |
| GET    | `/api/v1/mars/layers/{layer_id}`   | Detalle de una capa                    |
| GET    | `/api/v1/mars/layers/{layer_id}/capabilities` | Snapshot WMTS verificado    |
| GET    | `/api/v1/mars/layers/{layer_id}/capabilities?live=true` | GetCapabilities en vivo |
| GET    | `/api/v1/mars/locations/jezero`    | Metadatos de referencia de Jezero      |
| GET    | `/api/v1/aeolian/datasets`         | Manifiestos eólicos de Marte           |
| POST   | `/api/v1/aeolian/analyze`          | Análisis observado con `mars_ml`       |
| GET    | `/api/v1/aeolian/results/{analysis_id}` | Resultado de análisis en memoria   |
| POST   | `/api/v1/aeolian/predict`          | Predicción no disponible (`501`)       |

### Endpoint de salud

```http
GET http://127.0.0.1:8000/api/health
```

Respuesta:

```json
{
  "status": "healthy",
  "project": "MARS OPS"
}
```

El health check conserva exactamente el contrato de la etapa Flask. Los
endpoints versionados usan un sobre común:

```json
{
  "success": true,
  "data": []
}
```

Los errores también son consistentes:

```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "Layer 'missing' not found."
  }
}
```

CORS permite por defecto el servidor de desarrollo y el de preview de Vite:
`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:4173` y
`http://127.0.0.1:4173`. Se puede cambiar con la variable de entorno
`CORS_ORIGINS` (lista separada por comas).

### Análisis eólico con `mars_ml`

`POST /api/v1/aeolian/analyze` ejecuta el análisis histórico observado entre
observaciones locales. Requiere fechas UTC, rutas relativas a
`AEOLIAN_DATA_ROOT`, CRS compatibles y una escala métrica explícita para
calcular tasas. Devuelve desplazamiento, migración observada, calidad de
registro, unidades, limitaciones y procedencia; las tasas quedan en `null`
cuando falta escala o las fechas no permiten calcularlas.

`GET /api/v1/aeolian/datasets` lista los cinco manifiestos de Marte de
`mars_ml`, todos solo de metadatos. `POST /api/v1/aeolian/predict` existe como
contrato explícito pero responde `501 not_implemented` hasta que haya un
checkpoint validado y un informe de entrenamiento.

Los resultados se guardan en memoria y no se descargan productos científicos ni
se inventan mediciones. La página **Aeolian Dynamics** consume estos endpoints
para explorar metadatos verificados, ejecutar análisis observados con rutas
locales y mostrar resultados, rechazos, procedencia y limitaciones. No ofrece
carga de archivos ni predicciones simuladas. Ver
[`backend/README.md`](backend/README.md) para el payload completo.


## Integración frontend/API

Mars Explorer consume la API mediante `frontend/src/services/marsApi.js`:

```bash
cd frontend
cp .env.example .env
# VITE_API_BASE_URL=http://127.0.0.1:8000
```

La página carga el catálogo con `GET /api/v1/mars/layers`, filtra las capas
`visualizable` y solicita `GET /api/v1/mars/layers/{id}/capabilities` para la
capa seleccionada. Implementa estados de carga, error, reintento y limpieza de
peticiones con `AbortController`.

El mapa usa OpenLayers con una proyección marciana personalizada
(`IAU2000:104905`, unidades en grados), una `WMTSTileGrid` construida desde las
matrices del backend y el template REST de Mars Trek. Los tiles se cargan
directamente desde `trek.nasa.gov`; el backend nunca actúa como proxy de
imágenes.

## Datos reales y simulados

- **Real:** mosaicos WMTS HiRISE y CTX de Jezero Crater, MOLA global, mosaico
  CTX preliminar, catálogo NASA, procedencia, metadatos WMTS y análisis eólicos
  ejecutados sobre imágenes locales aportadas por el usuario.
- **No incluido:** píxeles satelitales, etiquetas por duna, checkpoints,
  edición de rutas o predicciones de migración.
- **Simulado:** telemetría, progreso, riesgos, eventos, objetivos científicos, la
  ruta superpuesta en el Route Planner y el resto de la planificación de la
  interfaz.

El detalle de procedencia, bounding boxes y limitaciones está en
[`docs/data_sources.md`](docs/data_sources.md).

## Comandos de verificación

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm run preview
```

Backend:

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall app tests
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/v1/mars/layers
curl "http://127.0.0.1:8000/api/v1/mars/layers/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/capabilities"
curl http://127.0.0.1:8000/api/v1/aeolian/datasets
```

## Variables de entorno del backend

| Variable                       | Valor por defecto                             | Descripción                            |
| ------------------------------ | --------------------------------------------- | -------------------------------------- |
| `APP_NAME`                     | `MARS OPS API`                                | Título de la API y OpenAPI             |
| `APP_VERSION`                  | `1.0.0`                                       | Versión documentada                    |
| `API_V1_PREFIX`                | `/api/v1`                                     | Prefijo de endpoints versionados       |
| `CORS_ORIGINS`                 | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173` | Orígenes permitidos, separados por `,` |
| `NASA_REQUEST_TIMEOUT_SECONDS` | `20`                                          | Timeout de las consultas a Mars Trek   |
| `AEOLIAN_DATA_ROOT`            | `../mars_ml/datasets/mars`                    | Raíz de imágenes y máscaras locales    |

## Catálogo y limitaciones

- El catálogo combina referencias estáticas con dos productos Jezero
  verificados contra NASA Mars Trek el 2026-11-14.
- No se descargan mosaicos ni productos científicos. El backend solo consulta
  GetCapabilities cuando se solicita `?live=true`; el navegador carga los tiles
  PNG directamente desde Mars Trek.
- `acquisition_date` queda en `null` para los mosaicos porque la capa no expone
  las fechas de adquisición de todas las imágenes contribuyentes.
- `data_created_date=2020-08-03` es la fecha de creación del producto, no la
  fecha de adquisición.
- Los bounding boxes están en orden oeste, sur, este, norte y no representan un
  límite oficial del cráter.
- No se representa una misión humana activa ni telemetría real.
- Cualquier uso científico debe validarse contra el producto PDS y la
  documentación oficial de NASA/USGS.
