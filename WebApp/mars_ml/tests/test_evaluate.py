from __future__ import annotations

import numpy as np
import pytest

from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    PixelDisplacement,
)
from mars_ml.training.evaluate import (
    metric_displacement_error,
    segmentation_metrics,
    evaluate_segmentation,
    displacement_error,
)


def test_segmentation_metrics_on_known_overlap():
    prediction = np.array([[1, 1], [0, 0]], dtype=bool)
    reference = np.array([[1, 0], [1, 0]], dtype=bool)
    metrics = segmentation_metrics(prediction, reference)
    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["true_negative"] == 1
    assert metrics["iou"] == pytest.approx(1 / 3)
    assert metrics["dice"] == pytest.approx(0.5)
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)


def test_aggregate_segmentation_metrics():
    prediction = np.array([[1, 1], [0, 0]], dtype=bool)
    reference = np.array([[1, 0], [1, 0]], dtype=bool)
    aggregate = evaluate_segmentation([prediction, prediction], [reference, reference])
    assert aggregate["image_count"] == 2
    assert aggregate["iou"] == pytest.approx(1 / 3)
    assert aggregate["counts"]["true_positive"] == 2


def test_displacement_errors_pixels_and_metric():
    estimate = PixelDisplacement(dx_px=10, dy_px=0, magnitude_px=10, azimuth_deg=90, method="test")
    reference = PixelDisplacement(dx_px=7, dy_px=4, magnitude_px=np.hypot(7, 4), azimuth_deg=60.255, method="truth")
    errors = displacement_error(estimate, reference)
    assert errors["vector_error_px"] == pytest.approx(5.0)
    assert errors["absolute_magnitude_error_px"] == pytest.approx(abs(10 - np.hypot(7, 4)))
    assert errors["angular_error_deg"] == pytest.approx(29.745, abs=1e-3)

    metric_estimate = MetricDisplacement(10, 0, 10, 90, (1.0, 1.0), "test")
    metric_reference = MetricDisplacement(7, 4, np.hypot(7, 4), 60.255, (1.0, 1.0), "truth")
    metric_errors = metric_displacement_error(metric_estimate, metric_reference)
    assert metric_errors["vector_error_m"] == pytest.approx(5.0)
