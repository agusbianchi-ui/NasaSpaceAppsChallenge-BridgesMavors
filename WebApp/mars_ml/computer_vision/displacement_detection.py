"""Apparent 2D displacement between aligned observations.

Two families of estimates are reported:
- Mask-centroid displacement: bulk change of the segmented dune footprint.
- Dense/sparse optical flow: apparent motion of image texture (which may track
  ripples or surface patterns rather than the dune body).

They are not interchangeable. Agreement is measured and reported. Conversion to
metres only occurs when the caller supplies a verified metres-per-pixel scale.
Pixel displacement is never silently treated as geographic displacement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import normalize_image, validate_image_array
from mars_ml.computer_vision.image_registration import (
    RegistrationResult,
    warp_to_reference,
)


class DisplacementError(RuntimeError):
    """Raised when displacement cannot be computed from the inputs."""


class ScaleUnavailableError(DisplacementError):
    """Raised when a metric conversion is requested without a known scale."""


@dataclass(frozen=True)
class PixelDisplacement:
    """Displacement in image pixels.

    ``dx_px`` is positive toward image +x (east in a north-up image);
    ``dy_px`` is positive toward geographic north, i.e. the negative of the
    downward image row axis.
    """

    dx_px: float
    dy_px: float
    magnitude_px: float
    azimuth_deg: float | None
    method: str
    reliable: bool = True
    support: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dx_px": self.dx_px,
            "dy_px": self.dy_px,
            "magnitude_px": self.magnitude_px,
            "azimuth_deg": self.azimuth_deg,
            "method": self.method,
            "reliable": self.reliable,
            "support": self.support,
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class MetricDisplacement:
    dx_m: float
    dy_m: float
    magnitude_m: float
    azimuth_deg: float | None
    meters_per_pixel: tuple[float, float]
    method: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "dx_m": self.dx_m,
            "dy_m": self.dy_m,
            "magnitude_m": self.magnitude_m,
            "azimuth_deg": self.azimuth_deg,
            "meters_per_pixel": list(self.meters_per_pixel),
            "method": self.method,
        }


@dataclass(frozen=True)
class DisplacementReport:
    status: str
    reliable: bool
    centroid: PixelDisplacement | None
    farneback: PixelDisplacement | None
    lucas_kanade: PixelDisplacement | None
    metric_centroid: MetricDisplacement | None
    mask_change: dict[str, Any]
    consistency: dict[str, Any]
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reliable": self.reliable,
            "centroid": self.centroid.as_dict() if self.centroid else None,
            "farneback": self.farneback.as_dict() if self.farneback else None,
            "lucas_kanade": self.lucas_kanade.as_dict() if self.lucas_kanade else None,
            "metric_centroid": self.metric_centroid.as_dict() if self.metric_centroid else None,
            "mask_change": dict(self.mask_change),
            "consistency": dict(self.consistency),
            "notes": self.notes,
        }


def azimuth_degrees(east: float, north: float) -> float | None:
    """Compass azimuth (clockwise from north) for an east/north vector."""

    if not np.isfinite(east) or not np.isfinite(north):
        return None
    if abs(east) < 1e-12 and abs(north) < 1e-12:
        return None
    return float(np.degrees(np.arctan2(east, north)) % 360.0)


def angular_difference_degrees(first: float, second: float) -> float:
    """Smallest absolute angular difference in ``[0, 180]``."""

    if not np.isfinite(first) or not np.isfinite(second):
        raise ValueError("Azimuths must be finite.")
    return float(abs((first - second + 180.0) % 360.0 - 180.0))


def pixels_to_meters(
    dx_px: float,
    dy_px: float,
    meters_per_pixel: float | tuple[float, float],
) -> tuple[float, float]:
    """Convert pixel offsets to metres using an explicit, verified scale.

    ``meters_per_pixel`` may be a scalar or an ``(x, y)`` pair. Geographic
    resolutions in degrees are not accepted here; convert to a metric CRS first.
    """

    if isinstance(meters_per_pixel, (tuple, list, np.ndarray)):
        if len(meters_per_pixel) != 2:
            raise ScaleUnavailableError("meters_per_pixel must be a scalar or an (x, y) pair.")
        scale_x, scale_y = float(meters_per_pixel[0]), float(meters_per_pixel[1])
        scale = (scale_x, scale_y)
    else:
        scale_x = scale_y = float(meters_per_pixel)
        scale = (scale_x, scale_y)
    if not all(np.isfinite(v) and v > 0 for v in scale):
        raise ScaleUnavailableError("Metres per pixel must be finite and positive.")
    return float(dx_px) * scale_x, float(dy_px) * scale_y


def metric_displacement(
    displacement: PixelDisplacement,
    meters_per_pixel: float | tuple[float, float] | None,
) -> MetricDisplacement | None:
    """Return a metric displacement only when a scale is supplied."""

    if meters_per_pixel is None:
        return None
    dx_m, dy_m = pixels_to_meters(displacement.dx_px, displacement.dy_px, meters_per_pixel)
    scale = (
        (float(meters_per_pixel), float(meters_per_pixel))
        if np.isscalar(meters_per_pixel)
        else (float(meters_per_pixel[0]), float(meters_per_pixel[1]))
    )
    return MetricDisplacement(
        dx_m=dx_m,
        dy_m=dy_m,
        magnitude_m=float(np.hypot(dx_m, dy_m)),
        azimuth_deg=displacement.azimuth_deg,
        meters_per_pixel=scale,
        method=displacement.method,
    )


def _centroid(mask: np.ndarray) -> tuple[float, float] | None:
    mask_bool = np.asarray(mask, dtype=bool)
    if mask_bool.ndim != 2:
        raise DisplacementError("Masks must be 2D.")
    count = int(np.count_nonzero(mask_bool))
    if count == 0:
        return None
    ys, xs = np.nonzero(mask_bool)
    return float(xs.mean()), float(ys.mean())


def centroid_displacement(reference_mask: np.ndarray, moving_mask: np.ndarray) -> PixelDisplacement:
    """Bulk displacement between two binary masks."""

    if reference_mask.shape != moving_mask.shape:
        raise DisplacementError("Masks must have identical shapes.")
    first = _centroid(reference_mask)
    second = _centroid(moving_mask)
    if first is None or second is None:
        return PixelDisplacement(
            dx_px=0.0,
            dy_px=0.0,
            magnitude_px=0.0,
            azimuth_deg=None,
            method="mask_centroid",
            reliable=False,
            support=0,
            diagnostics={"reason": "At least one mask is empty."},
        )
    dx = second[0] - first[0]
    dy_image = second[1] - first[1]
    dy_north = -dy_image
    magnitude = float(np.hypot(dx, dy_north))
    support = int(min(np.count_nonzero(reference_mask), np.count_nonzero(moving_mask)))
    return PixelDisplacement(
        dx_px=float(dx),
        dy_px=float(dy_north),
        magnitude_px=magnitude,
        azimuth_deg=azimuth_degrees(dx, dy_north),
        method="mask_centroid",
        reliable=True,
        support=support,
        diagnostics={
            "reference_centroid_xy": [first[0], first[1]],
            "moving_centroid_xy": [second[0], second[1]],
        },
    )


def _gray(image: np.ndarray) -> np.ndarray:
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


def _robust_vector(
    east: np.ndarray,
    north: np.ndarray,
    *,
    method: str,
    min_samples: int,
    min_inlier_fraction: float,
) -> PixelDisplacement:
    if east.size == 0:
        return PixelDisplacement(
            dx_px=0.0,
            dy_px=0.0,
            magnitude_px=0.0,
            azimuth_deg=None,
            method=method,
            reliable=False,
            support=0,
            diagnostics={"reason": "No valid samples."},
        )
    median_east = float(np.median(east))
    median_north = float(np.median(north))
    residual = np.hypot(east - median_east, north - median_north)
    mad = float(np.median(np.abs(residual - np.median(residual))))
    threshold = max(1.0, float(np.median(residual) + 3.0 * 1.4826 * mad))
    inliers = residual <= threshold
    inlier_fraction = float(np.mean(inliers))
    magnitude = float(np.hypot(median_east, median_north))
    reliable = bool(east.size >= min_samples and inlier_fraction >= min_inlier_fraction)
    return PixelDisplacement(
        dx_px=median_east,
        dy_px=median_north,
        magnitude_px=magnitude,
        azimuth_deg=azimuth_degrees(median_east, median_north),
        method=method,
        reliable=reliable,
        support=int(east.size),
        diagnostics={
            "inlier_fraction": inlier_fraction,
            "residual_threshold_px": threshold,
            "p95_magnitude_px": float(np.percentile(np.hypot(east, north), 95)),
            "min_samples": min_samples,
        },
    )


def farneback_displacement(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    min_samples: int = 500,
    min_inlier_fraction: float = 0.4,
) -> PixelDisplacement:
    """Dense Farneback flow summarized by a robust median vector."""

    validate_image_array(reference)
    validate_image_array(moving)
    if reference.shape[:2] != moving.shape[:2]:
        raise DisplacementError("Optical flow requires images on the same grid.")
    reference_u8 = np.round(_gray(reference) * 255).astype(np.uint8)
    moving_u8 = np.round(_gray(moving) * 255).astype(np.uint8)
    flow = cv2.calcOpticalFlowFarneback(
        reference_u8,
        moving_u8,
        None,
        pyr_scale=0.5,
        levels=4,
        winsize=21,
        iterations=5,
        poly_n=7,
        poly_sigma=1.5,
        flags=0,
    )
    if valid_mask is None:
        valid = np.ones(reference.shape[:2], dtype=bool)
    else:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != reference.shape[:2]:
            raise DisplacementError("valid_mask must match image dimensions.")
    east = flow[..., 0][valid].astype(np.float64)
    north = -flow[..., 1][valid].astype(np.float64)
    return _robust_vector(
        east,
        north,
        method="farneback_optical_flow",
        min_samples=min_samples,
        min_inlier_fraction=min_inlier_fraction,
    )


def lucas_kanade_displacement(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    max_corners: int = 5000,
    min_samples: int = 20,
    min_inlier_fraction: float = 0.5,
    forward_backward_threshold_px: float = 1.0,
) -> PixelDisplacement:
    """Sparse Lucas-Kanade flow with a forward-backward consistency check."""

    validate_image_array(reference)
    validate_image_array(moving)
    if reference.shape[:2] != moving.shape[:2]:
        raise DisplacementError("Optical flow requires images on the same grid.")
    reference_u8 = np.round(_gray(reference) * 255).astype(np.uint8)
    moving_u8 = np.round(_gray(moving) * 255).astype(np.uint8)
    feature_mask = None
    if valid_mask is not None:
        feature_mask = np.asarray(valid_mask, dtype=np.uint8) * 255
    features = cv2.goodFeaturesToTrack(
        reference_u8,
        maxCorners=max_corners,
        qualityLevel=0.01,
        minDistance=5,
        mask=feature_mask,
    )
    if features is None or len(features) < min_samples:
        return PixelDisplacement(
            dx_px=0.0,
            dy_px=0.0,
            magnitude_px=0.0,
            azimuth_deg=None,
            method="lucas_kanade",
            reliable=False,
            support=0 if features is None else len(features),
            diagnostics={"reason": "Insufficient trackable corners."},
        )
    next_points, status, _ = cv2.calcOpticalFlowPyrLK(reference_u8, moving_u8, features, None)
    back_points, back_status, _ = cv2.calcOpticalFlowPyrLK(moving_u8, reference_u8, next_points, None)
    if next_points is None or back_points is None:
        return PixelDisplacement(
            dx_px=0.0,
            dy_px=0.0,
            magnitude_px=0.0,
            azimuth_deg=None,
            method="lucas_kanade",
            reliable=False,
            diagnostics={"reason": "Optical flow returned no points."},
        )
    forward_backward_error = np.linalg.norm(
        (back_points - features).reshape(-1, 2), axis=1
    )
    keep = (
        (status.reshape(-1) == 1)
        & (back_status.reshape(-1) == 1)
        & (forward_backward_error <= forward_backward_threshold_px)
    )
    if not np.any(keep):
        return PixelDisplacement(
            dx_px=0.0,
            dy_px=0.0,
            magnitude_px=0.0,
            azimuth_deg=None,
            method="lucas_kanade",
            reliable=False,
            support=0,
            diagnostics={"reason": "No points passed the forward-backward check."},
        )
    deltas = (next_points - features).reshape(-1, 2)[keep]
    east = deltas[:, 0].astype(np.float64)
    north = -deltas[:, 1].astype(np.float64)
    result = _robust_vector(
        east,
        north,
        method="lucas_kanade",
        min_samples=min_samples,
        min_inlier_fraction=min_inlier_fraction,
    )
    diagnostics = dict(result.diagnostics)
    diagnostics["tracked_points"] = int(np.count_nonzero(keep))
    diagnostics["forward_backward_threshold_px"] = forward_backward_threshold_px
    return PixelDisplacement(
        dx_px=result.dx_px,
        dy_px=result.dy_px,
        magnitude_px=result.magnitude_px,
        azimuth_deg=result.azimuth_deg,
        method=result.method,
        reliable=result.reliable,
        support=result.support,
        diagnostics=diagnostics,
    )


def mask_change(
    reference_mask: np.ndarray,
    moving_mask: np.ndarray,
    *,
    meters_per_pixel: float | tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Area, overlap and boundary-change diagnostics for two masks."""

    if reference_mask.shape != moving_mask.shape:
        raise DisplacementError("Masks must have identical shapes.")
    first = np.asarray(reference_mask, dtype=bool)
    second = np.asarray(moving_mask, dtype=bool)
    area_first = int(np.count_nonzero(first))
    area_second = int(np.count_nonzero(second))
    intersection = int(np.count_nonzero(first & second))
    union = int(np.count_nonzero(first | second))
    iou = intersection / union if union else None
    dice = (2.0 * intersection / (area_first + area_second)) if (area_first + area_second) else None
    output: dict[str, Any] = {
        "reference_area_px": area_first,
        "moving_area_px": area_second,
        "area_difference_px": area_second - area_first,
        "area_relative_change": (area_second - area_first) / area_first if area_first else None,
        "intersection_px": intersection,
        "union_px": union,
        "iou": iou,
        "dice": dice,
        "symmetric_difference_px": union - intersection,
    }
    if meters_per_pixel is not None:
        if np.isscalar(meters_per_pixel):
            pixel_area = float(meters_per_pixel) ** 2
        else:
            pixel_area = float(meters_per_pixel[0]) * float(meters_per_pixel[1])
        output["pixel_area_m2"] = pixel_area
        output["reference_area_m2"] = area_first * pixel_area
        output["moving_area_m2"] = area_second * pixel_area
        output["area_difference_m2"] = (area_second - area_first) * pixel_area
    return output


def _consistency(
    centroid: PixelDisplacement | None,
    flow: PixelDisplacement | None,
    *,
    max_magnitude_difference_px: float = 5.0,
    max_azimuth_difference_deg: float = 45.0,
) -> dict[str, Any]:
    if centroid is None or flow is None or not centroid.reliable or not flow.reliable:
        return {
            "evaluated": False,
            "consistent": None,
            "reason": "One or both estimates are unavailable or unreliable.",
        }
    magnitude_difference = abs(centroid.magnitude_px - flow.magnitude_px)
    azimuth_difference = (
        angular_difference_degrees(centroid.azimuth_deg, flow.azimuth_deg)
        if centroid.azimuth_deg is not None and flow.azimuth_deg is not None
        else None
    )
    consistent = bool(
        magnitude_difference <= max_magnitude_difference_px
        and (
            azimuth_difference is None
            or azimuth_difference <= max_azimuth_difference_deg
        )
    )
    return {
        "evaluated": True,
        "consistent": consistent,
        "magnitude_difference_px": magnitude_difference,
        "azimuth_difference_deg": azimuth_difference,
        "max_magnitude_difference_px": max_magnitude_difference_px,
        "max_azimuth_difference_deg": max_azimuth_difference_deg,
    }


def estimate_displacement(
    reference: np.ndarray,
    moving: np.ndarray,
    reference_mask: np.ndarray,
    moving_mask: np.ndarray,
    *,
    alignment: RegistrationResult | None = None,
    meters_per_pixel: float | tuple[float, float] | None = None,
    use_flow: bool = True,
) -> DisplacementReport:
    """Estimate apparent 2D displacement under explicit safety gates.

    If a registration result is supplied and is not reliable, no displacement
    is computed. Metric values are only produced with an explicit scale.
    """

    if alignment is not None and not alignment.reliable:
        return DisplacementReport(
            status="registration_unreliable",
            reliable=False,
            centroid=None,
            farneback=None,
            lucas_kanade=None,
            metric_centroid=None,
            mask_change={},
            consistency={"evaluated": False, "consistent": None},
            notes="Displacement withheld because image registration was not reliable.",
        )
    if reference_mask.shape != moving_mask.shape:
        raise DisplacementError("Masks must have identical shapes.")
    if reference.shape[:2] != moving.shape[:2]:
        raise DisplacementError("Images must share a common reference grid before analysis.")

    overlap = None
    if alignment is not None and alignment.transform is not None:
        _, overlap_moving = warp_to_reference(np.ones(moving.shape[:2], dtype=np.uint8), alignment.transform, reference.shape[:2])
        overlap = overlap_moving & (reference_mask | moving_mask)
    centroid = centroid_displacement(reference_mask, moving_mask)
    farneback = None
    lucas_kanade = None
    if use_flow:
        farneback = farneback_displacement(reference, moving, valid_mask=overlap)
        lucas_kanade = lucas_kanade_displacement(reference, moving, valid_mask=overlap)
    consistency = _consistency(centroid, farneback)
    metric = metric_displacement(centroid, meters_per_pixel) if centroid.reliable else None
    reliable = bool(centroid.reliable and (consistency["consistent"] is not False))
    if not reliable and consistency["consistent"] is False:
        notes = (
            "Centroid and optical-flow estimates disagree. Review the masks, "
            "registration and surface texture before interpreting migration."
        )
    elif not reliable:
        notes = "Displacement estimates did not meet reliability requirements."
    else:
        notes = "Apparent 2D displacement only; no vertical motion or true dune flux is inferred."
    return DisplacementReport(
        status="ok" if reliable else "unreliable",
        reliable=reliable,
        centroid=centroid,
        farneback=farneback,
        lucas_kanade=lucas_kanade,
        metric_centroid=metric,
        mask_change=mask_change(reference_mask, moving_mask, meters_per_pixel=meters_per_pixel),
        consistency=consistency,
        notes=notes,
    )
