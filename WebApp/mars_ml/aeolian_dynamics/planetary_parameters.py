"""Reference planetary parameters and configurable aeolian transport helpers.

These are reference values for Earth and Mars, not local measurements. The
transport equations are deliberately parameterized so that empirical
coefficients can be calibrated per environment. In particular, no Earth-derived
migration rate is converted into a Mars migration rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

UNIVERSAL_GAS_CONSTANT_J_MOL_K = 8.314462618


class PlanetaryParameterError(ValueError):
    """Raised when planetary inputs are physically inconsistent."""


@dataclass(frozen=True)
class GasFraction:
    species: str
    fraction: float

    def __post_init__(self) -> None:
        if not 0 <= self.fraction <= 1:
            raise PlanetaryParameterError("Gas fractions must be in [0, 1].")


@dataclass(frozen=True)
class Atmosphere:
    name: str
    dominant_gases: tuple[GasFraction, ...]
    mean_molar_mass_kg_per_mol: float
    reference_surface_pressure_pa: float
    reference_temperature_k: float
    notes: str = ""

    def __post_init__(self) -> None:
        if self.mean_molar_mass_kg_per_mol <= 0:
            raise PlanetaryParameterError("Mean molar mass must be positive.")
        if self.reference_surface_pressure_pa <= 0:
            raise PlanetaryParameterError("Reference pressure must be positive.")
        if self.reference_temperature_k <= 0:
            raise PlanetaryParameterError("Reference temperature must be positive.")

    def density_from_ideal_gas(
        self,
        *,
        pressure_pa: float | None = None,
        temperature_k: float | None = None,
    ) -> float:
        """Estimate density from the ideal-gas law using reference defaults.

        This is a physical approximation. It is not a local weather measurement.
        """

        pressure = (
            self.reference_surface_pressure_pa if pressure_pa is None else float(pressure_pa)
        )
        temperature = (
            self.reference_temperature_k if temperature_k is None else float(temperature_k)
        )
        if not np.isfinite(pressure) or pressure <= 0:
            raise PlanetaryParameterError("Pressure must be finite and positive.")
        if not np.isfinite(temperature) or temperature <= 0:
            raise PlanetaryParameterError("Temperature must be finite and positive.")
        return float(
            pressure
            * self.mean_molar_mass_kg_per_mol
            / (UNIVERSAL_GAS_CONSTANT_J_MOL_K * temperature)
        )


@dataclass(frozen=True)
class PlanetaryParameters:
    key: str
    display_name: str
    gravity_m_s2: float
    atmosphere: Atmosphere
    source: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.gravity_m_s2 <= 0:
            raise PlanetaryParameterError("Gravity must be positive.")

    @property
    def reference_atmospheric_density_kg_m3(self) -> float:
        return self.atmosphere.density_from_ideal_gas()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "gravity_m_s2": self.gravity_m_s2,
            "atmosphere": {
                "name": self.atmosphere.name,
                "dominant_gases": [
                    {"species": gas.species, "fraction": gas.fraction}
                    for gas in self.atmosphere.dominant_gases
                ],
                "mean_molar_mass_kg_per_mol": self.atmosphere.mean_molar_mass_kg_per_mol,
                "reference_surface_pressure_pa": self.atmosphere.reference_surface_pressure_pa,
                "reference_temperature_k": self.atmosphere.reference_temperature_k,
                "reference_density_kg_m3": self.reference_atmospheric_density_kg_m3,
                "notes": self.atmosphere.notes,
            },
            "source": list(self.source),
            "notes": self.notes,
        }


EARTH = PlanetaryParameters(
    key="earth",
    display_name="Earth",
    gravity_m_s2=9.80665,
    atmosphere=Atmosphere(
        name="Nitrogen-oxygen atmosphere",
        dominant_gases=(
            GasFraction("N2", 0.7808),
            GasFraction("O2", 0.2095),
            GasFraction("Ar", 0.0093),
            GasFraction("CO2", 0.0004),
        ),
        mean_molar_mass_kg_per_mol=0.02897,
        reference_surface_pressure_pa=101325.0,
        reference_temperature_k=288.15,
        notes="Sea-level reference values, not local conditions.",
    ),
    source=(
        "NASA Earth Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html",
    ),
    notes="Approximate reference gravity 9.81 m/s2; local gravity varies with latitude and elevation.",
)

MARS = PlanetaryParameters(
    key="mars",
    display_name="Mars",
    gravity_m_s2=3.71,
    atmosphere=Atmosphere(
        name="Carbon-dioxide-dominated atmosphere",
        dominant_gases=(
            GasFraction("CO2", 0.9532),
            GasFraction("N2", 0.027),
            GasFraction("Ar", 0.016),
            GasFraction("O2", 0.0013),
            GasFraction("CO", 0.0008),
        ),
        mean_molar_mass_kg_per_mol=0.04334,
        reference_surface_pressure_pa=610.0,
        reference_temperature_k=210.0,
        notes=(
            "Mean surface reference values. Pressure and temperature vary strongly "
            "with season, altitude and location."
        ),
    ),
    source=(
        "NASA Mars Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html",
    ),
    notes=(
        "Approximate reference gravity 3.71 m/s2. These are not local measurements "
        "and do not constitute an operational Mars environment model."
    ),
)

PLANETS: dict[str, PlanetaryParameters] = {"earth": EARTH, "mars": MARS}


def get_planetary_parameters(key: str) -> PlanetaryParameters:
    normalized = key.strip().lower()
    if normalized not in PLANETS:
        raise PlanetaryParameterError(
            f"Unknown planet {key!r}; available values are {sorted(PLANETS)}."
        )
    return PLANETS[normalized]


@dataclass(frozen=True)
class LocalEnvironment:
    """User-supplied local conditions. Units are explicit."""

    gravity_m_s2: float
    atmospheric_density_kg_m3: float
    pressure_pa: float | None = None
    temperature_k: float | None = None
    wind_speed_m_s: float | None = None
    wind_reference_height_m: float | None = None
    roughness_length_m: float | None = None
    source: str = "user_supplied"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.gravity_m_s2 <= 0:
            raise PlanetaryParameterError("gravity_m_s2 must be positive.")
        if self.atmospheric_density_kg_m3 <= 0:
            raise PlanetaryParameterError("atmospheric_density_kg_m3 must be positive.")
        if self.pressure_pa is not None and self.pressure_pa <= 0:
            raise PlanetaryParameterError("pressure_pa must be positive.")
        if self.temperature_k is not None and self.temperature_k <= 0:
            raise PlanetaryParameterError("temperature_k must be positive.")
        if self.wind_speed_m_s is not None and self.wind_speed_m_s < 0:
            raise PlanetaryParameterError("wind_speed_m_s must be non-negative.")
        if self.wind_reference_height_m is not None and self.wind_reference_height_m <= 0:
            raise PlanetaryParameterError("wind_reference_height_m must be positive.")
        if self.roughness_length_m is not None and self.roughness_length_m <= 0:
            raise PlanetaryParameterError("roughness_length_m must be positive.")


@dataclass(frozen=True)
class TransportModelConfig:
    """Empirical coefficients for aeolian transport equations.

    Coefficients are not universal. ``calibration_status`` must be stated when
    reporting any derived flux or threshold.
    """

    threshold_coefficient: float
    flux_coefficient: float
    calibration_status: str = "uncalibrated"
    source: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.threshold_coefficient <= 0:
            raise PlanetaryParameterError("threshold_coefficient must be positive.")
        if self.flux_coefficient <= 0:
            raise PlanetaryParameterError("flux_coefficient must be positive.")


def friction_velocity_from_wind_speed(
    *,
    wind_speed_m_s: float,
    reference_height_m: float,
    roughness_length_m: float,
    von_karman_constant: float = 0.4,
) -> float:
    """Neutral logarithmic-law friction velocity.

    Requires a wind speed at a known height and a roughness length. These are
    not available for most orbital images by default.
    """

    if wind_speed_m_s < 0:
        raise PlanetaryParameterError("Wind speed must be non-negative.")
    if reference_height_m <= 0 or roughness_length_m <= 0:
        raise PlanetaryParameterError("Heights and roughness lengths must be positive.")
    if reference_height_m <= roughness_length_m:
        raise PlanetaryParameterError("Wind reference height must exceed roughness length.")
    return float(von_karman_constant * wind_speed_m_s / np.log(reference_height_m / roughness_length_m))


def threshold_friction_velocity(
    *,
    gravity_m_s2: float,
    atmospheric_density_kg_m3: float,
    grain_diameter_m: float,
    grain_density_kg_m3: float,
    coefficient: float,
) -> float:
    """Bagnold-type impact threshold with an explicit empirical coefficient.

    ``u_*t = A * sqrt(((rho_s / rho_a) - 1) * g * d)``

    ``coefficient`` (A) must be supplied for the environment being studied. A
    value near 0.1 is a terrestrial reference, not a Mars calibration.
    """

    if gravity_m_s2 <= 0 or atmospheric_density_kg_m3 <= 0:
        raise PlanetaryParameterError("Gravity and atmospheric density must be positive.")
    if grain_diameter_m <= 0 or grain_density_kg_m3 <= atmospheric_density_kg_m3:
        raise PlanetaryParameterError("Grain diameter and density contrast must be positive.")
    if coefficient <= 0:
        raise PlanetaryParameterError("coefficient must be positive.")
    density_ratio = grain_density_kg_m3 / atmospheric_density_kg_m3 - 1.0
    return float(coefficient * np.sqrt(density_ratio * gravity_m_s2 * grain_diameter_m))


def bagnold_saltation_flux(
    *,
    friction_velocity_m_s: float,
    threshold_friction_velocity_m_s: float,
    atmospheric_density_kg_m3: float,
    gravity_m_s2: float,
    coefficient: float,
) -> float:
    """Bagnold-type saltation flux in kg m^-1 s^-1.

    ``q = C * (rho_a / g) * (u_*^3 - u_*t^3)`` above threshold, else zero.

    This is a scaling model with an empirical coefficient, not a calibrated
    sediment-flux retrieval.
    """

    if atmospheric_density_kg_m3 <= 0 or gravity_m_s2 <= 0:
        raise PlanetaryParameterError("Density and gravity must be positive.")
    if friction_velocity_m_s < 0 or threshold_friction_velocity_m_s < 0:
        raise PlanetaryParameterError("Friction velocities must be non-negative.")
    if coefficient <= 0:
        raise PlanetaryParameterError("coefficient must be positive.")
    if friction_velocity_m_s <= threshold_friction_velocity_m_s:
        return 0.0
    return float(
        coefficient
        * atmospheric_density_kg_m3
        / gravity_m_s2
        * (friction_velocity_m_s**3 - threshold_friction_velocity_m_s**3)
    )


def environment_from_reference(
    planet: str,
    *,
    pressure_pa: float | None = None,
    temperature_k: float | None = None,
) -> LocalEnvironment:
    """Build a configurable environment from planetary reference values.

    The result is tagged as a reference environment, not a measurement.
    """

    parameters = get_planetary_parameters(planet)
    pressure = (
        parameters.atmosphere.reference_surface_pressure_pa
        if pressure_pa is None
        else float(pressure_pa)
    )
    temperature = (
        parameters.atmosphere.reference_temperature_k
        if temperature_k is None
        else float(temperature_k)
    )
    density = parameters.atmosphere.density_from_ideal_gas(
        pressure_pa=pressure, temperature_k=temperature
    )
    return LocalEnvironment(
        gravity_m_s2=parameters.gravity_m_s2,
        atmospheric_density_kg_m3=density,
        pressure_pa=pressure,
        temperature_k=temperature,
        source=f"reference values from {parameters.key}",
        notes="Reference-derived environment, not a local measurement.",
    )
