from pathlib import Path
skills={
'mars-geospatial':('Procesar DEM y DTM científicos de Marte, GeoTIFF y productos MOLA, CTX, HiRISE y HRSC con trazabilidad geográfica.', '''Usar únicamente elevaciones de NASA/PDS, USGS o ESA con producto y URL verificables. Nunca fabricar datos, ruido, montañas, rellenos ni utilizar imágenes generativas o capturas como DEM. Si falta la fuente, detener la geometría e informar.
Inspeccionar Rasterio/GDAL: CRS WKT, transformación afín, resolución, dimensiones, unidades, escala/offset, máscara y NoData antes de NumPy. No tratar NoData como altura cero. Conservar fuente, SHA-256, máscara y Float32 original.
Distinguir radio planetario, altura sobre elipsoide y altura sobre areoide. Verificar datum vertical en documentación; no inferirlo del nombre. Usar pyproj con cuerpo y elipsoide marcianos; jamás EPSG terrestre. Comprobar latitud planetocéntrica/planetográfica, longitudes este/oeste, centros/bordes de píxel y envoltura longitudinal.
Antes de combinar MOLA, CTX, HiRISE o HRSC verificar cobertura, registro horizontal, datum vertical y resolución efectiva. Una ortofoto no es un DTM. Registrar remuestreo y error; no presentar interpolación como medición. No incorporar más resolución si no mejora un producto compatible.
Entregar metadatos con origen local, conversión reversible de ejes, límites, referencia vertical y procedencia. Verificar alturas y coordenadas contra fuente en puntos distribuidos.
Consultar https://gdal.org/en/stable/drivers/raster/pds.html y https://rasterio.readthedocs.io/en/stable/topics/reproject.html para lectura y transformación. Para catálogo MOLA: https://pds-geosciences.wustl.edu/missions/mgs/megdr.html .'''),
'voxel-terrain':('Generar terrenos voxelizados en Blender Python a partir de matrices científicas reales de elevación de Marte.', '''Exigir entrada científica validada por mars-geospatial, máscara y transformación espacial. Exclusivamente alturas procesadas del DEM; prohibidos ruido, accidentes inventados y generadores IA 3D.
Trabajar con bpy mediante script reproducible o Blender MCP. Conservar escenas ajenas. Usar un mesh por chunk, no objetos por voxel. Crear techos de columnas y sólo porciones laterales expuestas entre vecinos, consultando también vecinos fuera del chunk. No crear caras internas entre alturas iguales. Greedy meshing sólo fusiona superficies coplanares del mismo material sin cambiar altura ni límites; es opcional si elimina detalle visual necesario.
Conservar escala horizontal/vertical 1:1. Documentar cuantización y su error máximo; mantener alturas originales aparte. No rellenar agujeros NoData artificialmente. Chunks y LOD comparten origen y extensión; agregación determinista con máscara documentada.
Estética Death Stranding 2 sólo como referencia: bloques pequeños densos, pendientes escalonadas, iluminación rasante y acabado mate. Paleta ocre, marrón, rojiza y gris; colores derivados de altura/pendiente se identifican como ilustrativos, no mediciones de albedo. Sin vegetación, estructuras ni UI.
Blender: X este, Y norte, Z arriba; exportador glTF convierte a X este, Y arriba, Z sur. Una unidad equivale a un metro. Validar orientación en archivo exportado y renderizar vista general y detalle.
API oficial: https://docs.blender.org/api/4.4/ .'''),
'glb-optimization':('Exportar, optimizar y validar terrenos GLB/glTF 2.0 con chunks, LOD y referencias espaciales conservadas para Three.js.', '''Exportar materiales PBR compatibles, compartir materiales y agrupar geometría para reducir draw calls. Conservar escala métrica, ejes y origen; no recentrar cada chunk. Mantener extras de procedencia y JSON externo con CRS, transformación, resolución, máscara y manifiesto.
Generar LOD desde el mismo DEM y comparar sus errores con LOD0. No afirmar que simplificación preserva exactitud sin medirla. Ofrecer GLB base interoperable. Meshopt (EXT_meshopt_compression) o Draco (KHR_draco_mesh_compression) son alternativas, no aplicar ambas por defecto. Registrar cuantización y comparar posiciones decodificadas; omitir compresión si excede presupuesto de error.
Para Three.js configurar GLTFLoader.setMeshoptDecoder o setDRACOLoader según extensión. No crear web ni interfaz para demostrarlo. Probar carga programática y verificar bounding boxes, ejes, materiales, metadatos y conteos.
Ejecutar Khronos glTF Validator, guardar reporte, resolver errores y explicar advertencias. Abrir en Blender y revisar visualmente. Reportar peso, triángulos, primitivas y limitaciones de LOD/chunks.
Documentación: https://github.com/KhronosGroup/glTF-Validator , https://gltf-transform.dev/ , https://threejs.org/docs/ .''')}
for name,(desc,body) in skills.items():
 p=Path('.agents/skills')/name;p.mkdir(parents=True,exist_ok=True)
 (p/'SKILL.md').write_text(f'---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n\n{body}\n',encoding='utf-8')
Path('AGENTS.md').write_text('''# Restricciones obligatorias
Usar .agents/skills/mars-geospatial, voxel-terrain y glb-optimization según etapa.
Proyecto: terreno voxelizado real de Jezero CTX 20 m, no globo global. Fuente inicial especificada por usuario. Nunca inventar geografía ni sustituir datos fallidos por ejemplos. No servicios generativos IA 3D.
No desarrollar páginas web, aplicaciones, UI, rutas, marcadores, servidores ni bases de datos. No instalar complementos innecesarios.
Conservar fuente científica, SHA-256, CRS marciano, datum vertical, NoData y alturas originales. Escala real 1:1, unidad metro, GLB X este/Y arriba/Z sur. Origen común para chunks y tres LOD cuando viable.
Estética sólo en materiales y discretización documentada; no modificar alturas sin registrar error. No mezclar Gale y Jezero. Validar científicamente y con glTF Validator; entregar renders, metadatos, binarios, máscara, manifiesto, scripts, README, SOURCES e informe. No afirmar exactitud absoluta.
Instalar dependencias localmente en .venv y tools. No sobrescribir trabajo ajeno de Blender.
''',encoding='utf-8')
