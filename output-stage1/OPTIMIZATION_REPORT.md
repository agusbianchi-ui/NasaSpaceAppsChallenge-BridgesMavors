# Etapa 1 — inspección y optimización del original

## Entrega y alcance
Original intacto: ../MapaMarteN.glb, SHA-256 8786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48. Verificación antes/después en script. No se sustituyó por output-visual ni se infirió región geográfica desde el nombre. Aplicación sin modificaciones.

Archivo principal: **terrain-joined-meshopt.glb**. Alternativa con particiones dentro de un archivo: terrain-lod0-meshopt.glb. Carga por sectores: los44 archivos chunks/*.glb. Elegir una alternativa; no cargar las tres simultáneamente.

Para herramientas sin Meshopt: terrain-joined-decoded.glb, derivado del archivo comprimido final, y terrain-lod0.glb (base sin compresión). Ambos conservan calidad completa. inventory.json incluye pesos y hashes de recursos. No instalar plugins para abrir la copia decodificada en Blender.

## Características verificadas directamente
| Característica | Original |
|---|---|
| Formato/peso | GLB2.0; 242847404 bytes; 231.597332 MiB |
| Escenas/nodos/mallas/materiales | 1 /45 /44 /44 |
| Triángulos | 2897732 |
| Primitivas | 44 TRIANGLES, una por malla |
| Color | COLOR_0 en todas las primitivas; conservado componente por componente |
| Materiales |44 definiciones equivalentes salvo nombre, metallicFactor0; resto valores glTF por defecto |
| Texturas |0; no hay imágenes para comprimir |
| Transformaciones del terreno | Identidad, comprobada en44 nodos; sin recentrado ni escalado |
| Animación/auxiliar |1 animación sobre Vista giratoria - no exportar; retirados junto con sus accessors |
| Límites XYZ | [-100000,1800,-101000] a [100000,15462,101000] |
| Dimensiones XYZ | [200000,13662,202000] unidades del modelo |
| Bloques superiores |250×250 unidades XZ; 507538 celdas superiores |
| Orientación |Y arriba geométricamente; Blender convierte a Z arriba al importar. Correspondencia este/norte/geográfica no verificada |
| Relieve3× |Nombre de escena lo sugiere; no prueba datum ni transformación científica. Escala vertical intacta |

original-structure.json conserva escenas/nodos/materiales/accessors del archivo. geometry.json contiene métricas. No se identificaron otras geometrías además de las44 mallas del terreno; el único auxiliar era nodo vacío animado.

## Métodos evaluados y decisiones
- Materiales equivalentes reunidos en uno; colores no dependen de nombres de material.
- Variante agrupada: concatenación explícita de posiciones/normales/colores e índices desplazados, sin simplificación ni soldadura que cambie discontinuidades. Una primitiva reduce la estimación de draw calls de44 a1 por pasada, a costa de perder descarte espacial por chunk.
- Alternativa44 chunks: misma partición que el original; coordenadas globales y origen compartido, transformación identidad. Permite carga/descarte por sector en una integración futura; no se implementó scheduler ni visor.
- Meshopt: compresión de buffers sin transformación de cuantización. Se verifica igualdad exacta de cada atributo y triángulo decodificado (se admiten rotaciones cíclicas equivalentes de índices). Error máximo de posición/color/normal0 en comparaciones realizadas. Es una propiedad de esta configuración/archivo, no garantía universal de Meshopt.
- Draco evaluado como alternativa: instalación existente, su transformación habitual cuantiza atributos y puede reordenarlos. No se aplicó ni se benchmarkeó porque Meshopt ya cumple igualdad exacta; no se afirma superioridad de tamaño/velocidad frente a Draco. No combinar compresores.
- Caras internas: comprobación de paredes frente a alturas de columnas vecinas encontró0 triángulos verticales completamente internos. No se eliminaron caras del terreno. No hay caras orientadas hacia abajo; base abierta preexistente, no sólido imprimible.
- LOD1/LOD2 no generados: simplificación arbitraria puede borrar escalones; los LOD históricos pertenecen a conjuntos no vinculados todavía por transformación verificada al original. Reagregar celdas de la matriz visual cambiaría bordes/alturas y requeriría un presupuesto de error aprobado. Se entrega LOD0 completo y chunks; no se presenta una copia de igual complejidad como LOD reducido. No se garantiza rendimiento móvil.

## Medidas
| Recurso | MiB | Triángulos | Mallas | Materiales | Primitivas/pasada estimadas |
|---|---:|---:|---:|---:|---:|
| Original |231.597|2897732|44|44|44|
| terrain-lod0-meshopt.glb |51.866|2897732|44|1|44|
| terrain-joined-meshopt.glb |51.808|2897732|1|1|1|

La variante agrupada ocupa54324304 bytes: reducción77.63%. Suma de44 archivos chunk:51.891MiB. Son alternativas de empaquetado, no distintos terrenos.

## Coordenadas y alturas visuales
original_to_optimized y optimized_to_original son matriz identidad4×4, incluidas en manifest.json: (x,y,z) permanece (x,y,z). Posición del nodo/origen común [0,0,0]; sus bounds no son su traslación. Mantener coordenadas al cargar. No afirmar unidades científicas/CRS a partir del formato GLB.

Matriz extraída: visual-height.f32 y visual-valid.u8, shape[808,800]. Filas crecen +Z, columnas +X; origen de bordes X=-100000,Z=-101000; paso250. Centro: X=-100000+(col+0.5)*250; Z=-101000+(fila+0.5)*250. Altura es Y visual original, no DEM científico ni dato sin exageración. Ausentes NaN, máscara0; presentes máscara1. La inversa usa floor((X+100000)/250), floor((Z+101000)/250) y comprobación de límites/máscara. En bordes entre columnas la superficie es discontinua; definir convención antes de anclar rutas. No calcular pendientes científicas ni dividir por3 sin verificar transformación del original.

## Validación
Todos46 GLB comprimidos se decodificaron, compararon y cargaron con Three.js GLTFLoader en Node; no prueba de navegador/GPU/FPS. Cada entrega registra bounds, SHA-256, conteos y resultados en manifest.json. Khronos Validator:0 errores/0 advertencias en comprimidos; informa que no valida EXT_meshopt_compression y un buffer de respaldo sin uso. Para cubrir esa limitación se validó también cada representación decodificada:0 errores/0 advertencias, además de comparación numérica y carga Three.js.

Blender4.4.3 abrió original y copia decodificada. Blender MCP volvió a conectar y abrió el optimizado en escena nueva, restituyendo la escena activa previa; no se guardó ni sobrescribió trabajo ajeno. Renders mediante proceso Blender independiente.

Comparación visual: original-overview.png vs optimized-overview.png y original-detail.png vs optimized-detail.png. Cámaras, iluminación, semilla, muestras y color iguales; render-settings.json detalla parámetros. Ambos pares son idénticos píxel a píxel: diferencia máxima0, media0; inspección visual confirma color, relieve y escalones. comparison.png: izquierda original, derecha optimizado; arriba general, abajo detalle.

Huecos:0 celdas vacías encerradas en máscara superior a250 unidades;0 triángulos degenerados. Igualdad de todos los triángulos/atributos garantiza que la optimización no introduce huecos ni cambia caras. No es certificación de manifold ni de seguridad de navegación. Se conserva perímetro escalonado y base abierta.

## Reproducibilidad
Desde raíz del proyecto, con dependencias existentes:

```powershell
.venv/Scripts/python.exe scripts/inspect-stage1.py
node --max-old-space-size=8192 tools/optimize-stage1.mjs
D:/blender.exe -b --python scripts/render-stage1.py
.venv/Scripts/python.exe scripts/compare-stage1.py
```

Scripts escriben exclusivamente sus derivados en output-stage1; el original se lee sin modificar. Inspección falla ante cambios de estructura incompatibles. Dependencias en tools/package-lock.json y entorno científico existente; no se instalaron otras.

## Fuentes técnicas y límites
[glTF Transform EXTMeshoptCompression](https://gltf-transform.dev/modules/extensions/classes/EXTMeshoptCompression), consultada durante la etapa: modo QUANTIZE sin preprocesamiento de cuantización, decoder explícito y validación de datos tras lectura. El tamaño transferido no equivale a rendimiento web. Documentación técnica no establece procedencia científica del GLB.

Etapa cerrada. No implementar visor, controles, rutas o indicadores sin siguiente prompt. Pendientes: vínculo científico del original, eventual método LOD con error aceptado y mediciones reales en navegador durante la integración.
