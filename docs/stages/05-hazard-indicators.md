# Etapa 5 — inspección e indicadores, revisión 2026-11-15

La especificación autorizada se conserva en [05-06-audit-prompt.md](05-06-audit-prompt.md). Este informe describe la implementación corregida, sin reconstruir un prompt histórico ausente. Pruebas y estados: [auditoría](../AUDIT_STAGES_05_06.md).

## Inspección
Raycaster/BVH intersecta el terreno; los símbolos de peligro se seleccionan por separado. El arbitraje distingue clic derecho, arrastre y pulsación prolongada. Cada consulta cancela la anterior, y los cambios de misión vuelven a consultar el punto. Respuestas abortadas no actualizan el panel.

Panel compacto debajo del terreno: coordenadas locales y geográficas verificadas, elevación científica independiente de Y visual y variables agrupadas. Detalles: unidad, fuente, resolución, tiempo, clasificación, método e incertidumbre disponible. Ausencia significa Unavailable/null, nunca cero. Use as Start/Destination/Waypoint actualiza la sesión común.

## Indicadores
Pendiente científica precalculada frente al límite de misión. Componentes conectados de cuatro vecinos agrupan celdas críticas. Iconos anclados en celdas reales de máxima pendiente, con línea al terreno, glifo, gravedad y etiqueta orientada a cámara. Desde lejos se agrupan por categoría y cuadrículas de 50 km, conservando cantidad y gravedad máxima; de cerca muestran componentes individuales. Selección y filtros también disponibles mediante lista accesible.

Etiquetas separadas por prioridad en pantalla y con profundidad. La oclusión puede ocultar un símbolo; la lista permite localizarlo. La selección muestra hasta 256 centros de celdas de borde sobre el relieve. No hay un contorno vectorial cerrado exacto. Excluir una región utiliza su rectángulo de celdas, indicado explícitamente, y puede excluir más superficie que el componente.

Polvo histórico MY36: una celda nativa de 6° × 5° cubre toda el área. Genera una advertencia regional, sin gradientes locales inventados. Soles faltantes no generan evaluación cuantitativa. Unknown conditions expresa ausencia de variables, no peligro físico medido. Temperatura, viento, movilidad y radiación permanecen no disponibles sin proveedores aplicables.

## Condiciones
MissionConfig gobierna inspección, peligros y rutas. Límites y prioridades son hipótesis del usuario, no límites NASA. Temperaturas del proveedor se convierten de Kelvin a Celsius. CDOD adimensional (Pa/Pa); pendiente en grados; viento en m/s. Ninguna elevación actúa como temperatura.

Walking/Rover aplica valores editables de velocidad/pendiente; no simula estabilidad del suelo. Ls, hora local y escenario climático están deshabilitados porque falta MCD numérico validado. Cambios invalidan rutas y consultas; importar condiciones idénticas conserva indicadores vigentes. No se modifican geometría ni colores.

Sólo hay LOD0; alineación entre LOD inexistentes no comprobable. Pruebas táctiles mediante eventos emulados, sin teléfono físico. No certifica seguridad para astronautas.
