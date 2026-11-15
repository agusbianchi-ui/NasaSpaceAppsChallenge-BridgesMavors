"""Compare two geometries without calling the difference migration.

Mask changes, crest shifts and orientation changes are diagnostics. They can
support or contradict a displacement estimate, but they are not independent
evidence of dune-body migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mars_ml.computer_vision.displacement_detection import (
    PixelDisplacement,
    angular_difference_degrees,
    centroid_displacement,
    mask_change,
    pixels_to_meters,
)
from mars_ml.computer_vision.dune_crests import CrestResult


class GeometryComparisonError(ValueError):
    """Raised when geometries cannot be compared."""


@dataclass(frozen=True)
class GeometryComparison:
    status: str
    reliable: bool
    iou: float | None
    dice: float | None
    area_delta_px: int
    centroid: PixelDisplacement | None
    centroid_dx_m: float | None
    centroid_dy_m: float | None
    centroid_distance_m: float | None
    orientation_difference_deg: float | None
    crest_length_delta_px: int | None
    chamfer_distance_px: float | None
    chamfer_distance_m: float | None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reliable": self.reliable,
            "iou": self.iou,
            "dice": self.dice,
            "area_delta_px": self.area_delta_px,
            "centroid": self.centroid.as_dict() if self.centroid else None,
            "centroid_dx_m": self.centroid_dx_m,
            "centroid_dy_m": self.centroid_dy_m,
            "centroid_distance_m": self.centroid_distance_m,
            "orientation_difference_deg": self.orientation_difference_deg,
            "crest_length_delta_px": self.crest_length_delta_px,
            "chamfer_distance_px": self.chamfer_distance_px,
            "chamfer_distance_m": self.chamfer_distance_m,
            "diagnostics": dict(self.diagnostics),
        }


def _binary(mask: np.ndarray) -> np.ndarray:
    value = np.asarray(mask)
    if value.ndim != 2:
        raise GeometryComparisonError("Masks must be 2D.")
    return value.astype(bool)


def _chamfer(reference: np.ndarray, moving: np.ndarray) -> float | None:
    if not np.any(reference) or not np.any(moving):
        return None
    reference_distance = cv2.distanceTransform((~reference).astype(np.uint8), cv2.DIST_L2, 5)
    moving_distance = cv2.distanceTransform((~moving).astype(np.uint8), cv2.DIST_L2, 5)
    forward = float(np.mean(reference_distance[moving]))
    backward = float(np.mean(moving_distance[reference]))
    return 0.5 * (forward + backward)


def compare_masks(
    reference_mask: np.ndarray,
    moving_mask: np.ndarray,
    *,
    meters_per_pixel: float | tuple[float, float] | None = None,
    reference_orientation_deg: float | None = None,
    moving_orientation_deg: float | None = None,
) -> GeometryComparison:
    reference = _binary(reference_mask)
    moving = _binary(moving_mask)
    if reference.shape != moving.shape:
        raise GeometryComparisonError("Masks must have identical shapes.")
    change = mask_change(reference, moving, meters_per_pixel=meters_per_pixel)
    centroid = centroid_displacement(reference, moving)
    dx_m = dy_m = distance_m = None
    if meters_per_pixel is not None and centroid.reliable:
        dx_m, dy_m = pixels_to_meters(centroid.dx_px, centroid.dy_px, meters_per_pixel)
        distance_m = float(np.hypot(dx_m, dy_m))
    orientation_difference = (
        angular_difference_degrees(reference_orientation_deg, moving_orientation_deg)
        if reference_orientation_deg is not None and moving_orientation_deg is not None
        else None
    )
    chamfer_px = _chamfer(reference, moving)
    chamfer_m = None
    if chamfer_px is not None and meters_per_pixel is not None:
        scale = (
            float(meters_per_pixel)
            if np.isscalar(meters_per_pixel)
            else float(np.sqrt(float(meters_per_pixel[0]) * float(meters_per_pixel[1])))
        )
        chamfer_m = chamfer_px * scale
    reliable = bool(centroid.reliable and change["union_px"] > 0)
    return GeometryComparison(
        status="geometry_compared" if reliable else "geometry_unreliable",
        reliable=reliable,
        iou=change["iou"],
        dice=change["dice"],
        area_delta_px=int(change["area_difference_px"]),
        centroid=centroid,
        centroid_dx_m=dx_m,
        centroid_dy_m=dy_m,
        centroid_distance_m=distance_m,
        orientation_difference_deg=orientation_difference,
        crest_length_delta_px=None,
        chamfer_distance_px=chamfer_px,
        chamfer_distance_m=chamfer_m,
        diagnostics={"mask_change": change},
    )


def compare_crests(
    reference: CrestResult,
    moving: CrestResult,
    *,
    meters_per_pixel: float | tuple[float, float] | None = None,
) -> GeometryComparison:
    reference_mask = _binary(reference.skeleton)
    moving_mask = _binary(moving.skeleton)
    if reference_mask.shape != moving_mask.shape:
        raise GeometryComparisonError("Crest skeletons must have identical shapes.")
    change = mask_change(reference_mask, moving_mask, meters_per_pixel=meters_per_pixel)
    centroid = centroid_displacement(reference_mask, moving_mask)
    dx_m = dy_m = distance_m = None
    if meters_per_pixel is not None and centroid.reliable:
        dx_m, dy_m = pixels_to_meters(centroid.dx_px, centroid.dy_px, meters_per_pixel)
        distance_m = float(np.hypot(dx_m, dy_m))
    orientation_difference = (
        angular_difference_degrees(reference.orientation_deg, moving.orientation_deg)
        if reference.orientation_deg is not None and moving.orientation_deg is not None
        else None
    )
    chamfer_px = _chamfer(reference_mask, moving_mask)
    chamfer_m = None
    if chamfer_px is not None and meters_per_pixel is not None:
        scale = (
            float(meters_per_pixel)
            if np.isscalar(meters_per_pixel)
            else float(np.sqrt(float(meters_per_pixel[0]) * float(meters_per_pixel[1])))
        )
        chamfer_m = chamfer_px * scale
    reliable = bool(centroid.reliable and reference.length_px > 0 and moving.length_px > 0)
    return GeometryComparison(
        status="crest_geometry_compared" if reliable else "crest_geometry_unreliable",
        reliable=reliable,
        iou=change["iou"],
        dice=change["dice"],
        area_delta_px=int(change["area_difference_px"]),
        centroid=centroid,
        centroid_dx_m=dx_m,
        centroid_dy_m=dy_m,
        centroid_distance_m=distance_m,
        orientation_difference_deg=orientation_difference,
        crest_length_delta_px=int(moving.length_px - reference.length_px),
        chamfer_distance_px=chamfer_px,
        chamfer_distance_m=chamfer_m,
        diagnostics={
            "reference_length_px": reference.length_px,
            "moving_length_px": moving.length_px,
            "mask_change": change,
        },
    )
