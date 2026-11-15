# Fuentes consultadas — 2026-11-14
## Geometría del área
NASA EMC / Mars Trek, Exploration Zones, EZ_Buffer FID 27, Jezero Crater, propuesta 1034. Centro de capa 17.5 N, 77 E; BUFF_DIST 100 km. Geometría original conservada, transformada a proyección local y rasterizada por centros de celda.
https://trek.nasa.gov/mars/trekarcgis/rest/services/EZMars/MapServer/4
El documento de propuesta cita otro centro (17.747 N, 77.037 E). Se priorizó el polígono de la captura de Mars Trek.
https://www.nasa.gov/wp-content/uploads/2015/06/mars-c-abstracts_in_order_of_presentation10242015_0.pdf
## DEM regional
NASA/MGS/MOLA, mosaico 128/64 ppd. Descarga numérica float32 TIFF, no relieve coloreado. Request y respuesta en docs/region-export.json. Remuestreo vecino más cercano a 500 m, recorte de polígono; LOD por medias válidas y cuantización a 2 m. Elevaciones topográficas MOLA respecto del areoide. Crédito NASA/MGS/MOLA Science Team y NASA/JPL Mars Trek; no se presupone licencia comercial de materiales ajenos.
https://trek.nasa.gov/mars/trekarcgis/rest/services/mola128_mola64_merge_90Nto90S_SimpleC_clon0/ImageServer
https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
## DEM CTX (prueba separada)
USGS/PDS/JPL, Fred Calef; Mars Reconnaissance Orbiter, Context Camera. Mars 2020 Science Investigation CTX DEM Mosaic, 20 m. Mangold et al. 2021, doi:10.1126/science.abl4051. Datos públicos científicos; conservar atribución del producto. Fuente y etiqueta PDS4 originales guardadas. Sólo recorte, medias LOD y cuantización; no fusión entre DEM.
https://astrogeology.usgs.gov/search/map/mars_2020_science_investigation_ctx_dem_mosaic
Descarga alternativa del mismo catálogo USGS (enlace planetarymaps devolvía 403):
https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif
https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/index.html
## Recursos investigados sin incorporar geometría
HiRISE TRN Jezero, USGS, doi:10.5066/P9REJ9JN, CC0; candidato de detalle, no fusionado porque requiere verificar registro/datum y no cubre toda la EZ.
https://www.usgs.gov/data/mars-2020-terrain-relative-navigation-hirise-dtm-mosaic
https://mars.nasa.gov/mars2020/multimedia/raw-images/ — fotografías rover, no DEM; galería requiere JavaScript. No se extrajo albedo medido.
https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars — catálogo interactivo, sin texto accesible.
https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ — referencia de Gale, excluida de Jezero.
https://trek.nasa.gov/mars/ — catálogo/API usados. Capa sombreada MOLA/HRSC de la captura no usada como alturas.
## Herramientas
https://gdal.org/en/stable/drivers/raster/pds.html
https://rasterio.readthedocs.io/en/stable/topics/reproject.html
https://github.com/KhronosGroup/glTF-Validator
https://gltf-transform.dev/modules/functions/functions/meshopt
https://threejs.org/docs/
## Referencias estéticas
Capturas y video de Death Stranding 2 proporcionados por usuario. Tres fotogramas a 15/50/85 por ciento del video de 28.11 s inspeccionados. Bloques densos, escalones y sombras laterales como guía; ningún dato geográfico o asset del juego utilizado en el modelo.

## Actualización visual autorizada — 2026-11-14
DEM USGS HRSC/MOLA blended 200 m v2: https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m
Archivo original: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif
NASA MGS MOLA y ESA Mars Express HRSC; recorte nativo por HTTP Range, reproyección bilineal a 250 m, datos originales conservados; sólo GLB exagerado 3x.
Color: https://astrogeology.usgs.gov/search/map/mars_viking_colorized_global_mosaic_232m
NASA Viking VIS, USGS MDIM21 colorizado. WMTS oficial, nivel 7: https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml
URLs de cada tesela y hashes en docs/visual-sources.json. Grilla WMTS de 0.005493 grados/pixel (~326 m al ecuador), producto nominal 232 m; no se confunde resolución de servicio con resolución fuente. Mosaico colorizado, no true-color calibrado. No se usó la captura del usuario como textura ni como elevación.

## Organización documental — 2026-11-14
Se preservan consultas/atribuciones anteriores. Esta revisión no volvió a acceder a fuentes web ni verifica nuevas licencias. Limitaciones centralizadas en docs/SCIENTIFIC_LIMITATIONS.md. No interpretar disponibilidad pública como licencia sin condiciones; comprobar condiciones antes de redistribuir cuando no estén determinadas.

Requisitos consolidados desde adjunto del usuario “Instrucciones complementarias permanentes — Bridges Mavors”, C:/Users/agusb/.codex/attachments/4443b26f-db54-49f4-9c94-3b2401bd6330/Texto pegado.txt y decisiones aprobadas de esta conversación. Son instrucciones de proyecto, no evidencia científica. Procedencia de MapaMarteN.glb/MapaMarte1.blend no determinada aquí; preservar y verificar antes de publicar.

## Evidencia Etapa 0 (2026-11-14)
- Instrucciones del usuario: docs/stages/00-preparacion-prompt.md, copia íntegra del adjunto 5a01b181-3f96-456e-87ea-27d2c6fa8998/Texto pegado.txt.
- ops_mars-main.zip: fuente local de código, no fuente científica. Catálogo/procedencia heredados en ops_mars-main/docs/data_sources.md; no se revalidaron todas las afirmaciones externas del catálogo en esta etapa.
- MapaMarteN.glb: original seleccionado por usuario; SHA-256 8786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48 sobre archivo completo. Inspección/Validator en docs/stages/00-evidence; no implica georreferencia certificada.
- ruta_marte_preliminar.json: artefacto local preexistente, georreferencia/supuestos no verificados según sus propios campos; no observación científica.
- Versiones, pruebas y diagnóstico se basan en archivos locales, ejecución y navegador; no se añadieron nuevas fuentes científicas ni mediciones.

## Etapa 1
Fuente geométrica exclusiva: MapaMarteN.glb, hash completo preservado en output-stage1/manifest.json. No nuevas coordenadas ni atribución planetaria inferida. Documentación técnica consultada: https://gltf-transform.dev/modules/extensions/classes/EXTMeshoptCompression . Métodos/errores medidos: output-stage1/OPTIMIZATION_REPORT.md.

## Etapa2 — 2026-11-15
Recursos exclusivos: output-stage1/chunks y manifest.json, verificados SHA-256 al preparar y descargar. Documentación oficial: https://threejs.org/docs/pages/OrbitControls.html y https://threejs.org/docs/pages/GLTFLoader.html . Referencias visuales: capturas suministradas y docs/video-reference.jpg (fotogramas del video del usuario). No se incorporaron assets de Death Stranding2.

## Etapa3 — geometría visual, acceso2026-11-15
Original MapaMarteN.glb, SHA-2568786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48: fuente única de matriz visual; no nueva fuente planetaria. Derivados/hash en output-stage3/terrain_metadata.json. ruta_marte_preliminar.json: referencia del proyecto,155 puntos, coincidencia Y visual exacta, no validación científica.
Documentación oficial consultada: https://threejs.org/docs/pages/Raycaster.html y https://github.com/gkjohnson/three-mesh-bvh . BVH indirecto usado sin reordenar atributos del terreno; versión0.9.18 en lockfile.

## Etapa4 — registro y consultas científicas (acceso2026-11-15)

- **HRSC/MOLA v2, USGS/NASA/ESA-DLR; MGS/MOLA yMars Express/HRSC.** [Catálogo](https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m), [GeoTIFFoficial](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif), [PDS3](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2_pds3.lbl), [ISIS](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.lbl). Nominal200m, planetocéntrico/este[-180,180], esfera3396190m. Elevacionesmetro preservadas; realizaciónvertical precisa pendiente. Recorteoficial guardadohash8f29232a711b87259e62ff1fe556841969c1b32686b361b332c4214375a81e46, cinco muestrasremotas contrastadas; nohashdelglobal completo. Reproyecciónbilineal250m, máscaraEZ yquantizaciónvisual documentadas, reconstrucciónexacta. AtribuciónFergason/Hare/Laura2018, NASA/USGS/ESA-DLR; términos de componentesMOLA(CC0)/HRSC(CC BY-SA3.0IGO) según [catálogoUSGScompañero](https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_shaded_relief_200m). Noimponer ±3m como incertidumbrelocal de lamezcla. Catálogo directo devolvió403; secontrastaron registroindexado y etiquetasdescargadas.
- **PolvoMY36v2.5, Montabone/LMD, MRO/MCSv5.2.** [Documentación/licencia](https://www-mars.lmd.jussieu.fr/mars/dust_climatology/), [NetCDF](https://www-mars.lmd.jussieu.fr/mars/dust_climatology/dataset_v2/griddedcdod_MY36_v2-5.nc). DerivadoobservacionalIWB,6°lon×5°lat,1sol/mediadía, MY36; fuente63,615,972bytes, SHA-256eb8bc34147850050f9b62fa0d842a1b74d00833a97aa6b104a8accdd785c1649. cdod610/unc enPa/Pa, absorción9.3µm normalizada610Pa; noextinciónvisible. Cacheunacelda[75,81)E×[15,20)N sininterpolación,558solesválidos/111NaN. Originalmetadatos,incertidumbre,tiemposyventanas retenidos. CC BY-SA3.0Unported; citarMontabone2015/2020 y recursoMY36v2.5, cambios: recorteregional/serializaciónNPZ. ConvenciónMCSplanetocéntrica referenciadaen [PDSODE](https://ode.rsl.wustl.edu/mars/pagehelp/Content/Frequently_Asked_Questions/Coordinate_System.htm); NetCDFdeclara gradosN/E, sinWKT. Noactualizarpresiónsinmodeloválido.
- **MCD:** [web6.2](https://www-mars.lmd.jussieu.fr/mcd_python/) y [documentaciónenlazada6.1](https://www-mars.lmd.jussieu.fr/mars/info_web/index.html). ClimatologíaGCM porLs,hora,altitud yescenarios de polvo/EUV; no pronóstico. Proveedor numérico/versionado nointegrado; valoresnull. Librepara usocientífico/ingeniería con citasdelautor; no conjunto descargado.
- **ASU:** [catálogo](https://mars.asu.edu/data/), [albedoTES8ppd](https://mars.asu.edu/data/tes_albedo/), [inerciaTES20ppd](https://mars.asu.edu/data/tes_putzigti/nighttime2005/), [polvosuperficial16ppd](https://mars.asu.edu/data/tes_ruffdust/). Disponibilidaddeproductosnuméricos ycoloreadosdistinta; rawVICARalbedo localizado pero sincontratoCRS/NoDatavalidado. No convertirPNGenvalores. No proveedor cuantitativoregistrado ni licenciaespecíficaverificada para redistribución.
- **Otrasfuentesconsultadas:** [NASA TrekAPI](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars), [PDSMOLA](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html), [HiRISE](https://hirise.lpl.arizona.edu/), [Perseveranceimágenes](https://mars.nasa.gov/mars2020/multimedia/raw-images/), [RADGale](https://science.nasa.gov/resource/radiation-measurements-on-mars/) y [rutaMountSharp/Gale](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/). Catálogos/referencias noañaden valorescientíficos de laregión. CTXlocal20m sigueparcial ysin fusiónvertical/registroreconciliados. Fotografías no DEM niestabilidad; RAD no mapaglobal.

Contratos/cobertura/faltantes porvariable: ops_mars-main/backend/app/data/science_catalog.json yGET/api/v1/science/sources. Metadatos/hashsalidas en output-stage4; registrosdescarga en data/science/downloads.json. [Rasterioreproject](https://rasterio.readthedocs.io/en/stable/topics/reproject.html) y [pyprojGeod](https://pyproj4.github.io/pyproj/stable/api/geod.html) consultados para reproyección/distancias sobre cuerpo marciano, no CRSterrestre.
