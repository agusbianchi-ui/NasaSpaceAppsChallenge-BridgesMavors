"""Environmental observations associated with an image, without imputation.

Wind, temperature, pressure, density and humidity are optional. A missing value
stays missing. Each observation records provenance and whether it is actually
simultaneous with the image, so a climatology value cannot be presented as an
in-situ measurement from the acquisition time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from mars_ml.aeolian_dynamics.planetary_parameters import (
    LocalEnvironment,
    PlanetaryParameterError,
    get_planetary_parameters,
)


class EnvironmentalObservationError(ValueError):
    """Raised when environmental metadata is inconsistent."""


def _parse_utc_or_none(value: str | datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise EnvironmentalObservationError(f"{field_name} must include a timezone.")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EnvironmentalObservation:
    source: str
    source_type: str = "unknown"
    image_datetime_utc: str | datetime | None = None
    observation_datetime_utc: str | datetime | None = None
    simultaneity_tolerance_s: float = 3600.0
    wind_speed_m_s: float | None = None
    wind_direction_deg: float | None = None
    wind_reference_height_m: float | None = None
    temperature_k: float | None = None
    pressure_pa: float | None = None
    atmospheric_density_kg_m3: float | None = None
    relative_humidity_pct: float | None = None
    scene_id: str | None = None
    units: dict[str, str] = field(
        default_factory=lambda: {
            "wind_speed_m_s": "m/s",
            "wind_direction_deg": "degrees clockwise from north",
            "wind_reference_height_m": "m above surface",
            "temperature_k": "K",
            "pressure_pa": "Pa",
            "atmospheric_density_kg_m3": "kg/m^3",
            "relative_humidity_pct": "%",
        }
    )
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise EnvironmentalObservationError("source is required.")
        if self.source_type not in {
            "in_situ",
            "reanalysis",
            "model",
            "climatology",
            "estimated",
            "unknown",
        }:
            raise EnvironmentalObservationError(
                "source_type must be in_situ, reanalysis, model, climatology, estimated or unknown."
            )
        image_time = _parse_utc_or_none(self.image_datetime_utc, "image_datetime_utc")
        observation_time = _parse_utc_or_none(
            self.observation_datetime_utc, "observation_datetime_utc"
        )
        if image_time is not None and observation_time is not None:
            if self.simultaneity_tolerance_s < 0:
                raise EnvironmentalObservationError(
                    "simultaneity_tolerance_s must be non-negative."
                )
        if self.wind_speed_m_s is not None and self.wind_speed_m_s < 0:
            raise EnvironmentalObservationError("wind_speed_m_s must be non-negative.")
        if self.wind_direction_deg is not None and not 0 <= self.wind_direction_deg < 360:
            raise EnvironmentalObservationError("wind_direction_deg must be in [0, 360).")
        if self.wind_reference_height_m is not None and self.wind_reference_height_m <= 0:
            raise EnvironmentalObservationError("wind_reference_height_m must be positive.")
        if self.temperature_k is not None and self.temperature_k <= 0:
            raise EnvironmentalObservationError("temperature_k must be positive.")
        if self.pressure_pa is not None and self.pressure_pa <= 0:
            raise EnvironmentalObservationError("pressure_pa must be positive.")
        if self.atmospheric_density_kg_m3 is not None and self.atmospheric_density_kg_m3 <= 0:
            raise EnvironmentalObservationError("atmospheric_density_kg_m3 must be positive.")
        if self.relative_humidity_pct is not None and not 0 <= self.relative_humidity_pct <= 100:
            raise EnvironmentalObservationError("relative_humidity_pct must be in [0, 100].")

    @property
    def image_datetime(self) -> datetime | None:
        return _parse_utc_or_none(self.image_datetime_utc, "image_datetime_utc")

    @property
    def observation_datetime(self) -> datetime | None:
        return _parse_utc_or_none(self.observation_datetime_utc, "observation_datetime_utc")

    def temporal_offset_seconds(self) -> float | None:
        image_time = self.image_datetime
        observation_time = self.observation_datetime
        if image_time is None or observation_time is None:
            return None
        return abs((observation_time - image_time).total_seconds())

    def simultaneous_with_image(self) -> bool | None:
        offset = self.temporal_offset_seconds()
        if offset is None:
            return None
        return offset <= self.simultaneity_tolerance_s

    def available_fields(self) -> dict[str, bool]:
        fields = (
            "wind_speed_m_s",
            "wind_direction_deg",
            "wind_reference_height_m",
            "temperature_k",
            "pressure_pa",
            "atmospheric_density_kg_m3",
            "relative_humidity_pct",
        )
        return {name: getattr(self, name) is not None for name in fields}

    def wind_vector(self) -> tuple[float, float] | None:
        """Return ``(east, north)`` wind components, or ``None`` if incomplete."""

        if self.wind_speed_m_s is None or self.wind_direction_deg is None:
            return None
        radians = np.radians(self.wind_direction_deg)
        east = float(self.wind_speed_m_s * np.sin(radians))
        north = float(self.wind_speed_m_s * np.cos(radians))
        return east, north

    def to_local_environment(self, planet: str) -> LocalEnvironment:
        """Build a LocalEnvironment without silently inventing missing values.

        Density is derived from pressure and temperature only when it was not
        supplied. The provenance notes state that derivation.
        """

        density = self.atmospheric_density_kg_m3
        notes = self.notes
        if density is None and self.pressure_pa is not None and self.temperature_k is not None:
            parameters = get_planetary_parameters(planet)
            density = parameters.atmosphere.density_from_ideal_gas(
                pressure_pa=self.pressure_pa,
                temperature_k=self.temperature_k,
            )
            notes = (notes + " Density derived from ideal gas using supplied P and T.").strip()
        if density is None:
            raise EnvironmentalObservationError(
                "Atmospheric density is unavailable and cannot be derived without pressure and temperature."
            )
        parameters = get_planetary_parameters(planet)
        try:
            return LocalEnvironment(
                gravity_m_s2=parameters.gravity_m_s2,
                atmospheric_density_kg_m3=density,
                pressure_pa=self.pressure_pa,
                temperature_k=self.temperature_k,
                wind_speed_m_s=self.wind_speed_m_s,
                wind_reference_height_m=self.wind_reference_height_m,
                source=f"{self.source} ({self.source_type})",
                notes=notes,
            )
        except PlanetaryParameterError as exc:
            raise EnvironmentalObservationError(str(exc)) from exc

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "scene_id": self.scene_id,
            "image_datetime_utc": self.image_datetime.isoformat() if self.image_datetime else None,
            "observation_datetime_utc": (
                self.observation_datetime.isoformat() if self.observation_datetime else None
            ),
            "temporal_offset_seconds": self.temporal_offset_seconds(),
            "simultaneity_tolerance_s": self.simultaneity_tolerance_s,
            "simultaneous_with_image": self.simultaneous_with_image(),
            "wind_speed_m_s": self.wind_speed_m_s,
            "wind_direction_deg": self.wind_direction_deg,
            "wind_reference_height_m": self.wind_reference_height_m,
            "temperature_k": self.temperature_k,
            "pressure_pa": self.pressure_pa,
            "atmospheric_density_kg_m3": self.atmospheric_density_kg_m3,
            "relative_humidity_pct": self.relative_humidity_pct,
            "wind_vector_east_north_m_s": list(self.wind_vector()) if self.wind_vector() else None,
            "available": self.available_fields(),
            "units": dict(self.units),
            "notes": self.notes,
        }
