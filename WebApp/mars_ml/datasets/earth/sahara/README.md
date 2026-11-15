# Sahara development area

The terrestrial development area is a western Erg Chebbi window, used only to
build and test processing techniques. It is not a Mars analogue claim.

## Verified scene metadata

The STAC search was executed on 2026-11-14 against:

- Copernicus Data Space Ecosystem, collection `sentinel-2-l2a`.
- USGS Landsat STAC, collection `landsat-c2l2-sr`.

The exact query parameters and scene metadata are in `scene_catalog.json`.
Sentinel-2 scenes on tile `30RVV` provide a same-tile April sequence with
scene-level cloud cover reported as 0.0 %. The Landsat scene is a single
cross-sensor reference; it is not yet a matched multitemporal sequence.

## What is not included

- No downloaded imagery.
- No cloud masks beyond scene-level metadata.
- No hand-labelled dune masks.
- No claim that the scene-level cloud percentage guarantees a clear target
  window.

## Download procedure

Authentication is required by the providers. Do not store credentials in this
repository. Use the provider's documented client or an authenticated STAC
workflow, request only the bands and windows needed, and record a local download
manifest with the scene ID, asset, checksum, download time and crop window.

The pipeline expects local imagery to be paired with masks before supervised
training. See the root `mars_ml/README.md`.
