## Etapa 2 — visor 3D integrado

[Informe, pruebas y ejecución](docs/stages/02-visor-navegacion.md). Abrir Mars Explorer y pulsar Load 3D terrain. Se conserva mapa2D. No hay rutas/indicadores científicos nuevos.

## Etapa 0 — aplicación existente

Preparación ejecutada. Consultar [diagnóstico y comandos Windows](docs/stages/00-diagnostico.md) y [estado](docs/IMPLEMENTATION_STATUS.md). Aplicación en ops_mars-main/; original autorizado MapaMarteN.glb preservado. No se inició integración3D.

# Documentación permanente de Bridges Mavors

- [AGENTS.md](AGENTS.md): reglas permanentes.
- [Especificación](docs/PROJECT_SPEC.md): visión, alcance y decisiones aprobadas.
- [Estado](docs/IMPLEMENTATION_STATUS.md): inventario, evidencia y pendientes.
- [Limitaciones](docs/SCIENTIFIC_LIMITATIONS.md): resolución, errores e interpretación.
- [Diccionario](docs/DATA_DICTIONARY.md): formatos, campos y coordenadas.
- [Arquitectura](docs/ARCHITECTURE.md): pipeline observado y criterios futuros.
- [Diseño](docs/DESIGN_GUIDELINES.md): identidad y validación visual.
- [Etapas](docs/stages/README.md): próximos prompts y secuencia de consulta.
- [Fuentes](SOURCES.md): procedencia y atribución.

Las instrucciones operativas conservadas abajo describen artefactos existentes. No autorizan iniciar implementaciones o regeneraciones. La aplicación de ops_mars-main.zip no está verificada aquí. Los metadatos y limitaciones deben acompañar al conjunto elegido; no ensamblar variantes directamente.

# Versión visual actualizada
La versión más reciente está en **output-visual/**: DEM HRSC/MOLA 200 m procesado a 250 m, relieve visual 3x y color orbital Viking de NASA Trek. Ver output-visual/README.md para integración y exportación. Los datos de elevación originales se conservan sin exagerar. output-visual/mars-visual-playback.blend incluye una cámara giratoria (Espacio para reproducir/pausar; no exportar cámaras ni animación). Los GLB ya exportados no incluyen esta cámara.

# Terreno marciano: zona de exploración Jezero
## Resultado y alcance
`output-region/` contiene toda la EZ circular oficial de Mars Trek (FID 27), centro 77 E, 17.5 N, buffer 100 km. Es una base regional MOLA con celdas 500 m; no ofrece detalle CTX de 20 m en toda la zona. El polígono original está en data/raw/ez-layer4.json.
`output/` contiene una prueba CTX del delta occidental de 15.36 km de lado, 20/40/80 m. No es toda la EZ. No ensamblar ambos conjuntos directamente: tienen distintos orígenes, proyecciones y referencias verticales pendientes de reconciliación. No se ha fusionado CTX con MOLA ni incorporado HiRISE.
## Archivos regionales
- manifest.json: 21 GLB base distribuidos en tres LOD, 500/1000/2000 m.
- manifest-meshopt.json y meshopt/: versiones comprimidas, posiciones conservadas exactamente.
- metadata.json: fuente, SHA256 del TIFF exportado, CRS WKT, origen, ejes y transformación.
- ez-dem.tif, elevation.f32 y valid.u8: matriz 512x512, Float32 little-endian por filas norte-sur; NaN fuera de cobertura, máscara 1 válido/0 inválido.
- jezero-preview.blend, preview-overview.png, preview-detail.png: inspección Blender de LOD0 regional.
- validation-data.json, validation-glb.json: errores de LOD y validación estructural/carga Three.js.
Material mate compartido con colores por vértice ilustrativos, sin texturas externas. No son colores medidos. Escala vertical 1:1. Cuantización vertical 2 m. Caras laterales sólo expuestas; superficie sin fondo sólido (no es modelo imprimible cerrado). Los muros exteriores son cierre visual hasta una cota documentada, no medición del subsuelo.
## Integración
Una unidad = un metro. GLB X este, Y arriba, Z sur. Todos los chunks de cada conjunto usan el mismo origen y coordenadas absolutas locales: no recentrar ni escalar individualmente. Cargar únicamente un LOD por sector; las cuadrículas de chunks cambian entre niveles. Los LOD gruesos generalizan el borde circular por presencia de datos válidos.
Para Meshopt, GLTFLoader.setMeshoptDecoder(MeshoptDecoder). Los GLB base no requieren decodificador. Usar la matriz inversa indicada en metadata para recuperar coordenadas proyectadas. La proyección regional azimutal equidistante preserva distancia desde el centro; no preserva exactamente todas las distancias entre puntos.
## Reproducción (PowerShell desde raíz)
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt
npm ci --prefix tools
.venv/Scripts/python.exe scripts/fetch_boundary.py
.venv/Scripts/python.exe scripts/download_region.py
.venv/Scripts/python.exe scripts/build_region.py
Push-Location tools
node validate-region.mjs
node compress-region.mjs
Pop-Location
& D:/blender.exe -b -t 8 --python scripts/render_region.py

Blender está instalado en D:/blender.exe; ajustar esa ruta y la raíz absoluta del script de render si se mueve el proyecto. Para la prueba CTX: scripts/download.py y scripts/build.py. La descarga fuente CTX ocupa unos 90 MB. No se instalaron addons Blender; MCP 4.4.3 disponible. GDAL se utiliza mediante Rasterio, no como CLI separada. Context7 no estaba disponible; se consultaron fuentes oficiales.
## Limitaciones científicas
MOLA ofrece aproximadamente 463 m por píxel en el ecuador; remuestrear no añade detalle medido. La base 500 m es para contexto regional, no navegación fina ni seguridad de astronautas. El relieve real parece poco pronunciado a escala de 200 km; no se exageró para imitar el videojuego. LOD1/2 sirven sólo para vistas lejanas; sus errores deben consultarse antes de utilizarlos científicamente. El datum CTX exacto no está explícito en la etiqueta y los metadatos del catálogo difieren ligeramente del radio del GeoTIFF; se conservó el CRS del archivo. El producto regional usa el CRS publicado por el servicio y su geometría vectorial, sin reclasificarlo como terrestre.

## Etapas3 y4
Visor con marcadores y rutas manuales: docs/stages/03-interaccion-geometrica.md.
Registro geográfico recuperado, alturas científicas y servicios: docs/stages/04-georreferenciacion-ciencia.md.
Demo local: http://127.0.0.1:4173/explorer . API: http://127.0.0.1:8000/docs . La API científica no certifica rutas ni seguridad. Datos faltantes explícitos; no A* ni nueva interfaz de peligros.
