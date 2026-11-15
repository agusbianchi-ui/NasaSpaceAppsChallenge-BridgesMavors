# Auditoría de etapas 5 y 6 — estado inicial y resultado, 2026-11-15

No hay historial Git disponible. La atribución a OpenCode se limita a los archivos aislados y modificaciones indicados por el usuario, contrastados con el respaldo de integración; no se inventa autoría línea por línea. Evidencia inicial en stages/05-06-evidence/initial-api.json; copia de fuentes before-audit.zip. Navegador confirmó páginas simuladas y ausencia de controles efectivos de planificación/peligros. IA operativa con cinco manifiestos; debe preservarse.

No se encontraron AGENTS activo ni PROJECT_SPEC/ARCHITECTURE/DATA_DICTIONARY/DESIGN_GUIDELINES ni prompts05/06 en docs o su copia recursosU/docs. Se consultaron README, SOURCES, INTEGRATION_REPORT y el informe científico04 como equivalentes. Las reglas AGENTS previas fueron revocadas por usuario. El prompt de esta auditoría es la especificación actual.

| Función | Estado inicial | Esperado / actual / causa y archivos | Prioridad, corrección y prueba |
|---|---|---|---|
| Registro y elevaciones | Correctly implemented | terrain_science + terrain_geospatial, matrices04/hash; alturas independientes del GLB, máscara y registro recuperados | P1 preservar, contrastar valores originales y transformaciones |
| Inspección | Partially implemented | Raycaster/BVH y cancelación existen; panel mínimo, sin promover a origen/destino ni metadatos completos | P1 panel compacto, acciones reales, pruebas selección y respuesta obsoleta |
| Peligros por punto | Incorrectly implemented | api/v1/science.py usa scientific_elevation como temperatura; hazard_evaluation tiene temperature_slope inexistente, umbrales fijos pese a config; métodos service inexistentes. HTTP500 | P0 eliminar proxy, usar contratos/datos04, configuración tipada y pruebas térmicas/NoData |
| Clusters permanentes | Missing / Incorrectly implemented | Sólo vecindad5x5 no renderizada; mezcla índices absolutos/locales, centro indexa dict como tuple. Sin capas/selección/LOD de iconos | P1 componentes conectados reales, anclas, agregación por zoom, filtros, extensiones y prueba visual |
| Misión | Missing | Parámetros sueltos backend ignorados, no estado UI compartido | P1 un contrato y estado persistente, condiciones invalidan rutas y consultas |
| MCD/ASU/RAD | Blocked by scientific data | Sólo fuentes candidatas; no matrices validadas por posición. Polvo MY36 sí integrado, celda6x5 grados, no tiempo local | P0 null explícito, controles no disponibles deshabilitados, polvo histórico nunca clima actual |
| Movilidad | Incorrectly implemented | índice sólo pendiente/rugosidad se describe como suelo; faltan roca/geología/inercia | P0 Unknown mobility conditions; penalizaciones topográficas identificadas |
| A* | Incorrectly implemented | Búsqueda existe en path_planning.py, pero valid_cell inexistente; máscara no cargada; métodos service inexistentes. Endpoint shadowea plan_route y usa firma/resultado incorrectos. HTTP500 | P0 reparar adaptador/búsqueda/endpoints, comparación con Dijkstra |
| Restricciones/costos | Incorrectly implemented | pendientes excesivas penalizadas en lugar de bloqueo; diagonales sin comprobación de esquinas; estrategias no gobiernan costo; desconocidos=0 | P0 restricciones duras, heurística admisible y costos normalizados; NoData/esquinas/sinruta/estrategias |
| Estadísticas | Incorrectly implemented | distancia=(n-1)*paso ignora diagonales; descenso placeholder; velocidad/escenario no evaluados coherentemente | P0 derivar aristas reales/geodésicas, duración/ganancias/cobertura, null ambientales |
| Ruta manual y render | Correctly implemented / Partially implemented | grilla visual y trazado por escalones probados; sin enlace al A* ni persistencia entre páginas | P1 conservar trazador, estado común, múltiples alternativas/exportación/importación |
| RoutePlanner/TerrainAnalysis | UI only | missionData simulado y overlay2D, no conexión al planificador/peligros; navegador confirma | P1 integrar módulo real compartido sin perder demostración previa etiquetada |
| IA | Correctly implemented en alcance registrado | chat determinista, galería y contratos eólicos; predicción no entrenada explícita | Preservar endpoints/prompts/config, regresión HTTP/UI |
| Rendimiento/cancelación | Missing para A* | sin trabajo cancelable acotado, límites/caché ni descarte obsoleto | P1 jobs backend con límites/cancelación, caché por entradas, abort cliente |

## Datos reales disponibles
HRSC/MOLA reproyectado250m, altura científica sin exageración, slope/aspect/roughness/relief; visual3x sólo para anclar. PolvoMY36 CDOD610Pa: promedio diario, una celda para región, incertidumbre y faltantes. No viento/temperatura/ionizante aplicables ni estabilidad mecánica medida. Fuentes y datum detallados en informe04/SOURCES. No nuevos datasets inferidos desde imágenes.

## Plan de corrección
Conservar motores de datos y render; reemplazar cuerpos defectuosos de hazard_evaluation/path_planning y adaptar sólo routers involucrados. Contrato misión común para punto/región/aristas/estadísticas. Persistencia y una sesión compartida entre tres páginas, sin visores simultáneos. Pruebas pequeñas sintéticas sólo en tests, pruebas reales con matriz04 y expediente preliminar. Registrar al final estados requisito por requisito y límites de proveedores.

## Resultado de las correcciones — 2026-11-15

Se conservaron registro, matrices y trazador visual existentes. Se repararon los endpoints que fallaban, la evaluación de peligros y el A*, y se conectaron los módulos de planificación reales a las tres páginas. IA, original, chunks, colores y navegación permanecen. No se atribuye toda línea modificada a OpenCode porque no existe Git para demostrar esa autoría.

Fallos corregidos: elevación usada como temperatura; variables/métodos inexistentes; firma de ruta que ocultaba el import; máscara inválida; clusters con índices equivocados; restricciones blandas donde se exigía bloqueo; diagonales que cortaban obstáculos; estrategias sin costo efectivo; estadísticas cardinales/descenso placeholder; pérdida de ruta entre páginas; falta de trabajos cancelables y respuestas obsoletas. En prueba final se corrigió también la importación de condiciones idénticas que limpiaba peligros sin disparar su consulta.

### Clasificación final por requisito del prompt

| Nº / requisito | Estado final | Evidencia o límite |
|---|---|---|
| 1. Contexto/alcance | Implemented and verified | Correcciones localizadas; sin reconstrucción ni nueva etapa |
| 2. Documentación | Implemented and verified | Equivalentes consultados antes; documentos faltantes reconstruidos sólo desde evidencia actual; AGENTS revocado no reinstalado |
| 3. Inspección real | Implemented and verified | HTTP, código, navegador y capturas; límites de gestos abajo |
| 4. Auditoría previa | Implemented and verified | Matriz inicial y before-audit.zip anteriores a correcciones; Git ausente |
| 5. Preservación | Implemented and verified | Hash original/matrices/IA, 44 chunks cargados; sin Untitled1.glb |
| 6. Fuente de verdad | Implemented and verified | Servicio04 + MissionConfig + evaluación común + sesión compartida |
| 7. Inspección de puntos | Partially implemented | Posiciones/acciones/cancelación comprobadas; arrastre derecho y multitáctil físico no verificados en navegador nativo, sí eventos/OrbitControls |
| 8. Panel científico | Implemented and verified | Grupos/metadatos/acciones y Unavailable; tres posiciones distintas |
| 9. Integración científica | Implemented and verified | Matrices/hash y polvo real comprobados; catálogos sin proveedor no se declaran integrados |
| 10. Indicadores | Partially implemented | Pendiente, polvo regional y desconocidos operativos; demás categorías Blocked por datos |
| 11. Apariencia/oclusiones | Implemented and verified | Glifos, anclas, billboards, profundidad, gravedad textual y lista accesible |
| 12. Agrupación/extensión | Partially implemented | Componentes/zoom y muestras de borde reales; contorno cerrado exacto Not implemented |
| 13. Evaluación de peligros | Partially implemented | Pendiente y polvo válidos, conversión térmica probada con fixture; movilidad/RAD/viento/temperatura regional Blocked |
| 14. Misión | Partially implemented | Umbrales, pesos, modo, velocidad y polvo efectivos; Ls/hora/clima Blocked y controles deshabilitados |
| 15. Auditoría A* | Implemented and verified | Fallos reproducidos/reparados; búsqueda real comparada con Dijkstra |
| 16. Origen/destino/waypoints | Implemented and verified | Colocación, edición, eliminación, Undo, Clear y promoción de inspección |
| 17. Cálculo automático | Partially implemented | DEM, distancias, pendientes, rugosidad y polvo; demás ambiente/mecánica Blocked |
| 18. Costos | Partially implemented | Normalización/pesos/heurística probados; exposiciones sin proveedor permanecen null |
| 19. Estrategias | Implemented and verified | Cuatro implementadas; ambiental explícitamente parcial o deshabilitada |
| 20. Restricciones | Implemented and verified | NoData, esquinas, límites, waypoints, exclusiones, ajuste y ausencia de solución |
| 21. Desconocidos | Implemented and verified | topography_only, penalize, avoid; 100% de cobertura desconocida explícita |
| 22. Render de rutas | Implemented and verified | Trazado de celdas/escalones, original y cuatro alternativas, captura/rotación/zoom |
| 23. Comparación/estadísticas | Implemented and verified | Métricas del camino, tabla/perfil y variables no evaluadas null |
| 24. Optimización temporal | Blocked | Sin clima/iluminación temporal aplicable; escenario estático identificado |
| 25. Ruta de referencia | Implemented and verified | 155 posiciones, extremos y métricas comprobados; recálculo por extremos o waypoints |
| 26. Coherencia científica | Implemented and verified | Mismo DEM/contrato; cambio de polvo/umbrales afecta inspección, peligros y costos |
| 27. Rendimiento | Implemented and verified | Jobs acotados, cancelación, caché y descarte; sin APIs dentro de búsqueda |
| 28. IA | Implemented and verified | Cinco archivos clave con hash idéntico, tests heredados y respuesta HTTP/UI |
| 29. Estado entre páginas | Implemented and verified | Origen/destino/ruta/condiciones persisten en Explorer, Routes y Terrain |
| 30. Pruebas reales | Partially implemented | Nueve grupos ejercitados según guía; clima/hora bloqueados, físico táctil y LOD adicionales no comprobables |
| 31. Pruebas automatizadas | Implemented and verified | 170 Python + 17 JS; Dijkstra, diagonales, datos reales y regresiones |
| 32. Validación visual | Implemented and verified | Siete capturas requeridas en carpeta de evidencia |
| 33. Orden/etapas | Implemented and verified | Auditoría inicial antes de refactor; sólo etapas5/6 |
| 34. Entrega/documentación | Implemented and verified | Este informe, status, fuentes, límites, diccionario y README actualizados |

Los estados parciales no ocultan botones decorativos. Identifican datos bloqueados, contornos pendientes y límites de verificación física. No se declara completada la evaluación ambiental total.

### Datos utilizados y fórmulas

DEM HRSC/MOLA reproyectado a 250 m; pendiente/orientación/rugosidad calculadas en etapa4 con distancias marcianas; matriz visual sólo para render. Polvo MY36: una celda nativa 6°×5°, absorción 9.3 µm normalizada a 610 Pa, media diaria y faltantes originales. No se descargaron datos numéricos nuevos.

Ver [etapa5](stages/05-hazard-indicators.md), [etapa6](stages/06-route-planning.md), [diccionario](DATA_DICTIONARY.md) y [limitaciones](SCIENTIFIC_LIMITATIONS.md). La heurística incorpora únicamente el mínimo regional demostrado del costo, y se contrasta con Dijkstra. Presión de normalización 610 Pa no es presión superficial medida.

### Archivos de implementación creados o modificados

Prefijos respecto de WebApp/:
- Backend: backend/app/schemas/planning.py; backend/app/services/hazard_evaluation.py, path_planning.py y planning_jobs.py; backend/app/api/v1/science.py; backend/tests/test_stages_05_06.py.
- Frontend: frontend/src/services/missionSession.js y marsApi.js; frontend/src/hooks/useTerrainPlanning.js; frontend/src/components/map/MarsTerrainViewer.jsx y MissionPlanningPanel.jsx; frontend/src/components/dashboard/ScientificInspectionPanel.jsx; frontend/src/terrain/terrainHazards.js y createTerrainEngine.js; frontend/src/pages/RoutePlanner.jsx y TerrainAnalysis.jsx; frontend/src/styles/terrain.css.
- Tests frontend: mission-session.test.mjs y calculated-route.test.mjs. Script raíz scripts/validate-stages-05-06.py.
- Documentos: este informe, IMPLEMENTATION_STATUS, SCIENTIFIC_LIMITATIONS, DATA_DICTIONARY, ARCHITECTURE, DESIGN_GUIDELINES, PROJECT_SPEC, README y SOURCES; informes05/06 y copia del prompt en docs/stages/.
- Evidencias nuevas bajo docs/stages/05-06-evidence/. Compilación regenerada en frontend/dist.

No se cambiaron ai.py, core/config.py, aeolian_service.py, AIAssistant.jsx ni AISystems.jsx. No se añadieron dependencias de producción. El asistente sigue siendo determinista: no recibe automáticamente la nueva ruta ni se presenta como modelo predictivo entrenado.

### Pruebas y resultados observados

Entorno: Windows, Intel Core i9-14900HX, RTX4080 Laptop/Intel UHD presentes; navegador integrado de Codex, preview Vite127.0.0.1:4173 y FastAPI8000. No se midió/adjudicó al navegador una GPU específica ni FPS.

- Python: 170 passed, 1 skipped en 5.39 s; omisión por privilegio de symlink Windows1314. Advertencias heredadas de Pydantic/TestClient, sin modificar IA para silenciarlas.
- JS: 17/17, lint correcto, build correcto. Aviso de bundles JS de ~896/949 kB sin comprimir; prueba local no equivale a benchmark móvil.
- Reproducción sobre matrices reales: cuatro estrategias exitosas en 1.840–2.046 s en ejecuciones locales sin caché de soluciones. Shortest:41834.333 m, pendiente máxima21.27°, media2.71°, ganancia1260.4 m/pérdida740.3 m. Low-slope:41834.359 m, máxima12.16°, media1.96°, ganancia977.6 m/pérdida457.5 m. 11.66/11.64 h con velocidad hipotética1 m/s.
- Referencia155 puntos:44920.020127 m, máxima5.943209°. Origen/destino visuales exactos. Mantener sus waypoints no equivale a ruta libre entre extremos.
- Costos con polvo MY36 sol1, umbral0.1 y penalize: shortest41834.33; low_slope80313.91; environmental160364.94; balanced163982.63. Son metros equivalentes, no niveles de seguridad. Sin ambiente los costos difieren legítimamente de esa ejecución.
- Default pendiente25°:81 componentes de pendiente +1 aviso regional de desconocidos. Con polvo válido/umbral0.1:83 regiones. Sol37/200 faltantes, sin polvo ficticio.
- Navegador: carga44 sectores, tres posiciones de inspección con alturas distintas, selección de peligro/causa, zoom/agrupación/filtros, promoción a waypoint y Undo, cálculo4 estrategias, no-route con pendiente0 y avoid, estado outdated al cambiar condición, Cancel, export/import/recalcular, conservación de ruta entre páginas, mapa2D y respuesta del asistente.
- Última compilación: importación de misión idéntica conserva82 regiones y recalcula; navegación a RoutePlanner conserva tabla. Sin errores de consola registrados en la verificación final.

A* frente a Dijkstra en fixtures; NoData/esquinas/exclusiones; pendientes firmadas; límites; cancelación/presupuesto; estadísticas diagonales; conversión K→°C; peligros con umbrales; API validada; escena real/hash; prueba de cada tramo de alternativas sobre matriz visual. Fixtures sintéticos sólo en tests.

Limitación de las pruebas: clic derecho sin arrastrar comprobado en navegador; arrastre derecho/touch/pinch/twist/tilt probados con eventos del controlador y OrbitControls en tests, sin entrada multitáctil física. Las tres posiciones visuales fueron distintas; selección adicional reproducible de máximo/mínimo/pendiente suave está en three-point-validation.json. Sólo hay LOD0. No se declara certificación de rendimiento web ni cobertura meteorológica completa.

### Evidencia y reproducción

Carpeta stages/05-06-evidence:
before-audit.zip, initial-api.json, ai-preservation.json, source-integrity.json, real-route-validation.json, real-hazard-validation.json, three-point-validation.json, exported-mission.json y assistant-response.txt.
Capturas: viewer-general.png, scientific-inspection.png, hazard-region.png, terrain-route.png, route-comparison.png, elevation-profile.png, mission-configuration.png. Capturas pueden incluir demos heredadas explícitamente simuladas.

Desde raíz PowerShell:
1. Ejecutar .\Start-BridgesMavors.ps1 y abrir http://127.0.0.1:4173/explorer. Backend http://127.0.0.1:8000/docs.
2. Load 3D terrain. Clic derecho en celdas distintas o Inspect mode + clic; revisar alturas/fuentes/Unavailable. Use as Start/Destination/Waypoint; Undo elimina la edición reciente.
3. Hazard indicators: elegir Steep slope en lista, revisar causa/umbral, Focus, acercar/alejar y alternar filtros. Puntos de borde muestran extensión muestreada, no un polígono cerrado.
4. Import preliminary route → Use endpoints only → Calculate routes con Compare all strategies. Seleccionar alternativas y revisar perfil. Se pueden colocar otros extremos en Route planning mode; no depende de la referencia.
5. Dust scenario=Historical MY36 daily CDOD, sol1, threshold0.1, Unknown-data policy=Allow unknown with penalty; recalcular. Polvo regional disponible y estrategia ambiental parcial. Sol37 produce faltante, sin inventar alerta.
6. Cambiar peso de pendiente o rugosidad en Planning priorities and method; recalcular para verificar costo. Ls/hora/clima están bloqueados con motivo, no botones simulados.
7. Max slope0 o Avoid unknown areas → calcular: No valid route found. Volver a25 y Topography-only para recuperar. Exclude inspected cell/rectángulo de región altera restricciones; Clear exclusions revierte.
8. Cambiar condiciones después de calcular marca Outdated; Cancel durante cálculo cancela trabajo. Rotar/zoom y comprobar línea sobre escalones.
9. Export mission → Import mission exige recálculo. Cambiar a Route Planner y Terrain Analysis conserva puntos/ruta; sólo cargar el visor de la página activa. En AI Systems enviar una consulta sobre datasets confirma asistente preservado.

Comandos de prueba:
- Desde WebApp/frontend: npm run test:terrain; npm run lint; npm run build.
- Desde WebApp/backend: establecer PYTHONPATH con rutas absolutas WebApp y WebApp/backend, luego .venv/Scripts/python.exe -m pytest tests ../mars_ml/tests -q.
- Desde raíz: WebApp/backend/.venv/Scripts/python.exe scripts/validate-stages-05-06.py (reescribe sólo evidencias derivadas).

No ejecutar reorganize.py/consolidate.py históricos. Los documentos describen el estado vigente y los bloqueos, sin autorizar etapas posteriores.
