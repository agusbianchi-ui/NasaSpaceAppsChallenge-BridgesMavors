# Especificación vigente — 2026-11-15

Bridges Mavors combina exploración 3D voxelizada, consultas científicas y asistencia para expediciones hipotéticas, preservando la integración del compañero. No es navegación certificada.

La instrucción de trabajo actual es docs/stages/05-06-audit-prompt.md: auditar, corregir y comprobar etapas 5/6 sin avanzar a otra etapa. Requisitos aprobados: conservar original/chunks, colores, navegación, mapa 2D, diseño general e IA; interfaz nueva en inglés; un terreno visual con variables científicas independientes.

Inspección: posición real del terreno, coordenadas verificadas y variables con procedencia/faltantes explícitos. Peligros: regiones reales agrupadas, anclas 3D seleccionables, causa y umbrales editables. Misión compartida con invalidación de resultados al cambiar condiciones.

Planificación: edición manual y A* sobre matrices científicas, restricciones duras, estrategias shortest/low_slope/environmental/balanced, políticas de desconocidos, comparación, perfil, persistencia y exportación/importación. Datos ausentes bloquean sólo lo que no puede evaluarse; no completar paneles con valores ficticios.

Las especificaciones detalladas y fórmulas están en stages/05-hazard-indicators.md y stages/06-route-planning.md. Estado comprobado en IMPLEMENTATION_STATUS.md; límites científicos en SCIENTIFIC_LIMITATIONS.md; contratos en DATA_DICTIONARY.md; fuentes en ../SOURCES.md. Esos informes no autorizan nuevas funcionalidades. No se reconstruyeron prompts históricos ausentes ni un AGENTS revocado.
