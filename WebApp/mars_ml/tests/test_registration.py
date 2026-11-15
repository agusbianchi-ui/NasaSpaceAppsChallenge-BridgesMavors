from __future__ import annotations

import numpy as np

from mars_ml.computer_vision.image_registration import (
    RegistrationConfig,
    register_images,
    warp_to_reference,
)
from mars_ml.tests.synthetic import textured_scene, translate


def test_registration_recovers_a_known_translation():
    reference = textured_scene()
    moving = translate(reference, 12.0, -7.0)
    result = register_images(reference, moving)
    assert result.reliable, result.message
    assert result.inliers >= result.matches * 0.5 or result.inliers >= 12
    assert result.rms_error_px is not None and result.rms_error_px <= 3.0
    aligned, valid = warp_to_reference(moving, result.transform, reference.shape[:2])
    assert np.any(valid)
    mse = float(np.mean((aligned.astype(float) - reference.astype(float))[valid] ** 2))
    original = float(np.mean((moving.astype(float) - reference.astype(float)) ** 2))
    assert mse < original


def test_registration_refuses_a_featureless_pair():
    reference = np.zeros((128, 128), dtype=np.uint8)
    moving = np.zeros((128, 128), dtype=np.uint8)
    result = register_images(reference, moving)
    assert not result.reliable
    assert result.message


def test_registration_respects_disabled_fallback():
    reference = np.zeros((64, 64), dtype=np.uint8)
    moving = np.zeros((64, 64), dtype=np.uint8)
    result = register_images(
        reference,
        moving,
        config=RegistrationConfig(allow_phase_correlation=False),
    )
    assert not result.reliable
    assert result.method == "orb_homography"
