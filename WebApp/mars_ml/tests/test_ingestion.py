from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from mars_ml.computer_vision.annotation_masks import annotation_summary, class_masks
from mars_ml.computer_vision.image_io import (
    RasterImage,
    SpatialMetadata,
    checksum_file,
    crs_linear_units,
    load_pds_image,
    parse_pds3_label,
    save_raster,
)
from mars_ml.ingestion.annotations import rasterize_annotations, write_annotation_rasters
from mars_ml.ingestion.catalog import (
    DatasetFile,
    DatasetManifestError,
    load_mars_manifest,
    manifest_summary,
)
from mars_ml.ingestion.download import DownloadError, download_plan, plan_downloads
from mars_ml.ingestion.readers import IngestionError, read_geojson, read_table
from mars_ml.ingestion.validation import (
    inspect_raster,
    validate_manifest_file,
    validate_vector_layer,
    verify_manifest_files,
)


def _reference_raster() -> RasterImage:
    data = np.zeros((100, 100), dtype=np.uint8)
    metadata = SpatialMetadata(
        crs="EPSG:32630",
        transform=(10.0, 0.0, 0.0, 0.0, -10.0, 100.0),
        resolution=(10.0, 10.0),
        source="synthetic annotation grid",
    )
    return RasterImage(data, metadata)


def _geojson_payload() -> dict:
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:32630"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"class": 1, "name": "first"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[10, 90], [50, 90], [50, 50], [10, 50], [10, 90]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"class": 2, "name": "second"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[60, 40], [90, 40], [90, 10], [60, 10], [60, 40]]],
                },
            },
        ],
    }


def test_mars_manifest_loads_and_validates():
    records = load_mars_manifest()
    assert len(records) == 5
    summary = manifest_summary(records)
    assert summary["dataset_count"] == 5
    assert summary["with_pixels"] == []
    assert "coprates_chasma_dunes" in summary["with_temporal_series"]
    assert validate_manifest_file()["valid"] is True


def test_invalid_manifest_reports_invalid(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"datasets": [{"dataset_id": "incomplete"}]}), encoding="utf-8")
    result = validate_manifest_file(path)
    assert result["valid"] is False
    assert result["error"]


def test_invalid_json_manifest_raises(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DatasetManifestError):
        load_mars_manifest(path)


def test_geojson_vector_and_table_readers(tmp_path):
    geojson = tmp_path / "annotations.geojson"
    geojson.write_text(json.dumps(_geojson_payload()), encoding="utf-8")
    layer = read_geojson(geojson)
    assert len(layer.records) == 2
    assert layer.geometry_type == "Polygon"
    assert "class" in layer.fields
    assert validate_vector_layer(layer)["record_count"] == 2

    table = tmp_path / "measurements.csv"
    table.write_text("id,rate\n1,0.5\n2,0.7\n", encoding="utf-8")
    data = read_table(table)
    assert data.row_count == 2
    assert data.columns == ("id", "rate")
    assert data.rows[0]["rate"] == 0.5

    with pytest.raises(IngestionError):
        read_table(tmp_path / "missing.csv")


def test_annotation_rasterization_and_class_masks(tmp_path):
    geojson = tmp_path / "annotations.geojson"
    geojson.write_text(json.dumps(_geojson_payload()), encoding="utf-8")
    result = rasterize_annotations(
        geojson,
        _reference_raster(),
        class_field="class",
    )
    assert result.class_values == (1, 2)
    assert result.mask.any()
    masks = class_masks(result)
    assert set(masks) == {1, 2}
    summary = annotation_summary(result)
    assert summary["class_pixel_counts"][1] > 0
    outputs = write_annotation_rasters(tmp_path / "masks", result)
    assert (tmp_path / "masks" / "annotation_mask.png").exists()
    assert set(outputs) == {"mask", "labels"}


def test_annotation_crs_mismatch_is_rejected(tmp_path):
    payload = _geojson_payload()
    payload["crs"] = {"type": "name", "properties": {"name": "EPSG:4326"}}
    geojson = tmp_path / "wrong.geojson"
    geojson.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="CRS"):
        rasterize_annotations(geojson, _reference_raster(), class_field="class")


def test_raster_inspection_preserves_metric_units(tmp_path):
    path = tmp_path / "metric.tif"
    save_raster(path, _reference_raster())
    inspection = inspect_raster(path)
    assert inspection.crs_units == "metre"
    assert inspection.metric_resolution == (10.0, 10.0)
    assert inspection.width == 100
    assert inspection.height == 100
    assert crs_linear_units("EPSG:4326") == "degrees"
    assert crs_linear_units("EPSG:32630") in {"metre", "meter", "m"}


def test_pds_label_parser_and_image_loader(tmp_path):
    label = tmp_path / "product.lbl"
    label.write_text(
        'PDS_VERSION_ID = "PDS3"\n/* comment */\nSTART_TIME = "2020-01-01T00:00:00Z"\n'
        'PRODUCT_ID = "TEST_PRODUCT"\n',
        encoding="utf-8",
    )
    parsed = parse_pds3_label(label)
    assert parsed["START_TIME"] == "2020-01-01T00:00:00Z"
    assert parsed["PDS_VERSION_ID"] == "PDS3"
    raster_path = tmp_path / "product.tif"
    save_raster(raster_path, _reference_raster())
    image = load_pds_image(raster_path, label_path=label)
    assert image.metadata.acquisition_datetime == "2020-01-01T00:00:00Z"
    assert image.metadata.extra["pds_label"]["PRODUCT_ID"] == "TEST_PRODUCT"
    assert checksum_file(raster_path) == checksum_file(raster_path)


def test_download_plan_is_dry_run_and_allowlisted():
    records = load_mars_manifest()
    plan = plan_downloads(records, dataset_ids=["coprates_chasma_dunes"])
    assert plan.dry_run is True
    assert plan.total_bytes > 0
    results = download_plan(plan, "/tmp/mars_ml_download_test", dry_run=True)
    assert all(result.status == "planned" for result in results)
    assert all(result.bytes_written == 0 for result in results)
    with pytest.raises(DownloadError):
        plan_downloads(
            records,
            dataset_ids=["coprates_chasma_dunes"],
            allowed_hosts={"example.com"},
        )


def test_verify_manifest_files_checks_size_and_checksum(tmp_path):
    payload = b"abc"
    digest = hashlib.sha256(payload).hexdigest()
    base = load_mars_manifest()[0]
    record = replace(
        base,
        dataset_id="verification_case",
        files=(
            DatasetFile(
                name="checked.bin",
                size_bytes=len(payload),
                url="https://example.com/checked.bin",
                sha256=digest,
            ),
            DatasetFile(
                name="size_only.bin",
                size_bytes=3,
                url="https://example.com/size_only.bin",
                selected=False,
            ),
        ),
    )
    root = tmp_path / "downloads"
    target = root / record.dataset_id / "checked.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)
    report = verify_manifest_files((record,), root)
    assert report["checked_count"] == 1
    assert report["verified_count"] == 1
    assert report["all_verified"] is True
    assert report["files"][0]["status"] == "verified"

    target.write_bytes(b"abcd")
    report = verify_manifest_files((record,), root)
    assert report["files"][0]["status"] == "size_mismatch"
    assert report["all_verified"] is False

    target.write_bytes(b"xyz")
    report = verify_manifest_files((record,), root)
    assert report["files"][0]["status"] == "checksum_mismatch"

    target.unlink()
    report = verify_manifest_files((record,), root)
    assert report["files"][0]["status"] == "missing"

    size_only = root / record.dataset_id / "size_only.bin"
    size_only.write_bytes(b"abc")
    report = verify_manifest_files((record,), root, selected_only=False)
    statuses = {item["name"]: item["status"] for item in report["files"]}
    assert statuses["size_only.bin"] == "size_verified"

    unsafe = replace(
        record,
        files=(
            DatasetFile(
                name="../../escape.bin",
                size_bytes=1,
                url="https://example.com/escape.bin",
            ),
        ),
    )
    report = verify_manifest_files((unsafe,), root)
    assert report["files"][0]["status"] == "invalid_path"
