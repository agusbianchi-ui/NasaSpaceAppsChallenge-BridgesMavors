"""Method-aware migration observations and uncertainty.

Centroid, crest, advancing-front and geometry-change estimates are kept separate.
Geometry change is not converted into a migration rate. A rate requires two
dated observations, an explicit metric scale and a reliable displacement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

import numpy as np

from mars_ml.aeolian_dynamics.dune_migration import interval_days
from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    PixelDisplacement,
    centroid_displacement,
    metric_displacement,
)
from mars_ml.computer_vision.geometry_comparison import GeometryComparison
from mars_ml.computer_vision.uncertainty import UncertaintyEstimate

_ALLOWED_METHODS = {"centroid", "crest", "advancing_front", "geometry"}


class MigrationAnalysisError(ValueError):
    """Raised when a migration observation cannot be constructed safely."""


@dataclass(frozen=True)
class MigrationObservation:
    dataset_id: str
    dune_id: str
    method: str
    reference_datetime_utc: str | None
    moving_datetime_utc: str | None
    interval_days: float | None
    dx_m: float | None
    dy_m: float | None
    distance_m: float | None
    azimuth_deg: float | None
    rate_m_per_year: float | None
    rate_standard_error_m_per_year: float | None
    distance_ci95_m: tuple[float, float] | None
    valid: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.method not in _ALLOWED_METHODS:
            raise MigrationAnalysisError(f"Unsupported migration method {self.method!r}.")
        if not self.dataset_id.strip() or not self.dune_id.strip():
            raise MigrationAnalysisError("dataset_id and dune_id are required.")
        if self.valid:
            if self.reasons:
                raise MigrationAnalysisError("A valid observation cannot carry rejection reasons.")
            for name in (
                "interval_days",
                "dx_m",
                "dy_m",
                "distance_m",
                "rate_m_per_year",
            ):
                value = getattr(self, name)
                if value is None or not np.isfinite(value):
                    raise MigrationAnalysisError(f"Valid observation requires finite {name}.")
            if self.interval_days is None or self.interval_days <= 0:
                raise MigrationAnalysisError("Valid observation requires a positive interval.")
            if self.method == "geometry":
                raise MigrationAnalysisError(
                    "Geometry change is not a migration method; create an invalid observation."
                )
        elif not self.reasons:
            raise MigrationAnalysisError("An invalid observation must state at least one reason.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dune_id": self.dune_id,
            "method": self.method,
            "reference_datetime_utc": self.reference_datetime_utc,
            "moving_datetime_utc": self.moving_datetime_utc,
            "interval_days": self.interval_days,
            "dx_m": self.dx_m,
            "dy_m": self.dy_m,
            "distance_m": self.distance_m,
            "azimuth_deg": self.azimuth_deg,
            "rate_m_per_year": self.rate_m_per_year,
            "rate_standard_error_m_per_year": self.rate_standard_error_m_per_year,
            "distance_ci95_m": list(self.distance_ci95_m) if self.distance_ci95_m else None,
            "valid": self.valid,
            "reasons": list(self.reasons),
            "assumptions": list(self.assumptions),
            "provenance": dict(self.provenance),
        }


def _iso(value: str | datetime) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise MigrationAnalysisError("Observation datetimes must include a timezone.")
        return value.isoformat()
    return value


def _invalid(
    dataset_id: str,
    dune_id: str,
    method: str,
    reason: str,
    *,
    reference_datetime_utc: str | None = None,
    moving_datetime_utc: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> MigrationObservation:
    return MigrationObservation(
        dataset_id=dataset_id,
        dune_id=dune_id,
        method=method,
        reference_datetime_utc=reference_datetime_utc,
        moving_datetime_utc=moving_datetime_utc,
        interval_days=None,
        dx_m=None,
        dy_m=None,
        distance_m=None,
        azimuth_deg=None,
        rate_m_per_year=None,
        rate_standard_error_m_per_year=None,
        distance_ci95_m=None,
        valid=False,
        reasons=(reason,),
        provenance=dict(provenance or {}),
    )


def observation_from_metric(
    dataset_id: str,
    dune_id: str,
    method: str,
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    displacement: MetricDisplacement | None,
    *,
    distance_standard_error_m: float | None = None,
    min_interval_days: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> MigrationObservation:
    if method not in _ALLOWED_METHODS:
        raise MigrationAnalysisError(f"Unsupported migration method {method!r}.")
    reference_iso = _iso(reference_datetime)
    moving_iso = _iso(moving_datetime)
    if method == "geometry":
        return _invalid(
            dataset_id,
            dune_id,
            "geometry",
            "Geometry change is a morphological diagnostic, not a migration rate.",
            reference_datetime_utc=reference_iso,
            moving_datetime_utc=moving_iso,
            provenance=provenance,
        )
    if method not in {"centroid", "crest", "advancing_front"}:
        raise MigrationAnalysisError(f"Unsupported migration method {method!r}.")
    if displacement is None:
        return _invalid(
            dataset_id,
            dune_id,
            method,
            "Metric displacement is unavailable; supply a verified metres-per-pixel scale.",
            reference_datetime_utc=reference_iso,
            moving_datetime_utc=moving_iso,
            provenance=provenance,
        )
    try:
        days = interval_days(reference_datetime, moving_datetime)
    except Exception as exc:
        return _invalid(
            dataset_id,
            dune_id,
            method,
            str(exc),
            reference_datetime_utc=reference_iso,
            moving_datetime_utc=moving_iso,
            provenance=provenance,
        )
    if days < min_interval_days:
        return _invalid(
            dataset_id,
            dune_id,
            method,
            f"Observation interval {days:.2f} days is shorter than {min_interval_days:.2f} days.",
            reference_datetime_utc=reference_iso,
            moving_datetime_utc=moving_iso,
            provenance=provenance,
        )
    years = days / 365.25
    rate = displacement.magnitude_m / years
    rate_se = None
    ci = None
    if distance_standard_error_m is not None:
        if distance_standard_error_m < 0 or not np.isfinite(distance_standard_error_m):
            raise MigrationAnalysisError("distance_standard_error_m must be finite and non-negative.")
        rate_se = distance_standard_error_m / years
        ci = (
            displacement.magnitude_m - 1.96 * distance_standard_error_m,
            displacement.magnitude_m + 1.96 * distance_standard_error_m,
        )
    return MigrationObservation(
        dataset_id=dataset_id,
        dune_id=dune_id,
        method=method,
        reference_datetime_utc=reference_iso,
        moving_datetime_utc=moving_iso,
        interval_days=days,
        dx_m=displacement.dx_m,
        dy_m=displacement.dy_m,
        distance_m=displacement.magnitude_m,
        azimuth_deg=displacement.azimuth_deg,
        rate_m_per_year=rate,
        rate_standard_error_m_per_year=rate_se,
        distance_ci95_m=ci,
        valid=True,
        assumptions=(
            "The displacement represents the selected dune component.",
            "The metric scale is valid across both observations.",
            "The two observations are registered and segmented consistently.",
            "Linear annualization does not imply a constant rate through time.",
            f"Method: {method}.",
        ),
        provenance=dict(provenance or {}),
    )


def observation_from_pixels(
    dataset_id: str,
    dune_id: str,
    method: str,
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    displacement: PixelDisplacement | None,
    meters_per_pixel: float | tuple[float, float] | None,
    *,
    distance_standard_error_m: float | None = None,
    min_interval_days: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> MigrationObservation:
    if method not in _ALLOWED_METHODS:
        raise MigrationAnalysisError(f"Unsupported migration method {method!r}.")
    if displacement is None or not displacement.reliable:
        return _invalid(
            dataset_id,
            dune_id,
            method,
            "Pixel displacement is unavailable or unreliable.",
            reference_datetime_utc=_iso(reference_datetime),
            moving_datetime_utc=_iso(moving_datetime),
            provenance=provenance,
        )
    metric = metric_displacement(displacement, meters_per_pixel)
    return observation_from_metric(
        dataset_id,
        dune_id,
        method,
        reference_datetime,
        moving_datetime,
        metric,
        distance_standard_error_m=distance_standard_error_m,
        min_interval_days=min_interval_days,
        provenance=provenance,
    )


def observation_from_masks(
    dataset_id: str,
    dune_id: str,
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    reference_mask: np.ndarray,
    moving_mask: np.ndarray,
    *,
    meters_per_pixel: float | tuple[float, float] | None,
    min_interval_days: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> MigrationObservation:
    displacement = centroid_displacement(reference_mask, moving_mask)
    return observation_from_pixels(
        dataset_id,
        dune_id,
        "centroid",
        reference_datetime,
        moving_datetime,
        displacement,
        meters_per_pixel,
        min_interval_days=min_interval_days,
        provenance=provenance,
    )


def geometry_change_observation(
    dataset_id: str,
    dune_id: str,
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    comparison: GeometryComparison,
    *,
    provenance: dict[str, Any] | None = None,
) -> MigrationObservation:
    return _invalid(
        dataset_id,
        dune_id,
        "geometry",
        "Geometry change is a morphological diagnostic, not a migration rate.",
        reference_datetime_utc=_iso(reference_datetime),
        moving_datetime_utc=_iso(moving_datetime),
        provenance={
            "geometry_status": comparison.status,
            "iou": comparison.iou,
            "orientation_difference_deg": comparison.orientation_difference_deg,
            **dict(provenance or {}),
        },
    )


def _circular_mean_deg(values: Iterable[float]) -> float | None:
    angles = np.radians(np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64))
    if angles.size == 0:
        return None
    return float(np.degrees(np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))) % 360.0)


def summarize_methods(
    observations: Iterable[MigrationObservation],
) -> dict[str, Any]:
    grouped: dict[str, list[MigrationObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.method, []).append(observation)
    summary: dict[str, Any] = {}
    for method, entries in sorted(grouped.items()):
        valid = [entry for entry in entries if entry.valid]
        rates = np.asarray(
            [entry.rate_m_per_year for entry in valid if entry.rate_m_per_year is not None],
            dtype=np.float64,
        )
        azimuths = [
            entry.azimuth_deg for entry in valid if entry.azimuth_deg is not None
        ]
        summary[method] = {
            "observation_count": len(entries),
            "valid_count": len(valid),
            "rejected_count": len(entries) - len(valid),
            "median_rate_m_per_year": float(np.median(rates)) if rates.size else None,
            "iqr_rate_m_per_year": (
                [float(np.percentile(rates, 25)), float(np.percentile(rates, 75))]
                if rates.size
                else None
            ),
            "circular_mean_azimuth_deg": _circular_mean_deg(azimuths),
            "rejection_reasons": sorted(
                {reason for entry in entries if not entry.valid for reason in entry.reasons}
            ),
        }
    return summary


def method_agreement(
    observations: Iterable[MigrationObservation],
    *,
    max_rate_ratio: float = 2.0,
    max_azimuth_difference_deg: float = 45.0,
) -> dict[str, Any]:
    valid = [entry for entry in observations if entry.valid]
    compared = 0
    rate_consistent = 0
    azimuth_consistent = 0
    for first_index, first in enumerate(valid):
        for second in valid[first_index + 1 :]:
            if first.dune_id != second.dune_id or first.method == second.method:
                continue
            compared += 1
            first_rate = first.rate_m_per_year or 0.0
            second_rate = second.rate_m_per_year or 0.0
            larger = max(first_rate, second_rate)
            smaller = min(first_rate, second_rate)
            ratio = larger / smaller if smaller > 0 else float("inf")
            if ratio <= max_rate_ratio:
                rate_consistent += 1
            if first.azimuth_deg is not None and second.azimuth_deg is not None:
                difference = abs((first.azimuth_deg - second.azimuth_deg + 180.0) % 360.0 - 180.0)
                if difference <= max_azimuth_difference_deg:
                    azimuth_consistent += 1
    return {
        "compared_pairs": compared,
        "rate_consistent_pairs": rate_consistent,
        "azimuth_consistent_pairs": azimuth_consistent,
        "max_rate_ratio": max_rate_ratio,
        "max_azimuth_difference_deg": max_azimuth_difference_deg,
    }


def distance_uncertainty(
    displacement: MetricDisplacement,
    *,
    scale_standard_error_m: float,
    registration_standard_error_px: float,
    meters_per_pixel: float | tuple[float, float],
) -> UncertaintyEstimate:
    scale = (
        float(meters_per_pixel)
        if np.isscalar(meters_per_pixel)
        else float(np.sqrt(float(meters_per_pixel[0]) * float(meters_per_pixel[1])))
    )
    registration_component = registration_standard_error_px * scale
    combined = float(np.hypot(scale_standard_error_m, registration_component))
    return UncertaintyEstimate(
        value=displacement.magnitude_m,
        standard_error=combined,
        ci95_low=float(displacement.magnitude_m - 1.96 * combined),
        ci95_high=float(displacement.magnitude_m + 1.96 * combined),
        method="scale_and_registration_propagation",
        sample_count=0,
        diagnostics={
            "scale_standard_error_m": scale_standard_error_m,
            "registration_standard_error_px": registration_standard_error_px,
            "meters_per_pixel": meters_per_pixel,
        },
    )
