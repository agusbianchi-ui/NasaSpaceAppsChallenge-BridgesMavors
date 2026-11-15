# Datos adicionales — 2026-11-15

## Incorporado y comprobado

Paquete original extraído en data/additional-science/BridgesMavors_science_pack. TIFF RGB/RGBA conservados como referencias; no se convierten colores a magnitudes físicas. Originales, numeric/ y referencias excluidos de Git por defecto.

Se ejecutó prepare_science.py --thermal both --roughness con el Python de WebApp/backend/.venv. TES: cuatro IMG originales y cuatro etiquetas PDS descargados, tamaños exactos verificados, MSB_INTEGER de 16/8 bits, 3600×7200, planetocéntrico/este, límites y offsets contrastados por el conversor. Se generan dos GeoTIFF int16 y dos máscaras uint8. La máscara original 0 indica interpolación y se excluye por defecto; máscara255/NoData y valores fuera de5..5000 no producen valores. Esta última selección es un filtro del conversor, no una bandera adicional inventada del PDS.

Inercia aparente TES día/noche en J m^-2 K^-1 s^-1/2; 0.05°, aproximadamente2.96 km ecuatoriales; observaciones1999-02 a2004-04. Son dos productos estáticos derivados, no temperatura ni pronóstico horario. Ambas fuentes usan latitud planetocéntrica y longitud este, por lo que se conserva la dirección angular. Sus radios esféricos difieren (3396km TES y3396.190km modelo); no se aplica transformación terrestre ni se cambia el terreno. Consulta por celda nativa sin interpolación espacial, con longitud envuelta a[-180,180). Las coordenadas del GLB siguen convirtiéndose mediante el registro04.

Servicio compartido: app/services/tes_thermal.py, llamado desde terrain_science.py. Campos thermal_inertia_day y thermal_inertia_night; los detalles conservan producto, calidad, celda, método, período y resolución. Se mantiene null para faltantes. No se introduce inercia como costo de ruta ni alerta sin un modelo validado de movilidad; tampoco se modifica IA. Los cuatro TIFF necesarios se comprueban antes de anunciar disponibilidad. El campo genérico antiguo de inercia ASU no sustituye ni promedia los nuevos productos PDS y se omite del panel para evitar duplicación.

Muestras originales verificadas, día/noche respectivamente:
- X24875, Z-55625:312/336.
- X8375, Z-20625:256/291.
- X-50000, Z0:229/233.

En las seis muestras el valor GeoTIFF coincide exactamente con IMG MSB y la máscara original es distinta de0. Evidencia JSON en three-samples.json; test_tes_thermal.py compara nuevamente los originales, prueba NoData/interpolación/antimeridiano. Clic derecho real adicional:18.20712N,76.39214E devuelve296/276 en el panel, captura tes-inspection.png.

## Mapas 2D

TES_Thermal_Inertia, TES_Dust y mola_roughness incorporados al catálogo con sus GetCapabilities oficiales archivados. Siete mapas visualizables en total. Las tres nuevas capas anuncian matrices0–1, formato PNG, default028mm y CRS marciano104905; se conserva el rango nativo. Tres teselas de prueba respondieron HTTP200 image/png. No se equipara la resolución de visualización con la del producto numérico.

Selector movido fuera del contenedor del mapa, debajo, en Mars Explorer y la referencia2D de RoutePlanner. Diseño en flujo y adaptable. Navegador confirmó selección de las tres capas y mapa MOLA cargado; capturas map-mola.png y layers-below.png.

## Bloqueos reales

MOLA: nueve RAW y PDF descargados, todos con MD5 del catálogo del autor verificado. PDF leído con pypdf7.1.0 instalado sólo como herramienta documental. E8R0/1/2:2880×1440, un byte por píxel; escalas0.6/2.4/9.2km. Mide rango intercuartil de curvatura, dimensión longitud inversa; fórmula C=(1/l)10^((DN-511)/80), no RMS del DEM HRSC.

No se publicó todavía un conversor georreferenciado ni consultas MOLA. La documentación dice corte0°E pero su fórmula de longitud con índices iniciados en1 introduce un desplazamiento de píxel; además usa x para latitud y y para longitud sin aclarar filas/columnas y no declara NoData o máscara válida. No se elige silenciosamente un registro o se declara que todos los bytes representan cobertura válida. Requiere reconciliar esos puntos con el autor/producto antes de completar el campo. Rugosidad HRSC actual preservada.

TES_Dust: GetCapabilities valida el mapa visual, pero no especifica definición/unidades de un raster físico. JMARS numeric-maps documenta mapas numéricos sin ofrecer en esa página el archivo exacto; la URL ASU DCI no fue accesible mediante consulta web. No se recuperó producto numérico equivalente verificado. DCI, porcentaje de polvo, abundancia mineral y CDOD atmosférico permanecen distintos. surface_dust sigue null.

Temperaturas, viento, presión, flujo solar y radiación continúan bloqueados según documentación04/05/06. Polvo atmosférico MY36 existente se conserva. La inercia sola no establece movilidad mecánica. Nada se presenta como estabilidad medida o seguridad certificada.

## Reproducción

Desde raíz: WebApp/backend/.venv/Scripts/python.exe data/additional-science/BridgesMavors_science_pack/prepare_science.py --thermal both --roughness. Consultar originales y máscaras; no usar datos sintéticos de tests como producción. Pruebas backend incluidas en suite; frontend lint, test:terrain y build. Para ver cambios ejecutar Start-BridgesMavors.ps1 y abrir /explorer; cargar3D, clic derecho y expandir Thermal.

Validación reproducible: scripts/validate-additional-science.py comprueba18 originales, etiquetas, tamaños, MD5 de autor y seis valores contra IMG/máscaras, generando download-integrity.json y three-samples.json. Resultado final:172 tests Python aprobados,1 omitido por symlink Windows;17 tests frontend aprobados, lint y build correctos (advertencia previa de bundles grandes). El test de catálogo se actualizó para exigir13 entradas y7 visualizables, conservando las anteriores. En navegador se verificó la compilación final y ausencia de errores de consola. Se reinició el backend local para cargar los módulos actualizados; no cambió configuración de IA.
