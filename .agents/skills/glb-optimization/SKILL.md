---
name: glb-optimization
description: Exportar, optimizar y validar terrenos GLB/glTF 2.0 con chunks, LOD y referencias espaciales conservadas para Three.js.
---

# glb-optimization

Exportar materiales PBR compatibles, compartir materiales y agrupar geometría para reducir draw calls. Conservar escala métrica, ejes y origen; no recentrar cada chunk. Mantener extras de procedencia y JSON externo con CRS, transformación, resolución, máscara y manifiesto.
Generar LOD desde el mismo DEM y comparar sus errores con LOD0. No afirmar que simplificación preserva exactitud sin medirla. Ofrecer GLB base interoperable. Meshopt (EXT_meshopt_compression) o Draco (KHR_draco_mesh_compression) son alternativas, no aplicar ambas por defecto. Registrar cuantización y comparar posiciones decodificadas; omitir compresión si excede presupuesto de error.
Para Three.js configurar GLTFLoader.setMeshoptDecoder o setDRACOLoader según extensión. No crear web ni interfaz para demostrarlo. Probar carga programática y verificar bounding boxes, ejes, materiales, metadatos y conteos.
Ejecutar Khronos glTF Validator, guardar reporte, resolver errores y explicar advertencias. Abrir en Blender y revisar visualmente. Reportar peso, triángulos, primitivas y limitaciones de LOD/chunks.
Documentación: https://github.com/KhronosGroup/glTF-Validator , https://gltf-transform.dev/ , https://threejs.org/docs/ .
