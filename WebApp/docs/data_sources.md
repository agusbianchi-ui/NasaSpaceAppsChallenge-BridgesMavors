# Fuentes de datos y procedencia

Este documento describe las fuentes NASA usadas por MARS OPS, qué datos son
reales y cuáles siguen siendo simulados. La regla del proyecto es no inventar
mediciones, proyecciones, fechas de adquisición ni bounding boxes.

## Resumen

| Elemento | Estado | Naturaleza |
| -------- | ------ | ---------- |
| Mapa orbital de Marte y Jezero | Integrado | WMTS real de NASA Mars Trek |
| Mosaicos HiRISE, CTX, MOLA y CTX preliminar | Verificados | Productos orbitales reales |
| Catálogo de capas y fuentes | Integrado | Metadatos estáticos referenciados |
| Telemetría, riesgos, eventos y objetivos | Simulado | Datos de demostración del dashboard |
| Ruta del Route Planner | Simulado | Superposición gráfica sobre el mapa real |
| MEDA | Solo catálogo | Mediciones in-situ, no un mapa |
| THEMIS y CRISM | Solo catálogo | Referencias, sin visualización integrada |

El backend no descarga mosaicos ni productos científicos. El navegador solicita
los tiles directamente a NASA Mars Trek; el backend solo entrega metadatos del
catálogo y de WMTS.

## NASA Mars Trek

- Portal: <https://trek.nasa.gov/mars/>
- Documentación del servicio: <https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars>
- Servicio: OGC WMTS 1.0.0, codificación REST.
- Endpoint base de tiles: `https://trek.nasa.gov/tiles/Mars/EQ/<layer_id>`
- Capacidades: `https://trek.nasa.gov/tiles/Mars/EQ/<layer_id>/1.0.0/WMTSCapabilities.xml`
- Plantilla de tile:
  `https://trek.nasa.gov/tiles/Mars/EQ/<layer_id>/1.0.0/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.<ext>`
- Estilo: `default`
- Formato: `image/png` en HiRISE, CTX y CTX preliminar; `image/jpeg` en MOLA.
  La extensión del tile se deriva del formato de cada capa.
- TileMatrixSet: `default028mm`
- CRS publicado: `urn:ogc:def:crs:EPSG::104905`
- Código de proyección usado por el frontend: `IAU2000:104905`
- Unidades: grados sobre una esfera marciana; **no es WGS84 terrestre**.
- Los tiles responden con `Access-Control-Allow-Origin: *`, por lo que el
  navegador puede cargarlos sin proxy.

La verificación se realizó el **2026-11-14** consultando GetCapabilities y
solicitando tiles de muestra. El snapshot verificado queda en el backend; el
endpoint `?live=true` permite volver a consultar Mars Trek bajo demanda.

## Capas visualizables

### MRO HiRISE, Jezero Mosaic, Controlled

- `layer_id`:
  `JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd`
- Instrumento: HiRISE (Mars Reconnaissance Orbiter)
- Resolución nominal: 0.25 m/pixel
- Región: Jezero Crater, Marte
- Bounding box: `[77.2229331, 18.3067994, 77.583964, 18.669315]`
- Orden del bounding box: oeste, sur, este, norte (grados)
- TileMatrix disponibles: `0` a `17`
- Producto: ortomosaico visible controlado, usado como basemap de navegación
  relativa al terreno para Mars 2020.
- Atribución: NASA/JPL-Caltech/University of Arizona · USGS Astrogeology
  Science Center · NASA Mars Trek

### MRO CTX, Jezero Mosaic, Controlled

- `layer_id`: `JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0`
- Instrumento: CTX (Mars Reconnaissance Orbiter)
- Resolución nominal: 6 m/pixel
- Región: Jezero Crater, Marte
- Bounding box: `[77.1604655, 18.2110274, 77.6991776, 18.7211945]`
- Orden del bounding box: oeste, sur, este, norte (grados)
- TileMatrix disponibles: `0` a `13`
- Producto: ortomosaico visible controlado; mapa del Lander Vision System de
  Mars 2020.
- Atribución: NASA/JPL-Caltech/MSSS · USGS Astrogeology Science Center · NASA
  Mars Trek

### MGS MOLA Color Shade, Global

- `layer_id`: `Mars_MGS_MOLA_ClrShade_merge_global_463m`
- Instrumento: MOLA (Mars Global Surveyor)
- Resolución nominal: 463 m/pixel
- Región: Marte global
- Bounding box: `[-180.0, -89.9991635, 179.9983271, 90.0]`
- TileMatrix disponibles: `0` a `7`
- Formato de tile: `image/jpeg`
- Producto: mosaico global de relieve coloreado derivado de topografía MOLA.
- Atribución: NASA/MOLA Science Team · NASA Mars Trek

### MRO CTX, Jezero Preliminary Mosaic

- `layer_id`: `Jezero_CTX_BlockAdj_dd`
- Instrumento: CTX (Mars Reconnaissance Orbiter)
- Resolución nominal: no publicada en GetCapabilities
- Región: región de Jezero, Marte
- Bounding box: `[75.1537692, 15.9058484, 78.8717121, 19.4453003]`
- TileMatrix disponibles: `0` a `12`
- Producto: mosaico CTX preliminar con ajuste por bloques; no es el producto
  controlado del Lander Vision System.
- Atribución: NASA/JPL-Caltech/MSSS · NASA Mars Trek

Las cuatro capas comparten el nombre de TileMatrixSet (`default028mm`) pero
**no** el mismo rango de zoom ni el mismo formato. El frontend construye la
rejilla a partir de las matrices devueltas por el backend y no asume que las
capas tengan la misma resolución máxima.

## Fechas y limitaciones

- `data_created_date=2020-08-03` en Mars Trek corresponde a la creación del
  producto, no a la fecha de adquisición de cada imagen.
- `acquisition_date` se deja en `null` porque la capa no expone las fechas de
  adquisición de todas las imágenes contribuyentes.
- La resolución indicada es la del producto/mosaico; no implica que cada píxel
  tenga esa resolución efectiva en todas las zonas.
- El bounding box es el publicado por el servicio WMTS, no un límite oficial
  del cráter.
- Cualquier uso científico debe validarse contra el producto PDS y la
  documentación oficial de NASA/USGS.

## MEDA

- Fuente: <https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:mars2020_meda&version=1.0>
- MEDA (Mars Environmental Dynamics Analyzer) mide condiciones ambientales en
  la ubicación del rover Perseverance.
- Es una medición in-situ, **no un mapa global**.
- En esta etapa no se descargan ni se muestran valores calibrados de
  temperatura, presión, viento o radiación.

## Otras capas del catálogo

Estas capas son referencias de catálogo; no se visualizan en el mapa:

- **MOLA Elevation** (Mars Global Surveyor): referencia de topografía global;
  para el mapa se usa el producto MOLA Color Shade verificado de Mars Trek.
  <https://pds-geosciences.wustl.edu/missions/mgs/mola.html>
- **THEMIS Thermal Infrared** (Mars Odyssey): infrarrojo térmico.
  <https://mars.asu.edu/data/>
- **CRISM Mineral Maps** (Mars Reconnaissance Orbiter): espectroscopía
  visible-infrarroja.
- **HiRISE / CTX genéricas**: referencias de instrumento; para el mapa se usan
  los productos verificados de Jezero.

## Endpoints del backend

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| GET | `/api/v1/mars/sources` | Fuentes NASA del catálogo |
| GET | `/api/v1/mars/layers` | Capas y metadatos de procedencia |
| GET | `/api/v1/mars/layers/{layer_id}` | Detalle de una capa |
| GET | `/api/v1/mars/layers/{layer_id}/capabilities` | Snapshot WMTS verificado |
| GET | `/api/v1/mars/layers/{layer_id}/capabilities?live=true` | GetCapabilities en vivo |
| GET | `/api/v1/mars/locations/jezero` | Metadatos de referencia de Jezero |

El endpoint `?live=true` puede responder `502 upstream_unavailable` si NASA Mars
Trek no está disponible o devuelve un documento inválido. Los tests no dependen
de servicios externos.

## Datos simulados

La telemetría, el progreso, los riesgos, los objetivos científicos, los eventos
del dashboard y los waypoints del Route Planner provienen de
`frontend/src/services/missionData.js` y son datos de demostración. La ruta se
superpone al mapa NASA para visualización; no se edita, no se analiza el terreno
y no representa una ruta operacional. El mapa orbital y los metadatos NASA son
la única parte real de esta etapa.
