from __future__ import annotations

from datetime import datetime

import pytest

from mars_ml.aeolian_dynamics.migration_analysis import (
    MigrationAnalysisError,
    distance_uncertainty,
    geometry_change_observation,
    method_agreement,
    observation_from_masks,
    observation_from_metric,
    observation_from_pixels,
    summarize_methods,
)
from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    PixelDisplacement,
    azimuth_degrees,
)
from mars_ml.computer_vision.geometry_comparison import compare_masks
from mars_ml.tests.synthetic import ellipse_mask


def _metric(dx: float, dy: float) -> MetricDisplacement:
    return MetricDisplacement(
        dx_m=dx,
        dy_m=dy,
        magnitude_m=(dx**2 + dy**2) ** 0.5,
        azimuth_deg=azimuth_degrees(dx, dy),
        meters_per_pixel=(10.0, 10.0),
        method="test",
    )


def _pixel(dx: float, dy: float, *, reliable: bool = True) -> PixelDisplacement:
    return PixelDisplacement(
        dx_px=dx,
        dy_px=dy,
        magnitude_px=(dx**2 + dy**2) ** 0.5,
        azimuth_deg=azimuth_degrees(dx, dy),
        method="mask_centroid",
        reliable=reliable,
    )


def test_metric_observation_annualizes_and_reports_uncertainty():
    observation = observation_from_metric(
        "dataset",
        "dune",
        "centroid",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _metric(10.0, 0.0),
        distance_standard_error_m=1.0,
    )
    assert observation.valid
    assert observation.rate_m_per_year == pytest.approx(9.97, abs=0.05)
    assert observation.rate_standard_error_m_per_year == pytest.approx(0.997, abs=0.01)
    assert observation.distance_ci95_m == pytest.approx((8.04, 11.96), abs=0.01)
    assert observation.azimuth_deg == pytest.approx(90.0)


def test_geometry_method_never_produces_a_rate():
    observation = observation_from_metric(
        "dataset",
        "dune",
        "geometry",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _metric(10.0, 0.0),
    )
    assert not observation.valid
    assert observation.rate_m_per_year is None
    assert "not a migration rate" in observation.reasons[0]


def test_missing_scale_and_unreliable_pixels_are_withheld():
    no_scale = observation_from_pixels(
        "dataset",
        "dune",
        "centroid",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _pixel(5.0, 2.0),
        None,
    )
    assert not no_scale.valid
    assert no_scale.reasons
    unreliable = observation_from_pixels(
        "dataset",
        "dune",
        "centroid",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _pixel(5.0, 2.0, reliable=False),
        10.0,
    )
    assert not unreliable.valid


def test_short_interval_and_unknown_method_are_rejected():
    short = observation_from_metric(
        "dataset",
        "dune",
        "centroid",
        "2020-01-01T00:00:00Z",
        "2020-01-01T12:00:00Z",
        _metric(1.0, 0.0),
    )
    assert not short.valid
    assert "shorter" in short.reasons[0]
    with pytest.raises(MigrationAnalysisError):
        observation_from_metric(
            "dataset",
            "dune",
            "unknown",
            "2020-01-01T00:00:00Z",
            "2021-01-01T00:00:00Z",
            _metric(1.0, 0.0),
        )
    with pytest.raises(MigrationAnalysisError):
        observation_from_metric(
            "dataset",
            "dune",
            "centroid",
            datetime(2020, 1, 1),
            "2021-01-01T00:00:00Z",
            _metric(1.0, 0.0),
        )


def test_masks_and_method_summary_keep_methods_separate():
    reference = ellipse_mask(100, 100, center=(40, 50), axes=(10, 8))
    moving = ellipse_mask(100, 100, center=(55, 50), axes=(10, 8))
    centroid = observation_from_masks(
        "dataset",
        "dune",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        reference,
        moving,
        meters_per_pixel=10.0,
    )
    assert centroid.valid
    crest = observation_from_metric(
        "dataset",
        "dune",
        "crest",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _metric(150.0, 0.0),
    )
    rejected = observation_from_metric(
        "dataset",
        "dune",
        "geometry",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _metric(150.0, 0.0),
    )
    summary = summarize_methods([centroid, crest, rejected])
    assert summary["centroid"]["valid_count"] == 1
    assert summary["crest"]["valid_count"] == 1
    assert summary["geometry"]["valid_count"] == 0
    assert summary["geometry"]["rejection_reasons"]
    agreement = method_agreement([centroid, crest])
    assert agreement["compared_pairs"] == 1
    assert agreement["rate_consistent_pairs"] == 1


def test_geometry_comparison_is_not_a_migration_observation():
    reference = ellipse_mask(100, 100, center=(40, 50), axes=(10, 8))
    moving = ellipse_mask(100, 100, center=(55, 50), axes=(14, 8))
    comparison = compare_masks(reference, moving, meters_per_pixel=10.0)
    observation = geometry_change_observation(
        "dataset",
        "dune",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        comparison,
    )
    assert not observation.valid
    assert observation.method == "geometry"
    assert observation.provenance["geometry_status"] == comparison.status


def test_distance_uncertainty_combines_scale_and_registration():
    estimate = distance_uncertainty(
        _metric(30.0, 40.0),
        scale_standard_error_m=0.5,
        registration_standard_error_px=0.2,
        meters_per_pixel=10.0,
    )
    assert estimate.value == pytest.approx(50.0)
    assert estimate.standard_error == pytest.approx((0.5**2 + 2.0**2) ** 0.5)
    assert estimate.ci95_low < estimate.value < estimate.ci95_high
