"""Dune migration derived from apparent 2D displacement and observation dates.

The result is an apparent horizontal migration rate between two observations.
It assumes that the measured centroid shift represents bulk dune motion and
that the interval is long enough for that interpretation to be meaningful.
It does not infer sediment flux, vertical change or a Mars migration rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from mars_ml.aeolian_dynamics.dune_morphology import (
    MorphologyFeatures,
    morphological_change,
)
from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    azimuth_degrees,
    pixels_to_meters,
)


class MigrationError(ValueError):
    """Raised when migration cannot be computed from the inputs."""


@dataclass(frozen=True)
class MigrationResult:
    status: str
    reliable: bool
    reference_datetime_utc: str
    moving_datetime_utc: str
    interval_days: float
    dx_m: float
    dy_m: float
    magnitude_m: float
    azimuth_deg: float | None
    rate_m_per_year: float
    area_change: dict[str, Any]
    notes: str = ""
    assumptions: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reliable": self.reliable,
            "reference_datetime_utc": self.reference_datetime_utc,
            "moving_datetime_utc": self.moving_datetime_utc,
            "interval_days": self.interval_days,
            "dx_m": self.dx_m,
            "dy_m": self.dy_m,
            "magnitude_m": self.magnitude_m,
            "azimuth_deg": self.azimuth_deg,
            "rate_m_per_year": self.rate_m_per_year,
            "area_change": dict(self.area_change),
            "notes": self.notes,
            "assumptions": list(self.assumptions),
        }


def _parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise MigrationError("Observation datetimes must include a timezone.")
    return parsed.astimezone(timezone.utc)


def interval_days(reference_datetime: str | datetime, moving_datetime: str | datetime) -> float:
    reference = _parse_utc(reference_datetime)
    moving = _parse_utc(moving_datetime)
    days = (moving - reference).total_seconds() / 86400.0
    if days <= 0:
        raise MigrationError("Moving observation must be later than the reference observation.")
    return days


def migration_from_metric(
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    displacement: MetricDisplacement | None,
    *,
    area_change: dict[str, Any] | None = None,
    min_interval_days: float = 1.0,
) -> MigrationResult:
    """Annualize an apparent metric displacement between two dated observations."""

    if displacement is None:
        raise MigrationError(
            "Metric displacement is unavailable. Supply a verified metres-per-pixel scale."
        )
    days = interval_days(reference_datetime, moving_datetime)
    if days < min_interval_days:
        raise MigrationError(
            f"Observation interval {days:.2f} days is shorter than the minimum "
            f"{min_interval_days:.2f} days."
        )
    rate = displacement.magnitude_m / days * 365.25
    reference_utc = _parse_utc(reference_datetime).isoformat()
    moving_utc = _parse_utc(moving_datetime).isoformat()
    return MigrationResult(
        status="apparent_2d_migration",
        reliable=True,
        reference_datetime_utc=reference_utc,
        moving_datetime_utc=moving_utc,
        interval_days=days,
        dx_m=displacement.dx_m,
        dy_m=displacement.dy_m,
        magnitude_m=displacement.magnitude_m,
        azimuth_deg=displacement.azimuth_deg,
        rate_m_per_year=rate,
        area_change=dict(area_change or {}),
        notes=(
            "Apparent horizontal migration from two observations. "
            "Not a sediment flux and not validated against field measurements."
        ),
        assumptions=(
            "The centroid shift represents bulk dune motion.",
            "The metre-per-pixel scale is valid across both images.",
            "The two images are registered and segmented consistently.",
            "Linear annualization does not imply constant migration through time.",
        ),
    )


def estimate_migration(
    reference: MorphologyFeatures,
    moving: MorphologyFeatures,
    reference_datetime: str | datetime,
    moving_datetime: str | datetime,
    *,
    meters_per_pixel: float | tuple[float, float],
    min_interval_days: float = 1.0,
) -> MigrationResult:
    """Compute apparent migration directly from two morphology snapshots."""

    days = interval_days(reference_datetime, moving_datetime)
    if days < min_interval_days:
        raise MigrationError(
            f"Observation interval {days:.2f} days is shorter than the minimum "
            f"{min_interval_days:.2f} days."
        )
    dx_px = moving.centroid_x_px - reference.centroid_x_px
    dy_px = -(moving.centroid_y_px - reference.centroid_y_px)
    dx_m, dy_m = pixels_to_meters(dx_px, dy_px, meters_per_pixel)
    magnitude = float(np.hypot(dx_m, dy_m))
    scale = (
        (float(meters_per_pixel), float(meters_per_pixel))
        if np.isscalar(meters_per_pixel)
        else (float(meters_per_pixel[0]), float(meters_per_pixel[1]))
    )
    displacement = MetricDisplacement(
        dx_m=dx_m,
        dy_m=dy_m,
        magnitude_m=magnitude,
        azimuth_deg=azimuth_degrees(dx_px, dy_px),
        meters_per_pixel=scale,
        method="mask_centroid",
    )
    return migration_from_metric(
        reference_datetime,
        moving_datetime,
        displacement,
        area_change=morphological_change(reference, moving, meters_per_pixel=meters_per_pixel),
        min_interval_days=min_interval_days,
    )


def direction_difference_degrees(first: MigrationResult, second: MigrationResult) -> float | None:
    """Angular difference between two migration directions, if both exist."""

    if first.azimuth_deg is None or second.azimuth_deg is None:
        return None
    return float(abs((first.azimuth_deg - second.azimuth_deg + 180.0) % 360.0 - 180.0))
