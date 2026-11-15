# Limitaciones científicas — 2026-11-15

Actualización posterior a la auditoría: inercia térmica aparente TES día/noche ya tiene proveedor numérico validado por posición; sustituye la limitación anterior para esos dos campos. No habilita temperatura ni movilidad. MOLA multiescala carece de registro/cobertura reconciliados y TES_Dust no tiene producto físico equivalente recuperado. Ver [informe adicional](additional-science/REPORT.md).

Esta revisión describe archivos y proveedores efectivos, no disponibilidad hipotética de catálogos.

- El registro de etapa 4 relaciona modelo y DEM: esfera marciana R=3396190 m, latitud planetocéntrica, longitud este, AEQD centrada en 17.5°N/77°E. La región procede del polígono EMC de Mars Trek; el terreno incluye áreas cercanas a Jezero, no sólo su cráter. Ver output-stage4/georeference-validation.json y recursosU/docs/stages/04-georreferenciacion-ciencia.md.
- DEM HRSC/MOLA nominal 200 m, remuestreado a 250 m. No hay resolución científica de 20 m en todo el terreno ni detalle nuevo extraído de fotografías. Realización precisa del datum vertical e incertidumbre local del producto combinado siguen pendientes; no aplicar ±3 m universal.
- Y visual = 3 × (round(h/2) × 2 + 4500). Invertirla sólo recupera altura cuantizada, no la muestra científica original. Pendientes/rutas consultan scientific_elevation, no Y/3.
- Pendiente, orientación y rugosidad derivan de un entorno 3×3 válido. Borde/NoData puede carecer de gradiente; nunca se rellena por cero. Rugosidad RMS no mide estabilidad mecánica.
- Polvo MY36 v2.5 es CDOD de absorción a 9.3 µm normalizada a 610 Pa, adimensional. Promedio diario, resolución nativa 6° × 5°, una celda en toda la región. 558 de 669 soles válidos; faltantes sin interpolación. No indica tormenta actual, presión local ni polvo superficial. No confundir con extinción visible.
- MCD, temperatura superficial/atmosférica, viento, presión, inercia térmica, rocas, geología, mineralogía, flujo solar y radiación ionizante no tienen proveedor numérico validado aplicable en esta versión. Catálogos/URLs no equivalen a integración.
- Sin índice mecánico de movilidad: Unknown mobility conditions. Sombras no implican protección cósmica; RAD de Gale no se extrapola a esta región.
- Umbrales, Walking/Rover, velocidad y pesos son hipótesis editables, no límites oficiales NASA ni modelos de vehículo. A* optimiza las métricas disponibles a 250 m; no garantiza transitabilidad subcelda.
- Planificación ambiental parcial: sólo polvo histórico regional y penalización explícita por faltantes. No existe optimización temporal ni exposición acumulada validada. 100% de cobertura ambiental desconocida significa que al menos una variable requerida falta en toda el área.
- Contornos de peligros: muestras de bordes, no polígonos cerrados exactos. Excluir rectángulos de componentes es conservador. Sólo LOD0, sin validación entre otros LOD.
- IA preservada: asistente determinista y manifiestos; no hay checkpoint predictivo validado. Demostraciones de telemetría/targets siguen identificadas como simuladas y no alimentan el motor científico.

Herramienta de exploración y asistencia para expediciones hipotéticas; no sistema certificado para astronautas. Fuentes, licencias y atribuciones: ../SOURCES.md. Pruebas y alcance: AUDIT_STAGES_05_06.md.
