# BRIDGES MAVORS — Etapa 4: Georreferenciación y procesamiento científico

Consultá AGENTS.md, IMPLEMENTATION_STATUS.md y toda la documentación previa.

Conservá las funcionalidades de las etapas 1 a 3.

## Objetivo

Relacionar el modelo tridimensional con ubicaciones reales de Marte e implementar una infraestructura reproducible de consulta científica por posición.

No generar modelos 3D adicionales para representar las variables.

## Georreferenciación

Localizá los archivos utilizados para generar MapaMarteN.glb:

- GeoTIFF.
- DEM o DTM.
- Imágenes orbitales.
- Scripts Python.
- Archivos JSON.
- Archivos NumPy.
- Matrices binarias.
- Metadatos.
- Proyecto Blender.

Identificá:

- Región real.
- Proyección cartográfica marciana.
- Sistema de referencia.
- Convención de latitud planetocéntrica o planetográfica.
- Longitud positiva hacia el este u oeste.
- Convención de longitudes.
- Resolución original.
- Extensión geográfica.
- Origen local.
- Escala horizontal.
- Escala vertical.
- Desplazamientos.
- Rotaciones.
- Orientación de los ejes.
- Referencia vertical de elevaciones.
- Valores NoData.

No asumir que corresponde a Jezero.

No utilizar sistemas de referencia terrestres para representar coordenadas marcianas.

No deducir la ubicación únicamente mediante similitud visual.

Implementá funciones equivalentes a:

- modelToGeographic(x, y, z)
- geographicToModel(latitude, longitude, elevation)
- modelToGrid(x, z)
- gridToModel(row, column)

Verificá las transformaciones utilizando puntos de control conocidos.

Considerá centros de píxel, orden de matrices y desplazamientos.

## Alturas científicas

Recuperá las elevaciones reales utilizadas para construir el terreno.

La escena indica una exageración vertical de tres veces, pero debe verificarse la transformación completa.

Investigá:

- Factor de exageración.
- Desplazamiento vertical.
- Elevación de referencia.
- Normalización.
- Transformaciones de objetos.
- Unidades.

No asumir que dividir Y por tres recupera elevaciones absolutas.

Mantener por separado:

- visual_elevation: alturas de representación.
- scientific_elevation: elevaciones científicas.

Utilizar las primeras para posicionar elementos visuales y las segundas para cálculos geográficos.

## Fuentes científicas prioritarias

Tenés autorización para consultar fuentes públicas y descargar los datos necesarios, respetando las restricciones del entorno.

Verificá disponibilidad, documentación, cobertura, unidades, resolución y condiciones de uso.

### NASA Mars Trek

https://trek.nasa.gov/mars/

https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars

Referencia cartográfica:

https://trek.nasa.gov/mars/#v=0.1&x=-3.1011212579707035&y=-21.5046735396579&z=2

Buscar productos de elevación, imágenes orbitales, albedo, polvo, minerales, propiedades térmicas y cartografía marciana.

### USGS Astrogeology

https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars

Buscar DEM, DTM, MOLA, HRSC, CTX, HiRISE, mapas geológicos y servicios geoespaciales.

### NASA Planetary Data System

https://pds.nasa.gov/

Buscar productos científicos originales, identificadores, metadatos y documentación.

### Mars Climate Database

https://www-mars.lmd.jussieu.fr/mcd_python/

Consultar variables modeladas de temperatura superficial y atmosférica, viento, presión, polvo y flujos de radiación.

Verificar los parámetros disponibles para longitud solar marciana Ls, hora local y escenarios climáticos.

No presentar sus resultados como pronósticos meteorológicos actuales.

### Arizona State University — Mars Global Data Sets

https://mars.asu.edu/data/

Buscar productos de inercia térmica, polvo superficial, albedo, abundancia de rocas, elevación y rugosidad.

### Martian Atmospheric Dust Climatology

https://www-mars.lmd.jussieu.fr/mars/dust_climatology/

Buscar información histórica y climatológica de opacidad óptica, variaciones estacionales y tormentas de polvo.

### NASA — Radiation Measurements on Mars

https://science.nasa.gov/resource/radiation-measurements-on-mars/

Utilizar mediciones RAD como referencia científica de radiación ionizante.

No extrapolar mediciones locales como si fueran mapas globales de alta resolución.

### NASA — Perseverance Raw Images

https://mars.nasa.gov/mars2020/multimedia/raw-images/

Utilizar como referencia visual de colores, rocas y materiales cuando corresponda a la región.

No utilizar fotografías individuales como fuente cuantitativa de elevación o estabilidad mecánica.

### NASA — Curiosity's Proposed Path up Mount Sharp

https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/

Utilizar como referencia científica y visual de planificación de recorridos.

Este recurso corresponde al cráter Gale. No mezclar sus datos con otras regiones.

### HiRISE

https://hirise.lpl.arizona.edu/

Buscar datos de alta resolución cuando exista cobertura sobre la región correspondiente.

### DEM de Jezero

https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif

Fue considerado durante la etapa inicial del proyecto.

Utilizarlo únicamente si se confirma que corresponde a la región del modelo. No sustituir un DEM HRSC de otra ubicación por este archivo.

## Variables científicas

Prepará consultas para:

### Topografía

- Elevación.
- Pendiente.
- Orientación de pendiente.
- Rugosidad.
- Desnivel local.

### Temperatura

- Temperatura superficial.
- Temperatura atmosférica.
- Inercia térmica.
- Variación durante el día marciano.
- Mínimos y máximos según el escenario.

### Atmósfera

- Presión.
- Velocidad y dirección del viento.
- Polvo atmosférico.
- Opacidad óptica.
- Escenarios de polvo elevado.

### Superficie

- Polvo superficial.
- Albedo.
- Abundancia de rocas.
- Geología.
- Mineralogía.
- Propiedades térmicas.
- Variables indirectas de movilidad.

### Radiación

- Flujo solar.
- Exposición solar.
- Iluminación topográfica.
- Radiación ultravioleta, si existen datos.
- Radiación ionizante, únicamente si existe un modelo aplicable y científicamente fundamentado.

## Procesamiento

Implementá scripts reproducibles para:

- Descargar archivos.
- Verificar integridad.
- Registrar SHA-256 cuando sea viable.
- Recortar la región.
- Detectar NoData.
- Convertir unidades.
- Reproyectar.
- Procesar matrices.
- Preparar consultas.
- Generar metadatos.
- Almacenar datos en caché.

Utilizá herramientas adecuadas como Rasterio, GDAL, NumPy, pyproj, SciPy o Xarray.

No utilizar los colores de una imagen renderizada como valores científicos sin una conversión documentada.

No descargar datasets planetarios completos desde el navegador para cada consulta.

## Resoluciones científicas

Las variables pueden tener resoluciones espaciales muy diferentes.

No forzar todas a una precisión de 250 metros.

Mantener la resolución científica original.

Si una celda ambiental cubre cientos de bloques del modelo, permitir que todos compartan el valor correspondiente.

No inventar variaciones locales.

Utilizar remuestreos adecuados y documentados.

No interpolar zonas sin cobertura de forma injustificada.

## Metadatos

Cada dato debe incluir:

- Nombre.
- Valor.
- Unidad.
- Fuente.
- Producto científico.
- Resolución espacial.
- Resolución temporal.
- Fecha o escenario.
- Método.
- Incertidumbre, cuando exista.
- Estado de disponibilidad.

Diferenciar:

- Observed.
- Derived.
- Modeled.
- Estimated.
- Unavailable.

Representar datos faltantes mediante null o estados explícitos.

No representar información desconocida como cero.

## Cálculos topográficos

Calcular pendientes, orientación y rugosidad utilizando el DEM real.

Para desplazamientos entre celdas:

pendiente = atan2(abs(diferenciaElevacion), distanciaHorizontal)

Documentar el método de gradiente utilizado para análisis por celda.

Comprobar las distancias horizontales reales según la proyección.

## Infraestructura de consulta

Utilizá el backend FastAPI existente o una solución local eficiente.

Diseñá servicios equivalentes a:

- GET /api/terrain/metadata
- GET /api/terrain/point
- GET /api/science/sources
- GET /api/science/variables
- GET /api/mission/scenarios

Adaptá los nombres a la arquitectura actual.

Implementá validación, caché, manejo de errores, unidades, metadatos y comprobación de cobertura.

## Documentación

Actualizar SOURCES.md con:

- Producto.
- Institución.
- Misión e instrumento.
- URL original.
- URL de descarga.
- Fecha de acceso.
- Resolución.
- Región.
- Proyección.
- Unidades.
- Referencia temporal.
- Condiciones de uso.
- Transformaciones.
- Limitaciones.

## Si faltan datos

No inventar información.

Si no puede recuperarse la georreferenciación:

- Mantener las consultas geométricas locales.
- Preparar las interfaces científicas.
- Identificar las variables como no disponibles.
- Documentar los archivos exactos necesarios.
- No asociar temperaturas, polvo o radiación a ubicaciones desconocidas.

No detener el desarrollo de funcionalidades independientes.

## Validación y entrega

Comprobá muestras contra los datos originales.

Verificá transformaciones, unidades, resolución, límites, NoData y fuentes.

Entregá:

- Infraestructura geoespacial.
- Metadatos.
- Matrices disponibles.
- Scripts reproducibles.
- Servicios de consulta.
- SOURCES.md actualizado.
- Informe de cobertura y limitaciones.
- IMPLEMENTATION_STATUS.md actualizado.

No implementes todavía la interfaz definitiva de peligros ni el algoritmo A*. Detenete al completar esta etapa.