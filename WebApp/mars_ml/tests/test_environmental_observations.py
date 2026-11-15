from __future__ import annotations

import pytest

from mars_ml.aeolian_dynamics.environmental_observations import (
    EnvironmentalObservation,
    EnvironmentalObservationError,
)


def test_missing_environmental_fields_stay_missing():
    observation = EnvironmentalObservation(
        source="test fixture",
        source_type="unknown",
        image_datetime_utc="2024-04-27T10:56:19Z",
    )
    assert observation.available_fields()["wind_speed_m_s"] is False
    assert observation.wind_vector() is None
    assert observation.simultaneous_with_image() is None
    with pytest.raises(EnvironmentalObservationError):
        observation.to_local_environment("mars")


def test_simultaneity_is_explicit():
    observation = EnvironmentalObservation(
        source="hypothetical in-situ station",
        source_type="in_situ",
        image_datetime_utc="2024-04-27T10:56:19Z",
        observation_datetime_utc="2024-04-27T11:10:00Z",
        simultaneity_tolerance_s=600,
        wind_speed_m_s=6.0,
        wind_direction_deg=90.0,
        wind_reference_height_m=2.0,
        temperature_k=210.0,
        pressure_pa=610.0,
    )
    assert observation.simultaneous_with_image() is False
    assert observation.temporal_offset_seconds() == pytest.approx(821.0)
    east, north = observation.wind_vector()
    assert east == pytest.approx(6.0)
    assert north == pytest.approx(0.0, abs=1e-12)
    environment = observation.to_local_environment("mars")
    assert environment.atmospheric_density_kg_m3 > 0
    assert "derived from ideal gas" in environment.notes.lower()


def test_invalid_humidity_and_direction_are_rejected():
    with pytest.raises(EnvironmentalObservationError):
        EnvironmentalObservation(source="x", relative_humidity_pct=120)
    with pytest.raises(EnvironmentalObservationError):
        EnvironmentalObservation(source="x", wind_direction_deg=360)
