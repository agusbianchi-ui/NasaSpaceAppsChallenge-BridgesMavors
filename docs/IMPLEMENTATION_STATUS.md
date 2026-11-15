# Estado comprobado — 2026-11-15

Actualización posterior: dos campos TES de inercia aparente (día/noche) conectados al panel y servicio científico; mapas2D TES_Thermal_Inertia, TES_Dust, mola_roughness añadidos y selector movido debajo del mapa. MOLA y polvo superficial numéricos siguen bloqueados según [informe adicional](additional-science/REPORT.md). Las cifras de pruebas de la auditoría inferior son históricas.

Aplicación canónica en WebApp; integración previa conservada. Original MapaMarteN.glb y matrices de etapa 4 verificadas por SHA-256. 44 chunks Meshopt LOD0; no LOD1/LOD2.

## Etapas 5 y 6
Corregidas y comprobadas en navegador y tests: inspección contextual, acciones Start/Destination/Waypoint, indicadores de pendiente agrupados, filtros/selección, misión compartida, A* real, restricciones, cuatro estrategias con disponibilidad explícita, comparación/perfil, cancelación/caché, estados obsoletos y exportación/importación.

Resultados: 170 tests Python aprobados y uno omitido por privilegio Windows de symlinks; 17 tests frontend aprobados; lint y build correctos. Build advierte bundles grandes; no se afirma rendimiento móvil certificado. Comparación de cuatro estrategias reales en 1.840–2.046 s en ejecuciones locales documentadas, no garantía universal.

Pendientes/alcance parcial:
- Variables ambientales adicionales bloqueadas por ausencia de proveedores numéricos validados. Ambiental sólo evalúa polvo histórico regional si se selecciona y datos desconocidos; sin optimización temporal.
- Bordes de peligros mostrados con muestras de celdas, sin contorno cerrado exacto.
- Gestos táctiles y clic derecho/arrastre comprobados en tests de eventos y OrbitControls; sin prueba física multitáctil ni arrastre derecho nativo en navegador automatizado.
- Sólo LOD0; no prueba entre otros LOD.
- Demo de telemetría/targets e IA determinista permanecen identificadas; modelo predictivo no disponible.

No se avanzó a otra etapa. Auditoría inicial/final, archivos, pruebas, capturas y guía: [AUDIT_STAGES_05_06.md](AUDIT_STAGES_05_06.md). Fórmulas y contrato: stages/05-hazard-indicators.md y stages/06-route-planning.md. Limitaciones: SCIENTIFIC_LIMITATIONS.md.
