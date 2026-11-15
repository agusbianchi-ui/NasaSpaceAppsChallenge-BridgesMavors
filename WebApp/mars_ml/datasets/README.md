# Datasets

This directory separates metadata from pixels. No satellite pixels are committed.

## Rules

- Do not invent scene IDs, acquisition dates, bounding boxes or resolutions.
- Every scene in a catalog must be traceable to a provider search result.
- `data_status` must state whether metadata was verified and whether pixels were
  downloaded and validated.
- Synthetic test fixtures live under `tests/` and are never presented as
  satellite observations.
- Keep an area/sequence grouping so train/validation/test splits cannot leak
  images from the same dune field or acquisition sequence.

## Earth

`earth/sahara/scene_catalog.json` contains verified STAC metadata for a western
Erg Chebbi study window: four Sentinel-2 L2A scenes on MGRS tile `30RVV`
(2019, 2021, 2024, 2025) and one Landsat 8 Collection 2 surface-reflectance
scene. Verification date: 2026-11-14. Pixels were **not** downloaded.

`earth/sentinel/README.md` documents the Sentinel access path.
`earth/landsat/README.md` documents the USGS Landsat access path.

## Mars

`mars/` contains verified metadata only; no Mars pixels or per-dune labels are
committed.

- `mars/manifest.json` indexes five dataset manifests.
- `mars/hargraves/dataset.json`: Hargraves Crater dune polygons and morphometry
  from Mendeley Data, DOI `10.17632/bfnxzwhd4r.3`; no pixels, no time series.
- `mars/coprates/dataset.json`: Coprates Chasma polygons, measurement tables and
  CTX/DEM products from figshare, DOI `10.6084/m9.figshare.c.5198183.v3`;
  acquisition dates still require PDS resolution.
- `mars/ctx_multitemporal/dataset.json`: one selected Nili Patera early/late CTX
  pair plus DEM and FOM from figshare, DOI `10.6084/m9.figshare.c.4649537.v1`;
  acquisition dates still require PDS resolution. The other five sites are
  referenced, not selected.
- `mars/hirise/dataset.json`: archive-level PDS record only; no product chosen.
- `mars/jezero/dataset.json`: repeat-coverage assessment only; it exists to
  prevent unsupported rate transfer to Jezero.
- `mars/environmental_sources.json`: candidate MEDA, REMS, MCD, THEMIS and
  InSight sources. All entries have `metadata_verified: false`; none is an
  in-situ measurement at a dune field by default.
- `mars/published_measurements.json`: aggregate published ranges for context
  only. They are not per-dune labels and must not be used as training targets
  for individual dunes.

Dates absent from source material stay `requires_pds_resolution` or
`not_reported`; they are never inferred from filenames. `ingestion/catalog.py`
validates these manifests. `ingestion/download.py` never downloads unless a
caller explicitly enables it.

The existing MARS OPS backend uses NASA Mars Trek WMTS mosaics for Jezero;
those mosaics are not a multitemporal dune observation archive and must not be
treated as one.
