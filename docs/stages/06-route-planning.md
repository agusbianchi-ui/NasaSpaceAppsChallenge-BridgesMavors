# Etapa 6 — planificación, revisión 2026-11-15

Especificación autorizada: [05-06-audit-prompt.md](05-06-audit-prompt.md). Pruebas y guía personal: [auditoría](../AUDIT_STAGES_05_06.md).

## Búsqueda
A* recorre ocho vecinos de matrices científicas de etapa 4. NoData, exclusiones, límites y pendientes son restricciones duras. Para una arista, d es la distancia geodésica entre centros sobre la esfera marciana y Δh procede del DEM científico: pendiente firmada = atan2(Δh,d). Ascenso y descenso tienen límites distintos. La pendiente 3×3 de celda también se limita conservadoramente al mayor de ambos umbrales; sin gradiente válido se comprueban las aristas.

Una diagonal exige ambos vecinos de esquina y cuatro aristas cardinales compatibles. Waypoints resueltos en orden. Posiciones ajustadas a centros de 250 m: se devuelven solicitud, posición ajustada y changed. No se desplaza automáticamente un endpoint NoData. Sin solución se informa No valid route found, sin línea recta automática alternativa.

## Costos
Cada arista cuesta d × factor, con factor ≥ 1 y pesos no negativos:
- S = min(1, |pendiente de arista| / límite direccional).
- R = min(1, rugosidad RMS / roughness_scale), ambas magnitudes en metros.
- D = min(1, CDOD610 / high_dust), sólo con polvo histórico válido.
- U = fracción de seis variables ambientales requeridas sin valor: temperaturas superficial/atmosférica, viento, polvo, flujo solar y radiación ionizante.
- T = slope_weight × S² + roughness_weight × R.
- E = environment_weight × D, si la política permite evaluar ambiente.
- P = unknown_weight × U, sólo con política penalize.

| Estrategia | Factor |
|---|---|
| shortest | 1; conserva restricciones duras |
| low_slope | 1 + T + P |
| environmental | 1 + E + P; requiere polvo válido explícito |
| balanced | 1 + T + E + P |

Topography-only omite E y P. Avoid unknown rechaza celdas con variables requeridas desconocidas; actualmente puede bloquear toda el área. Polvo/faltantes uniformes pueden modificar costos sin crear gradientes espaciales. Distintas estrategias pueden coincidir.

Heurística = distancia geodésica al objetivo × mínimo regional demostrado del factor: 1 para shortest, 1+P para low_slope y 1+E+P para balanced/environmental. Omite términos topográficos no negativos. Se contrasta contra Dijkstra en pequeñas cuadrículas para todas las estrategias. Esta cota depende de la cobertura ambiental uniforme actual; futuros proveedores espaciales deben revisar el mínimo. Costo en metros equivalentes normalizados, no probabilidad de riesgo.

## Estadísticas y render
Distancia horizontal = Σd; superficie = Σhypot(d,Δh); duración = superficie/velocidad estimada. Ganancias/pérdidas suman incrementos positivos/negativos. Pendiente media ponderada por distancia, máximos direccionales, rugosidad y perfil usan muestras científicas del camino. Variables no evaluadas retornan null. CDOD no se integra como dosis.

Unknown environment fraction mide la fracción espacial con al menos una variable requerida desconocida: actualmente 100%. Unknown variable fraction registra aparte la fracción de variables faltantes. Escenario estático; no hay optimización temporal ni cálculo radiológico desde sombras.

Sólo el render utiliza alturas visuales: recorre todas las celdas cruzadas, sigue escalones y separa la línea 8 unidades visuales. Puentes junto al escalón abarcan hasta una unidad horizontal por lado. Las cuatro alternativas reales se contrastan contra la grilla con muestreo denso. Se muestra una alternativa seleccionada, tabla comparativa y perfil.

## Trabajos y sesión
FastAPI: dos workers, máximo cuatro trabajos activos, 150000 expansiones y 25 s por comparación, con revisión de cancelación/presupuesto cada 128 expansiones. Cliente consulta cada 300 ms, cancela al cambiar entradas o desmontar y descarta respuestas obsoletas. Caché FIFO de 12 resultados por fuente/entrada; hasta 40 trabajos completados durante 10 minutos. Sin APIs externas dentro de A*.

Las tres páginas comparten puntos, misión, exclusiones, estrategia y rutas. Datos científicos/peligros compartidos en memoria; localStorage conserva entradas/resultados, sin esos cachés ni historial Undo. No hay sincronización remota. Export mission descarga JSON. Import mission valida fuente, estructura, rangos y celdas, recalcula Y visual y descarta estadísticas importadas para exigir recálculo. Demos previas conservadas en un bloque identificado.

## Referencia
Origen XYZ (24875,5790,-55625), destino (8375,7350,-20625). Referencia de 155 puntos: 44920.020 m horizontales y pendiente máxima 5.94321° sobre DEM científico. Coincidencia visual comprobada; no expedición validada. Import preliminary route conserva todos los waypoints. Use endpoints only permite comparar soluciones libres entre extremos, aproximadamente 41834 m. No se necesitan las marcas celestes de la captura para validar esta integración.
