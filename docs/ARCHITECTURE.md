# Arquitectura efectiva — 2026-11-15

Aplicación canónica en WebApp. Copias históricas raíz backend/ y ops_mars-main/ no son servidores activos; recursosU conserva originales. Detalles de consolidación en INTEGRATION_REPORT.md.

Flujo científico:
output-stage4 → terrain_science.py + terrain_geospatial.py → hazard_evaluation.py → inspección/regiones y path_planning.py → API science.py → marsApi.js → sesión React/visor.

MissionConfig comparte parámetros entre consultas, peligros y planificación. No hay modelos temáticos ni valores ambientales dentro del GLB. Original y 44 chunks Meshopt conservan coordenadas, colores y exageración visual.

- MarsTerrainViewer.jsx monta createTerrainEngine.js y conserva navegación, Raycaster/BVH y render de ruta sobre bloques.
- terrainHazards.js mantiene su grupo separado y libera geometrías, materiales y texturas.
- missionSession.js comparte entradas/resultados entre Mars Explorer, Route Planner y Terrain Analysis, con localStorage y cachés científicos en memoria.
- useTerrainPlanning.js conserva edición, Undo, importación de referencia y trazado visual.
- ScientificInspectionPanel.jsx muestra consultas y acciones de puntos.
- MissionPlanningPanel.jsx configura misión, trabajos, alternativas, perfil y JSON.
- planning_jobs.py acota trabajos/cancelación/caché; path_planning.py no realiza llamadas externas.
- NASA/OpenLayers 2D permanece independiente; demos previas identificadas no alimentan A*.
- IA existente en api/v1/ai.py, aeolian_service.py, componentes ai/ y mars_ml permanece preservada; no se reescribieron prompts ni proveedores.

Contratos documentados por FastAPI en /docs. Las rutas antiguas en informes históricos deben resolverse contra esta estructura, no ejecutarse literalmente. Límites, pruebas y estados reales: AUDIT_STAGES_05_06.md.
