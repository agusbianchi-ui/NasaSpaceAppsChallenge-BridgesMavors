# MARS OPS — Backend

API REST del proyecto MARS OPS, construida con **FastAPI**, Uvicorn, Pydantic y
HTTPX. Expone el endpoint de salud, un catálogo de fuentes, capas y ubicaciones
de Marte, metadatos WMTS verificados para los mosaicos de Jezero Crater y una
API de análisis eólico que reutiliza el paquete independiente `mars_ml`.

La documentación completa del proyecto está en [`../README.md`](../README.md) y
la procedencia de datos en [`../docs/data_sources.md`](../docs/data_sources.md).

## Estado actual

- `GET /api/health` conserva el contrato original de la etapa Flask.
- `GET /api/v1/mars/*` devuelve datos de catálogo y procedencia, no telemetría.
- Los dos mosaicos HiRISE y CTX de Jezero se verificaron contra NASA Mars Trek
  el 2026-11-14. El backend entrega un snapshot WMTS y puede consultar
  GetCapabilities en vivo con `?live=true`.
- No se descargan mosaicos ni productos científicos. El navegador solicita los
  tiles PNG directamente a `trek.nasa.gov`.
- Los metadatos científicos opcionales no confirmados se devuelven como `null`;
  el catálogo no inventa mediciones, fechas de adquisición ni bounding boxes.
- `GET /api/v1/aeolian/datasets` expone los cinco manifiestos de Marte de
  `mars_ml`. Todos son solo metadatos (`has_pixels=false`).
- `POST /api/v1/aeolian/analyze` ejecuta el análisis histórico observado con
  `mars_ml` sobre imágenes y máscaras locales indicadas por el cliente. No
  descarga productos ni inventa escalas, fechas o desplazamientos.
- `POST /api/v1/aeolian/predict` devuelve `501 not_implemented`: no existe un
  checkpoint, informe de entrenamiento ni validación independiente registrados.

## Estructura

```
backend/
├── app/
│   ├── main.py                 # create_app, CORS, errores y routers
│   ├── core/
│   │   └── config.py           # Settings desde variables de entorno
│   ├── api/
│   │   └── v1/
│   │       ├── health.py       # GET /api/health
│   │       └── mars.py         # GET /api/v1/mars/*
│   ├── schemas/
│   │   ├── common.py           # APIResponse, errores, health
│   │   └── mars.py             # fuentes, capas, ubicaciones y WMTS
│   └── services/
│       ├── mars_data_service.py # catálogo y fetch de capacidades
│       └── mars_wmts.py         # snapshot verificado y parser WMTS
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_mars.py
│   └── test_wmts.py
├── .env.example
├── requirements.txt
└── README.md
```

## Instalación

El repositorio incluye el entorno virtual en `backend/.venv` (Python 3.14).

```bash
cd backend
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps -e ../mars_ml
cp .env.example .env
```

## Ejecución

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La API queda disponible en `http://127.0.0.1:8000`.

Documentación interactiva:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Endpoints

| Método | Ruta                               | Descripción                              |
| ------ | ---------------------------------- | ---------------------------------------- |
| GET    | `/api/health`                      | Salud de la API                          |
| GET    | `/api/v1/mars/sources`             | Fuentes NASA del catálogo                |
| GET    | `/api/v1/mars/layers`              | Capas disponibles                        |
| GET    | `/api/v1/mars/layers/{layer_id}`   | Detalle de una capa                      |
| GET    | `/api/v1/mars/layers/{layer_id}/capabilities` | Snapshot WMTS verificado     |
| GET    | `/api/v1/mars/layers/{layer_id}/capabilities?live=true` | GetCapabilities en vivo |
| GET    | `/api/v1/mars/locations/jezero`    | Metadatos de referencia de Jezero Crater |
| GET    | `/api/v1/aeolian/datasets`         | Manifiestos eólicos de Marte de `mars_ml` |
| POST   | `/api/v1/aeolian/analyze`          | Análisis observado entre dos observaciones |
| GET    | `/api/v1/aeolian/results/{analysis_id}` | Resultado de análisis en memoria     |
| POST   | `/api/v1/aeolian/predict`          | Predicción (no disponible: `501`)       |

### Salud

```http
GET /api/health
```

```json
{
  "status": "healthy",
  "project": "MARS OPS"
}
```

La respuesta se mantiene plana, sin el sobre `APIResponse`, para conservar la
compatibilidad con la etapa anterior.

### Catálogo

Los endpoints versionados usan un sobre común:

```json
{
  "success": true,
  "data": []
}
```

Ejemplos:

```bash
curl http://127.0.0.1:8000/api/v1/mars/sources
curl http://127.0.0.1:8000/api/v1/mars/layers
curl http://127.0.0.1:8000/api/v1/mars/layers/hirise-imagery
curl http://127.0.0.1:8000/api/v1/mars/locations/jezero
curl "http://127.0.0.1:8000/api/v1/mars/layers/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/capabilities"
curl "http://127.0.0.1:8000/api/v1/mars/layers/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/capabilities?live=true"
```

El snapshot WMTS incluye endpoint, plantilla REST, estilo, formato,
TileMatrixSet, CRS publicado y matrices de zoom. El modo `live=true` consulta
NASA Mars Trek y puede devolver `502 upstream_unavailable` si el servicio no
está disponible o el documento no es válido.

Error estandarizado para una capa inexistente:

```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "Layer 'missing' not found."
  }
}
```

### Análisis eólico

`POST /api/v1/aeolian/analyze` recibe dos o más observaciones locales con fechas
UTC, rutas relativas a `AEOLIAN_DATA_ROOT`, CRS y una escala métrica explícita.
El servicio valida rutas, CRS y escala, ejecuta `run_mars_sequence` de `mars_ml`
y devuelve desplazamiento observado, calidad de registro, migración observada,
unidades y procedencia (incluido SHA-256 cuando está disponible).

```json
{
  "dataset_id": "ctx_multitemporal_six_sites",
  "observations": [
    {
      "observation_id": "early",
      "product_id": "B21_017762_1891_XN_09N292W",
      "acquisition_datetime_utc": "2012-01-01T00:00:00Z",
      "image_path": "nili_early.tif",
      "mask_path": "nili_early_mask.tif",
      "crs": "IAU2000:49900"
    },
    {
      "observation_id": "late",
      "product_id": "B22_018039_1890_XN_09N292W",
      "acquisition_datetime_utc": "2013-01-01T00:00:00Z",
      "image_path": "nili_late.tif",
      "mask_path": "nili_late_mask.tif",
      "crs": "IAU2000:49900"
    }
  ],
  "meters_per_pixel": {
    "x_m_per_pixel": 6.0,
    "source": "CTX orthoimage 6 m/pixel declarado por el producto"
  },
  "method": "centroid"
}
```

Reglas científicas aplicadas:

- `dx_m`/`dy_m` conservan la convención de `mars_ml`: `dx` hacia el este, `dy`
  hacia el norte, azimut horario desde el norte.
- `rate_m_per_earth_year` solo se calcula con fechas UTC y escala métrica
  explícita. Si falta la escala, la tasa queda en `null` y se conserva el motivo.
- La tasa observada y las predicciones son campos separados. El endpoint de
  predicción no genera valores y responde `501 not_implemented`.
- Los resultados viven en memoria del proceso; no hay persistencia.
- No se incluyen píxeles, etiquetas ni checkpoints en el repositorio.
- El registro y la segmentación son líneas base clásicas de `mars_ml`, no
  validación científica independiente.


## Configuración

La configuración se carga desde `backend/.env` y variables de entorno del
proceso.

| Variable                      | Valor por defecto                                    | Descripción                          |
| ----------------------------- | ---------------------------------------------------- | ------------------------------------ |
| `APP_NAME`                    | `MARS OPS API`                                       | Título de la API y OpenAPI           |
| `APP_VERSION`                 | `1.0.0`                                              | Versión documentada                  |
| `API_V1_PREFIX`               | `/api/v1`                                            | Prefijo de los endpoints versionados |
| `CORS_ORIGINS`                | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173` | Orígenes permitidos, separados por `,` |
| `NASA_REQUEST_TIMEOUT_SECONDS`| `20`                                                 | Timeout de consultas a Mars Trek     |
| `AEOLIAN_DATA_ROOT`           | `../mars_ml/datasets/mars`                           | Raíz de imágenes y máscaras locales  |

CORS permite por defecto el frontend de Vite (desarrollo y preview) tanto en
`localhost` como en `127.0.0.1`.

## Tests

Los 47 tests usan `TestClient` y fixtures locales; no dependen de servicios NASA
ni de red. El parser WMTS se prueba con un documento GetCapabilities reducido y
el snapshot verificado se valida sin consultar Mars Trek. Los 20 tests eólicos
usan pares sintéticos de `mars_ml` y cubren validación de entradas, integración
con `run_mars_sequence`, unidades, procedencia SHA-256, rutas simbólicas,
errores de configuración, CRS y escala incompatibles, máscaras inválidas,
secuencias de tres observaciones y la respuesta `501` de predicción.

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall app tests
```

## Migración desde Flask

La etapa anterior usaba Flask, Flask-CORS y `run.py`. Esos archivos y
dependencias se eliminaron tras verificar FastAPI. El único contrato que se
conserva sin cambios es `GET /api/health`.

## Integración con NASA WMTS

`MarsDataService.create_http_client()` crea un cliente HTTPX asíncrono con el
timeout configurado. Solo se invoca Mars Trek cuando el cliente pide
`?live=true`; el resto del tiempo se devuelve el snapshot verificado.

Los endpoints de tiles no pasan por el backend. El navegador los solicita
directamente a `trek.nasa.gov`, que responde con
`Access-Control-Allow-Origin: *`. Esto evita almacenar o reproyectar imágenes en
el servidor.

Detalles y limitaciones de procedencia:
[`../docs/data_sources.md`](../docs/data_sources.md).
