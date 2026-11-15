from __future__ import annotations

import pytest

from mars_ml.aeolian_dynamics.planetary_parameters import (
    EARTH,
    MARS,
    PlanetaryParameterError,
    bagnold_saltation_flux,
    environment_from_reference,
    friction_velocity_from_wind_speed,
    get_planetary_parameters,
    threshold_friction_velocity,
)


def test_reference_planets_have_expected_orders_of_magnitude():
    assert EARTH.gravity_m_s2 == pytest.approx(9.81, abs=0.01)
    assert MARS.gravity_m_s2 == pytest.approx(3.71, abs=0.01)
    assert EARTH.reference_atmospheric_density_kg_m3 == pytest.approx(1.225, rel=0.03)
    assert 0.01 < MARS.reference_atmospheric_density_kg_m3 < 0.03
    mars_gases = {gas.species: gas.fraction for gas in MARS.atmosphere.dominant_gases}
    assert mars_gases["CO2"] > 0.9
    assert get_planetary_parameters("Earth") is EARTH


def test_unknown_planet_is_rejected():
    with pytest.raises(PlanetaryParameterError):
        get_planetary_parameters("venus")


def test_reference_environment_is_labelled_as_reference():
    environment = environment_from_reference("mars")
    assert environment.source.startswith("reference values")
    assert "not a local measurement" in environment.notes.lower()
    assert environment.atmospheric_density_kg_m3 > 0


def test_friction_velocity_from_log_law():
    value = friction_velocity_from_wind_speed(
        wind_speed_m_s=10.0,
        reference_height_m=10.0,
        roughness_length_m=0.01,
    )
    assert value > 0
    with pytest.raises(PlanetaryParameterError):
        friction_velocity_from_wind_speed(
            wind_speed_m_s=10.0,
            reference_height_m=0.01,
            roughness_length_m=0.01,
        )


def test_threshold_and_flux_require_explicit_coefficients():
    earth_threshold = threshold_friction_velocity(
        gravity_m_s2=EARTH.gravity_m_s2,
        atmospheric_density_kg_m3=EARTH.reference_atmospheric_density_kg_m3,
        grain_diameter_m=0.00025,
        grain_density_kg_m3=2650.0,
        coefficient=0.1,
    )
    mars_threshold = threshold_friction_velocity(
        gravity_m_s2=MARS.gravity_m_s2,
        atmospheric_density_kg_m3=MARS.reference_atmospheric_density_kg_m3,
        grain_diameter_m=0.00025,
        grain_density_kg_m3=2650.0,
        coefficient=0.1,
    )
    assert earth_threshold > 0
    assert mars_threshold > 0
    assert earth_threshold != mars_threshold
    flux_below = bagnold_saltation_flux(
        friction_velocity_m_s=mars_threshold * 0.9,
        threshold_friction_velocity_m_s=mars_threshold,
        atmospheric_density_kg_m3=MARS.reference_atmospheric_density_kg_m3,
        gravity_m_s2=MARS.gravity_m_s2,
        coefficient=1.5,
    )
    flux_above = bagnold_saltation_flux(
        friction_velocity_m_s=mars_threshold * 1.5,
        threshold_friction_velocity_m_s=mars_threshold,
        atmospheric_density_kg_m3=MARS.reference_atmospheric_density_kg_m3,
        gravity_m_s2=MARS.gravity_m_s2,
        coefficient=1.5,
    )
    assert flux_below == 0.0
    assert flux_above > 0


def test_threshold_requires_positive_coefficient():
    with pytest.raises(PlanetaryParameterError):
        threshold_friction_velocity(
            gravity_m_s2=9.81,
            atmospheric_density_kg_m3=1.2,
            grain_diameter_m=0.00025,
            grain_density_kg_m3=2650.0,
            coefficient=0.0,
        )
