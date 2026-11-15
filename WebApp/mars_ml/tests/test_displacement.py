from __future__ import annotations

import numpy as np
import pytest

from mars_ml.computer_vision.displacement_detection import (
    ScaleUnavailableError,
    angular_difference_degrees,
    centroid_displacement,
    estimate_displacement,
    farneback_displacement,
    lucas_kanade_displacement,
    mask_change,
    metric_displacement,
    pixels_to_meters,
)
from mars_ml.computer_vision.image_registration import RegistrationResult
from mars_ml.tests.synthetic import ellipse_mask, textured_scene, translate


def test_centroid_displacement_reports_east_and_north():
    height, width = 120, 140
    reference = ellipse_mask(height, width, center=(50, 60), axes=(12, 8))
    moving = ellipse_mask(height, width, center=(60, 55), axes=(12, 8))
    result = centroid_displacement(reference, moving)
    assert result.reliable
    assert result.dx_px == pytest.approx(10.0, abs=0.5)
    assert result.dy_px == pytest.approx(5.0, abs=0.5)
    assert result.magnitude_px == pytest.approx(np.hypot(10, 5), abs=0.5)
    assert result.azimuth_deg is not None
    assert 0 <= result.azimuth_deg < 360


def test_empty_mask_makes_centroid_unreliable():
    reference = np.zeros((40, 40), dtype=bool)
    moving = np.ones((40, 40), dtype=bool)
    result = centroid_displacement(reference, moving)
    assert not result.reliable


def test_pixels_to_meters_requires_positive_explicit_scale():
    assert pixels_to_meters(10, -4, 5.0) == (50.0, -20.0)
    assert pixels_to_meters(10, -4, (2.0, 4.0)) == (20.0, -16.0)
    with pytest.raises(ScaleUnavailableError):
        pixels_to_meters(1, 1, 0.0)


def test_metric_displacement_is_absent_without_scale():
    reference = ellipse_mask(100, 100, center=(40, 50), axes=(10, 8))
    moving = ellipse_mask(100, 100, center=(44, 50), axes=(10, 8))
    pixel = centroid_displacement(reference, moving)
    assert metric_displacement(pixel, None) is None
    metric = metric_displacement(pixel, 10.0)
    assert metric is not None
    assert metric.magnitude_m == pytest.approx(pixel.magnitude_px * 10.0, rel=1e-6)


def test_displacement_is_withheld_when_registration_is_unreliable():
    reference = textured_scene(96, 96)
    moving = translate(reference, 5, 3)
    masks = ellipse_mask(96, 96, center=(48, 48), axes=(20, 12))
    failed = RegistrationResult(
        transform=None,
        method="orb_homography",
        reliable=False,
        message="synthetic failure",
    )
    report = estimate_displacement(reference, moving, masks, masks, alignment=failed)
    assert report.status == "registration_unreliable"
    assert report.centroid is None


def test_farneback_tracks_a_known_texture_shift():
    reference = textured_scene(128, 128)
    moving = translate(reference, 8.0, -5.0)
    result = farneback_displacement(reference, moving, min_samples=100)
    assert result.reliable
    assert result.dx_px == pytest.approx(8.0, abs=2.0)
    assert result.dy_px == pytest.approx(5.0, abs=2.0)


def test_lucas_kanade_tracks_a_known_texture_shift():
    reference = textured_scene(128, 128)
    moving = translate(reference, 6.0, -4.0)
    result = lucas_kanade_displacement(reference, moving, min_samples=10)
    assert result.reliable
    assert result.dx_px == pytest.approx(6.0, abs=2.0)
    assert result.dy_px == pytest.approx(4.0, abs=2.0)


def test_mask_change_reports_iou_and_area():
    reference = ellipse_mask(100, 100, center=(40, 50), axes=(15, 10))
    moving = ellipse_mask(100, 100, center=(50, 50), axes=(15, 10))
    change = mask_change(reference, moving, meters_per_pixel=10.0)
    assert change["reference_area_px"] > 0
    assert change["moving_area_px"] > 0
    assert change["iou"] is not None
    assert change["pixel_area_m2"] == pytest.approx(100.0)
    assert change["reference_area_m2"] == pytest.approx(change["reference_area_px"] * 100.0)


def test_angular_difference_wraps_at_360():
    assert angular_difference_degrees(350.0, 10.0) == pytest.approx(20.0)
    assert angular_difference_degrees(10.0, 350.0) == pytest.approx(20.0)
    assert angular_difference_degrees(0.0, 180.0) == pytest.approx(180.0)
