from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from mars_ml.aeolian_dynamics.environmental_observations import (
    EnvironmentalObservation,
)
from mars_ml.computer_vision.image_io import RasterImage, SpatialMetadata
from mars_ml.computer_vision.image_registration import RegistrationConfig
from mars_ml.inference.mars_sequence import (
    MarsSequenceConfig,
    MarsSequenceError,
    SequenceObservation,
    load_sequence_plan,
    main,
    run_mars_sequence,
    run_sequence_plan,
)
from mars_ml.tests.synthetic import dune_pair


def _sequence(crs: str | None = None):
    first, second, first_mask, second_mask = dune_pair(
        height=96, width=96, dx=6.0, dy=-2.0
    )
    metadata = SpatialMetadata(crs=crs)
    reference = SequenceObservation(
        "reference",
        "PRODUCT_A",
        "2020-01-01T00:00:00Z",
        RasterImage(first, metadata),
        first_mask,
    )
    moving = SequenceObservation(
        "moving",
        "PRODUCT_B",
        "2021-01-01T00:00:00Z",
        RasterImage(second, metadata),
        second_mask,
    )
    return reference, moving


def test_sequence_withholds_migration_without_scale():
    reference, moving = _sequence()
    result = run_mars_sequence(
        [reference, moving],
        config=MarsSequenceConfig(meters_per_pixel=None),
    )
    assert len(result.observations) == 2
    assert len(result.pairs) == 1
    pair = result.pairs[0]
    assert pair.status in {"analyzed", "displacement_only", "registration_unreliable"}
    if pair.migration is not None:
        assert not pair.migration.valid
        assert any("scale" in reason.lower() for reason in pair.reasons)


def test_sequence_with_scale_reports_positive_rate_when_registered():
    reference, moving = _sequence()
    result = run_mars_sequence(
        [reference, moving],
        config=MarsSequenceConfig(meters_per_pixel=10.0, include_geometry=True),
    )
    pair = result.pairs[0]
    assert pair.registration is not None
    if pair.registration.reliable:
        assert pair.displacement is not None
        assert pair.geometry is not None
        if pair.migration is not None and pair.migration.valid:
            assert pair.migration.rate_m_per_year > 0
            assert pair.status == "analyzed"


def test_sequence_registration_gate_on_crs_mismatch():
    first, second, first_mask, second_mask = dune_pair(
        height=96, width=96, dx=4.0, dy=0.0
    )
    reference = SequenceObservation(
        "reference",
        "PRODUCT_A",
        "2020-01-01T00:00:00Z",
        RasterImage(first, SpatialMetadata(crs="EPSG:32630")),
        first_mask,
    )
    moving = SequenceObservation(
        "moving",
        "PRODUCT_B",
        "2021-01-01T00:00:00Z",
        RasterImage(second, SpatialMetadata(crs="EPSG:32631")),
        second_mask,
    )
    result = run_mars_sequence(
        [reference, moving], config=MarsSequenceConfig(meters_per_pixel=10.0)
    )
    pair = result.pairs[0]
    assert pair.status == "registration_not_attempted"
    assert pair.registration.reliable is False
    assert pair.migration is None


def test_sequence_rejects_shape_mismatch_and_short_input():
    reference, moving = _sequence()
    with pytest.raises(MarsSequenceError):
        run_mars_sequence([reference])
    with pytest.raises(MarsSequenceError):
        MarsSequenceConfig(method="advancing_front").validate()
    with pytest.raises(MarsSequenceError):
        SequenceObservation(
            "bad",
            "PRODUCT_A",
            "2020-01-01T00:00:00Z",
            reference.image,
            np.zeros((4, 4), dtype=bool),
        )


def test_environment_is_attached_without_becoming_simultaneous_by_default():
    reference, moving = _sequence()
    environment = EnvironmentalObservation(
        source="Mars Climate Database",
        source_type="model",
        scene_id="PRODUCT_B",
        image_datetime_utc="2021-01-01T00:00:00Z",
        observation_datetime_utc="2021-01-01T02:00:00Z",
        wind_speed_m_s=4.0,
        wind_direction_deg=90.0,
        pressure_pa=600.0,
        temperature_k=210.0,
    )
    moving = SequenceObservation(
        moving.observation_id,
        moving.product_id,
        moving.datetime_utc,
        moving.image,
        moving.mask,
        environment,
    )
    result = run_mars_sequence(
        [reference, moving], config=MarsSequenceConfig(meters_per_pixel=10.0)
    )
    payload = result.pairs[0].environment
    assert payload is not None
    assert payload["source_type"] == "model"
    assert payload["simultaneous_with_image"] is False


def test_sequence_normalizes_dates_and_uses_registration_config():
    reference, moving = _sequence()
    result = run_mars_sequence(
        [reference, moving],
        config=MarsSequenceConfig(
            meters_per_pixel=10.0,
            registration=RegistrationConfig(
                min_matches=10000,
                min_inliers=10000,
                allow_phase_correlation=False,
            ),
        ),
    )
    assert result.observations[0]["datetime_utc"] == "2020-01-01T00:00:00+00:00"
    assert result.pairs[0].status == "registration_unreliable"
    assert result.pairs[0].migration is None

    with pytest.raises(MarsSequenceError):
        SequenceObservation(
            "naive",
            "PRODUCT_A",
            "2020-01-01T00:00:00",
            reference.image,
            reference.mask,
        )
    with pytest.raises(MarsSequenceError):
        SequenceObservation(
            "invalid",
            "PRODUCT_A",
            "not-a-date",
            reference.image,
            reference.mask,
        )


def test_sequence_plan_loader_and_runner(tmp_path):
    first, second, first_mask, second_mask = dune_pair(
        height=96, width=96, dx=6.0, dy=-2.0
    )
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    cv2.imwrite(str(inputs / "reference.png"), first)
    cv2.imwrite(str(inputs / "moving.png"), second)
    cv2.imwrite(str(inputs / "reference_mask.png"), first_mask.astype(np.uint8) * 255)
    cv2.imwrite(str(inputs / "moving_mask.png"), second_mask.astype(np.uint8) * 255)
    plan = {
        "config": {"meters_per_pixel": 10.0, "include_geometry": True},
        "observations": [
            {
                "observation_id": "reference",
                "product_id": "PRODUCT_A",
                "datetime_utc": "2020-01-01T00:00:00Z",
                "image": "inputs/reference.png",
                "mask": "inputs/reference_mask.png",
            },
            {
                "observation_id": "moving",
                "product_id": "PRODUCT_B",
                "datetime_utc": "2021-01-01T00:00:00Z",
                "image": "inputs/moving.png",
                "mask": "inputs/moving_mask.png",
                "environment": {
                    "source": "Mars Climate Database",
                    "source_type": "model",
                    "scene_id": "PRODUCT_B",
                    "observation_datetime_utc": "2021-01-01T02:00:00Z",
                    "wind_speed_m_s": 4.0,
                },
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    observations, config = load_sequence_plan(plan_path)
    assert len(observations) == 2
    assert observations[0].datetime_utc == "2020-01-01T00:00:00+00:00"
    assert config.meters_per_pixel == 10.0
    output = tmp_path / "outputs" / "sequence.json"
    report = run_sequence_plan(plan_path, output)
    assert output.exists()
    assert report["plan_path"] == str(plan_path.resolve())
    assert report["scientific_status"] == "research_pipeline_unvalidated"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["pair_count"] == 1
    assert main(["--plan", str(plan_path), "--output", str(output)]) == 0


def test_sequence_plan_requires_explicit_fields(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps({"observations": [{"observation_id": "only"}]}), encoding="utf-8"
    )
    with pytest.raises(MarsSequenceError):
        load_sequence_plan(plan_path)
    plan_path.write_text(
        json.dumps(
            {
                "observations": [
                    {"observation_id": "a"},
                    {"observation_id": "b"},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(MarsSequenceError):
        load_sequence_plan(plan_path)
