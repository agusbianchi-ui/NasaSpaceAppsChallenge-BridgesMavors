# Informe de reorganización y combinación — 2026-11-15

## Estado recibido

Había una aplicación incompleta en WebApp (frontend sin src, backend sin app y sin __init__.py), restos de la estructura anterior en ops_mars-main, dos servicios aislados en backend/app/services y recursos movidos a recursosU. Los scripts reorganize.py y consolidate.py copiaban/movían recursos, eliminaban árboles y excluían inicializadores Python. No se ejecutaron. El ZIP nuevo es la versión del compañero; sus documentos se conservaron como contenido de referencia, sin tratarlos como instrucciones del usuario.

Respaldo de fuentes previo: integration-review/before-integration.zip. Inventario SHA-256: before-inventory.json. Extracción del ZIP en incoming/ con comprobación de rutas. Copia exacta del WebApp a previous-WebApp/. No se sobrescribió el ZIP ni el terreno original de recursosU.

## Resultado

WebApp es la ubicación principal, con frontend/src, backend/app, tests y mars_ml. Se sumaron la galería visual, Dune Explorer, CV Lab, mejoras de Mission Overview, Route Planner y Scientific Targets, tablero Kanban, manifiestos y procesamiento eólico del compañero. Se conservaron el visor Three.js, los 44 chunks, selección, marcadores, rutas manuales, referencia de 155 puntos, matrices científicas, consultas geográficas y polvo histórico.

Se combinaron los dos clientes HTTP y las familias de routers. Se recuperaron hazard_evaluation.py y path_planning.py que habían quedado aislados, conservando las rutas de API existentes. Su presencia no certifica evaluación científica de riesgos ni madurez del planificador. No se ejecutó entrenamiento ni se inventaron mediciones.

El panel científico local estaba incompleto: importaciones relativas erróneas, JSX inválido, API inexistente, coordenadas cero rechazadas, pérdida del handle del motor y callback de colocación ausente. Se reparó el visor y se conectó una consulta cancelable por inspección con información real del backend; no se elige automáticamente MY36/sol1 para representar condiciones actuales. La edición de marcadores permanece en sus controles existentes; no se conservaron botones de panel sin lógica que sólo cerraban la ventana. El panel anterior sigue en incomplete-components/.

Se retiró el panel duplicado «3D pending/Cesium» del Explorer. Dune Explorer tenía estado actualizado durante render y categorías incompletas: ahora deriva los filtros y muestra Unclassified sin inventar categorías. CV Lab tenía hooks/importaciones ausentes y componentes escritos en minúscula: reparados. No se presenta el preview de imágenes como inferencia entrenada. Las imágenes externas y sus descripciones del catálogo del compañero no se validaron científicamente una por una.

Se sustituyó el prototipo eólico no conectado por la interfaz de catálogo/detalles/formulario/resultados existente en el ZIP. Permite consultar los cinco manifiestos y enviar solicitudes al backend, con errores explícitos cuando faltan archivos. El modelo predictivo conserva Unavailable. El asistente es determinista y basado en reglas, no un LLM entrenado; se eliminó su afirmación fija de que todos los servicios y 54 pruebas estaban verificados.

Kanban: corregidos ciclo de carga, permisos CORS para PUT/DELETE, prioridad numérica y campos target_id/due_date; las respuestas conservan todos los campos de las tareas. El almacenamiento backend sigue siendo temporal en memoria. Se verificaron altas, edición y borrado por HTTP con una tarea de prueba eliminada al finalizar. Se añadieron rutas de navegación faltantes para Aeolian Dynamics y Mission Tasks.

## Organización y conservación

Los duplicados aplanados de WebApp se trasladaron a integration-review/flattened-duplicates. Los prototipos no conectados DuneIntelligence/useApi y el panel defectuoso se conservaron en incomplete-components. Las copias antiguas de raíz no se eliminaron: tienen LEGACY_COPY.md para evitar usarlas como aplicación activa. Los recursos pesados permanecen en su ubicación actual y las salidas científicas siguen en output-stage*. El launcher y README de raíz apuntan sólo a WebApp.

Los scripts científicos históricos siguen documentando el layout anterior; no se promete que todos acepten la reorganización nueva. Antes de regenerar datos se deben adaptar explícitamente sus rutas y volver a comprobar hashes. La app actual ya tiene los recursos estáticos y las matrices, y no necesita ejecutar esos scripts para arrancar.

## Validación ejecutada

- 159 pruebas Python de backend y mars_ml aprobadas; una omitida porque Windows no habilita creación de symlinks. Se conserva esa prueba con omisión explícita únicamente para WinError1314.
- 14 pruebas de terreno aprobadas; lint sin errores y compilación de producción correcta. Sigue el aviso de bundles superiores a 500 kB.
- Pruebas HTTP: terreno Available, cinco datasets, asistente y CRUD de tarea; evidencia api-smoke.json.
- Navegador: Mission Overview, AI Systems, Dune Explorer, CV Lab, Route Planner, Scientific Targets, Kanban, visor, fullscreen, carga de 44 chunks, ruta155 e inspección científica. Se corrigió también el fallo de categoría que se observó al abrir Dune Explorer.
- Dependencias instaladas en entornos de WebApp; npm audit informó cero vulnerabilidades en esa instalación. Sin entrenamiento de Torch/checkpoints nuevos.

Persisten avisos de deprecación de Pydantic/TestClient heredados. No se probó teléfono físico ni se descargaron los píxeles faltantes de todos los datasets eólicos. No se certifican predicciones, seguridad de recorridos ni cada descripción de la galería. Las fuentes científicas y sus limitaciones previas permanecen en SOURCES.md y docs/SCIENTIFIC_LIMITATIONS.md.

Inventario final: integration-review/merged-inventory.json. Capturas: merged-viewer.png y merged-ai.png. Servidores locales activos en 4173 y 8000 desde WebApp. Arranque reproducible con Start-BridgesMavors.ps1. Detenerse aquí antes de ampliar funciones del proyecto.
