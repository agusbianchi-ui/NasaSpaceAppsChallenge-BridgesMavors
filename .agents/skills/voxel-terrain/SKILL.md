---
name: voxel-terrain
description: Generar terrenos voxelizados en Blender Python a partir de matrices científicas reales de elevación de Marte.
---

# voxel-terrain

Exigir entrada científica validada por mars-geospatial, máscara y transformación espacial. Exclusivamente alturas procesadas del DEM; prohibidos ruido, accidentes inventados y generadores IA 3D.
Trabajar con bpy mediante script reproducible o Blender MCP. Conservar escenas ajenas. Usar un mesh por chunk, no objetos por voxel. Crear techos de columnas y sólo porciones laterales expuestas entre vecinos, consultando también vecinos fuera del chunk. No crear caras internas entre alturas iguales. Greedy meshing sólo fusiona superficies coplanares del mismo material sin cambiar altura ni límites; es opcional si elimina detalle visual necesario.
Conservar escala horizontal/vertical 1:1. Documentar cuantización y su error máximo; mantener alturas originales aparte. No rellenar agujeros NoData artificialmente. Chunks y LOD comparten origen y extensión; agregación determinista con máscara documentada.
Estética Death Stranding 2 sólo como referencia: bloques pequeños densos, pendientes escalonadas, iluminación rasante y acabado mate. Paleta ocre, marrón, rojiza y gris; colores derivados de altura/pendiente se identifican como ilustrativos, no mediciones de albedo. Sin vegetación, estructuras ni UI.
Blender: X este, Y norte, Z arriba; exportador glTF convierte a X este, Y arriba, Z sur. Una unidad equivale a un metro. Validar orientación en archivo exportado y renderizar vista general y detalle.
API oficial: https://docs.blender.org/api/4.4/ .
