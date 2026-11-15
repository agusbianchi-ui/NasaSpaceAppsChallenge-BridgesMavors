# MARS OPS — Backend

API REST del proyecto MARS OPS, construida con **FastAPI**, Uvicorn, Pydantic y
HTTPX. Expone el endpoint de salud, un catálogo de fuentes, capas y ubicaciones
de Marte, y metadatos WMTS verificados para los mosaicos de Jezero Crater.

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

El repositorio incluye el entorno virtual en `backend/venv` (Python 3.14).

```bash
cd backend
venv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Ejecución

```bash
cd backend
venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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

CORS permite por defecto el frontend de Vite (desarrollo y preview) tanto en
`localhost` como en `127.0.0.1`.

## Tests

Los 27 tests usan `TestClient` y fixtures locales; no dependen de servicios NASA
ni de red. El parser WMTS se prueba con un documento GetCapabilities reducido y
el snapshot verificado se valida sin consultar Mars Trek.

```bash
cd backend
venv/bin/python -m pytest -q
venv/bin/python -m compileall app tests
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
