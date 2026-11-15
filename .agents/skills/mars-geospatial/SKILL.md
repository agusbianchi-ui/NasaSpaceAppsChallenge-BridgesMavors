---
name: mars-geospatial
description: Procesar DEM y DTM científicos de Marte, GeoTIFF y productos MOLA, CTX, HiRISE y HRSC con trazabilidad geográfica.
---

# mars-geospatial

Usar únicamente elevaciones de NASA/PDS, USGS o ESA con producto y URL verificables. Nunca fabricar datos, ruido, montañas, rellenos ni utilizar imágenes generativas o capturas como DEM. Si falta la fuente, detener la geometría e informar.
Inspeccionar Rasterio/GDAL: CRS WKT, transformación afín, resolución, dimensiones, unidades, escala/offset, máscara y NoData antes de NumPy. No tratar NoData como altura cero. Conservar fuente, SHA-256, máscara y Float32 original.
Distinguir radio planetario, altura sobre elipsoide y altura sobre areoide. Verificar datum vertical en documentación; no inferirlo del nombre. Usar pyproj con cuerpo y elipsoide marcianos; jamás EPSG terrestre. Comprobar latitud planetocéntrica/planetográfica, longitudes este/oeste, centros/bordes de píxel y envoltura longitudinal.
Antes de combinar MOLA, CTX, HiRISE o HRSC verificar cobertura, registro horizontal, datum vertical y resolución efectiva. Una ortofoto no es un DTM. Registrar remuestreo y error; no presentar interpolación como medición. No incorporar más resolución si no mejora un producto compatible.
Entregar metadatos con origen local, conversión reversible de ejes, límites, referencia vertical y procedencia. Verificar alturas y coordenadas contra fuente en puntos distribuidos.
Consultar https://gdal.org/en/stable/drivers/raster/pds.html y https://rasterio.readthedocs.io/en/stable/topics/reproject.html para lectura y transformación. Para catálogo MOLA: https://pds-geosciences.wustl.edu/missions/mgs/megdr.html .
