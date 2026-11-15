"""Metrics for migration-rate and direction predictions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from mars_ml.computer_vision.displacement_detection import angular_difference_degrees


class MigrationMetricsError(ValueError):
    """Raised when migration predictions and references are incompatible."""


@dataclass(frozen=True)
class MigrationMetrics:
    count: int
    mae_m_per_year: float
    rmse_m_per_year: float
    bias_m_per_year: float
    mean_absolute_angular_error_deg: float | None
    interval_coverage: float | None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mae_m_per_year": self.mae_m_per_year,
            "rmse_m_per_year": self.rmse_m_per_year,
            "bias_m_per_year": self.bias_m_per_year,
            "mean_absolute_angular_error_deg": self.mean_absolute_angular_error_deg,
            "interval_coverage": self.interval_coverage,
            "diagnostics": dict(self.diagnostics),
        }


def _paired_arrays(
    estimates: Iterable[float],
    references: Iterable[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    estimate_array = np.asarray(list(estimates), dtype=np.float64)
    reference_array = np.asarray(list(references), dtype=np.float64)
    if estimate_array.size != reference_array.size:
        raise MigrationMetricsError("Estimate and reference counts differ.")
    if estimate_array.size == 0:
        raise MigrationMetricsError("No estimates were supplied.")
    finite = np.isfinite(estimate_array) & np.isfinite(reference_array)
    if not np.any(finite):
        raise MigrationMetricsError("No finite estimate/reference pairs remain.")
    return estimate_array[finite], reference_array[finite], finite


def migration_metrics(
    estimates_m_per_year: Iterable[float],
    references_m_per_year: Iterable[float],
    *,
    estimate_azimuths_deg: Iterable[float] | None = None,
    reference_azimuths_deg: Iterable[float] | None = None,
    lower_m_per_year: Iterable[float] | None = None,
    upper_m_per_year: Iterable[float] | None = None,
) -> MigrationMetrics:
    estimates, references, finite = _paired_arrays(
        estimates_m_per_year, references_m_per_year
    )
    errors = estimates - references
    angular_error = None
    if estimate_azimuths_deg is not None or reference_azimuths_deg is not None:
        if estimate_azimuths_deg is None or reference_azimuths_deg is None:
            raise MigrationMetricsError("Both azimuth collections must be supplied together.")
        estimated_angles = np.asarray(list(estimate_azimuths_deg), dtype=object)
        reference_angles = np.asarray(list(reference_azimuths_deg), dtype=object)
        if estimated_angles.size != finite.size or reference_angles.size != finite.size:
            raise MigrationMetricsError("Azimuth counts must match rate counts.")
        differences = [
            angular_difference_degrees(float(first), float(second))
            for first, second in zip(
                estimated_angles[finite], reference_angles[finite]
            )
            if first is not None and second is not None
        ]
        angular_error = float(np.mean(differences)) if differences else None
    coverage = None
    if lower_m_per_year is not None or upper_m_per_year is not None:
        if lower_m_per_year is None or upper_m_per_year is None:
            raise MigrationMetricsError("Both lower and upper intervals are required.")
        lower = np.asarray(list(lower_m_per_year), dtype=np.float64)
        upper = np.asarray(list(upper_m_per_year), dtype=np.float64)
        if lower.size != finite.size or upper.size != finite.size:
            raise MigrationMetricsError("Interval counts must match rate counts.")
        lower = lower[finite]
        upper = upper[finite]
        interval_finite = np.isfinite(lower) & np.isfinite(upper)
        if np.any(interval_finite):
            inside = (references[interval_finite] >= lower[interval_finite]) & (
                references[interval_finite] <= upper[interval_finite]
            )
            coverage = float(np.mean(inside))
    return MigrationMetrics(
        count=int(estimates.size),
        mae_m_per_year=float(np.mean(np.abs(errors))),
        rmse_m_per_year=float(np.sqrt(np.mean(errors**2))),
        bias_m_per_year=float(np.mean(errors)),
        mean_absolute_angular_error_deg=angular_error,
        interval_coverage=coverage,
        diagnostics={
            "max_absolute_error_m_per_year": float(np.max(np.abs(errors))),
            "median_absolute_error_m_per_year": float(np.median(np.abs(errors))),
        },
    )


def grouped_migration_metrics(
    estimates_m_per_year: Iterable[float],
    references_m_per_year: Iterable[float],
    groups: Iterable[str],
) -> dict[str, Any]:
    estimate_array = np.asarray(list(estimates_m_per_year), dtype=np.float64)
    reference_array = np.asarray(list(references_m_per_year), dtype=np.float64)
    group_array = np.asarray(list(groups), dtype=object)
    if not (estimate_array.size == reference_array.size == group_array.size):
        raise MigrationMetricsError("Estimate, reference and group counts differ.")
    output: dict[str, Any] = {}
    for group in sorted(set(str(value) for value in group_array)):
        mask = group_array.astype(str) == group
        if not np.any(mask):
            continue
        metrics = migration_metrics(estimate_array[mask], reference_array[mask])
        output[group] = metrics.as_dict()
    return output
