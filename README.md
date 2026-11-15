# Bridges Mavors — aplicación combinada

Actualización de datos: inercia térmica aparente TES de día/noche disponible en la inspección. Mapas2D TES_Thermal_Inertia, TES_Dust y mola_roughness añadidos, selector debajo del mapa. Descargas, pruebas y bloqueos científicos en [informe adicional](docs/additional-science/REPORT.md). Verificación reproducible: WebApp/backend/.venv/Scripts/python.exe scripts/validate-additional-science.py.

La aplicación principal está en **WebApp/**:

- WebApp/frontend/src: interfaz React, visor 3D, rutas manuales/A*, mapas NASA y módulos de IA.
- WebApp/backend/app: API FastAPI de ciencia, catálogo NASA, análisis eólico, asistente y tareas.
- WebApp/mars_ml: procesamiento e investigación del ZIP del compañero.
- recursosU/: fuentes, originales, scripts y documentación históricos conservados.
- output-stage1/, output-stage3/, output-stage4/: derivados y cachés consumidos por la aplicación.
- integration-review/: respaldo anterior, ZIP extraído, inventarios y evidencias de la combinación.

Las carpetas ops_mars-main/ y backend/ de la raíz son copias parciales históricas, identificadas con LEGACY_COPY.md. No ejecutar sus servidores ni los scripts reorganize.py/consolidate.py antiguos: esos scripts borran o mueven carpetas y originaron referencias rotas. Se conservaron para recuperación; no son el punto de desarrollo.

## Arranque

Ejecutar Start-BridgesMavors.ps1 desde esta carpeta. Inicia los servidores locales que falten y muestra el enlace http://127.0.0.1:4173/explorer. La vista usa la última compilación.

Después de cambiar frontend, ejecutar desde WebApp/frontend: npm run build. Para desarrollo: npm run dev. Para backend: WebApp/backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000, desde WebApp/backend. API documentada en http://127.0.0.1:8000/docs.

## Verificación

Frontend: npm run lint, npm run build y npm run test:terrain desde WebApp/frontend.
Backend: .venv/Scripts/python.exe -m pytest tests ../mars_ml/tests -q, desde WebApp/backend, con PYTHONPATH incluyendo WebApp y WebApp/backend.
Dependencias: npm ci en frontend; uv pip install --python WebApp/backend/.venv/Scripts/python.exe -r WebApp/backend/requirements.txt desde la raíz.

Detalles y límites en docs/INTEGRATION_REPORT.md. El catálogo de imágenes y las simulaciones de misión no constituyen mediciones científicas validadas. Los análisis eólicos necesitan imágenes/etiquetas locales y metadatos; el ZIP aporta manifiestos, no todos los píxeles ni un modelo predictivo entrenado.

## Etapas 5 y 6 auditadas — 2026-11-15

Inspección científica, indicadores agrupados, condiciones compartidas y A* conectados a Mars Explorer, Route Planner y Terrain Analysis. Se preservaron IA, mapa 2D, original y chunks. Estado detallado, archivos, pruebas y capturas: [auditoría](docs/AUDIT_STAGES_05_06.md). [Límites científicos](docs/SCIENTIFIC_LIMITATIONS.md), [diccionario](docs/DATA_DICTIONARY.md) y [arquitectura](docs/ARCHITECTURE.md).

Para comprobar: Load 3D terrain → Import preliminary route → Use endpoints only → Calculate routes. Comparar alternativas y perfil; inspeccionar mediante clic derecho o Inspect mode. Export mission guarda JSON; Import mission valida entradas y requiere recalcular. Cambiar condiciones marca resultados anteriores Outdated. La guía completa incluye filtros, exclusiones, ausencia de solución, cancelación y persistencia entre páginas.

Datos efectivos: DEM HRSC/MOLA a 250 m y polvo histórico MY36 regional opcional. Temperatura, viento, movilidad mecánica y radiación no evaluados se muestran Unavailable. Hora local/Ls/clima deshabilitados sin MCD. No hay optimización temporal ni navegación certificada. Contornos exactos y prueba táctil física pendientes; sólo LOD0.

Resultado final: 170 pruebas Python aprobadas, una omitida por symlinks Windows; 17 pruebas frontend, lint y build aprobados. Reproducción científica desde raíz: WebApp/backend/.venv/Scripts/python.exe scripts/validate-stages-05-06.py. Las advertencias de bundles grandes persisten; no equivalen a una prueba de rendimiento móvil.
