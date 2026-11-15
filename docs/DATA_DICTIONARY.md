# Diccionario de datos — 2026-11-15

Actualización adicional: thermal_inertia_day y thermal_inertia_night incorporan productos TES PDS numéricos con unidad J m^-2 K^-1 s^-1/2, resolución0.05°, calidad nativa y exclusión de interpolados. No son temperatura. Archivos y pruebas: [informe adicional](additional-science/REPORT.md). MOLA multiescala y surface_dust cuantitativo siguen bloqueados; sus mapas2D son referencias visuales independientes.

## Terreno y registro
Fuente de verdad: output-stage4/terrain_metadata.json y manifiesto; servicio WebApp/backend/app/services/terrain_science.py. Matrices 808 filas × 800 columnas, little-endian, row-major; filas crecen +Z, columnas +X. Origen de esquina (-100000,-101000), paso proyectado 250 m, límites semiabiertos; centros desplazados 125 m. 507538 celdas válidas, 504326 gradientes 3×3 válidos. X este, Y visual arriba, Z sur. Transformación original→optimizado identidad.

| Archivo/campo | Tipo/unidad | Significado |
|---|---|---|
| scientific_elevation.bin | float32, m | DEM reproyectado, sin exageración |
| visual_elevation.bin | float32, unidades visuales | Altura de bloques cuantizada/exagerada |
| valid_mask.bin | uint8 | 1 válido, 0 ausente |
| slope.bin | float32, grados | Pendiente de ajuste local 3×3 |
| aspect.bin | float32, grados | Descenso horario desde norte; plano indefinido |
| roughness.bin | float32, m | RMS residual del plano, no estabilidad |
| local_relief.bin | float32, m | Relieve local derivado |
| NoData | NaN y/o máscara 0 | No convertir a cero |
| latitude/longitude | grados | Planetocéntrica / este [-180,180] |

Funciones compartidas en terrain_geospatial.py. AEQD usa R=3396190 m y centro 17.5°N/77°E; conversión horizontal (X,-Z) ↔ (lon,lat). Ver metadatos para hashes y advertencias verticales.

El manifest.json de chunks generado en etapa 1 conserva georeference_verified=false como registro histórico de aquella etapa. La validación posterior está en output-stage4/terrain_metadata.json (true) y georeference-validation.json; el servicio científico utiliza este paquete posterior. No interpretar el manifiesto histórico como una nueva invalidación ni inferir coordenadas desde él.

## Variables y condiciones
Cada variable devuelve value nullable, unit, source, clasificación, resolución, tiempo, método e incertidumbre disponible. Catálogo actual: WebApp/backend/app/data/science_catalog.json; contrato HTTP: /api/v1/science/sources.

dust-my36-region.npz / dust-metadata.json: CDOD610 y su incertidumbre en Pa/Pa, absorción 9.3 µm. MY36, sol entero 1..669, celda [75,81)E × [15,20)N, 558 disponibles. climate_scenario=unavailable, ls/local_time=null; solicitudes que inventen esos escenarios se rechazan.

MissionConfig en WebApp/backend/app/schemas/planning.py define rangos y defaults: velocidad m/s, límites de ascenso/descenso en grados, límites térmicos °C, high_dust adimensional, high_wind m/s, roughness_scale m, pesos adimensionales. displacements foot/rover; unknown_policy topography_only/penalize/avoid. Defaults son hipótesis.

## Peligros y rutas
Región: id, categoría, gravedad, ancla visual en celda real, cell_count, bbox y hasta 256 boundary_points de centros de celdas; no contorno cerrado. Polvo/faltantes son regionales.

PlanRequest: points con x/z finitos (2..200), misión, estrategia, compare y excluded_cells [fila,columna] (máximo 20000). POST /api/v1/plan/route devuelve trabajo; GET /plan/jobs/{id} devuelve estado/resultado; DELETE cancela.

Resultado: routes por estrategia, success, path_local para render, snapping con ajuste explícito y estadísticas. Distancias m, duración s, pendientes grados, ganancias/pérdidas m. total_cost en metros equivalentes normalizados. unknown_environment_fraction y unknown_variable_fraction son distintos; variables no evaluadas null. Fórmulas en stages/06-route-planning.md.

Exportación bridges-mission-v1: source_sha256 del original, points, mission, strategy, excluded_cells, results y advertencia. Importación valida la fuente, reancla Y y elimina resultados no confiables; requiere recálculo. No incluye DEM ni GLB.
