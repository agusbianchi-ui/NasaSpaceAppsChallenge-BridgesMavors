# MARS OPS Stage 2 — Ingestion, Migration and Models

Date: 2026-11-14
Workspace: `/home/pietro/Documents/bridges_mavors`

## 1. Scope

Extended the independent `mars_ml/` workspace with Mars metadata ingestion,
method-aware migration analysis, grouped migration and pixel models, aggregate
published-range validation, and dated sequence orchestration.

No files under `frontend/` or `backend/` were changed. No Mars pixels were
downloaded. No reusable model checkpoint was produced.

## 2. Files added or extended

### Ingestion and image I/O

- `mars_ml/ingestion/catalog.py` — load and validate dataset manifests.
- `mars_ml/ingestion/readers.py` — raster, vector, table and PDS readers.
- `mars_ml/ingestion/annotations.py` — annotation rasterization.
- `mars_ml/ingestion/download.py` — allowlisted dry-run download planning.
- `mars_ml/ingestion/validation.py` — manifest/checksum helpers.
- `mars_ml/computer_vision/image_io.py` — added `CRSUnitError`,
  `SpatialMetadata.linear_units`, `ensure_metric_resolution`,
  `crs_linear_units`, `checksum_file`, `parse_pds3_label`,
  `acquisition_datetime_from_label` and `load_pds_image`.
- `mars_ml/computer_vision/annotation_masks.py` — raster annotation helpers.
- `mars_ml/computer_vision/correlation_displacement.py` — correlation-based
  displacement support.
- `mars_ml/computer_vision/dune_crests.py` — crest extraction helpers.
- `mars_ml/computer_vision/geometry_comparison.py` — shape-change diagnostics.
- `mars_ml/computer_vision/uncertainty.py` — shared uncertainty helpers.

### Migration analysis and models

- `mars_ml/aeolian_dynamics/migration_analysis.py` — centroid, crest and
  geometry observations with explicit validity and rejection reasons.
- `mars_ml/aeolian_dynamics/migration_models.py` — Ridge and Random Forest
  migration models with grouped cross-validation.
- `mars_ml/aeolian_dynamics/hybrid_model.py` — explicit environmental covariate
  assembly and optional verified-source requirement.
- `mars_ml/aeolian_dynamics/environmental_sources.py` — environmental source
  catalog schema and validation.
- `mars_ml/training/migration_metrics.py` — rate, angular and interval metrics.
- `mars_ml/training/train_classifier.py` — pixel feature extraction and grouped
  dune pixel classifier with explicit joblib save/load.
- `mars_ml/training/train_migration.py` — explicit observation-table training
  and reporting.
- `mars_ml/validation/published_measurements.py` — aggregate published ranges.
- `mars_ml/validation/compare.py` — aggregate comparison that refuses to relabel
  individual dunes.
- `mars_ml/inference/mars_sequence.py` — dated sequence orchestration, JSON plan
  loader and CLI.

### Metadata manifests

- `mars_ml/datasets/mars/manifest.json`
- `mars_ml/datasets/mars/hargraves/dataset.json`
- `mars_ml/datasets/mars/coprates/dataset.json`
- `mars_ml/datasets/mars/ctx_multitemporal/dataset.json`
- `mars_ml/datasets/mars/hirise/dataset.json`
- `mars_ml/datasets/mars/jezero/dataset.json`
- `mars_ml/datasets/mars/environmental_sources.json`
- `mars_ml/datasets/mars/published_measurements.json`

All `dataset.json` files have `has_pixels: false`. Missing dates remain
`requires_pds_resolution` or `not_reported`; they are not inferred from
filenames.

### Tests

- `mars_ml/tests/test_ingestion.py`
- `mars_ml/tests/test_migration_analysis.py`
- `mars_ml/tests/test_migration_models.py`
- `mars_ml/tests/test_train_classifier.py`
- `mars_ml/tests/test_train_migration.py`
- `mars_ml/tests/test_mars_sequence.py`

## 3. Implemented behavior

- Manifest validation checks required fields, UTC dates, file paths, checksums,
  dataset IDs and pixel/label/temporal-series flags.
- `verify_manifest_files()` checks downloaded files against manifest sizes and
  SHA-256 values. It reports `size_verified`, not `verified`, when a checksum was
  not declared.
- Raster inspection reports shape, CRS, transform, resolution, nodata, dtype and
  validity without inventing missing metadata.
- PDS3 label parsing extracts acquisition time and checksums; a label failure is
  reported as an error rather than silently ignored.
- Pixel-to-metre conversion requires an explicit metric resolution. A degree
  grid is rejected as a metric scale.
- Migration observations preserve method, distance, interval, rate, azimuth,
  uncertainty, validity and rejection reasons.
- Geometry change is reported as a morphological diagnostic and never as a
  migration rate. `advancing_front` is reserved and not implemented.
- Grouped cross-validation holds out whole dune fields or sequences.
- Models reject negative rates, non-finite values and insufficient groups.
- Negative model predictions are clipped to zero and this is recorded in the
  model report.
- Environmental covariates must be explicitly supplied; missing values are not
  filled. Requiring a verified source fails when `metadata_verified` is false.
- Published ranges are aggregate context only; they are not per-dune labels or
  training targets.
- Dated sequence inference withholds migration when dates, scale, masks or
  registration reliability are missing, and keeps the reasons in the result.
- Sequence datetimes are normalized to UTC; the supplied registration config is
  used for every pair.
- `mars_sequence` can load a JSON plan of local images and masks and write a
  sequence report through its CLI.

## 4. Tests and checks

Commands:

```bash
cd /home/pietro/Documents/bridges_mavors
mars_ml/.venv/bin/python -m pytest mars_ml/tests -q
mars_ml/.venv/bin/python -m compileall -q mars_ml
```

Result: `96 passed`; compileall succeeded.

The tests use synthetic images and local fixtures only. They do not contact NASA,
Copernicus, USGS, figshare, Mendeley or any other provider. They are software
tests, not scientific validation of Mars migration.

## 5. Environment

The workspace uses the checked-in `mars_ml/.venv` (Python 3.14). Installed
packages include NumPy 2.5.4, OpenCV headless 5.0.0.93, Rasterio 1.5.2,
Matplotlib 3.11.2, pytest 9.2.0, pandas 3.1.1, pyshp 3.1.8, openpyxl 3.1.5,
scikit-learn 1.9.1 and joblib 1.6.0. PyTorch remains optional and is not
installed.

## 6. Data still missing

- Mars image pixels, checksummed and validated locally.
- Per-dune labels suitable for supervised training.
- PDS-resolved acquisition timestamps for the selected CTX products.
- Verified environmental records joined to specific image times.
- Independent displacement or migration measurements for local validation.
- A trained checkpoint and its run report.

## 7. What is not claimed

- No Mars migration rate has been measured in this repository.
- No trained model or checkpoint is presented.
- No published aggregate range has been converted into per-dune labels.
- No Earth migration rate or transport coefficient has been transferred to Mars.
- No WMTS mosaic has been treated as a multitemporal dune observation archive.

## 8. Recommended next steps

1. Select one small, verified Mars pair, download it under an allowlisted plan,
   verify checksums and read acquisition times from PDS labels.
2. Validate registration and metre-per-pixel scale on that pair without
   annualizing a rate.
3. Acquire per-dune masks and independent reference displacements.
4. Run `mars_sequence` only after dates, scale and masks are verified.
5. Compare local observations with aggregate published ranges using
   `validation/compare.py`, keeping the aggregate limitation explicit.
6. Calibrate any environmental or transport model against Mars observations
   before using it predictively.
