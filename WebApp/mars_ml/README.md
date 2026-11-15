# MARS OPS — MARS AEOLIAN DYNAMICS (`mars_ml`)

Módulo científico independiente para detectar dunas, registrarlas entre fechas y
medir desplazamientos aparentes en imágenes satelitales. Se desarrolla primero
sobre el Sahara como referencia terrestre y deja preparada la arquitectura para
una futura adaptación a Marte.

> **Estado científico:** pipeline de investigación no validado. No incluye un
> modelo entrenado, no incluye imágenes satelitales descargadas y no produce
> predicciones operacionales para Marte. La segmentación por defecto es un
> baseline clásico de OpenCV sin validación contra un dataset etiquetado.

## 1. Objetivo científico

El sistema busca:

1. Detectar y segmentar regiones candidatas a dunas.
2. Alinear observaciones de distintas fechas.
3. Medir desplazamiento aparente 2D, dirección y morfología.
4. Separar movimiento real de diferencias por iluminación, perspectiva,
   resolución o errores de registro.
5. Generar features y manifiestos para un futuro entrenamiento supervisado.

El pipeline no asume que toda diferencia entre imágenes sea movimiento de arena.
Si el registro no supera los umbrales configurados, el desplazamiento se niega
explícitamente. Si no se conoce la escala métrica, no se convierte píxeles a
metros.

## 2. Arquitectura

```text
mars_ml/
├── datasets/
│   ├── earth/{sahara,sentinel,landsat}/
│   ├── mars/{hargraves,coprates,ctx_multitemporal,hirise,jezero}/
│   │   ├── */dataset.json        # metadatos verificados, sin píxeles
│   │   ├── manifest.json
│   │   ├── environmental_sources.json
│   │   └── published_measurements.json
│   └── scene_catalog.py          # validación de catálogos de escenas
├── computer_vision/
│   ├── image_io.py               # carga, metadatos, CRS, PDS3 y checksums
│   ├── image_registration.py     # ORB + homografía, correlación de fase
│   ├── dune_segmentation.py      # baseline clásico + adaptador U-Net
│   ├── displacement_detection.py # centroides, Farneback, Lucas-Kanade
│   ├── correlation_displacement.py
│   ├── dune_crests.py
│   ├── geometry_comparison.py
│   ├── annotation_masks.py
│   └── uncertainty.py
├── ingestion/
│   ├── catalog.py                # manifiestos de datasets marcianos
│   ├── readers.py                # raster, vector, tabla y PDS
│   ├── annotations.py            # rasterización de anotaciones
│   ├── download.py               # plan de descarga permitido, dry-run
│   └── validation.py
├── aeolian_dynamics/
│   ├── dune_morphology.py
│   ├── dune_migration.py
│   ├── migration_analysis.py     # métodos de cresta/centroide y geometría
│   ├── migration_models.py       # Ridge y Random Forest agrupados
│   ├── hybrid_model.py           # covariables ambientales explícitas
│   ├── environmental_observations.py
│   ├── environmental_sources.py
│   └── planetary_parameters.py
├── training/
│   ├── prepare_dataset.py
│   ├── train_segmentation.py
│   ├── train_classifier.py       # clasificador de píxeles de dunas
│   ├── train_migration.py        # tabla explícita de observaciones
│   ├── migration_metrics.py
│   └── evaluate.py
├── validation/
│   ├── published_measurements.py # rangos agregados, no etiquetas
│   └── compare.py
├── inference/
│   ├── dune_analysis.py
│   └── mars_sequence.py          # secuencias fechadas de Marte
├── visualization/
│   └── plots.py
├── models/                       # sin pesos; ver models/README.md
├── notebooks/                    # sin notebooks; ver notebooks/README.md
├── tests/                        # fixtures sintéticos, sin red
├── requirements.txt
├── requirements-training.txt     # PyTorch opcional, no instalado
├── README.md
├── STAGE1_REPORT.md
└── STAGE2_REPORT.md
```

`mars_ml` no importa FastAPI ni React. No se modificó `frontend/` ni `backend/`
en esta etapa.

## 3. Instalación y verificación

El workspace incluye un entorno propio en `mars_ml/.venv` (Python 3.14).
`mars_ml` se instala como paquete local editable; así queda registrado en el
intérprete y puede importarse desde cualquier directorio sin `PYTHONPATH` ni
`sys.path` manuales.

```bash
cd /home/pietro/Documents/bridges_mavors
uv venv --python 3.14 mars_ml/.venv
uv pip install --python mars_ml/.venv/bin/python -e mars_ml
```

`mars_ml/pyproject.toml` declara el paquete, sus subpaquetes, los datos JSON/MD
y lee las dependencias fijadas de `mars_ml/requirements.txt`.

Verificación de importación:

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -c "import mars_ml; print(mars_ml.__file__)"
cd mars_ml
./.venv/bin/python -c "import mars_ml; print(mars_ml.__file__)"
```

Dependencias instaladas: NumPy 2.5.4, OpenCV headless 5.0.0.93, Rasterio 1.5.2,
Matplotlib 3.11.2, pytest 9.2.0, pandas 3.1.1, pyshp 3.1.8, openpyxl 3.1.5,
scikit-learn 1.9.1 y joblib 1.6.0. PyTorch **no** está instalado; el extra
`[training]` lo mantiene opcional.

Tests:

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -m pytest mars_ml/tests -q
```

Resultado actual: **96 tests passed**. Los tests usan imágenes sintéticas y
fixtures locales; no dependen de servicios externos.

Chequeo sintáctico:

```bash
mars_ml/.venv/bin/python -m compileall -q mars_ml
```

## 4. Fuentes de datos

### Sahara verificado

`datasets/earth/sahara/scene_catalog.json` contiene metadatos verificados el
**2026-11-14**:

- Copernicus Data Space Ecosystem, colección `sentinel-2-l2a`.
  - Endpoint STAC: <https://catalogue.dataspace.copernicus.eu/stac/search>
  - Cuatro escenas L2A sobre la tesela MGRS `30RVV`, abril de 2019, 2021, 2024
    y 2025, con `eo:cloud_cover = 0.0` a nivel de escena.
  - CRS de escena: `EPSG:32630`; assets de 10 m: `B02`, `B03`, `B04`, `B08`.
- USGS Landsat, colección `landsat-c2l2-sr`.
  - Endpoint STAC: <https://landsatlook.usgs.gov/stac-server/search>
  - Una escena Landsat 8 (`LC08_L2SP_199039_20230629_20230711_02_T1_SR`),
    `EPSG:32630`, grilla nominal de 30 m.
  - Es una referencia cross-sensor; todavía no forma una secuencia
    multitemporal emparejada.

Las consultas usaron un `bbox` aproximado `[-4.1, 31.0, -3.8, 31.3]`, nubes
`< 10 %` y ventanas de abril para reducir diferencias estacionales. El catálogo
guarda IDs, fechas UTC, bbox WGS84, CRS, resolución, bandas, nubosidad, URL del
item STAC y fecha de recuperación. **No se descargaron píxeles.**

Documentación:

- <https://dataspace.copernicus.eu/>
- <https://www.usgs.gov/landsat-missions>
- <https://earthdata.nasa.gov/>
- <https://documentation.dataspace.copernicus.eu/>
- <https://m2m.cr.usgs.gov/>

Google Earth Engine solo debe usarse si existe acceso autorizado; no se usó en
esta etapa. No se almacenan credenciales.

### Marte

`datasets/mars/` contiene **solo metadatos verificados**, no píxeles:

- Hargraves Crater: polígonos de dunas y atributos morfométricos (Mendeley Data,
  DOI `10.17632/bfnxzwhd4r.3`).
- Coprates Chasma: polígonos, tablas de mediciones y productos CTX/DEM
  (figshare, DOI `10.6084/m9.figshare.c.5198183.v3`).
- CTX multitemporal: un par Nili Patera temprano/tardío más DEM y FOM
  (figshare, DOI `10.6084/m9.figshare.c.4649537.v1`); los otros cinco sitios
  están referenciados pero no seleccionados.
- HiRISE: registro a nivel de archivo PDS, sin producto ni par seleccionado.
- Jezero: registro de evaluación de cobertura repetida, sin píxeles ni etiquetas.

`datasets/mars/manifest.json` indexa los cinco manifiestos. Las fechas que no
aparecen en las fuentes quedan como `requires_pds_resolution` o `not_reported`;
no se infieren desde el nombre del archivo. `has_pixels` es `false` en todos los
casos.

`environmental_sources.json` cataloga posibles fuentes ambientales (MEDA, REMS,
MCD, THEMIS, InSight) con `metadata_verified: false`; no se presenta ninguna
como meteorología simultánea a una imagen. `published_measurements.json` guarda
rangos agregados de migración y flujo para contexto, explícitamente no etiquetas
por duna.

Los mosaicos WMTS de Jezero que usa MARS OPS en el mapa no son un archivo
multitemporal de dunas y no deben presentarse como tal.

## 5. Preparación de imágenes

`computer_vision/image_io.py`:

- Carga imágenes comunes con OpenCV y GeoTIFF con Rasterio.
- Conserva CRS, transformación afín, resolución, nodata, bandas y procedencia.
- Normaliza con percentiles robustos y devuelve una máscara de píxeles válidos.
- Detecta dimensiones, canales, dtype, valores no finitos y nodata.
- Recorta y actualiza la transformación afín para no perder georreferencia.
- Puede escribir GeoTIFF conservando CRS, transformación y nodata.

La escala métrica nunca se deduce de una resolución en grados. `meters_per_pixel`
debe proporcionarse explícitamente y con una unidad verificada.

## 6. Registro de imágenes

`computer_vision/image_registration.py`:

- ORB + ratio test + homografía RANSAC como método principal.
- Correlación de fase como fallback de traslación.
- Reporta matches, inliers, ratio, RMS y error mediano de reproyección.
- Evalúa plausibilidad geométrica de la homografía.
- Marca `reliable = False` si no alcanza los umbrales.
- `warp_to_reference` devuelve imagen alineada y máscara de validez.

El desplazamiento no se calcula si `reliable` es falso. El informe JSON conserva
el motivo del rechazo.

## 7. Segmentación de dunas

`computer_vision/dune_segmentation.py`:

- Baseline clásico: textura local + energía de gradientes, umbral Otsu,
  morfología, relleno de huecos y eliminación de componentes pequeños.
- Interfaz `DuneSegmenter` y adaptador `UNetSegmenter`.
- El adaptador U-Net exige un checkpoint externo y PyTorch. No hay pesos
  incluidos ni se inventa un modelo entrenado.
- El baseline responde a terreno texturado en general; no es un detector
  semántico validado de dunas.

## 8. Desplazamiento y migración

`computer_vision/displacement_detection.py`:

- Desplazamiento de centroides de máscara (movimiento del cuerpo segmentado).
- Farneback denso y Lucas-Kanade disperso con chequeo forward-backward.
- Comparación de área, intersección, IoU, Dice y diferencia simétrica.
- Consistencia entre centroide y optical flow; si discrepan, el resultado se
  marca como no confiable.

Convención: `dx_px` positivo hacia el este de la imagen, `dy_px` positivo hacia
el norte; el azimut es horario desde el norte.

`aeolian_dynamics/dune_migration.py`:

- Calcula tasa aparente 2D = desplazamiento métrico / intervalo × 365.25.
- Exige fechas UTC con timezone, escala métrica, registro confiable y un
  intervalo mínimo configurable.
- Devuelve supuestos explícitos: el centroide representa movimiento del cuerpo
  de la duna, la escala es válida y la anualización no implica tasa constante.
- No calcula flujo de sedimento ni migración vertical.

La conversión de píxeles a metros solo ocurre con escala explícita. Un
desplazamiento en píxeles nunca se etiqueta como desplazamiento geográfico.

## 9. Morfología

`aeolian_dynamics/dune_morphology.py` extrae:

- Área y perímetro.
- Centroide y bounding box.
- Orientación del eje mayor (azimut, `[0, 180)`).
- Ejes mayor/menor y relación de aspecto.
- Circularidad, solidez y curvatura de borde (media, p95, máximo).
- Número de componentes.
- Área y longitudes métricas solo si se conoce `meters_per_pixel`.
- `feature_vector()` con `NaN` explícito para valores ausentes.

## 10. Datos ambientales y parámetros planetarios

`aeolian_dynamics/environmental_observations.py` modela observaciones opcionales
de viento, temperatura, presión, densidad y humedad. Cada campo ausente queda
ausente. Cada registro conserva:

- Fuente y tipo (`in_situ`, `reanalysis`, `model`, `climatology`, `estimated`,
  `unknown`).
- Fecha/hora de la imagen y de la observación.
- Offset temporal y tolerancia de simultaneidad.
- Unidades.
- Vector de viento este/norte cuando hay velocidad y dirección.

Una climatología no se presenta como medición simultánea. La densidad solo se
deriva de presión y temperatura cuando ambos existen, y el informe lo indica.

`aeolian_dynamics/planetary_parameters.py` separa Tierra y Marte:

| Parámetro de referencia | Tierra | Marte |
| --- | --- | --- |
| Gravedad | 9.80665 m/s² | 3.71 m/s² |
| Atmósfera dominante | N₂/O₂ | CO₂ |
| Presión superficial de referencia | 101325 Pa | 610 Pa |
| Temperatura de referencia | 288.15 K | 210 K |
| Masa molar media | 0.02897 kg/mol | 0.04334 kg/mol |

Son valores de referencia, no mediciones locales. Incluye:

- Densidad por gas ideal con presión y temperatura configurables.
- Ley logarítmica de viento para obtener velocidad de fricción.
- Umbral de fricción tipo Bagnold con coeficiente empírico **obligatorio**.
- Flujo de saltación tipo Bagnold con coeficiente explícito y estado de
  calibración.

No se aplican tasas de migración del Sahara a Marte ni se convierten parámetros
terrestres en predicciones marcianas. Cualquier coeficiente marciano debe
calibrarse con observaciones.

## 11. Dataset y entrenamiento

`training/prepare_dataset.py` espera:

```text
<root>/<region>/<sequence>/<observation>/image.<ext>
<root>/<region>/<sequence>/<observation>/mask.<ext>
```

También acepta `image.png` + `mask.png` en la misma carpeta. Genera un manifiesto
JSON con hashes, dimensiones, canales, CRS, transformación, resolución, calidad
de datos, splits y warnings.

- Agrupa por `region/sequence`: todas las observaciones de un grupo caen en un
  solo split para evitar fuga de datos.
- Rechaza máscaras no binarias, vacías o con dimensiones distintas.
- Detecta archivos faltantes.
- `load_manifest()` rechaza muestras sin máscara para entrenamiento.

Comandos:

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -m mars_ml.training.prepare_dataset \
  --root mars_ml/datasets/earth/sahara/labelled \
  --output mars_ml/datasets/earth/sahara/manifest.json

# Valida el manifiesto sin instalar PyTorch
mars_ml/.venv/bin/python -m mars_ml.training.train_segmentation \
  --manifest mars_ml/datasets/earth/sahara/manifest.json \
  --dry-run
```

Entrenamiento real (no ejecutado en esta etapa):

```bash
uv pip install --python mars_ml/.venv/bin/python \
  -r mars_ml/requirements.txt -r mars_ml/requirements-training.txt
mars_ml/.venv/bin/python -m mars_ml.training.train_segmentation \
  --manifest mars_ml/datasets/earth/sahara/manifest.json \
  --output-dir mars_ml/models/runs/sahara_unet
```

`train_segmentation.py` se niega a entrenar si faltan datos, no hay splits
suficientes, hay fuga de grupos o no existe PyTorch. Si entrena, escribe
checkpoint y `training_report.json` con métricas producidas por esa ejecución.
No hay resultados de entrenamiento preexistentes.

### Etiquetado

1. Seleccionar un AOI y escenas con fechas verificables.
2. Confirmar nubosidad, sombras y calidad del registro.
3. Dibujar máscaras binarias de dunas (0 = fondo, >0 = duna).
4. Mantener la misma geometría que la imagen.
5. Nombrar región, secuencia y fecha de forma trazable.
6. Revisar que una misma secuencia no se reparta entre train y test.
7. Documentar criterio de etiqueta, incertidumbre y calidad.

## 12. Evaluación

`training/evaluate.py` implementa, sin resultados precalculados:

- Segmentación: IoU, Dice, precision, recall y conteos TP/FP/FN/TN.
- Registro: matches, inliers, ratio, RMS y error mediano.
- Desplazamiento: error vectorial, error absoluto de magnitud y diferencia
  angular, tanto en píxeles como en metros cuando hay escala.

Ninguna métrica se publica en este README porque todavía no se ejecutó una
evaluación contra datos etiquetados reales. Los tests verifican las fórmulas con
casos sintéticos.

## 13. Inferencia y visualización

`inference/dune_analysis.py` orquesta:

1. Carga y validación.
2. Registro y control de confiabilidad.
3. Segmentación o carga de máscaras.
4. Alineación de la observación móvil.
5. Morfología por fecha.
6. Desplazamiento y consistencia.
7. Migración si hay fechas, escala y registro confiable.
8. JSON y PNGs.

Ejemplo de ejecución (requiere archivos locales):

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -m mars_ml.inference.dune_analysis \
  --reference ruta/referencia.tif \
  --moving ruta/observacion.tif \
  --reference-mask ruta/referencia_mask.png \
  --moving-mask ruta/observacion_mask.png \
  --reference-date 2019-04-24T10:56:29Z \
  --moving-date 2025-04-27T10:56:41Z \
  --meters-per-pixel 10 \
  --output mars_ml/outputs/erg_chebbi_demo
```

Salidas por defecto: imagen de referencia, máscaras, imagen alineada, diferencia,
vectores de desplazamiento, morfología por fecha y `analysis_report.json`.

Estados posibles:

- `registration_unreliable`: no se calcula desplazamiento.
- `displacement_unreliable`: el registro pasó, pero las estimaciones no son
  consistentes.
- `analysis_complete_without_migration`: hay análisis 2D, faltan fechas o escala.
- `analysis_complete`: incluye migración aparente 2D.

## 14. Pruebas

Cubren:

- Carga, canales, normalización, nodata, recorte y roundtrip GeoTIFF.
- Registro con traslación conocida y rechazo de pares sin textura.
- Segmentación sintética y rechazo de imágenes planas.
- Centroides, Farneback, Lucas-Kanade, escala métrica y gating por registro.
- Morfología, migración, parámetros planetarios y observaciones ambientales.
- Catálogo de escenas y validación de metadatos.
- Preparación de dataset, splits agrupados y fuga de datos.
- Métricas de evaluación.
- Inferencia end-to-end con imágenes sintéticas y retención por registro no
  confiable.

Ningún test usa red ni servicios externos.

## 15. Limitaciones

- No hay dataset etiquetado ni modelo entrenado.
- El baseline clásico no distingue de forma semántica una duna de otro terreno
  texturado.
- No hay corrección radiométrica, BRDF, sombras ni normalización multitemporal
  completa.
- No se usan máscaras de nubes/shadow del producto L2A.
- El registro puede fallar con cambios estacionales, agua, vegetación o escenas
  de baja textura.
- El movimiento se mide en 2D aparente; no hay cambio vertical ni flujo de
  sedimento.
- La migración por centroide supone que el cuerpo segmentado representa la duna.
- La escala métrica debe verificarse; una resolución nominal no garantiza
  precisión efectiva en todas las zonas.
- No se modela perspectiva, rugosidad, calibración de la cámara ni órbita.
- No se ha validado nada en Marte ni con imágenes HiRISE/CTX.
- Los datos ambientales no están integrados con observaciones marcianas.
- Los tests usan datos sintéticos; no son evidencia de desempeño científico.

## 16. Próximos pasos recomendados

1. Descargar y validar un subconjunto pequeño de las escenas Sentinel-2 ya
   verificadas, conservando checksums y ventanas de recorte.
2. Generar máscaras etiquetadas por duna y mediciones de referencia.
3. Evaluar sistemáticamente el registro en la secuencia 2019–2025.
4. Sustituir o complementar el baseline con U-Net entrenada y comparar métricas.
5. Incorporar enmascaramiento de nubes/sombras y control de iluminación.
6. Validar desplazamientos contra mediciones independientes o anotaciones
   manuales.
7. Definir un protocolo de calibración ambiental con procedencia y unidades.
8. Solo después, construir pares HiRISE/CTX marcianos con geometría y escala
   verificadas, y calibrar transporte eólico marciano.

No avanzar a predicción operacional de migración marciana hasta completar las
etapas de datos, etiquetado, validación y calibración.

## 17. Reglas de trazabilidad

- No inventar escenas, fechas, bboxes, resoluciones, observaciones ni métricas.
- No presentar fixtures sintéticos como imágenes satelitales.
- No afirmar que existe un modelo entrenado sin checkpoint y reporte.
- No convertir píxeles a metros sin escala verificada.
- No calcular desplazamiento si el registro no es confiable.
- No usar datos climáticos generales como si fueran simultáneos a la imagen.
- No aplicar tasas terrestres a Marte.
- No modificar `frontend/` ni `backend/` desde este módulo.

## 18. Etapa 2 — ingesta, migración y modelos

La segunda etapa añade procesamiento sobre metadatos y fixtures sintéticos, sin
descargar píxeles ni entrenar un modelo reutilizable.

### Ingesta

`ingestion/catalog.py` carga y valida `dataset.json` y el manifiesto raíz.
Comprueba IDs, fechas UTC, rutas de archivos, checksums declarados, estados de
píxeles/etiquetas y coherencia de series temporales. `ingestion/readers.py`
inspecciona rasters, vectores, tablas y productos PDS3; no inventa metadatos
ausentes. `ingestion/annotations.py` rasteriza polígonos o máscaras de anotación
sin asumir orden de filas. `ingestion/download.py` genera un plan de descarga
solo con URLs y archivos permitidos; por defecto es `dry_run`.
`ingestion/validation.py` incluye `verify_manifest_files()`, que comprueba en
disco tamaño y SHA-256 de los archivos descargados. Si un archivo no declara
SHA-256, el estado es `size_verified`, no `verified`: el checksum sigue sin
comprobarse.

`computer_vision/image_io.py` incorpora:

- Validación de unidades lineales del CRS: una resolución en grados no se
  convierte en metros.
- `load_pds_image()` para imágenes PDS con etiqueta `.lbl`/`.xml`.
- `checksum_file()`, `parse_pds3_label()` y
  `acquisition_datetime_from_label()`.
- `SpatialMetadata.linear_units` y `ensure_metric_resolution()`.

### Métodos de migración

`aeolian_dynamics/migration_analysis.py` separa observaciones por método:

- `centroid`: desplazamiento del centroide del cuerpo segmentado.
- `crest`: desplazamiento de crestas, cuando la geometría lo permite.
- `advancing_front`: reservado; no implementado.
- `geometry_change`: diagnóstico morfológico, nunca una tasa de migración.

Cada observación conserva distancia, intervalo, tasa, azimut, incertidumbre,
método, estado de validez y motivos de rechazo. `summarize_methods()` agrupa
tasas válidas y `method_agreement()` compara métodos sin fusionarlos
silenciosamente. La incertidumbre de distancia se propaga a la tasa; la tasa no
se calcula sin escala, fechas o registro confiable.

`aeolian_dynamics/migration_models.py` ofrece modelos Ridge y Random Forest con
validación agrupada (`GroupKFold`). Los grupos representan campos o secuencias,
no filas individuales. Los modelos rechazan tasas negativas, NaN y grupos
insuficientes. Las predicciones negativas se recortan a cero y el reporte debe
conservar esa nota.

`aeolian_dynamics/hybrid_model.py` exige una tabla explícita de covariables
ambientales. Rechaza covariables ausentes o no finitas y puede exigir fuentes
con `metadata_verified=True`. No rellena huecos ni convierte climatología en
medición simultánea.

### Entrenamiento y validación

`training/train_classifier.py` construye muestras de píxeles con features
locales y entrena un clasificador de dunas con splits agrupados. Guarda y carga
con `joblib` solo si se solicita explícitamente; los tests no dejan modelos
versionados.

`training/train_migration.py` parte de una tabla CSV o XLSX explícita de
observaciones, calcula tasas con `migration_analysis` y reporta métricas de
validación agrupada. No escribe checkpoints ni presenta resultados de prueba
como validación científica.

`training/migration_metrics.py` calcula MAE, RMSE, sesgo, error angular y
cobertura de intervalos. `validation/published_measurements.py` compara una
observación con un rango agregado publicado; rechaza usar el rango como etiqueta
por duna y conserva la limitación en el resultado.

`inference/mars_sequence.py` orquesta pares consecutivos de observaciones
fechadas: registro, desplazamiento, migración, geometría y contexto ambiental.
Si el registro no es confiable, no hay escala o faltan fechas, devuelve el
motivo y no una tasa. No implementa `advancing_front`. Las fechas se normalizan
a UTC y la configuración de registro se pasa explícitamente a cada par.

El mismo módulo puede ejecutarse sobre un plan JSON local:

```json
{
  "config": {
    "meters_per_pixel": 6.0,
    "method": "centroid",
    "include_geometry": true
  },
  "observations": [
    {
      "observation_id": "early",
      "product_id": "PRODUCT_A",
      "datetime_utc": "2020-01-01T00:00:00Z",
      "image": "inputs/early.tif",
      "mask": "inputs/early_mask.tif"
    },
    {
      "observation_id": "late",
      "product_id": "PRODUCT_B",
      "datetime_utc": "2021-01-01T00:00:00Z",
      "image": "inputs/late.tif",
      "mask": "inputs/late_mask.tif",
      "environment": {
        "source": "Mars Climate Database",
        "source_type": "model",
        "scene_id": "PRODUCT_B",
        "observation_datetime_utc": "2021-01-01T02:00:00Z",
        "wind_speed_m_s": 4.0
      }
    }
  ]
}
```

```bash
mars_ml/.venv/bin/python -m mars_ml.inference.mars_sequence   --plan plan.json --output outputs/mars_sequence.json
```

Las rutas son relativas al plan. Las máscaras deben ser de una sola banda y
binarias; las imágenes GeoTIFF/JP2 se leen con Rasterio y los PNG/JPEG con
OpenCV. Sin escala métrica o sin registro confiable no se escribe una tasa.

### Pruebas añadidas

- `tests/test_ingestion.py`: manifiestos, verificación de tamaño/SHA-256,
  lectores, anotaciones, PDS3 y plan de descarga.
- `tests/test_migration_analysis.py`: observaciones por método, incertidumbre,
  rechazo de geometría como tasa y comparación de métodos.
- `tests/test_migration_models.py`: modelos agrupados, métricas, híbrido,
  fuentes ambientales y rangos publicados.
- `tests/test_train_classifier.py`: features, clasificador, validación agrupada
  y roundtrip `joblib`.
- `tests/test_train_migration.py`: tabla explícita, CSV, grupos y reporte sin
  checkpoint.
- `tests/test_mars_sequence.py`: secuencia, falta de escala, configuración de
  registro, normalización de fechas, plan JSON, CLI y contexto ambiental.

Resultado: **96 tests passed**, sin red. Siguen siendo pruebas de software con
fixtures sintéticos; no validan migración marciana real.
