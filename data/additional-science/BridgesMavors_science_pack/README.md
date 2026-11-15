# Bridges Mavors — paquete científico para inspección del terreno

## Qué contiene
- `references/`: los tres GeoTIFF originales del usuario, intactos. Son imágenes RGB/RGBA, no datos cuantitativos.
- `uploaded_rasters_metadata.json`: metadatos extraídos de los archivos reales (CRS, transformada, dimensiones, NoData, bandas, SHA-256).
- `science_catalog.json`: catálogo de fuentes originales, productos, unidades conocidas y estado de disponibilidad.
- `prepare_science.py`: descarga de originales TES y MOLA; conversión numérica de TES inercia térmica a GeoTIFF, con máscara de calidad.
- `query_science.py`: consulta por latitud planetocéntrica y longitud este; devuelve JSON para el backend.
- `PROMPT_CODEX.md`: instrucciones de integración.
- `requirements.txt`: dependencias de estos scripts; no reemplaza las dependencias de la aplicación.

## Estado real
Los tres originales fueron inspeccionados con Rasterio. Son `uint8` con bandas R/G/B (inercia térmica incluye alfa). No tienen unidades de bandas ni una tabla de calibración científica. Se conservaron sin cambios. No se convirtieron colores a valores físicos.

La descarga externa de archivos binarios no está disponible en el entorno en que se preparó este paquete. Las fuentes y las etiquetas PDS de inercia térmica fueron consultadas, pero **los datos numéricos originales aún no están incluidos**. Ejecutar las descargas desde el equipo de desarrollo con acceso a Internet. El conversor TES está preparado contra las etiquetas PDS; no fue ejecutado sobre los binarios originales. MOLA requiere leer la documentación del autor antes de convertir sus RAW. El producto numérico exacto de TES_Dust no se ha identificado de manera concluyente.

## Uso en Windows (desde la carpeta extraída)
```powershell
python -m pip install -r requirements.txt
python prepare_science.py --thermal both
python prepare_science.py --roughness
python query_science.py 0 0
```
El último comando solo comprueba el funcionamiento de la consulta en un punto marciano de prueba; no implica que ese punto corresponda al modelo del proyecto.

El primer procesamiento descarga unos 156 MB de binarios de inercia (día, noche y máscaras). Se generan cuatro GeoTIFF en `numeric/`: los valores de inercia y las máscaras de día/noche. Se conservan los archivos originales en `raw/`.
El segundo procesamiento descarga los RAW de rugosidad y su PDF de documentación, comprueba MD5 y se detiene; Codex debe decodificar los RAW siguiendo esa documentación, no inferir parámetros.

## Contrato de coordenadas
La consulta TES espera latitud planetocéntrica (no planetográfica) y longitud positiva hacia el este. La imagen PDS usa una esfera de radio 3396 km, norte arriba, 20 píxeles/grado, límites -180..180 y -90..90. La malla 3D requiere una transformación verificada previamente. No interpretar X/Z directamente como grados ni usar EPSG:4326 terrestre. Los TIFF del usuario declaran ESRI:104905, un CRS distinto del CRS esférico del producto PDS; la convención de latitud y cualquier transformación entre productos deben verificarse explícitamente.

## Cómo interpretar los valores
- Inercia térmica aparente: J m^-2 K^-1 s^-1/2; producto derivado de observaciones MGS/TES 1999–2004. Resolución 0,05° (2,96 km en el ecuador). Día/noche son productos distintos, no un termómetro ni una serie horaria. La máscara original 0 significa relleno por interpolación; la consulta lo excluye por defecto. El convertidor marca valores fuera de 5–5000 como NoData; conservar esa decisión documentada.
- Rugosidad MOLA: el producto publicado mide rugosidad a distintas escalas kilométricas. No es el mismo indicador que pendiente local ni rugosidad calculada desde el DEM HRSC. Conservar escala de análisis, método, unidades y cobertura.
- Polvo superficial: NASA Mars Trek distingue `TES_Dust` y `tes_ruffdust`. Verificar los metadatos del primero; para una alternativa independiente se puede usar DCI de Ruff & Christensen (2002) con su propia identificación. DCI menor indica mayor presencia de polvo fino; no es porcentaje ni opacidad atmosférica. JMARS ofrece también TES Surface Dust numérico; verificar su definición y unidades. El PNG de ASU no constituye un archivo numérico.
- Movilidad: usar estas variables como indicios, nunca como mediciones directas de estabilidad o capacidad portante.
- Temperatura, viento, polvo atmosférico y radiación necesitan fuentes adicionales y escenarios adecuados. Consultar MCD y climatología de polvo; no deducirlos de estas tres imágenes.

## Fuentes
- NASA Mars Trek catálogo: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars
- NASA PDS TES: https://pds-geosciences.wustl.edu/missions/mgs/tes-timap.html
- Datos originales: https://pds-geosciences.wustl.edu/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data/
- Rugosidad: https://doi.org/10.5281/zenodo.15734221 y https://doi.org/10.1029/2000JE001259
- ASU JMARS: https://jmars.mars.asu.edu/numeric-maps
- DCI: https://doi.org/10.1029/2001JE001580 ; https://www.mars.asu.edu/~ruff/DCI/dci.html
- DCI adaptación de investigación (verificar procesamiento, no confundir con original): https://doi.org/10.17169/refubium-50906
- ASU catálogo gráfico: https://mars.asu.edu/data/
- Polvo atmosférico: https://www-mars.lmd.jussieu.fr/mars/dust_climatology/index.html
- MCD: https://www-mars.lmd.jussieu.fr/mcd_python/
