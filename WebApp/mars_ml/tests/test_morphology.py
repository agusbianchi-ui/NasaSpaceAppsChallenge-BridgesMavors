from __future__ import annotations

import numpy as np
import pytest

from mars_ml.aeolian_dynamics.dune_morphology import (
    MorphologyError,
    extract_morphology,
    morphological_change,
)
from mars_ml.tests.synthetic import ellipse_mask


def test_ellipse_morphology_has_expected_geometry():
    mask = ellipse_mask(120, 160, center=(80, 60), axes=(50, 25), angle=0)
    features = extract_morphology(mask)
    assert features.area_px > 1000
    assert features.perimeter_px > 0
    assert features.centroid_x_px == pytest.approx(80, abs=1.0)
    assert features.centroid_y_px == pytest.approx(60, abs=1.0)
    assert features.aspect_ratio is not None and features.aspect_ratio > 1.3
    assert features.orientation_deg is not None
    assert min(abs(features.orientation_deg - 90), 180 - abs(features.orientation_deg - 90)) < 10
    assert features.circularity is not None
    assert features.solidity is not None
    assert features.mean_curvature_per_px is not None


def test_metric_morphology_requires_a_scale_to_appear():
    mask = ellipse_mask(80, 80, center=(40, 40), axes=(20, 10))
    pixel_features = extract_morphology(mask)
    metric_features = extract_morphology(mask, meters_per_pixel=(10.0, 10.0))
    assert "area_m2" not in pixel_features.metrics
    assert metric_features.metrics["area_m2"] == pytest.approx(pixel_features.area_px * 100.0)


def test_empty_mask_raises():
    with pytest.raises(MorphologyError):
        extract_morphology(np.zeros((20, 20), dtype=bool))


def test_feature_vector_encodes_missing_values_as_nan():
    features = extract_morphology(ellipse_mask(40, 40, center=(20, 20), axes=(8, 4)))
    vector = features.feature_vector()
    assert vector.shape == (13,)
    assert not np.isnan(vector[0])


def test_morphological_change_reports_centroid_offset():
    reference = extract_morphology(ellipse_mask(100, 100, center=(40, 50), axes=(12, 8)))
    moving = extract_morphology(ellipse_mask(100, 100, center=(50, 53), axes=(12, 8)))
    change = morphological_change(reference, moving, meters_per_pixel=10.0)
    assert change["centroid_dx_px"] == pytest.approx(10.0, abs=1.0)
    assert change["centroid_dy_px"] == pytest.approx(-3.0, abs=1.0)
    assert change["centroid_distance_m"] is not None
