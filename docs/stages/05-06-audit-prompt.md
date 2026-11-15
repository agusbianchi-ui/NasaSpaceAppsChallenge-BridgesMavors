# BRIDGES MAVORS — Auditoría, corrección y finalización de las etapas 5 y 6

## 1. Contexto

Estamos desarrollando Bridges Mavors para NASA Space Apps Challenge 2026, en el desafío Interplanetary Survival Guide: Martian Map.

La aplicación integra un mapa tridimensional voxelizado de Marte inspirado en Death Stranding 2, información científica y herramientas de planificación de expediciones.

El proyecto actualmente contiene dos líneas de desarrollo que ya fueron integradas correctamente:

- El visor tridimensional, navegación, datos científicos y planificación desarrollados por mí.
- El sistema de inteligencia artificial desarrollado por mi compañero.

Las etapas 5 y 6 fueron implementadas mediante OpenCode utilizando las especificaciones originales, pero sospecho que algunas funcionalidades no fueron implementadas correctamente, están incompletas o no se comportan como deberían.

Quiero que realices una auditoría exhaustiva y posteriormente corrijas y completes ambas etapas.

No reconstruyas la aplicación desde cero.

No elimines las funcionalidades que ya funcionan.

No reviertas la integración con la inteligencia artificial.

No avances hacia nuevas etapas hasta que las etapas 5 y 6 hayan sido verificadas.

## 2. Documentación obligatoria

Antes de modificar el código, consultá:

- AGENTS.md
- README.md
- docs/PROJECT_SPEC.md
- docs/IMPLEMENTATION_STATUS.md
- docs/SCIENTIFIC_LIMITATIONS.md
- docs/DATA_DICTIONARY.md
- docs/ARCHITECTURE.md
- docs/DESIGN_GUIDELINES.md
- docs/stages/05-hazard-indicators.md
- docs/stages/06-route-planning.md
- SOURCES.md

Si algunos archivos no existen, utilizá la documentación equivalente disponible.

No asumir que una funcionalidad está correctamente implementada solamente porque IMPLEMENTATION_STATUS.md la identifica como completada.

Verificá el código y el comportamiento real.

## 3. Inspección inicial de la aplicación

Analizá el estado actual del proyecto y comprobá el funcionamiento real de las funcionalidades correspondientes a las etapas 5 y 6.

Utilizá herramientas de navegador, Playwright, DevTools, capturas de pantalla o cualquier herramienta de inspección disponible cuando resulte necesario.

No te limites a leer los archivos.

Inspeccioná especialmente:

- Mars Explorer.
- Route Planner.
- Terrain Analysis.
- El visor tridimensional.
- Los paneles de inspección.
- Los indicadores de peligro.
- El selector de condiciones de misión.
- El sistema de planificación manual.
- El sistema de planificación automática.
- Las conexiones con el backend.
- La integración con el asistente de inteligencia artificial.

Revisá errores de consola, errores de red, solicitudes fallidas, estados de carga y problemas de rendimiento relacionados con las funcionalidades que estás auditando.

Si no podés realizar determinadas pruebas visuales, indicá expresamente esa limitación y ejecutá las comprobaciones alternativas disponibles.

## 4. Auditoría antes de modificar

Identificá todos los cambios correspondientes a las etapas 5 y 6 realizados por OpenCode.

Revisá el historial de Git si está disponible.

Clasificá cada funcionalidad como:

- Correctly implemented.
- Partially implemented.
- Incorrectly implemented.
- UI only.
- Missing.
- Blocked by scientific data.

Creá un archivo:

docs/AUDIT_STAGES_05_06.md

Para cada funcionalidad documentá:

- Comportamiento esperado.
- Comportamiento actual.
- Archivos responsables.
- Problemas encontrados.
- Causa técnica.
- Datos científicos utilizados.
- Correcciones necesarias.
- Prioridad.
- Pruebas correspondientes.

Realizá esta auditoría antes de comenzar una refactorización.

No me entregues solamente el informe: después de identificar los problemas, corregilos.

## 5. Reglas de preservación

Conservá:

- El modelo MapaMarteN.glb y sus versiones optimizadas.
- La geometría voxelizada.
- Los colores originales.
- La navegación mediante mouse y pantalla táctil.
- Las funcionalidades de las etapas anteriores.
- El mapa 2D, si continúa formando parte del proyecto.
- El diseño general.
- Los componentes funcionales.
- La integración con la inteligencia artificial.
- Los servicios y configuraciones de mi compañero.

No eliminar ni sobrescribir archivos originales.

No realizar refactorizaciones masivas si pueden corregirse los problemas mediante cambios localizados.

No utilizar Untitled1.glb.

Mantener el idioma inglés de la interfaz.

## 6. Arquitectura científica obligatoria

Debe existir un único terreno tridimensional como representación visual.

Las variables científicas deben mantenerse independientes de la geometría.

No quiero:

- Un modelo 3D diferente para cada variable.
- Modelos coloreados según temperatura, polvo o radiación.
- Capas raster planas superpuestas al terreno.
- Valores ambientales aleatorios.
- Indicadores colocados arbitrariamente.
- Datos simulados presentados como mediciones reales.

Los indicadores, las consultas por punto y las rutas deben utilizar la misma infraestructura científica.

Verificá que exista una fuente de verdad compartida para:

- Transformaciones geográficas.
- Elevaciones.
- Condiciones ambientales.
- Parámetros de misión.
- Evaluación de riesgos.
- Marcadores.
- Rutas.

No permitir que el panel de inspección, el motor de peligros y el planificador utilicen datos contradictorios.

---

# PARTE A — CORRECCIÓN DE LA ETAPA 5

## 7. Inspección interactiva de puntos

Verificá que el usuario pueda hacer clic derecho sobre cualquier posición válida del terreno.

El comportamiento esperado es:

1. Detectar si fue un clic derecho o un arrastre.
2. Obtener la intersección real con el terreno mediante Raycaster.
3. Obtener sus coordenadas tridimensionales.
4. Convertirlas a coordenadas geográficas marcianas verificadas, cuando estén disponibles.
5. Consultar los datos correspondientes a esa posición.
6. Mostrar un marcador temporal sobre el punto.
7. Abrir el panel científico.

El clic derecho y arrastrar debe continuar rotando e inclinando el mapa.

Un clic derecho sin arrastrar debe inspeccionar la posición.

No abrir el menú contextual del navegador dentro del visor.

En dispositivos táctiles, utilizar una pulsación prolongada o un modo explícito de inspección.

Diferenciar correctamente los gestos de navegación, selección y planificación.

Comprobá que al seleccionar una montaña, un valle y una región plana, las consultas correspondan realmente a diferentes posiciones.

No reutilizar datos de un punto anterior por error.

Manejar consultas simultáneas, cancelaciones y respuestas fuera de orden.

## 8. Panel científico

Revisá y completá el panel de información contextual.

Debe mostrar, cuando existan datos válidos:

### Topografía

- Elevation.
- Slope.
- Aspect.
- Roughness.

### Condiciones térmicas

- Surface temperature.
- Atmospheric temperature.
- Thermal inertia.

### Atmósfera

- Atmospheric dust.
- Dust optical depth.
- Wind speed.
- Wind direction.
- Atmospheric pressure.

### Superficie

- Surface dust.
- Rock abundance.
- Geology.
- Mineralogy.
- Estimated mobility difficulty.

### Radiación

- Solar irradiance.
- Solar exposure.
- Ionizing radiation, únicamente si existe información científica aplicable.

Para cada variable, permitir consultar:

- Valor.
- Unidad.
- Fuente.
- Resolución espacial.
- Referencia temporal.
- Tipo de dato.
- Incertidumbre, cuando esté disponible.
- Limitaciones.

Diferenciar:

- Observed.
- Derived.
- Modeled.
- Estimated.
- Unavailable.

No presentar información desconocida como cero.

No utilizar valores ficticios para completar el panel.

No mostrar latitudes o longitudes reales si la georreferenciación todavía no está validada.

El panel debe ser compacto, legible y no ocultar innecesariamente el terreno.

Permitir utilizar el punto inspeccionado como origen, destino o waypoint.

## 9. Validación de los datos científicos

Investigá qué fuentes utilizó OpenCode y si están realmente integradas.

Verificá la existencia de archivos descargados, matrices, metadatos, servicios y resultados reproducibles.

No considerar una fuente incorporada únicamente porque aparece su nombre o URL en la interfaz.

Comprobá especialmente:

- DEM HRSC, MOLA u otros productos utilizados para generar el modelo.
- Mars Climate Database.
- NASA Mars Trek.
- USGS Astrogeology.
- NASA Planetary Data System.
- Arizona State University Mars Global Data Sets.
- Martian Atmospheric Dust Climatology.
- Datos RAD de Curiosity.

Fuentes prioritarias:

https://trek.nasa.gov/mars/

https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars

https://pds.nasa.gov/

https://www-mars.lmd.jussieu.fr/mcd_python/

https://mars.asu.edu/data/

https://www-mars.lmd.jussieu.fr/mars/dust_climatology/

https://science.nasa.gov/resource/radiation-measurements-on-mars/

Verificá que los productos correspondan a la región real del modelo.

No asumir que corresponde al cráter Jezero.

No utilizar el relieve visual exagerado tres veces como elevación científica real.

Si todavía falta la georreferenciación, identificá este bloqueo y no inventes variables ambientales por posición.

No generar variaciones espaciales superiores a la resolución nativa de las fuentes.

## 10. Indicadores permanentes de peligro

Esta es una de las principales características del proyecto.

El mapa debe mostrar indicadores visuales permanentes cuando existan regiones con condiciones críticas o desfavorables.

Categorías:

- Steep slope.
- Extreme heat.
- Extreme cold.
- Atmospheric dust.
- Strong winds.
- Mobility risk.
- Radiation exposure.
- Unknown conditions.

Los indicadores deben generarse a partir de datos y umbrales documentados.

No colocarlos manualmente en posiciones aleatorias para mejorar la estética.

Cada indicador debe:

- Estar asociado a una región o posición real.
- Permanecer anclado al terreno.
- Mantener su posición al mover la cámara.
- Mantener su posición al cambiar el zoom.
- Mantener su alineación al cambiar el nivel de detalle.
- Ser seleccionable.
- Mostrar su categoría.
- Mostrar su gravedad.
- Utilizar un icono reconocible.
- Permitir consultar la causa de la advertencia.

Utilizar indicadores holográficos inspirados en Death Stranding 2.

No depender exclusivamente del color.

## 11. Apariencia y comportamiento de los indicadores

Analizá las capturas y el video de referencia.

Quiero indicadores que parezcan formar parte del mapa tridimensional y no botones de una interfaz convencional flotando arbitrariamente por la pantalla.

Implementá:

- Iconos orientados hacia la cámara cuando sea apropiado.
- Líneas de anclaje al terreno.
- Etiquetas discretas.
- Tamaño visual legible.
- Selección mediante clic o toque.
- Tratamiento adecuado de la oclusión.
- Diferenciación por categoría y gravedad.

Los indicadores críticos deben permanecer identificables.

No permitir que queden completamente inutilizables al acercar o alejar la cámara.

No generar miles de objetos independientes si pueden agruparse.

## 12. Agrupación espacial

Verificá que las regiones peligrosas contiguas se agrupen correctamente.

Implementá clustering o componentes conectados.

Cuando la cámara esté alejada:

- Agrupar advertencias.
- Mostrar cantidad de peligros.
- Indicar gravedad máxima.

Cuando la cámara se acerque:

- Separar los grupos.
- Mostrar advertencias más específicas.
- Permitir inspeccionar cada región.

Un peligro que afecta una región extensa no debe interpretarse como un único punto aislado.

Cuando sea necesario, mostrar su extensión mediante contornos tridimensionales adaptados al relieve.

No superponer planos sobre el terreno.

## 13. Evaluación científica de los peligros

### Pendientes

Calcular las pendientes a partir de elevaciones científicas y distancias horizontales verificadas.

No utilizar directamente las alturas exageradas del GLB.

Si solo existen datos visuales, identificar los resultados como estimaciones geométricas preliminares.

### Temperatura

Diferenciar temperatura superficial y atmosférica.

Considerar tanto temperaturas altas como bajas.

Los umbrales deben depender de la configuración de la misión y no presentarse como límites oficiales de la NASA.

### Polvo

Diferenciar polvo superficial de polvo atmosférico.

No presentar climatologías históricas como tormentas actuales.

Si una fuente tiene resolución regional, mostrar advertencias regionales.

### Suelo y movilidad

No afirmar que se conoce la estabilidad mecánica exacta del suelo.

Cuando existan datos suficientes, utilizar pendiente, rugosidad, abundancia de rocas, inercia térmica y geología para construir un índice estimado de dificultad de desplazamiento.

Documentar su metodología.

Si faltan datos, mostrar Unknown mobility conditions.

### Radiación

Separar flujo solar, exposición ultravioleta y radiación ionizante.

No asumir que una zona a la sombra protege de la radiación cósmica.

No extrapolar directamente mediciones RAD de Curiosity a cada posición de Marte.

No generar alertas radiológicas locales sin información científica suficiente.

## 14. Configuración de la misión

Verificá que los controles disponibles tengan efectos reales.

Permitir configurar:

- Solar longitude Ls.
- Local solar time.
- Climate scenario.
- Dust scenario.
- Walking or rover.
- Estimated travel speed.
- Maximum slope.
- Thermal limits.
- Prioridades de planificación.

Los valores iniciales deben identificarse como hipótesis de simulación.

Al modificar las condiciones, actualizar:

- Datos científicos consultados.
- Indicadores de peligro.
- Evaluación de riesgos.
- Costos de planificación.

No cambiar la geometría del terreno.

Si una ruta fue calculada bajo condiciones anteriores, marcarla como desactualizada y permitir recalcularla.

Verificá que los selectores no sean elementos puramente decorativos.

---

# PARTE B — CORRECCIÓN DE LA ETAPA 6

## 15. Auditoría del planificador

Inspeccioná la implementación actual de A* y determiná:

- Si realmente existe un algoritmo de búsqueda.
- Si utiliza la cuadrícula del terreno.
- Si utiliza elevaciones reales o visuales.
- Si consulta las variables ambientales.
- Si las estrategias modifican efectivamente la función de costo.
- Si evita posiciones inválidas.
- Si respeta las pendientes máximas.
- Si utiliza datos precalculados o recorridos fijos.
- Si las estadísticas corresponden al camino calculado.

No aceptar una línea recta, una curva predefinida o un recorrido fijo como implementación de A*.

## 16. Selección de origen y destino

El usuario debe poder seleccionar cualquier posición válida del mapa.

Permitir:

- Start.
- Destination.
- Waypoints.
- Edición de puntos.
- Eliminación.
- Undo.
- Clear route.

Los marcadores deben mantenerse correctamente alineados con el relieve.

La selección de posiciones no debe interferir con la navegación ni con la inspección mediante clic derecho.

No limitar la planificación a la ruta de demostración existente.

## 17. Cálculo automático de rutas

Implementá o corregí el algoritmo A* sobre la cuadrícula topográfica.

El algoritmo debe considerar:

- Distancia horizontal.
- Diferencias de elevación.
- Pendientes ascendentes.
- Pendientes descendentes.
- Rugosidad.
- Celdas inválidas.
- Límites del terreno.
- Restricciones de movilidad.
- Peligros disponibles.
- Condiciones térmicas.
- Polvo atmosférico.
- Viento.
- Exposición solar.
- Radiación ionizante cuando existan datos aplicables.

No utilizar alturas visuales exageradas para calcular pendientes científicas.

Comprobar la transformación completa de escalas antes de recuperar métricas reales.

No asumir que dividir directamente las coordenadas Y por tres permite recuperar elevaciones absolutas.

## 18. Función de costo

La función de costo debe combinar factores normalizados.

No sumar directamente metros, grados, temperaturas y radiación sin una metodología.

Implementar costos no negativos y una heurística compatible con la estrategia seleccionada.

Considerar:

- Costo de desplazamiento.
- Penalización por pendiente.
- Penalización por rugosidad.
- Penalización por dificultad de movilidad.
- Penalización por riesgo térmico.
- Penalización por polvo.
- Penalización por viento.
- Penalización ambiental.
- Duración y exposición acumulada.
- Información desconocida.

Documentar fórmulas, unidades, normalización y ponderaciones.

Verificá que los controles de prioridades modifiquen efectivamente los costos utilizados por el algoritmo.

No deben modificar solamente los textos mostrados.

## 19. Estrategias de planificación

Implementá y verificá:

### Shortest route

Prioriza la distancia dentro de las restricciones activas.

### Low-slope route

Prioriza pendientes suaves y evita cambios bruscos de elevación.

### Environmental risk route

Prioriza condiciones ambientales favorables utilizando exclusivamente variables disponibles y verificadas.

### Balanced route

Combina distancia, topografía y condiciones ambientales.

Si no existen datos ambientales suficientes, deshabilitar la estrategia correspondiente o identificarla como parcialmente evaluada.

No afirmar que una ruta está optimizada por radiación o temperatura si esos factores no participaron realmente en el cálculo.

No obligar a que todas las estrategias produzcan rutas diferentes: podrían coincidir legítimamente si el terreno y los costos favorecen el mismo recorrido.

## 20. Restricciones del algoritmo

El algoritmo debe:

- Evitar celdas NoData.
- Evitar posiciones fuera de los límites.
- Respetar la pendiente máxima configurada.
- Comprobar movimientos diagonales.
- Evitar atravesar esquinas de obstáculos.
- Respetar waypoints.
- Respetar regiones excluidas.
- Evaluar correctamente las celdas intermedias.

Si no existe un recorrido válido, informar No valid route found.

No generar automáticamente una línea recta como solución alternativa sin identificarla como trazado manual no evaluado.

Si una posición debe ajustarse a una celda válida, mostrar el cambio explícitamente.

## 21. Datos desconocidos

No interpretar ausencia de información como ausencia de peligro.

Permitir políticas como:

- Avoid unknown areas.
- Allow with penalty.
- Topography-only planning.

Documentar la política aplicada.

Mostrar qué variables se utilizaron realmente.

Si solo está disponible el relieve visual, identificar el resultado como Preliminary geometric route.

No presentar métricas científicas no verificadas.

## 22. Representación tridimensional de las rutas

La ruta calculada debe proyectarse sobre el terreno voxelizado.

No unir posiciones mediante segmentos largos que atraviesen montañas.

Para cada tramo:

1. Obtener sus coordenadas horizontales.
2. Recorrer las celdas correspondientes.
3. Consultar las alturas visuales.
4. Detectar cambios de altura.
5. Construir una línea que siga los escalones.
6. Añadir una separación mínima.
7. Comprobar que la línea no atraviese la geometría.

No utilizar curvas suavizadas que atraviesen bloques o queden suspendidas sobre valles.

La geometría visual exagerada se utilizará únicamente para renderizar la ruta.

Los cálculos científicos deben realizarse mediante las elevaciones correspondientes.

La ruta debe ser claramente visible al rotar, acercar y desplazar el mapa.

Utilizar líneas holográficas azules y marcadores inspirados en Death Stranding 2.

Las alternativas pueden tener estilos o colores diferenciados, sin saturar el mapa.

## 23. Comparación de rutas

Permitir comparar recorridos calculados entre el mismo origen y destino.

Mostrar cuando corresponda:

- Distance.
- Estimated duration.
- Maximum slope.
- Average slope.
- Elevation gain.
- Elevation loss.
- Mobility difficulty.
- Temperature conditions.
- Atmospheric dust.
- Solar exposure.
- Ionizing radiation exposure.
- Unknown data coverage.

Calcular las estadísticas a partir del recorrido real generado.

No utilizar valores hardcodeados.

No incluir estadísticas de variables no disponibles como si estuvieran evaluadas.

Explicar por qué una ruta resulta preferible según las prioridades configuradas.

## 24. Optimización temporal

Si existen datos adecuados, considerar el horario estimado de llegada a cada tramo.

Una ruta más larga puede generar mayor exposición acumulada, aunque tenga menor riesgo instantáneo.

Considerar:

- Velocidad estimada.
- Duración.
- Cambios térmicos.
- Cambios en iluminación.
- Exposición acumulada.

Si la planificación utiliza un escenario ambiental estático, identificarlo claramente.

No afirmar que existe optimización temporal si el algoritmo no la realiza.

## 25. Ruta específica de la expedición

Existe una captura de referencia con un círculo celeste como región de origen y un punto celeste como destino.

También puede estar disponible ruta_marte_preliminar.json.

Los valores preliminares informados fueron:

Origen:

- X: 24875
- Y: 5790
- Z: -55625

Destino:

- X: 8375
- Y: 7350
- Z: -20625

Recorrido preliminar:

- Aproximadamente 155 puntos.
- Distancia horizontal estimada de 44,9 km.
- Pendiente máxima estimada de 5,94 grados.

Verificá estos valores antes de utilizarlos.

Comprobá que las coordenadas correspondan al modelo actual y a sus transformaciones.

No presentar esta ruta como científicamente validada.

Utilizala como prueba de integración y comparación.

Permitir recalcularla utilizando las estrategias disponibles.

## 26. Integración con los datos científicos

El planificador debe utilizar el mismo motor de datos que utiliza el panel de inspección y los indicadores de peligro.

Si un punto presenta una advertencia, el algoritmo debe considerarla cuando la estrategia y configuración lo requieran.

No duplicar valores en archivos separados.

No utilizar distintos umbrales sin justificación.

Asegurar que los cambios de escenario afecten coherentemente a:

- Panel científico.
- Indicadores.
- Planificador.
- Estadísticas.
- Evaluaciones de riesgo.

## 27. Rendimiento

Ejecutar los cálculos pesados mediante FastAPI, Web Workers o la arquitectura apropiada existente.

La interfaz no debe congelarse al calcular una ruta.

Implementá:

- Estado de cálculo.
- Cancelación.
- Manejo de errores.
- Caché.
- Límites de recursos.
- Descarte de resultados obsoletos.

No consultar APIs científicas externas dentro de cada iteración de A*.

Prepará previamente los datos necesarios.

---

# PARTE C — INTEGRACIÓN Y VERIFICACIÓN

## 28. Preservación de la inteligencia artificial

La integración realizada anteriormente con el trabajo de mi compañero debe mantenerse intacta.

Inspeccioná las dependencias, servicios y componentes relacionados con la IA antes de realizar cambios en archivos compartidos.

No modificar:

- Configuración de proveedores de IA.
- Credenciales.
- Prompts del asistente.
- Endpoints existentes.
- Funcionalidades del chatbot.

Salvo cuando resulte estrictamente necesario para corregir una incompatibilidad, y documentando el cambio.

Si la IA ya utiliza datos del mapa, verificar que reciba información consistente con las nuevas consultas y rutas.

No realizar una nueva implementación completa de inteligencia artificial.

## 29. Estado compartido entre páginas

Verificá que Mars Explorer, Route Planner y Terrain Analysis puedan compartir correctamente:

- Origen.
- Destino.
- Waypoints.
- Ruta activa.
- Condiciones de misión.
- Estrategia.
- Datos científicos.
- Peligros.

Cambiar de página no debe eliminar accidentalmente la ruta.

No crear múltiples motores de planificación contradictorios.

Reutilizar la infraestructura existente.

## 30. Pruebas reales obligatorias

Ejecutá la aplicación y realizá las siguientes pruebas.

### Prueba 1: inspección

- Seleccionar una montaña.
- Seleccionar un valle.
- Seleccionar una región plana.
- Comprobar que los datos corresponden a cada punto.
- Verificar unidades, fuentes y estados desconocidos.

### Prueba 2: indicadores

- Seleccionar una región con pendientes pronunciadas.
- Verificar la causa de la advertencia.
- Acercar y alejar la cámara.
- Comprobar agrupación y anclaje.
- Probar filtros.

### Prueba 3: navegación

- Arrastrar con clic derecho.
- Hacer clic derecho sin arrastrar.
- Comprobar que no existen conflictos.
- Probar selección táctil o emulación.

### Prueba 4: condiciones ambientales

- Cambiar el horario.
- Cambiar el escenario climático.
- Cambiar la configuración de polvo.
- Comprobar que los datos disponibles y las alertas se actualizan.
- Verificar que los cambios corresponden a fuentes reales o modelos documentados.

### Prueba 5: A*

- Seleccionar dos puntos separados por una montaña.
- Calcular Shortest route.
- Calcular Low-slope route.
- Comparar distancia y pendientes.
- Verificar las restricciones utilizadas.

### Prueba 6: planificación ambiental

- Calcular Environmental risk route si existen datos suficientes.
- Identificar las variables utilizadas.
- Modificar prioridades.
- Recalcular.
- Verificar que los costos realmente cambian.

### Prueba 7: restricciones

- Reducir la pendiente máxima.
- Seleccionar posiciones difíciles.
- Comprobar que el algoritmo evita celdas inválidas.
- Comprobar el resultado cuando no existe una ruta.

### Prueba 8: representación

- Girar el mapa.
- Acercarse al recorrido.
- Verificar que la ruta sigue las alturas.
- Comprobar que no atraviesa montañas.
- Comprobar alineación en diferentes niveles de detalle.

### Prueba 9: integración

- Crear una ruta en Mars Explorer.
- Cambiar a Route Planner.
- Consultar Terrain Analysis.
- Comprobar que la información permanece consistente.
- Verificar que la sección de IA continúa funcionando.

## 31. Pruebas automatizadas

Agregar o corregir pruebas para:

- Transformaciones de coordenadas.
- Consulta de alturas.
- Cálculo de pendientes.
- Evaluación de peligros.
- Costos normalizados.
- A*.
- Restricciones.
- Movimientos diagonales.
- NoData.
- Datos desconocidos.
- Comparación de rutas.
- Cambios de escenario.
- Estadísticas.
- Exportación e importación.

Utilizar datos sintéticos exclusivamente para pruebas.

Comparar A* con un algoritmo de referencia en cuadrículas pequeñas cuando resulte apropiado.

No modificar las pruebas para ocultar errores.

Ejecutar los comandos de lint, build y tests disponibles en el proyecto.

## 32. Validación visual

Utilizá el navegador para comprobar la aplicación final.

Generá capturas de:

- Visor general.
- Inspección científica.
- Indicadores de peligro.
- Ruta adaptada al relieve.
- Comparación de rutas.
- Perfil de elevación, si existe.
- Configuración de misión.

No considerar una funcionalidad terminada únicamente porque compila.

## 33. Orden de trabajo

Realizá las tareas en este orden:

1. Inspeccionar la versión actual.
2. Realizar la auditoría.
3. Identificar problemas y bloqueos.
4. Corregir la infraestructura científica.
5. Corregir la inspección de puntos.
6. Corregir los indicadores.
7. Corregir los escenarios de misión.
8. Validar la etapa 5.
9. Corregir el algoritmo de planificación.
10. Corregir la función de costo.
11. Corregir la representación de rutas.
12. Validar estrategias y estadísticas.
13. Validar la etapa 6.
14. Comprobar la integración con la IA.
15. Ejecutar todas las pruebas.
16. Actualizar la documentación.

No avanzar a etapas posteriores.

## 34. Entrega final

Actualizar:

- IMPLEMENTATION_STATUS.md
- AUDIT_STAGES_05_06.md
- SCIENTIFIC_LIMITATIONS.md
- SOURCES.md
- README.md
- DATA_DICTIONARY.md, cuando corresponda.

Entregar un informe en español que indique:

- Qué problemas encontraste en la implementación de OpenCode.
- Qué funcionalidades estaban correctamente implementadas.
- Qué funcionalidades eran solamente interfaces.
- Qué archivos modificaste.
- Qué errores corregiste.
- Qué datos científicos se utilizan realmente.
- Qué variables todavía no están disponibles.
- Cómo funciona el motor de peligros.
- Cómo funciona el planificador.
- Qué pruebas realizaste.
- Qué resultados obtuviste.
- Qué limitaciones persisten.
- Cómo puedo comprobar personalmente cada funcionalidad.

Clasificar cada requisito como:

- Implemented and verified.
- Implemented but not verified.
- Partially implemented.
- Blocked.
- Not implemented.

No declarar completadas funcionalidades que únicamente muestran paneles, botones o datos simulados.

Bridges Mavors debe seguir siendo una herramienta de exploración y asistencia para expediciones hipotéticas, no un sistema certificado de navegación para astronautas.

Comenzá inspeccionando la aplicación actual y posteriormente realizá las correcciones necesarias. Quiero una implementación funcional, visualmente comprobada y científicamente fundamentada.