# Etapa 4 — Georreferenciación y consulta científica

Completada el 2026-11-15 para la infraestructura y los conjuntos disponibles. Se conservaron el GLB original, los chunks, el visor, los marcadores y las rutas. No se generaron otros terrenos ni se implementaron A* o la interfaz definitiva de peligros.

## Registro recuperado

La geometría de MapaMarteN.glb coincide exactamente con el pipeline histórico output-visual. Se reconstruyó el DEM desde data/raw/ez-hrsc200.tif mediante reproyección bilineal y la máscara del polígono guardado: diferencia cero respecto de output-visual/ez-dem.tif. El recorte correspondiente al GLB empieza en la fila 108 y columna 112 de esa matriz histórica. Coinciden la máscara y los 507.538 techos, con diferencia Y máxima cero usando:

`Y = 3 × (round(h / 2) × 2 + 4500)`

El registro se vincula al SHA-256 del original: `8786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48`. Cinco muestras distribuidas del GeoTIFF oficial se verificaron por rangos HTTP, tanto el valor entero como su centro de píxel. Cinco controles procesados y el centro publicado (77° E, 17,5° N) verificaron la conversión en ambos sentidos con error numérico menor de 1e-8 m.

Los reportes están en output-stage4/georeference-validation.json y remote-source-check.json. Son controles de reconstrucción y procedencia; no son un levantamiento independiente ni prueban exactitud absoluta. No se dedujo la ubicación por semejanza visual.

MapaMarte1.blend se leyó en un proceso aislado, sin guardar cambios: escena «Marte - HRSC 250m - Color orbital - Relieve 3x», unidades METRIC, escala 1 y 47 objetos. Su inventario queda registrado. El GLB y su equivalencia con la matriz son la autoridad geométrica. El apartado lineage de terrain_metadata.json identifica y calcula hashes de scripts, GeoTIFF, matrices, máscara, imagen Viking y proyecto Blender.

## Referencia espacial y alturas

Las etiquetas PDS3 e ISIS oficiales declaran Marte, esfera de radio 3.396.190 m, latitud planetocéntrica, longitud positiva al este y dominio [-180°, 180°]. La fuente es simple cilíndrica, nominalmente 200 m/píxel o 0,003374120830641°/píxel. El recorte tiene 1215 × 1185 muestras int16, NoData = -32768, escala 1 y offset 0.

El modelo usa proyección azimutal equidistante centrada en 77° E / 17,5° N, con X = E, Y visual arriba y Z = -N. Una unidad horizontal equivale a un metro; origen E = N = 0 y sin rotación adicional. La región corresponde al buffer de la propuesta NASA EMC denominada Jezero Crater, FID 27, incluido el terreno circundante: no sólo el cráter.

La matriz del modelo tiene 808 × 800 celdas de 250 m proyectados. Esquina de bordes XZ = (-100000, -101000); filas hacia +Z y columnas hacia +X. Centros desplazados 125 m y límites semiabiertos. Los centros válidos abarcan 75,2327345–78,7672655° E y 15,7981540–19,2018223° N; no son los límites vectoriales exactos del polígono.

Las alturas científicas recuperadas conservan el DEM procesado sin cuantizar ni exagerar: -3726,8115 a 654,9348 m. La representación cuantiza cada 2 m y exagera 3× alrededor de -4500 m. La inversa `Y / 3 - 4500` recupera sólo la altura cuantizada, con hasta 1 m de diferencia frente a la matriz procesada. El servicio consulta la matriz científica independiente.

Se preservó la referencia vertical del producto HRSC/MOLA. El catálogo relaciona MOLA con el areoide, pero las etiquetas recuperadas no identifican inequívocamente la realización vertical de toda la mezcla. No se declara altura elipsoidal, un modelo GMM concreto ni incertidumbre local absoluta. No se fusionaron CTX/HiRISE ni se reinterpretó el polígono histórico en otra convención angular.

## Cálculos y resoluciones

Pendiente y orientación usan un plano que pasa por la muestra central, ajustado a sus ocho vecinos. Los desplazamientos este/norte proceden de azimut y distancia geodésica sobre la esfera marciana. La pendiente es atan de la magnitud del gradiente; la orientación es descendente, medida desde el norte verdadero. Se requieren nueve muestras válidas. La orientación de una superficie plana y los vecinos incompletos quedan sin dato.

La rugosidad es el RMS de los residuos del plano en las nueve muestras. El desnivel es máximo menos mínimo en la misma vecindad. No equivalen a estabilidad mecánica ni revelan detalles subpíxel. Hay 504.326 celdas con métricas; pendientes procesadas de 0,003529 a 35,307087°. La función entre celdas aplica atan2(abs(Δh), distancia horizontal geodésica).

La distancia geodésica entre vecinos X varía entre 249,96324 y 250 m en la zona válida. La proyección no conserva todas las distancias. El paso procesado de 250 m tampoco implica observaciones uniformes a esa resolución: el producto mezcla fuentes MOLA y HRSC de detalle variable.

El polvo histórico procede del NetCDF MY36 v2.5, descargado una vez (63,6 MB). La región ocupa una sola celda nativa centrada en 78° E / 17,5° N, con límites [75,81)° E × [15,20)° N. Se conservan 669 soles: 558 con valor y 111 sin datos. Todos los bloques comparten el valor de esa celda y sol; no se interpolan variaciones locales.

La consulta requiere `mars_year=36` y `sol=1…669`. El campo cdod610 es absorción infrarroja a 9,3 µm normalizada a 610 Pa, en Pa/Pa. No representa extinción visible, polvo superficial ni condiciones instantáneas. Se conservan incertidumbre, Ls, ventana de observación, conteo medio, fiabilidad y referencia MJD. Es un promedio diario derivado de observaciones MCS, no un pronóstico. Sólo la caché regional se consulta en el servidor.

Las demás variables tienen contratos, fuentes candidatas y estado Unavailable/null. MCD numérico no está integrado: la web anuncia 6.2 y enlaza documentación 6.1; falta validar un proveedor y su contrato versionado. Los productos coloreados de ASU no se transformaron en valores científicos. RAD de Gale es una referencia, no un mapa de esta región.

## Servicios

Se amplió el backend existente, conservando respuestas data/success y errores estructurados:

- GET /api/v1/terrain/metadata
- GET /api/v1/terrain/point?x=24875&z=-55625&mars_year=36&sol=1
- GET /api/v1/terrain/point?latitude=18.4379318332&longitude=77.4423449153
- GET /api/v1/science/sources
- GET /api/v1/science/variables
- GET /api/v1/mission/scenarios

Un punto acepta X/Z local o latitud/longitud, sin mezclar sistemas. Se validan números finitos, rangos y tiempo. Sin tiempo explícito no se elige un escenario actual. Fuera de la máscara se devuelve cobertura Unavailable y valores null.

La integridad se comprueba al cargar el servicio; las matrices se abren en lectura y se reutilizan mediante memmap y una caché LRU de 2048 celdas. Las consultas no descargan productos externos. Reiniciar el backend después de reprocesar; MARS_SCIENCE_DATA_DIR configura la ubicación del paquete. Si falta ciencia, el visor geométrico sigue funcionando.

frontend/src/services/marsApi.js incorpora las consultas cancelables para su siguiente integración. No se cambió el panel científico: el visor conserva su aviso local conservador hasta consumir explícitamente estos metadatos. No hay indicadores nuevos.

## Reproducción

Desde la raíz:

1. `uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt`
2. `.venv/Scripts/python.exe scripts/download-stage4.py`
3. `.venv/Scripts/python.exe scripts/verify-stage4-source.py`
4. `.venv/Scripts/python.exe scripts/process-stage4.py`
5. `.venv/Scripts/python.exe scripts/process-stage4-dust.py`
6. `.venv/Scripts/python.exe scripts/finalize-stage4.py`
7. `uv pip install --python ops_mars-main/backend/.venv/Scripts/python.exe -r ops_mars-main/backend/requirements.txt`

Desde backend, ejecutar `.venv/Scripts/python.exe -m pytest -q` y luego `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Desde frontend: `npm run test:terrain`, `npm run lint`, `npm run build`.

## Pruebas y límites

Pasaron 37 pruebas de backend y 14 de frontend, además de lint/build. Cubren transformaciones, alturas separadas, límites y NoData, plano analítico, gradiente real contrastado con mínimos cuadrados independiente, entradas inválidas, polvo original/incertidumbre, sol sin datos y ausencia/corrupción de caché. Persisten los avisos previos de bundle grande y TestClient/httpx.

HTTP real verificó los cinco servicios y el catálogo 2D. Veinticinco consultas locales con caché caliente tuvieron mediana de 1,354 ms y máximo de 2,079 ms, incluyendo serialización; no es rendimiento de despliegue ni FPS. Evidencia: 04-api-observations.json. La interfaz del visor no cambió y conserva la evidencia funcional de la Etapa 3. El hash del GLB original permanece intacto.

No se probó una instalación enteramente limpia ni se descargó de nuevo todo el GeoTIFF: el recorte histórico validado sigue siendo dependencia. download_visual.py documenta su descarga original, pero no debe usarse para sobrescribir los archivos preservados. Quedan pendientes el datum vertical detallado, proveedores ambientales restantes y pruebas en móvil físico. No se afirma validación científica externa, seguridad o cobertura de todos los proveedores.
