from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from mars_ml.inference.dune_analysis import (
    DuneAnalysisConfig,
    run_analysis,
)
from mars_ml.tests.synthetic import ellipse_mask, textured_scene, translate


def _write_observation(directory, reference, moving, reference_mask, moving_mask):
    directory.mkdir(parents=True, exist_ok=True)
    reference_path = directory / "reference.png"
    moving_path = directory / "moving.png"
    reference_mask_path = directory / "reference_mask.png"
    moving_mask_path = directory / "moving_mask.png"
    cv2.imwrite(str(reference_path), reference)
    cv2.imwrite(str(moving_path), moving)
    cv2.imwrite(str(reference_mask_path), reference_mask.astype(np.uint8) * 255)
    cv2.imwrite(str(moving_mask_path), moving_mask.astype(np.uint8) * 255)
    return reference_path, moving_path, reference_mask_path, moving_mask_path


def test_end_to_end_analysis_with_masks_and_dates(tmp_path):
    reference = textured_scene(160, 160, seed=21)
    moving = translate(reference, 9.0, -5.0)
    reference_mask = ellipse_mask(160, 160, center=(70, 80), axes=(30, 18), angle=15)
    moving_mask = translate(reference_mask.astype(np.uint8) * 255, 9.0, -5.0) > 127
    paths = _write_observation(tmp_path / "inputs", reference, moving, reference_mask, moving_mask)
    output = tmp_path / "outputs"
    result = run_analysis(
        *paths[:2],
        output,
        reference_mask_path=paths[2],
        moving_mask_path=paths[3],
        reference_datetime="2020-01-01T10:00:00Z",
        moving_datetime="2021-01-01T10:00:00Z",
        config=DuneAnalysisConfig(meters_per_pixel=10.0, use_flow=False),
    )
    assert result["registration"]["reliable"] is True
    assert result["displacement"] is not None
    assert result["displacement"]["reliable"] is True
    assert result["displacement"]["metric_centroid"] is not None
    assert abs(result["displacement"]["centroid"]["dx_px"]) < 2.0
    assert abs(result["displacement"]["centroid"]["dy_px"]) < 2.0
    assert result["status"] == "analysis_complete"
    assert result["migration"] is not None
    assert result["reference_morphology"] is not None
    assert (output / "analysis_report.json").exists()
    payload = json.loads((output / "analysis_report.json").read_text(encoding="utf-8"))
    assert payload["status"] == result["status"]
    assert payload["scientific_status"] == "research_pipeline_unvalidated"


def test_unreliable_registration_withholds_displacement(tmp_path):
    reference = np.zeros((96, 96), dtype=np.uint8)
    moving = np.zeros((96, 96), dtype=np.uint8)
    reference_mask = ellipse_mask(96, 96, center=(48, 48), axes=(20, 12))
    moving_mask = reference_mask.copy()
    paths = _write_observation(tmp_path / "inputs", reference, moving, reference_mask, moving_mask)
    result = run_analysis(
        *paths[:2],
        tmp_path / "outputs",
        reference_mask_path=paths[2],
        moving_mask_path=paths[3],
        reference_datetime="2020-01-01T00:00:00Z",
        moving_datetime="2021-01-01T00:00:00Z",
        config=DuneAnalysisConfig(
            meters_per_pixel=10.0,
            use_flow=False,
            save_visualizations=False,
        ),
    )
    assert result["status"] == "registration_unreliable"
    assert result["displacement"] is None
    assert result["migration"] is None
    assert result["registration"]["reliable"] is False
