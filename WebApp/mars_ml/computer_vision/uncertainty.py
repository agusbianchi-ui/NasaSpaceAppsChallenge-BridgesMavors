"""Resampling and propagation utilities for displacement uncertainty.

Uncertainty is reported as an interval, never as false precision. The functions
assume the caller supplies independent samples or explicit standard errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np


class UncertaintyError(ValueError):
    """Raised when uncertainty cannot be estimated from the inputs."""


@dataclass(frozen=True)
class UncertaintyEstimate:
    value: float
    standard_error: float | None
    ci95_low: float | None
    ci95_high: float | None
    method: str
    sample_count: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not np.isfinite(self.value):
            raise UncertaintyError("Estimate value must be finite.")
        for name in ("standard_error", "ci95_low", "ci95_high"):
            value = getattr(self, name)
            if value is not None and not np.isfinite(value):
                raise UncertaintyError(f"{name} must be finite when supplied.")
        if self.standard_error is not None and self.standard_error < 0:
            raise UncertaintyError("standard_error cannot be negative.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "standard_error": self.standard_error,
            "ci95_low": self.ci95_low,
            "ci95_high": self.ci95_high,
            "method": self.method,
            "sample_count": self.sample_count,
            "diagnostics": dict(self.diagnostics),
        }


def bootstrap_estimate(
    values: Sequence[float] | np.ndarray,
    *,
    statistic: Callable[[np.ndarray], float] = np.median,
    n_resamples: int = 500,
    confidence: float = 0.95,
    seed: int = 0,
) -> UncertaintyEstimate:
    samples = np.asarray(values, dtype=np.float64)
    samples = samples[np.isfinite(samples)]
    if samples.size < 3:
        raise UncertaintyError("At least three finite samples are required.")
    if n_resamples < 50:
        raise UncertaintyError("n_resamples must be at least 50.")
    if not 0.5 < confidence < 1.0:
        raise UncertaintyError("confidence must be in (0.5, 1).")
    rng = np.random.default_rng(seed)
    draw = rng.choice(samples, size=(n_resamples, samples.size), replace=True)
    estimates = np.asarray([statistic(row) for row in draw], dtype=np.float64)
    estimates = estimates[np.isfinite(estimates)]
    if estimates.size < 2:
        raise UncertaintyError("Bootstrap produced too few finite estimates.")
    alpha = 1.0 - confidence
    return UncertaintyEstimate(
        value=float(statistic(samples)),
        standard_error=float(np.std(estimates, ddof=1)),
        ci95_low=float(np.percentile(estimates, 100 * alpha / 2)),
        ci95_high=float(np.percentile(estimates, 100 * (1 - alpha / 2))),
        method="bootstrap_percentile",
        sample_count=int(samples.size),
        diagnostics={"n_resamples": n_resamples, "confidence": confidence, "seed": seed},
    )


def bootstrap_displacement(
    east_px: Sequence[float] | np.ndarray,
    north_px: Sequence[float] | np.ndarray,
    *,
    n_resamples: int = 500,
    confidence: float = 0.95,
    seed: int = 0,
) -> dict[str, UncertaintyEstimate]:
    east = np.asarray(east_px, dtype=np.float64)
    north = np.asarray(north_px, dtype=np.float64)
    if east.shape != north.shape:
        raise UncertaintyError("East and north samples must share a shape.")
    finite = np.isfinite(east) & np.isfinite(north)
    east = east[finite]
    north = north[finite]
    if east.size < 3:
        raise UncertaintyError("At least three finite paired samples are required.")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, east.size, size=(n_resamples, east.size))
    median_east = np.median(east[indices], axis=1)
    median_north = np.median(north[indices], axis=1)
    median_magnitude = np.hypot(median_east, median_north)
    alpha = 1.0 - confidence
    outputs: dict[str, UncertaintyEstimate] = {}
    for name, samples, value in (
        ("dx_px", median_east, float(np.median(east))),
        ("dy_px", median_north, float(np.median(north))),
        ("magnitude_px", median_magnitude, float(np.hypot(np.median(east), np.median(north)))),
    ):
        finite_samples = samples[np.isfinite(samples)]
        outputs[name] = UncertaintyEstimate(
            value=value,
            standard_error=float(np.std(finite_samples, ddof=1)) if finite_samples.size > 1 else None,
            ci95_low=float(np.percentile(finite_samples, 100 * alpha / 2)),
            ci95_high=float(np.percentile(finite_samples, 100 * (1 - alpha / 2))),
            method="bootstrap_median_paired",
            sample_count=int(east.size),
            diagnostics={"n_resamples": n_resamples, "confidence": confidence, "seed": seed},
        )
    return outputs


def propagate_ratio_uncertainty(
    numerator: float,
    numerator_standard_error: float,
    denominator: float,
    denominator_standard_error: float,
) -> UncertaintyEstimate:
    if denominator == 0:
        raise UncertaintyError("Denominator cannot be zero.")
    if numerator_standard_error < 0 or denominator_standard_error < 0:
        raise UncertaintyError("Standard errors cannot be negative.")
    value = numerator / denominator
    relative = np.hypot(
        numerator_standard_error / abs(numerator) if numerator != 0 else 0.0,
        denominator_standard_error / abs(denominator) if denominator != 0 else 0.0,
    )
    standard_error = abs(value) * float(relative)
    return UncertaintyEstimate(
        value=float(value),
        standard_error=standard_error,
        ci95_low=float(value - 1.96 * standard_error),
        ci95_high=float(value + 1.96 * standard_error),
        method="first_order_ratio_propagation",
        sample_count=0,
        diagnostics={
            "numerator": numerator,
            "numerator_standard_error": numerator_standard_error,
            "denominator": denominator,
            "denominator_standard_error": denominator_standard_error,
        },
    )
