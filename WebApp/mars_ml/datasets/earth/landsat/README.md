# USGS Landsat

- Missions: <https://www.usgs.gov/landsat-missions>
- STAC endpoint used for verification: <https://landsatlook.usgs.gov/stac-server/search>
- Collection: `landsat-c2l2-sr` (Collection 2 Level-2 surface reflectance)
- Data access and authentication: <https://m2m.cr.usgs.gov/>

## Verified record

`../sahara/scene_catalog.json` contains one verified scene:

- `LC08_L2SP_199039_20230629_20230711_02_T1_SR`
- Landsat 8 OLI/TIRS, WRS-2 path 199 row 039
- Acquisition: 2023-06-29T10:45:35.517341Z
- CRS: `EPSG:32630`
- Nominal surface-reflectance grid: 30 m

A single Landsat scene is not a multitemporal sequence. Use it for cross-sensor
comparison only after verifying a matched scene from another date.

## Processing notes

- Landsat and Sentinel-2 have different spatial resolutions, spectral response
  functions and acquisition times. Compare them only after explicit resampling
  and uncertainty documentation.
- Do not mix Landsat and Sentinel-2 pixels into one training example without
  recording the resampling method and target grid.
- USGS authentication is required for bulk machine-to-machine access. Do not
  store credentials in this repository.
