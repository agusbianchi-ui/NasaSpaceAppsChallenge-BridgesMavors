from __future__ import annotations

import pytest

from mars_ml.aeolian_dynamics.dune_migration import (
    MigrationError,
    direction_difference_degrees,
    estimate_migration,
    interval_days,
    migration_from_metric,
)
from mars_ml.aeolian_dynamics.dune_morphology import extract_morphology
from mars_ml.computer_vision.displacement_detection import MetricDisplacement, azimuth_degrees
from mars_ml.tests.synthetic import ellipse_mask


def _displacement(dx_m: float, dy_m: float) -> MetricDisplacement:
    return MetricDisplacement(
        dx_m=dx_m,
        dy_m=dy_m,
        magnitude_m=(dx_m**2 + dy_m**2) ** 0.5,
        azimuth_deg=azimuth_degrees(dx_m, dy_m),
        meters_per_pixel=(10.0, 10.0),
        method="test",
    )


def test_interval_days_requires_aware_increasing_dates():
    assert interval_days("2021-01-01T00:00:00Z", "2022-01-01T00:00:00Z") == pytest.approx(365.0)
    with pytest.raises(MigrationError):
        interval_days("2022-01-01T00:00:00Z", "2021-01-01T00:00:00Z")
    with pytest.raises(MigrationError):
        interval_days("2021-01-01T00:00:00", "2022-01-01T00:00:00")


def test_migration_rate_is_annualized_and_requires_metric_displacement():
    result = migration_from_metric(
        "2021-01-01T00:00:00Z",
        "2022-01-01T00:00:00Z",
        _displacement(10.0, 0.0),
    )
    assert result.reliable
    assert result.rate_m_per_year == pytest.approx(10.0, abs=0.1)
    with pytest.raises(MigrationError):
        migration_from_metric("2021-01-01T00:00:00Z", "2022-01-01T00:00:00Z", None)


def test_estimate_migration_from_morphology():
    reference = extract_morphology(ellipse_mask(100, 100, center=(40, 50), axes=(12, 8)))
    moving = extract_morphology(ellipse_mask(100, 100, center=(50, 50), axes=(12, 8)))
    result = estimate_migration(
        reference,
        moving,
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        meters_per_pixel=10.0,
    )
    assert result.magnitude_m == pytest.approx(100.0, abs=2.0)
    assert result.rate_m_per_year == pytest.approx(100.0, abs=3.0)


def test_direction_difference_is_symmetric():
    first = migration_from_metric(
        "2021-01-01T00:00:00Z",
        "2022-01-01T00:00:00Z",
        _displacement(10.0, 0.0),
    )
    second = migration_from_metric(
        "2021-01-01T00:00:00Z",
        "2022-01-01T00:00:00Z",
        _displacement(0.0, 10.0),
    )
    assert direction_difference_degrees(first, second) == pytest.approx(90.0, abs=1e-6)


def test_single_day_interval_is_rejected_by_default():
    with pytest.raises(MigrationError):
        migration_from_metric(
            "2021-01-01T00:00:00Z",
            "2021-01-01T12:00:00Z",
            _displacement(1.0, 0.0),
        )
