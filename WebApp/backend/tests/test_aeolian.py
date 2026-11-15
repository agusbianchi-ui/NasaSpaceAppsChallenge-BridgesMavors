from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.v1 import aeolian as aeolian_api
from app.services.aeolian_service import AeolianService
from mars_ml.computer_vision.image_io import (
    RasterImage,
    SpatialMetadata,
    save_raster,
)
from mars_ml.tests.synthetic import dune_pair


def _write_pair(root: Path, *, prefix: str = "") -> None:
    first, second, first_mask, second_mask = dune_pair(
        height=128, width=128, dx=6.0, dy=-2.0
    )
    cv2.imwrite(
        str(root / f"{prefix}reference.png"),
        np.round(first * 255).astype(np.uint8),
    )
    cv2.imwrite(
        str(root / f"{prefix}moving.png"),
        np.round(second * 255).astype(np.uint8),
    )
    cv2.imwrite(
        str(root / f"{prefix}reference_mask.png"),
        first_mask.astype(np.uint8) * 255,
    )
    cv2.imwrite(
        str(root / f"{prefix}moving_mask.png"),
        second_mask.astype(np.uint8) * 255,
    )


@pytest.fixture
def aeolian_setup(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, Path]:
    _write_pair(tmp_path)
    service = AeolianService(data_root=tmp_path)
    monkeypatch.setattr(aeolian_api, "_service", service)
    return client, tmp_path


def _payload(
    *,
    dataset_id: str = "ctx_multitemporal_six_sites",
    prefix: str = "",
    crs_second: str = "IAU2000:49900",
    meters_per_pixel: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "dataset_id": dataset_id,
        "observations": [
            {
                "observation_id": "reference",
                "product_id": "PRODUCT_A",
                "acquisition_datetime_utc": "2020-01-01T00:00:00Z",
                "image_path": f"{prefix}reference.png",
                "mask_path": f"{prefix}reference_mask.png",
                "crs": "IAU2000:49900",
            },
            {
                "observation_id": "moving",
                "product_id": "PRODUCT_B",
                "acquisition_datetime_utc": "2021-01-01T00:00:00Z",
                "image_path": f"{prefix}moving.png",
                "mask_path": f"{prefix}moving_mask.png",
                "crs": crs_second,
            },
        ],
        "method": "centroid",
    }
    if meters_per_pixel is not None:
        payload["meters_per_pixel"] = meters_per_pixel
    return payload


def test_list_datasets_exposes_metadata_without_inventing_readiness(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.get("/api/v1/aeolian/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    datasets = payload["data"]
    assert len(datasets) == 5
    identifiers = {dataset["dataset_id"] for dataset in datasets}
    assert "ctx_multitemporal_six_sites" in identifiers
    assert "jezero_crater_repeat_coverage_assessment" in identifiers

    ctx = next(
        dataset
        for dataset in datasets
        if dataset["dataset_id"] == "ctx_multitemporal_six_sites"
    )
    assert ctx["has_pixels"] is False
    assert ctx["has_temporal_series"] is True
    assert ctx["analysis_capability"]["analysis_ready"] is False
    assert ctx["analysis_capability"]["local_observations_required"] is True
    assert any(
        "metadata only" in blocker
        for blocker in ctx["analysis_capability"]["blockers"]
    )
    assert ctx["coordinate_reference_system"]["units"] == "metre"
    assert ctx["files"]
    assert ctx["limitations"]


def test_analyze_png_pair_reuses_mars_ml_and_converts_units(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(
            meters_per_pixel={
                "x_m_per_pixel": 6.0,
                "source": "test fixture declared scale",
            }
        ),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["summary"]["valid_migration_count"] >= 1
    assert data["predictions"] == []
    assert data["prediction_status"] == "not_available"
    assert data["provenance"]["software"].endswith("run_mars_sequence")
    assert data["provenance"]["scale_source"] == "test fixture declared scale"
    assert all(file["sha256"] for file in data["provenance"]["files"])
    for file in data["provenance"]["files"]:
        expected = hashlib.sha256((_root / file["path"]).read_bytes()).hexdigest()
        assert file["sha256"] == expected
    assert data["units"]["rate_m_per_earth_year"].startswith("m per Earth year")

    pair = data["pairs"][0]
    centroid = pair["displacement"]["centroid"]
    metric = pair["displacement"]["metric_centroid"]
    migration = pair["observed_migration"]
    assert metric["dx_m"] == pytest.approx(centroid["dx_px"] * 6.0)
    assert metric["dy_m"] == pytest.approx(centroid["dy_px"] * 6.0)
    assert migration["source"] == "observed"
    assert migration["direction_azimuth_deg"] == pytest.approx(
        metric["azimuth_deg"]
    )
    assert migration["rate_m_per_earth_year"] == pytest.approx(
        migration["distance_m"] / migration["interval_days"] * 365.25
    )


def test_get_result_round_trip_and_unknown_id(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    created = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(
            meters_per_pixel={
                "x_m_per_pixel": 6.0,
                "source": "test fixture declared scale",
            }
        ),
    ).json()["data"]
    analysis_id = created["analysis_id"]

    response = client.get(f"/api/v1/aeolian/results/{analysis_id}")
    assert response.status_code == 200
    assert response.json()["data"] == created

    missing = client.get("/api/v1/aeolian/results/not-an-analysis")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_analyze_without_scale_withholds_migration_rate(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post("/api/v1/aeolian/analyze", json=_payload())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed_without_valid_migration"
    assert data["summary"]["valid_migration_count"] == 0
    migration = data["pairs"][0]["observed_migration"]
    assert migration is not None
    assert migration["valid"] is False
    assert migration["rate_m_per_earth_year"] is None
    assert any("scale" in reason.lower() for reason in migration["reasons"])
    assert any("metres-per-pixel" in item for item in data["limitations"])


def test_analyze_unknown_dataset_returns_404(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(dataset_id="missing-dataset"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_analyze_dataset_without_temporal_series_returns_422(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(dataset_id="hargraves_crater_dunes"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "temporal series" in response.json()["error"]["message"]


def test_analyze_rejects_mixed_coordinate_references(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(crs_second="IAU2000:49901"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "same coordinate reference system" in response.json()["error"][
        "message"
    ]


def test_analyze_rejects_missing_file_and_path_escape(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    missing = _payload()
    missing["observations"][0]["mask_path"] = "does-not-exist.png"
    response = client.post("/api/v1/aeolian/analyze", json=missing)
    assert response.status_code == 422
    assert "not found" in response.json()["error"]["message"]

    escaped = _payload()
    escaped["observations"][0]["image_path"] = "../outside.png"
    response = client.post("/api/v1/aeolian/analyze", json=escaped)
    assert response.status_code == 422
    assert "escapes AEOLIAN_DATA_ROOT" in response.json()["error"]["message"]


def test_analyze_rejects_naive_and_duplicate_inputs(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    naive = _payload()
    naive["observations"][0]["acquisition_datetime_utc"] = "2020-01-01T00:00:00"
    response = client.post("/api/v1/aeolian/analyze", json=naive)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

    duplicate = _payload()
    duplicate["observations"][1]["observation_id"] = "reference"
    response = client.post("/api/v1/aeolian/analyze", json=duplicate)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_analyze_rejects_scale_that_conflicts_with_metric_raster(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    first, second, first_mask, second_mask = dune_pair(
        height=64, width=64, dx=3.0, dy=0.0
    )
    metadata = SpatialMetadata(
        crs="EPSG:32630",
        transform=(2.0, 0.0, 0.0, 0.0, -2.0, 0.0),
        resolution=(2.0, 2.0),
    )
    save_raster(
        root / "geo_reference.tif",
        RasterImage(np.round(first * 255).astype(np.uint8), metadata),
    )
    save_raster(
        root / "geo_moving.tif",
        RasterImage(np.round(second * 255).astype(np.uint8), metadata),
    )
    save_raster(
        root / "geo_reference_mask.tif",
        RasterImage(first_mask.astype(np.uint8), metadata),
    )
    save_raster(
        root / "geo_moving_mask.tif",
        RasterImage(second_mask.astype(np.uint8), metadata),
    )
    payload = _payload(
        prefix="geo_",
        crs_second="EPSG:32630",
        meters_per_pixel={
            "x_m_per_pixel": 6.0,
            "source": "incorrect declared scale",
        },
    )
    payload["observations"][0]["crs"] = "EPSG:32630"
    payload["observations"][0]["image_path"] = "geo_reference.tif"
    payload["observations"][0]["mask_path"] = "geo_reference_mask.tif"
    payload["observations"][1]["image_path"] = "geo_moving.tif"
    payload["observations"][1]["mask_path"] = "geo_moving_mask.tif"

    response = client.post("/api/v1/aeolian/analyze", json=payload)

    assert response.status_code == 422
    assert "does not match raster resolution" in response.json()["error"][
        "message"
    ]


def test_predict_is_explicitly_unavailable(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    response = client.post(
        "/api/v1/aeolian/predict",
        json={"dataset_id": "ctx_multitemporal_six_sites", "target": "both"},
    )

    assert response.status_code == 501
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_implemented"
    assert "Prediction is not available" in payload["error"]["message"]
    assert "trained segmentation" in payload["error"]["message"]


def test_aeolian_routes_are_documented_and_allow_post_cors(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/aeolian/datasets" in paths
    assert "/api/v1/aeolian/analyze" in paths
    assert "/api/v1/aeolian/results/{analysis_id}" in paths
    assert "/api/v1/aeolian/predict" in paths

    response = client.options(
        "/api/v1/aeolian/analyze",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )


def _write_geo_rasters(
    root: Path,
    *,
    crs: str,
    resolution: float,
) -> None:
    first, second, first_mask, second_mask = dune_pair(
        height=64, width=64, dx=3.0, dy=0.0
    )
    metadata = SpatialMetadata(
        crs=crs,
        transform=(resolution, 0.0, 0.0, 0.0, -resolution, 0.0),
        resolution=(resolution, resolution),
    )
    rasters = {
        "geo_reference.tif": np.round(first * 255).astype(np.uint8),
        "geo_moving.tif": np.round(second * 255).astype(np.uint8),
        "geo_reference_mask.tif": first_mask.astype(np.uint8),
        "geo_moving_mask.tif": second_mask.astype(np.uint8),
    }
    for name, data in rasters.items():
        save_raster(root / name, RasterImage(data, metadata))


def _set_geo_files(payload: dict[str, object], *, crs: str) -> None:
    observations = payload["observations"]
    assert isinstance(observations, list)
    for observation, image, mask in (
        (observations[0], "geo_reference.tif", "geo_reference_mask.tif"),
        (observations[1], "geo_moving.tif", "geo_moving_mask.tif"),
    ):
        observation["crs"] = crs
        observation["image_path"] = image
        observation["mask_path"] = mask


def test_analyze_three_observations_builds_consecutive_sorted_pairs(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    _write_pair(root, prefix="third_")
    payload = _payload()
    observations = payload["observations"]
    assert isinstance(observations, list)
    third = {
        "observation_id": "third",
        "product_id": "PRODUCT_C",
        "acquisition_datetime_utc": "2022-01-01T00:00:00Z",
        "image_path": "third_reference.png",
        "mask_path": "third_reference_mask.png",
        "crs": "IAU2000:49900",
    }
    payload["observations"] = [observations[1], third, observations[0]]

    response = client.post("/api/v1/aeolian/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["observation_count"] == 3
    assert data["summary"]["pair_count"] == 2
    assert [
        (pair["reference_id"], pair["moving_id"]) for pair in data["pairs"]
    ] == [
        ("reference", "moving"),
        ("moving", "third"),
    ]
    assert [item["observation_id"] for item in data["observations"]] == [
        "reference",
        "moving",
        "third",
    ]


def test_analyze_rejects_request_validation_errors(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    missing_observations = client.post(
        "/api/v1/aeolian/analyze",
        json={"dataset_id": "ctx_multitemporal_six_sites"},
    )
    assert missing_observations.status_code == 422
    assert missing_observations.json()["error"]["code"] == "validation_error"

    unsupported_method = _payload()
    unsupported_method["method"] = "advancing_front"
    response = client.post(
        "/api/v1/aeolian/analyze", json=unsupported_method
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_analyze_rejects_invalid_masks_and_unreadable_images(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    base = _payload()
    image = cv2.imread(str(root / "reference.png"), cv2.IMREAD_GRAYSCALE)
    assert image is not None

    cv2.imwrite(
        str(root / "multiband_mask.png"),
        cv2.cvtColor(image, cv2.COLOR_GRAY2BGR),
    )
    multiband = _payload()
    multiband["observations"][1]["mask_path"] = "multiband_mask.png"
    response = client.post("/api/v1/aeolian/analyze", json=multiband)
    assert response.status_code == 422
    assert "single-band" in response.json()["error"]["message"]

    cv2.imwrite(
        str(root / "empty_mask.png"),
        np.zeros((128, 128), dtype=np.uint8),
    )
    empty = _payload()
    empty["observations"][1]["mask_path"] = "empty_mask.png"
    response = client.post("/api/v1/aeolian/analyze", json=empty)
    assert response.status_code == 422
    assert "empty" in response.json()["error"]["message"]

    cv2.imwrite(
        str(root / "small_mask.png"),
        np.ones((64, 64), dtype=np.uint8) * 255,
    )
    mismatched = _payload()
    mismatched["observations"][1]["mask_path"] = "small_mask.png"
    response = client.post("/api/v1/aeolian/analyze", json=mismatched)
    assert response.status_code == 422
    assert "mask shape" in response.json()["error"]["message"]

    (root / "broken.png").write_bytes(b"not an image")
    broken = _payload()
    broken["observations"][0]["image_path"] = "broken.png"
    response = client.post("/api/v1/aeolian/analyze", json=broken)
    assert response.status_code == 422
    assert "could not be loaded" in response.json()["error"]["message"]
    assert base["observations"][0]["image_path"] == "reference.png"


def test_analyze_requires_crs_and_rejects_crs_mismatch(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    missing_crs = _payload()
    missing_crs["observations"][0].pop("crs")
    missing_crs["observations"][1].pop("crs")
    response = client.post("/api/v1/aeolian/analyze", json=missing_crs)
    assert response.status_code == 422
    assert "CRS is required" in response.json()["error"]["message"]

    _write_geo_rasters(root, crs="EPSG:32630", resolution=2.0)
    mismatched = _payload(prefix="geo_")
    _set_geo_files(mismatched, crs="IAU2000:49900")
    response = client.post("/api/v1/aeolian/analyze", json=mismatched)
    assert response.status_code == 422
    assert "does not match raster CRS" in response.json()["error"]["message"]


def test_analyze_rejects_metric_scale_for_geographic_raster(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    _write_geo_rasters(root, crs="EPSG:4326", resolution=0.0001)
    payload = _payload(
        prefix="geo_",
        meters_per_pixel={
            "x_m_per_pixel": 6.0,
            "source": "invalid metric scale for a degree grid",
        },
    )
    _set_geo_files(payload, crs="EPSG:4326")

    response = client.post("/api/v1/aeolian/analyze", json=payload)

    assert response.status_code == 422
    assert "not metres" in response.json()["error"]["message"]


def test_analyze_rejects_symlink_escape(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, root = aeolian_setup
    outside = root.parent / f"{root.name}-outside.png"
    outside.write_bytes((root / "reference.png").read_bytes())
    link = root / "outside_link.png"
    try:
        link.symlink_to(outside)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege unavailable")
        raise
    payload = _payload()
    payload["observations"][0]["image_path"] = "outside_link.png"

    response = client.post("/api/v1/aeolian/analyze", json=payload)

    assert response.status_code == 422
    assert "escapes AEOLIAN_DATA_ROOT" in response.json()["error"]["message"]


def test_analyze_and_datasets_report_configuration_errors(
    aeolian_setup: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, root = aeolian_setup
    missing_root_service = AeolianService(data_root=root / "missing-root")
    monkeypatch.setattr(aeolian_api, "_service", missing_root_service)
    response = client.post("/api/v1/aeolian/analyze", json=_payload())
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "AEOLIAN_DATA_ROOT" in response.json()["error"]["message"]

    invalid_manifest_service = AeolianService(
        data_root=root,
        manifest_path=root / "missing-manifest.json",
    )
    monkeypatch.setattr(aeolian_api, "_service", invalid_manifest_service)
    response = client.get("/api/v1/aeolian/datasets")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_predict_handles_missing_and_mismatched_references(
    aeolian_setup: tuple[TestClient, Path],
) -> None:
    client, _root = aeolian_setup
    missing_reference = client.post("/api/v1/aeolian/predict", json={})
    assert missing_reference.status_code == 422
    assert missing_reference.json()["error"]["code"] == "validation_error"

    unknown_analysis = client.post(
        "/api/v1/aeolian/predict",
        json={"analysis_id": "missing-analysis"},
    )
    assert unknown_analysis.status_code == 404
    assert unknown_analysis.json()["error"]["code"] == "not_found"

    created = client.post(
        "/api/v1/aeolian/analyze",
        json=_payload(
            meters_per_pixel={
                "x_m_per_pixel": 6.0,
                "source": "test fixture declared scale",
            }
        ),
    ).json()["data"]
    mismatch = client.post(
        "/api/v1/aeolian/predict",
        json={
            "analysis_id": created["analysis_id"],
            "dataset_id": "hargraves_crater_dunes",
        },
    )
    assert mismatch.status_code == 422
    assert "different datasets" in mismatch.json()["error"]["message"]

    available_but_unimplemented = client.post(
        "/api/v1/aeolian/predict",
        json={"analysis_id": created["analysis_id"]},
    )
    assert available_but_unimplemented.status_code == 501
    assert (
        available_but_unimplemented.json()["error"]["code"]
        == "not_implemented"
    )
