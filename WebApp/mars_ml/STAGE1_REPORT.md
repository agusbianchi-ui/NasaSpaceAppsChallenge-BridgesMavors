# MARS OPS Stage 1 — Final Report

Date: 2026-11-14
Workspace: `/home/pietro/Documents/bridges_mavors`

## 1. Scope delivered

Created an independent `mars_ml/` module for dune detection, multitemporal
registration, apparent 2D displacement, morphology and Earth/Mars planetary
scaffolding. No files under `frontend/` or `backend/` were changed.

## 2. Files created

### Packages and modules

- `mars_ml/__init__.py`
- `mars_ml/computer_vision/image_io.py`
- `mars_ml/computer_vision/image_registration.py`
- `mars_ml/computer_vision/dune_segmentation.py`
- `mars_ml/computer_vision/displacement_detection.py`
- `mars_ml/aeolian_dynamics/dune_morphology.py`
- `mars_ml/aeolian_dynamics/dune_migration.py`
- `mars_ml/aeolian_dynamics/environmental_observations.py`
- `mars_ml/aeolian_dynamics/planetary_parameters.py`
- `mars_ml/models/unet.py`
- `mars_ml/training/prepare_dataset.py`
- `mars_ml/training/train_segmentation.py`
- `mars_ml/training/evaluate.py`
- `mars_ml/inference/dune_analysis.py`
- `mars_ml/visualization/plots.py`
- `mars_ml/datasets/scene_catalog.py`

### Dataset structure and catalogs

- `mars_ml/datasets/README.md`
- `mars_ml/datasets/earth/sahara/README.md`
- `mars_ml/datasets/earth/sahara/scene_catalog.json`
- `mars_ml/datasets/earth/sentinel/README.md`
- `mars_ml/datasets/earth/landsat/README.md`
- `mars_ml/datasets/mars/hirise/README.md`
- `mars_ml/datasets/mars/ctx/README.md`
- `mars_ml/datasets/mars/dune_observations/README.md`

### Documentation and environment

- `mars_ml/README.md`
- `mars_ml/models/README.md`
- `mars_ml/notebooks/README.md`
- `mars_ml/requirements.txt`
- `mars_ml/requirements-training.txt`
- `mars_ml/.gitignore`
- `mars_ml/STAGE1_REPORT.md`

### Tests

- `mars_ml/tests/conftest.py`
- `mars_ml/tests/synthetic.py`
- `mars_ml/tests/test_image_io.py`
- `mars_ml/tests/test_registration.py`
- `mars_ml/tests/test_segmentation.py`
- `mars_ml/tests/test_displacement.py`
- `mars_ml/tests/test_morphology.py`
- `mars_ml/tests/test_migration.py`
- `mars_ml/tests/test_planetary.py`
- `mars_ml/tests/test_environmental_observations.py`
- `mars_ml/tests/test_scene_catalog.py`
- `mars_ml/tests/test_prepare_dataset.py`
- `mars_ml/tests/test_evaluate.py`
- `mars_ml/tests/test_inference.py`

## 3. Dependencies installed

Environment: `mars_ml/.venv`, Python 3.14.4, created with `uv`.

| Package | Version |
| --- | --- |
| numpy | 2.5.4 |
| opencv-python-headless | 5.0.0.93 |
| rasterio | 1.5.2 |
| matplotlib | 3.11.2 |
| pytest | 9.2.0 |

PyTorch is intentionally not installed. `requirements-training.txt` records the
optional training extra.

## 4. Scientific data sources

Verified via STAC metadata on 2026-11-14:

- Sentinel-2 L2A, Copernicus Data Space Ecosystem:
  `https://catalogue.dataspace.copernicus.eu/stac/search`, collection
  `sentinel-2-l2a`.
- Landsat Collection 2 Level-2 SR, USGS:
  `https://landsatlook.usgs.gov/stac-server/search`, collection
  `landsat-c2l2-sr`.

Catalogued scenes:

- Four Sentinel-2 scenes over MGRS `30RVV`, April 2019/2021/2024/2025,
  `eo:cloud_cover = 0.0` at scene level, `EPSG:32630`, 10 m assets.
- One Landsat 8 scene, `LC08_L2SP_199039_20230629_20230711_02_T1_SR`,
  2023-06-29, `EPSG:32630`, nominal 30 m grid.

No satellite pixels were downloaded. No credentials were stored. Mars datasets
remain empty by design.

## 5. Implemented capabilities

- Robust image loading with OpenCV and Rasterio.
- Dimension, channel, dtype, nodata and invalid-data validation.
- Percentile normalization and valid-pixel masks.
- ROI cropping with updated affine transforms.
- GeoTIFF export preserving CRS, transform and nodata.
- ORB + RANSAC homography registration.
- Phase-correlation fallback and registration reliability gating.
- Classical texture/gradient dune segmentation baseline.
- U-Net adapter requiring an external checkpoint and PyTorch.
- Centroid, Farneback and Lucas-Kanade displacement estimation.
- Consistency checks between displacement estimators.
- Explicit pixel-to-metre conversion only with `meters_per_pixel`.
- Morphology: area, perimeter, centroid, axes, aspect ratio, orientation,
  circularity, solidity, edge curvature and component count.
- Apparent annualized 2D migration with reliability gates.
- Grouped, leak-resistant dataset manifests.
- Manifest validation, patch extraction, training loop and checkpoint writing
  (training refuses to run without data, PyTorch and valid splits).
- Segmentation, registration and displacement evaluation metrics.
- Environmental observation records with provenance, units, temporal offset and
  explicit missing values.
- Earth/Mars reference parameters and coefficient-gated transport equations.
- End-to-end inference CLI with JSON and PNG outputs.
- Synthetic-only test suite.

## 6. Tests and results

Command:

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -m pytest mars_ml/tests -q
```

Result: `57 passed`.

Static check:

```bash
mars_ml/.venv/bin/python -m compileall -q mars_ml
```

Result: success. `uv pip check` reports all installed packages compatible.

These are software tests on synthetic fixtures. They are not scientific
validation or model-performance evidence.

## 7. Data still missing

- Downloaded and checksummed Sentinel-2/Landsat imagery.
- Labelled dune masks.
- Independent displacement or migration reference measurements.
- Local environmental observations simultaneous with the images.
- Any validated Mars dataset or calibration.
- Trained U-Net weights and real validation/test metrics.

## 8. Limitations

- The classical segmenter is not semantically validated.
- No radiometric/BRDF/illumination normalization or cloud-shadow masking.
- Registration can reject low-texture or strongly changed pairs.
- Displacement is apparent 2D motion, not sediment flux or 3D change.
- Centroid migration assumes the segmented body represents a dune.
- Metric accuracy depends on verified ground sample distance.
- No operational Mars prediction exists.
- No Earth migration rate is transferred to Mars.
- No scientific metric is claimed in this report.

## 9. Recommended next stage

1. Download a small, checksummed subset of the catalogued Sentinel-2 scenes.
2. Label dunes and define a reproducible annotation protocol.
3. Evaluate registration across the 2019–2025 sequence.
4. Compare the classical baseline with a trained U-Net on held-out groups.
5. Add cloud/shadow masking and illumination normalization.
6. Validate displacement against independent or manually measured references.
7. Only then prepare calibrated HiRISE/CTX pairs for Mars.
