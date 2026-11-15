"""Subpixel translation estimation with phase correlation.

The returned vector is the shift of the moving image relative to the reference
image. ``dx_px`` points east and ``dy_px`` points north, so the image row axis is
inverted. A low peak or insufficient overlap makes the estimate unreliable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mars_ml.computer_vision.image_io import normalize_image, validate_image_array


class CorrelationError(ValueError):
    """Raised when phase correlation cannot be computed."""


@dataclass(frozen=True)
class CorrelationConfig:
    max_shift_fraction: float = 0.45
    min_peak: float = 0.08
    min_overlap_fraction: float = 0.2
    apply_window: bool = True

    def validate(self) -> None:
        if not 0 < self.max_shift_fraction < 1:
            raise CorrelationError("max_shift_fraction must be in (0, 1).")
        if not 0 <= self.min_peak <= 1:
            raise CorrelationError("min_peak must be in [0, 1].")
        if not 0 <= self.min_overlap_fraction <= 1:
            raise CorrelationError("min_overlap_fraction must be in [0, 1].")


@dataclass(frozen=True)
class CorrelationResult:
    dx_px: float
    dy_px: float
    magnitude_px: float
    azimuth_deg: float | None
    peak: float
    overlap_fraction: float
    reliable: bool
    method: str = "phase_correlation_fft"
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dx_px": self.dx_px,
            "dy_px": self.dy_px,
            "magnitude_px": self.magnitude_px,
            "azimuth_deg": self.azimuth_deg,
            "peak": self.peak,
            "overlap_fraction": self.overlap_fraction,
            "reliable": self.reliable,
            "method": self.method,
            "diagnostics": dict(self.diagnostics),
        }


def _gray_float(image: np.ndarray) -> np.ndarray:
    validate_image_array(image)
    normalized, _ = normalize_image(image)
    if normalized.ndim == 3:
        gray = (
            0.299 * normalized[..., 0]
            + 0.587 * normalized[..., 1]
            + 0.114 * normalized[..., 2]
        )
    else:
        gray = normalized
    return np.asarray(gray, dtype=np.float32)


def _azimuth(east: float, north: float) -> float | None:
    if abs(east) < 1e-12 and abs(north) < 1e-12:
        return None
    return float(np.degrees(np.arctan2(east, north)) % 360.0)


def _parabolic_offset(left: float, center: float, right: float) -> float:
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-12:
        return 0.0
    offset = 0.5 * (left - right) / denominator
    return float(np.clip(offset, -0.5, 0.5))


def _subpixel_peak(surface: np.ndarray, peak_y: int, peak_x: int) -> tuple[float, float]:
    height, width = surface.shape
    left = float(surface[peak_y, (peak_x - 1) % width])
    center = float(surface[peak_y, peak_x])
    right = float(surface[peak_y, (peak_x + 1) % width])
    up = float(surface[(peak_y - 1) % height, peak_x])
    down = float(surface[(peak_y + 1) % height, peak_x])
    return _parabolic_offset(left, center, right), _parabolic_offset(up, center, down)


def _overlap_fraction(
    valid: np.ndarray,
    dx_image: float,
    dy_image: float,
    *,
    max_shift: float,
) -> float:
    if abs(dx_image) > max_shift or abs(dy_image) > max_shift:
        return 0.0
    height, width = valid.shape
    reference_ys, reference_xs = np.nonzero(valid)
    moving_xs = np.rint(reference_xs + dx_image).astype(np.int64)
    moving_ys = np.rint(reference_ys + dy_image).astype(np.int64)
    inside = (
        (moving_xs >= 0)
        & (moving_xs < width)
        & (moving_ys >= 0)
        & (moving_ys < height)
    )
    if not np.any(inside):
        return 0.0
    reference_count = int(np.count_nonzero(valid))
    if reference_count == 0:
        return 0.0
    return float(np.count_nonzero(inside) / reference_count)


def phase_correlation_displacement(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    config: CorrelationConfig | None = None,
) -> CorrelationResult:
    cfg = config or CorrelationConfig()
    cfg.validate()
    reference_gray = _gray_float(reference)
    moving_gray = _gray_float(moving)
    if reference_gray.shape != moving_gray.shape:
        raise CorrelationError("Phase correlation requires images with identical dimensions.")
    if valid_mask is None:
        valid = np.ones(reference_gray.shape, dtype=bool)
    else:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != reference_gray.shape:
            raise CorrelationError("valid_mask must match image dimensions.")
    if np.count_nonzero(valid) < 16:
        raise CorrelationError("At least 16 valid pixels are required.")

    reference_work = reference_gray.copy()
    moving_work = moving_gray.copy()
    mean_reference = float(reference_work[valid].mean())
    mean_moving = float(moving_work[valid].mean())
    reference_work = np.where(valid, reference_work - mean_reference, 0.0)
    moving_work = np.where(valid, moving_work - mean_moving, 0.0)
    if cfg.apply_window:
        window = np.outer(np.hanning(reference_work.shape[0]), np.hanning(reference_work.shape[1]))
        reference_work = reference_work * window
        moving_work = moving_work * window

    reference_spectrum = np.fft.fft2(reference_work)
    moving_spectrum = np.fft.fft2(moving_work)
    cross_power = reference_spectrum * np.conj(moving_spectrum)
    magnitude = np.abs(cross_power)
    cross_power = np.divide(
        cross_power,
        magnitude,
        out=np.zeros_like(cross_power),
        where=magnitude > 1e-12,
    )
    correlation = np.real(np.fft.ifft2(cross_power))
    surface = np.fft.fftshift(correlation)
    center_y = surface.shape[0] // 2
    center_x = surface.shape[1] // 2
    peak_index = int(np.argmax(surface))
    peak_y, peak_x = np.unravel_index(peak_index, surface.shape)
    peak_value = float(surface[peak_y, peak_x])
    offset_x, offset_y = _subpixel_peak(surface, int(peak_y), int(peak_x))
    dx_image = float(peak_x - center_x) + offset_x
    dy_image = float(peak_y - center_y) + offset_y
    max_shift = cfg.max_shift_fraction * min(reference_gray.shape)
    overlap = _overlap_fraction(valid, dx_image, dy_image, max_shift=max_shift)
    reliable = bool(
        peak_value >= cfg.min_peak
        and overlap >= cfg.min_overlap_fraction
        and abs(dx_image) <= max_shift
        and abs(dy_image) <= max_shift
    )
    return CorrelationResult(
        dx_px=dx_image,
        dy_px=-dy_image,
        magnitude_px=float(np.hypot(dx_image, dy_image)),
        azimuth_deg=_azimuth(dx_image, -dy_image),
        peak=peak_value,
        overlap_fraction=overlap,
        reliable=reliable,
        diagnostics={
            "max_shift_px": max_shift,
            "subpixel_offset_xy": [offset_x, offset_y],
            "valid_pixels": int(np.count_nonzero(valid)),
            "window_applied": cfg.apply_window,
        },
    )
