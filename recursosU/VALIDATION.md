# Alcance del informe histórico

Este informe corresponde a output-region/ (MOLA 1:1), no a variante visual posterior. Ver [estado actual](docs/IMPLEMENTATION_STATUS.md) y reportes de output-visual/. No se repitieron pruebas en revisión documental.

# Verificación

{
  "glb_files": 21,
  "base_bytes": 76728572,
  "meshopt_bytes": 16737240,
  "triangles_by_lod": {
    "0": 679256,
    "1": 186018,
    "2": 47864
  },
  "validator_errors": 0,
  "validator_warnings": 0,
  "lod_errors": [
    {
      "lod": 0,
      "max_error_m": 1.0,
      "rmse_m": 0.7071855664253235
    },
    {
      "lod": 1,
      "max_error_m": 275.0,
      "rmse_m": 23.95650863647461
    },
    {
      "lod": 2,
      "max_error_m": 521.0,
      "rmse_m": 47.217857360839844
    }
  ]
}

21 GLB abiertos mediante GLTFLoader de Three.js; compresión Meshopt decodificada con igualdad exacta de todas las posiciones. Blender importó LOD0 y produjo dos renders revisados. Escala sin exageración. Datos Float32 y máscara conservados. La cuantización de LOD0 introduce como máximo 1 m respecto de la matriz remuestreada; no representa exactitud instrumental de MOLA. LOD1/2 aumentan error y sólo sirven para visualización distante. La silueta circular se rasteriza, no es un límite vectorial exacto. No se verificó el datum CTX contra MOLA; ambas entregas permanecen separadas.
