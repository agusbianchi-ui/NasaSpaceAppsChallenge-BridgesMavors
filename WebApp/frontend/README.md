# MARS OPS — Frontend

Interfaz Mission Control del proyecto MARS OPS. Construida con React 19, Vite,
JavaScript (JSX), React Router, Lucide React, Chart.js y OpenLayers.

La documentación completa del proyecto está en [`../README.md`](../README.md) y
la procedencia de datos en [`../docs/data_sources.md`](../docs/data_sources.md).

## Comandos

```bash
npm run dev      # servidor de desarrollo en http://localhost:5173
npm run lint     # ESLint
npm run build    # build de producción
npm run preview  # servir el build
```

## Estructura

```
src/
├── components/   # layout, dashboard, gráficos y mapa
│   └── map/      # MarsMap, selector, controles, leyenda y atribución
├── pages/        # una página por sección
├── services/     # navegación, datos simulados y cliente API
├── hooks/        # hooks compartidos
├── styles/       # tema, estilos y mapa
├── App.jsx       # rutas
└── main.jsx      # entrypoint
```

Rutas: `/` (Mission Overview), `/explorer`, `/terrain`, `/routes`, `/targets` y
`/ai`. Cualquier otra ruta muestra una página 404.

## Mapa WMTS

Mars Explorer integra OpenLayers con una proyección marciana personalizada
(`IAU2000:104905`, unidades en grados). El componente `MarsMap`:

- construye una `WMTSTileGrid` desde las matrices devueltas por el backend;
- usa el template REST de NASA Mars Trek y solicita los tiles PNG directamente
  a `trek.nasa.gov`;
- dibuja el bounding box publicado y muestra coordenadas, escala aproximada,
  leyenda, información de capa y atribución;
- permite alternar entre los mosaicos HiRISE y CTX de Jezero.

El backend debe estar en ejecución para cargar el catálogo y los metadatos
WMTS. La página incluye estados de carga, error y reintento. Si el backend no
está disponible, el resto del dashboard sigue funcionando.

## Cliente API

`src/services/marsApi.js` usa `VITE_API_BASE_URL` (por defecto
`http://127.0.0.1:8000`) y expone:

- `fetchMarsLayers()` — `GET /api/v1/mars/layers`
- `fetchMarsLayerCapabilities(layerId, { live })` — snapshot WMTS o
  `?live=true`
- `fetchJezeroLocation()` — `GET /api/v1/mars/locations/jezero`

Configuración:

```bash
cd frontend
cp .env.example .env
# VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Datos reales y simulados

- **Real:** mosaicos HiRISE y CTX de Jezero, metadatos WMTS y procedencia NASA.
- **Simulado:** telemetría, progreso, riesgos, eventos y objetivos definidos en
  `src/services/missionData.js`.

No representan mediciones reales de Marte ni una misión humana activa. CesiumJS
sigue sin integrarse; el visor 3D queda para una etapa posterior.
