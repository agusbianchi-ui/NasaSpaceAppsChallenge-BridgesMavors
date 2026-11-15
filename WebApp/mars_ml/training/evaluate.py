"""Evaluation metrics for segmentation, registration and displacement.

These functions only compute metrics from supplied predictions and references.
Running them is required before reporting any number; the module itself does not
contain results or claim that an evaluation was performed.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    PixelDisplacement,
    angular_difference_degrees,
    pixels_to_meters,
)
from mars_ml.computer_vision.image_registration import RegistrationResult


class EvaluationError(ValueError):
    """Raised when predictions and references are incompatible."""


def _binary_pair(prediction: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    predicted = np.asarray(prediction).astype(bool)
    truth = np.asarray(reference).astype(bool)
    if predicted.shape != truth.shape:
        raise EvaluationError("Prediction and reference must have identical shapes.")
    return predicted, truth


def segmentation_confusion(
    prediction: np.ndarray,
    reference: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
) -> dict[str, int]:
    predicted, truth = _binary_pair(prediction, reference)
    if valid_mask is not None:
        valid = np.asarray(valid_mask).astype(bool)
        if valid.shape != predicted.shape:
            raise EvaluationError("valid_mask must match the segmentation shape.")
        predicted = predicted[valid]
        truth = truth[valid]
    return {
        "true_positive": int(np.count_nonzero(predicted & truth)),
        "false_positive": int(np.count_nonzero(predicted & ~truth)),
        "false_negative": int(np.count_nonzero(~predicted & truth)),
        "true_negative": int(np.count_nonzero(~predicted & ~truth)),
    }


def segmentation_metrics(
    prediction: np.ndarray,
    reference: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    counts = segmentation_confusion(prediction, reference, valid_mask=valid_mask)
    tp = counts["true_positive"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    union = tp + fp + fn
    iou = tp / union if union else None
    dice_denominator = 2 * tp + fp + fn
    dice = (2 * tp / dice_denominator) if dice_denominator else None
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    precision = tp / precision_denominator if precision_denominator else None
    recall = tp / recall_denominator if recall_denominator else None
    return {
        **counts,
        "iou": iou,
        "dice": dice,
        "precision": precision,
        "recall": recall,
    }


def evaluate_segmentation(
    predictions: Iterable[np.ndarray],
    references: Iterable[np.ndarray],
) -> dict[str, Any]:
    """Micro-aggregated metrics over a collection of masks."""

    prediction_list = list(predictions)
    reference_list = list(references)
    if len(prediction_list) != len(reference_list):
        raise EvaluationError("Prediction and reference counts differ.")
    if not prediction_list:
        raise EvaluationError("No predictions were supplied.")
    totals = {"true_positive": 0, "false_positive": 0, "false_negative": 0, "true_negative": 0}
    per_image: list[dict[str, Any]] = []
    for prediction, reference in zip(prediction_list, reference_list):
        counts = segmentation_confusion(prediction, reference)
        for key in totals:
            totals[key] += counts[key]
        per_image.append(segmentation_metrics(prediction, reference))
    tp = totals["true_positive"]
    fp = totals["false_positive"]
    fn = totals["false_negative"]
    union = tp + fp + fn
    dice_denominator = 2 * tp + fp + fn
    return {
        "counts": totals,
        "iou": tp / union if union else None,
        "dice": (2 * tp / dice_denominator) if dice_denominator else None,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "image_count": len(per_image),
        "per_image": per_image,
    }


def registration_metrics(result: RegistrationResult) -> dict[str, Any]:
    return {
        "method": result.method,
        "reliable": result.reliable,
        "matches": result.matches,
        "inliers": result.inliers,
        "inlier_ratio": result.inlier_ratio,
        "rms_error_px": result.rms_error_px,
        "median_error_px": result.median_error_px,
        "phase_response": result.phase_response,
    }


def displacement_error(
    estimate: PixelDisplacement,
    reference: PixelDisplacement,
) -> dict[str, float | None]:
    """Vector and angular error for two pixel displacements."""

    vector_error = float(np.hypot(estimate.dx_px - reference.dx_px, estimate.dy_px - reference.dy_px))
    magnitude_error = float(abs(estimate.magnitude_px - reference.magnitude_px))
    angular_error = (
        angular_difference_degrees(estimate.azimuth_deg, reference.azimuth_deg)
        if estimate.azimuth_deg is not None and reference.azimuth_deg is not None
        else None
    )
    return {
        "vector_error_px": vector_error,
        "absolute_magnitude_error_px": magnitude_error,
        "angular_error_deg": angular_error,
    }


def metric_displacement_error(
    estimate: MetricDisplacement,
    reference: MetricDisplacement,
) -> dict[str, float | None]:
    vector_error = float(np.hypot(estimate.dx_m - reference.dx_m, estimate.dy_m - reference.dy_m))
    magnitude_error = float(abs(estimate.magnitude_m - reference.magnitude_m))
    angular_error = (
        angular_difference_degrees(estimate.azimuth_deg, reference.azimuth_deg)
        if estimate.azimuth_deg is not None and reference.azimuth_deg is not None
        else None
    )
    return {
        "vector_error_m": vector_error,
        "absolute_magnitude_error_m": magnitude_error,
        "angular_error_deg": angular_error,
    }


def evaluate_displacement_pixels(
    estimates: Iterable[PixelDisplacement],
    references: Iterable[PixelDisplacement],
) -> dict[str, Any]:
    estimate_list = list(estimates)
    reference_list = list(references)
    if len(estimate_list) != len(reference_list):
        raise EvaluationError("Estimate and reference counts differ.")
    if not estimate_list:
        raise EvaluationError("No displacement estimates were supplied.")
    errors = [displacement_error(estimate, reference) for estimate, reference in zip(estimate_list, reference_list)]
    vector_errors = np.array([error["vector_error_px"] for error in errors], dtype=np.float64)
    magnitude_errors = np.array(
        [error["absolute_magnitude_error_px"] for error in errors], dtype=np.float64
    )
    angular_errors = np.array(
        [error["angular_error_deg"] for error in errors if error["angular_error_deg"] is not None],
        dtype=np.float64,
    )
    return {
        "count": len(errors),
        "mean_vector_error_px": float(vector_errors.mean()),
        "rmse_vector_error_px": float(np.sqrt(np.mean(vector_errors**2))),
        "mean_absolute_magnitude_error_px": float(magnitude_errors.mean()),
        "mean_angular_error_deg": float(angular_errors.mean()) if angular_errors.size else None,
        "per_sample": errors,
    }


def evaluate_displacement_metric(
    estimates: Iterable[MetricDisplacement],
    references: Iterable[MetricDisplacement],
) -> dict[str, Any]:
    estimate_list = list(estimates)
    reference_list = list(references)
    if len(estimate_list) != len(reference_list):
        raise EvaluationError("Estimate and reference counts differ.")
    if not estimate_list:
        raise EvaluationError("No displacement estimates were supplied.")
    errors = [metric_displacement_error(estimate, reference) for estimate, reference in zip(estimate_list, reference_list)]
    vector_errors = np.array([error["vector_error_m"] for error in errors], dtype=np.float64)
    magnitude_errors = np.array(
        [error["absolute_magnitude_error_m"] for error in errors], dtype=np.float64
    )
    angular_errors = np.array(
        [error["angular_error_deg"] for error in errors if error["angular_error_deg"] is not None],
        dtype=np.float64,
    )
    return {
        "count": len(errors),
        "mean_vector_error_m": float(vector_errors.mean()),
        "rmse_vector_error_m": float(np.sqrt(np.mean(vector_errors**2))),
        "mean_absolute_magnitude_error_m": float(magnitude_errors.mean()),
        "mean_angular_error_deg": float(angular_errors.mean()) if angular_errors.size else None,
        "per_sample": errors,
    }


def scale_aware_error(
    estimate: PixelDisplacement,
    reference: PixelDisplacement,
    *,
    meters_per_pixel: float | tuple[float, float],
) -> dict[str, float | None]:
    """Pixel and metric errors together, using one explicit scale."""

    pixel = displacement_error(estimate, reference)
    estimated_dx_m, estimated_dy_m = pixels_to_meters(
        estimate.dx_px, estimate.dy_px, meters_per_pixel
    )
    reference_dx_m, reference_dy_m = pixels_to_meters(
        reference.dx_px, reference.dy_px, meters_per_pixel
    )
    metric_vector = float(np.hypot(estimated_dx_m - reference_dx_m, estimated_dy_m - reference_dy_m))
    metric_magnitude = float(
        abs(np.hypot(estimated_dx_m, estimated_dy_m) - np.hypot(reference_dx_m, reference_dy_m))
    )
    return {
        **pixel,
        "vector_error_m": metric_vector,
        "absolute_magnitude_error_m": metric_magnitude,
    }
