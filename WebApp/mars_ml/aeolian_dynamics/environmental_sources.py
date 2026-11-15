"""Catalogued environmental data sources with explicit provenance.

The catalog describes what a source is and what it cannot provide. A catalogued
source is not automatically verified, simultaneous with an image, or valid at a
dune field. In-situ, model and climatology products remain distinct.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ENVIRONMENTAL_SOURCES_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "mars"
    / "environmental_sources.json"
)

_ALLOWED_SOURCE_TYPES = {
    "in_situ",
    "reanalysis",
    "model",
    "climatology",
    "estimated",
    "unknown",
}
_UNITS_BY_VARIABLE = {
    "wind_speed_m_s": {"m/s"},
    "wind_direction_deg": {"degrees clockwise from north", "degree"},
    "wind_reference_height_m": {"m"},
    "temperature_k": {"K"},
    "pressure_pa": {"Pa"},
    "atmospheric_density_kg_m3": {"kg/m^3"},
    "relative_humidity_pct": {"%"},
    "thermal_inertia_tiu": {"J m^-2 K^-1 s^-1/2", "J m^-2 K^-1 s^-0.5"},
}


class EnvironmentalSourceError(ValueError):
    """Raised when an environmental source record is inconsistent."""


@dataclass(frozen=True)
class EnvironmentalSource:
    source_id: str
    name: str
    provider: str
    source_type: str
    platform: str
    instrument: str
    location: str
    variables: tuple[str, ...]
    units: dict[str, str]
    spatial_support: str
    temporal_support: str
    simultaneous_with_image: bool | None
    metadata_verified: bool
    url: str | None = None
    doi: str | None = None
    limitations: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "name",
            "provider",
            "platform",
            "instrument",
            "location",
            "spatial_support",
            "temporal_support",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise EnvironmentalSourceError(f"{self.source_id or '<unknown>'}: {name} is required.")
        if not self.source_id.replace("_", "").isalnum():
            raise EnvironmentalSourceError(
                f"{self.source_id}: source_id must be alphanumeric with underscores."
            )
        if self.source_type not in _ALLOWED_SOURCE_TYPES:
            raise EnvironmentalSourceError(
                f"{self.source_id}: unsupported source_type {self.source_type!r}."
            )
        if not self.variables:
            raise EnvironmentalSourceError(f"{self.source_id}: at least one variable is required.")
        if len(set(self.variables)) != len(self.variables):
            raise EnvironmentalSourceError(f"{self.source_id}: duplicate variables.")
        for variable in self.variables:
            if variable not in self.units:
                raise EnvironmentalSourceError(
                    f"{self.source_id}: variable {variable!r} has no unit."
                )
            allowed = _UNITS_BY_VARIABLE.get(variable)
            if allowed is not None and self.units[variable] not in allowed:
                raise EnvironmentalSourceError(
                    f"{self.source_id}: unsupported unit {self.units[variable]!r} for {variable}."
                )
        if self.url is not None and not self.url.startswith(("https://", "http://")):
            raise EnvironmentalSourceError(f"{self.source_id}: URL must use HTTP(S).")
        if self.metadata_verified and self.url is None and self.doi is None:
            raise EnvironmentalSourceError(
                f"{self.source_id}: verified metadata requires a URL or DOI."
            )
        if not self.limitations:
            raise EnvironmentalSourceError(f"{self.source_id}: limitations cannot be empty.")

    def is_local_measurement(self) -> bool:
        return self.source_type == "in_situ" and self.metadata_verified

    def can_be_simultaneous(self) -> bool:
        return self.simultaneous_with_image is True

    def required_fields(self) -> tuple[str, ...]:
        return tuple(self.variables)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "provider": self.provider,
            "source_type": self.source_type,
            "platform": self.platform,
            "instrument": self.instrument,
            "location": self.location,
            "variables": list(self.variables),
            "units": dict(self.units),
            "spatial_support": self.spatial_support,
            "temporal_support": self.temporal_support,
            "simultaneous_with_image": self.simultaneous_with_image,
            "metadata_verified": self.metadata_verified,
            "url": self.url,
            "doi": self.doi,
            "limitations": list(self.limitations),
            "notes": self.notes,
        }


def _source_from_dict(payload: dict[str, Any]) -> EnvironmentalSource:
    required = {
        "source_id",
        "name",
        "provider",
        "source_type",
        "platform",
        "instrument",
        "location",
        "variables",
        "units",
        "spatial_support",
        "temporal_support",
        "simultaneous_with_image",
        "metadata_verified",
        "limitations",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise EnvironmentalSourceError(
            f"Environmental source is missing fields: {', '.join(missing)}."
        )
    try:
        return EnvironmentalSource(
            source_id=str(payload["source_id"]),
            name=str(payload["name"]),
            provider=str(payload["provider"]),
            source_type=str(payload["source_type"]),
            platform=str(payload["platform"]),
            instrument=str(payload["instrument"]),
            location=str(payload["location"]),
            variables=tuple(str(value) for value in payload["variables"]),
            units={str(key): str(value) for key, value in dict(payload["units"]).items()},
            spatial_support=str(payload["spatial_support"]),
            temporal_support=str(payload["temporal_support"]),
            simultaneous_with_image=payload["simultaneous_with_image"],
            metadata_verified=bool(payload["metadata_verified"]),
            url=None if payload.get("url") is None else str(payload["url"]),
            doi=None if payload.get("doi") is None else str(payload["doi"]),
            limitations=tuple(str(value) for value in payload["limitations"]),
            notes=str(payload.get("notes", "")),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, EnvironmentalSourceError):
            raise
        raise EnvironmentalSourceError(
            f"Invalid environmental source {payload.get('source_id', '<unknown>')}: {exc}"
        ) from exc


def load_environmental_sources(
    path: str | Path | None = None,
) -> tuple[EnvironmentalSource, ...]:
    source_path = Path(path) if path is not None else DEFAULT_ENVIRONMENTAL_SOURCES_PATH
    if not source_path.exists():
        raise EnvironmentalSourceError(f"Environmental source catalog not found: {source_path}")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EnvironmentalSourceError(f"Invalid JSON in {source_path}: {exc}") from exc
    entries = payload.get("sources")
    if not isinstance(entries, list) or not entries:
        raise EnvironmentalSourceError("Environmental source catalog must contain sources.")
    sources = tuple(_source_from_dict(entry) for entry in entries)
    identifiers = [source.source_id for source in sources]
    if len(set(identifiers)) != len(identifiers):
        raise EnvironmentalSourceError("Duplicate source_id in environmental source catalog.")
    return sources


def source_by_id(
    sources: Iterable[EnvironmentalSource], source_id: str
) -> EnvironmentalSource:
    for source in sources:
        if source.source_id == source_id:
            return source
    raise EnvironmentalSourceError(f"Unknown environmental source: {source_id}")


def source_summary(sources: Iterable[EnvironmentalSource]) -> dict[str, Any]:
    entries = tuple(sources)
    return {
        "source_count": len(entries),
        "source_ids": [source.source_id for source in entries],
        "verified": [source.source_id for source in entries if source.metadata_verified],
        "unverified": [source.source_id for source in entries if not source.metadata_verified],
        "in_situ": [source.source_id for source in entries if source.source_type == "in_situ"],
        "simultaneous_capable": [
            source.source_id for source in entries if source.can_be_simultaneous()
        ],
    }


def require_simultaneous(source: EnvironmentalSource) -> None:
    if not source.can_be_simultaneous():
        raise EnvironmentalSourceError(
            f"{source.source_id} cannot be treated as simultaneous with an image; "
            f"simultaneous_with_image={source.simultaneous_with_image!r}."
        )


def validate_covariate_variables(
    source: EnvironmentalSource, variables: Iterable[str]
) -> tuple[str, ...]:
    requested = tuple(str(variable) for variable in variables)
    unknown = sorted(set(requested) - set(source.variables))
    if unknown:
        raise EnvironmentalSourceError(
            f"{source.source_id} does not provide variables: {', '.join(unknown)}."
        )
    return requested
