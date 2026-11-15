"""Published aggregate measurements used as context, never as per-dune labels."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_PUBLISHED_MEASUREMENTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "mars"
    / "published_measurements.json"
)

_ALLOWED_QUANTITIES = {
    "dune_migration_rate",
    "dune_brink_migration_rate",
    "ripple_crest_migration_rate",
    "sediment_flux",
    "morphometric_range",
}
_ALLOWED_USAGE = {"aggregate_context_only"}


class PublishedMeasurementError(ValueError):
    """Raised when a published measurement record is inconsistent."""


@dataclass(frozen=True)
class PublishedMeasurement:
    measurement_id: str
    dataset_id: str
    citation_doi: str
    citation: str
    quantity: str
    value_min: float
    value_max: float
    unit: str
    spatial_scope: str
    temporal_scope: str
    usage: str = "aggregate_context_only"
    limitations: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        for name in (
            "measurement_id",
            "dataset_id",
            "citation_doi",
            "citation",
            "unit",
            "spatial_scope",
            "temporal_scope",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise PublishedMeasurementError(
                    f"{self.measurement_id or '<unknown>'}: {name} is required."
                )
        if self.quantity not in _ALLOWED_QUANTITIES:
            raise PublishedMeasurementError(
                f"{self.measurement_id}: unsupported quantity {self.quantity!r}."
            )
        if self.usage not in _ALLOWED_USAGE:
            raise PublishedMeasurementError(
                f"{self.measurement_id}: published values are aggregate context only."
            )
        if not (self.value_min <= self.value_max):
            raise PublishedMeasurementError(
                f"{self.measurement_id}: value_min must not exceed value_max."
            )
        if not self.limitations:
            raise PublishedMeasurementError(
                f"{self.measurement_id}: limitations cannot be empty."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "dataset_id": self.dataset_id,
            "citation_doi": self.citation_doi,
            "citation": self.citation,
            "quantity": self.quantity,
            "value_min": self.value_min,
            "value_max": self.value_max,
            "unit": self.unit,
            "spatial_scope": self.spatial_scope,
            "temporal_scope": self.temporal_scope,
            "usage": self.usage,
            "limitations": list(self.limitations),
            "notes": self.notes,
        }


def _measurement_from_dict(payload: Mapping[str, Any]) -> PublishedMeasurement:
    required = {
        "measurement_id",
        "dataset_id",
        "citation_doi",
        "citation",
        "quantity",
        "value_min",
        "value_max",
        "unit",
        "spatial_scope",
        "temporal_scope",
        "limitations",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise PublishedMeasurementError(
            f"Published measurement is missing fields: {', '.join(missing)}."
        )
    try:
        return PublishedMeasurement(
            measurement_id=str(payload["measurement_id"]),
            dataset_id=str(payload["dataset_id"]),
            citation_doi=str(payload["citation_doi"]),
            citation=str(payload["citation"]),
            quantity=str(payload["quantity"]),
            value_min=float(payload["value_min"]),
            value_max=float(payload["value_max"]),
            unit=str(payload["unit"]),
            spatial_scope=str(payload["spatial_scope"]),
            temporal_scope=str(payload["temporal_scope"]),
            usage=str(payload.get("usage", "aggregate_context_only")),
            limitations=tuple(str(value) for value in payload["limitations"]),
            notes=str(payload.get("notes", "")),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, PublishedMeasurementError):
            raise
        raise PublishedMeasurementError(
            f"Invalid published measurement {payload.get('measurement_id', '<unknown>')}: {exc}"
        ) from exc


def load_published_measurements(
    path: str | Path | None = None,
) -> tuple[PublishedMeasurement, ...]:
    measurement_path = Path(path) if path is not None else DEFAULT_PUBLISHED_MEASUREMENTS_PATH
    if not measurement_path.exists():
        raise PublishedMeasurementError(
            f"Published measurement catalog not found: {measurement_path}"
        )
    try:
        payload = json.loads(measurement_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishedMeasurementError(
            f"Invalid JSON in {measurement_path}: {exc}"
        ) from exc
    entries = payload.get("measurements")
    if not isinstance(entries, list) or not entries:
        raise PublishedMeasurementError(
            "Published measurement catalog must contain measurements."
        )
    measurements = tuple(_measurement_from_dict(entry) for entry in entries)
    identifiers = [measurement.measurement_id for measurement in measurements]
    if len(set(identifiers)) != len(identifiers):
        raise PublishedMeasurementError("Duplicate measurement_id in catalog.")
    return measurements


def measurements_for_dataset(
    measurements: Iterable[PublishedMeasurement], dataset_id: str
) -> tuple[PublishedMeasurement, ...]:
    return tuple(
        measurement
        for measurement in measurements
        if measurement.dataset_id == dataset_id
    )


def measurement_by_id(
    measurements: Iterable[PublishedMeasurement], measurement_id: str
) -> PublishedMeasurement:
    for measurement in measurements:
        if measurement.measurement_id == measurement_id:
            return measurement
    raise PublishedMeasurementError(f"Unknown published measurement: {measurement_id}")


def migration_range(
    measurements: Iterable[PublishedMeasurement], dataset_id: str
) -> tuple[float, float] | None:
    matching = [
        measurement
        for measurement in measurements_for_dataset(measurements, dataset_id)
        if measurement.quantity in {"dune_migration_rate", "dune_brink_migration_rate"}
    ]
    if not matching:
        return None
    return (
        min(measurement.value_min for measurement in matching),
        max(measurement.value_max for measurement in matching),
    )


def require_aggregate_context(measurement: PublishedMeasurement) -> None:
    if measurement.usage != "aggregate_context_only":
        raise PublishedMeasurementError(
            f"{measurement.measurement_id}: measurement is not aggregate context."
        )
