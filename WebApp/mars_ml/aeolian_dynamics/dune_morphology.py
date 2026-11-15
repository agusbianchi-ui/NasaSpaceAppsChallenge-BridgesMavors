"""Morphological descriptors for segmented dune candidates.

Feature conventions:
- Pixel coordinates use ``x`` to the right and ``y`` downward.
- ``orientation_deg`` is the compass azimuth (clockwise from north) of the
  major axis, reduced to ``[0, 180)`` because an axis has no direction.
- Metric features are produced only when an explicit metres-per-pixel scale is
  supplied. No CRS unit is guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mars_ml.computer_vision.displacement_detection import (
    angular_difference_degrees,
    pixels_to_meters,
)


class MorphologyError(ValueError):
    """Raised when morphology cannot be computed from a mask."""


@dataclass(frozen=True)
class MorphologyFeatures:
    area_px: int
    perimeter_px: float
    centroid_x_px: float
    centroid_y_px: float
    orientation_deg: float | None
    major_axis_px: float | None
    minor_axis_px: float | None
    aspect_ratio: float | None
    circularity: float | None
    solidity: float | None
    mean_curvature_per_px: float | None
    p95_curvature_per_px: float | None
    max_curvature_per_px: float | None
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    component_count: int
    metrics: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "area_px": self.area_px,
            "perimeter_px": self.perimeter_px,
            "centroid_x_px": self.centroid_x_px,
            "centroid_y_px": self.centroid_y_px,
            "orientation_deg": self.orientation_deg,
            "major_axis_px": self.major_axis_px,
            "minor_axis_px": self.minor_axis_px,
            "aspect_ratio": self.aspect_ratio,
            "circularity": self.circularity,
            "solidity": self.solidity,
            "mean_curvature_per_px": self.mean_curvature_per_px,
            "p95_curvature_per_px": self.p95_curvature_per_px,
            "max_curvature_per_px": self.max_curvature_per_px,
            "bbox": {
                "x": self.bbox_x,
                "y": self.bbox_y,
                "width": self.bbox_width,
                "height": self.bbox_height,
            },
            "component_count": self.component_count,
            "metrics": dict(self.metrics),
        }

    def feature_vector(self) -> np.ndarray:
        """Stable numeric vector for future ML experiments.

        Missing values are encoded as ``nan`` so imputation is explicit.
        """

        def value(item: float | None) -> float:
            return float("nan") if item is None else float(item)

        return np.array(
            [
                self.area_px,
                self.perimeter_px,
                self.centroid_x_px,
                self.centroid_y_px,
                value(self.orientation_deg),
                value(self.major_axis_px),
                value(self.minor_axis_px),
                value(self.aspect_ratio),
                value(self.circularity),
                value(self.solidity),
                value(self.mean_curvature_per_px),
                value(self.p95_curvature_per_px),
                value(self.max_curvature_per_px),
            ],
            dtype=np.float64,
        )


def _largest_component(mask: np.ndarray) -> tuple[np.ndarray, int, list[int]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if count <= 1:
        raise MorphologyError("Mask has no foreground component.")
    areas = [int(stats[label, cv2.CC_STAT_AREA]) for label in range(1, count)]
    largest_label = 1 + int(np.argmax(areas))
    component = labels == largest_label
    return component, count - 1, areas


def _curvature_stats(contour: np.ndarray) -> tuple[float | None, float | None, float | None]:
    points = contour.reshape(-1, 2).astype(np.float64)
    if len(points) < 5:
        return None, None, None
    closed = np.vstack([points, points[:1]])
    vectors = np.diff(closed, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    valid = lengths > 1e-9
    if np.count_nonzero(valid) < 3:
        return None, None, None
    vectors = vectors[valid]
    lengths = lengths[valid]
    unit = vectors / lengths[:, None]
    angles = []
    for index in range(len(unit)):
        first = unit[index - 1]
        second = unit[index]
        dot = float(np.clip(np.dot(first, second), -1.0, 1.0))
        angle = float(np.arccos(dot))
        step = float(0.5 * (lengths[index - 1] + lengths[index]))
        if step > 1e-9:
            angles.append(angle / step)
    if not angles:
        return None, None, None
    values = np.asarray(angles, dtype=np.float64)
    return float(np.mean(values)), float(np.percentile(values, 95)), float(np.max(values))


def _pca_geometry(component: np.ndarray) -> tuple[float | None, float | None, float | None, float | None]:
    ys, xs = np.nonzero(component)
    if xs.size < 3:
        return None, None, None, None
    coordinates = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    centered = coordinates - coordinates.mean(axis=0)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 0.0)
    major_vector = eigenvectors[:, order[0]]
    east = float(major_vector[0])
    north = float(-major_vector[1])
    if abs(east) < 1e-12 and abs(north) < 1e-12:
        orientation = None
    else:
        orientation = float(np.degrees(np.arctan2(east, north)) % 180.0)
    major_axis = float(4.0 * np.sqrt(eigenvalues[0]))
    minor_axis = float(4.0 * np.sqrt(eigenvalues[1]))
    aspect = major_axis / minor_axis if minor_axis > 1e-9 else None
    return orientation, major_axis, minor_axis, aspect


def extract_morphology(
    mask: np.ndarray,
    *,
    meters_per_pixel: float | tuple[float, float] | None = None,
    largest_only: bool = True,
) -> MorphologyFeatures:
    """Extract descriptors from a binary mask.

    ``largest_only`` selects the largest connected component by default. Set it
    to ``False`` to merge all components into one connected footprint for
    perimeter/contour calculations (individual components are still reported in
    ``component_count``).
    """

    mask_bool = np.asarray(mask)
    if mask_bool.ndim != 2:
        raise MorphologyError("Mask must be 2D.")
    mask_bool = mask_bool.astype(bool)
    if not np.any(mask_bool):
        raise MorphologyError("Mask is empty.")

    component, component_count, component_areas = _largest_component(mask_bool)
    working = component if largest_only else mask_bool
    contours, _ = cv2.findContours(working.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise MorphologyError("No contour could be extracted from the mask.")
    contour = max(contours, key=cv2.contourArea)

    area = float(cv2.contourArea(contour))
    if area <= 0:
        area = float(np.count_nonzero(working))
    perimeter = float(cv2.arcLength(contour, True))
    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        ys, xs = np.nonzero(working)
        centroid_x = float(xs.mean())
        centroid_y = float(ys.mean())
    else:
        centroid_x = float(moments["m10"] / moments["m00"])
        centroid_y = float(moments["m01"] / moments["m00"])

    orientation, major_axis, minor_axis, aspect = _pca_geometry(component if largest_only else working)
    circularity = 4.0 * np.pi * area / (perimeter**2) if perimeter > 0 else None
    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = area / hull_area if hull_area > 0 else None
    mean_curvature, p95_curvature, max_curvature = _curvature_stats(contour)
    bbox_x, bbox_y, bbox_width, bbox_height = cv2.boundingRect(contour)

    metrics: dict[str, float] = {}
    if meters_per_pixel is not None:
        if np.isscalar(meters_per_pixel):
            scale_x = scale_y = float(meters_per_pixel)
        else:
            scale_x = float(meters_per_pixel[0])
            scale_y = float(meters_per_pixel[1])
        if not all(np.isfinite(v) and v > 0 for v in (scale_x, scale_y)):
            raise MorphologyError("Metres per pixel must be finite and positive.")
        pixel_area = scale_x * scale_y
        mean_scale = float(np.sqrt(pixel_area))
        metrics = {
            "area_m2": area * pixel_area,
            "perimeter_m": perimeter * mean_scale,
            "major_axis_m": major_axis * mean_scale if major_axis is not None else None,
            "minor_axis_m": minor_axis * mean_scale if minor_axis is not None else None,
        }
        metrics = {key: value for key, value in metrics.items() if value is not None}

    return MorphologyFeatures(
        area_px=int(round(area)),
        perimeter_px=perimeter,
        centroid_x_px=centroid_x,
        centroid_y_px=centroid_y,
        orientation_deg=orientation,
        major_axis_px=major_axis,
        minor_axis_px=minor_axis,
        aspect_ratio=aspect,
        circularity=float(circularity) if circularity is not None else None,
        solidity=float(solidity) if solidity is not None else None,
        mean_curvature_per_px=mean_curvature,
        p95_curvature_per_px=p95_curvature,
        max_curvature_per_px=max_curvature,
        bbox_x=int(bbox_x),
        bbox_y=int(bbox_y),
        bbox_width=int(bbox_width),
        bbox_height=int(bbox_height),
        component_count=int(component_count),
        metrics=metrics,
    )


def morphological_change(
    reference: MorphologyFeatures,
    moving: MorphologyFeatures,
    *,
    meters_per_pixel: float | tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Compare two morphology snapshots without implying causality."""

    centroid_dx_px = moving.centroid_x_px - reference.centroid_x_px
    centroid_dy_px = -(moving.centroid_y_px - reference.centroid_y_px)
    output: dict[str, Any] = {
        "area_delta_px": moving.area_px - reference.area_px,
        "area_relative_change": (
            (moving.area_px - reference.area_px) / reference.area_px
            if reference.area_px
            else None
        ),
        "perimeter_delta_px": moving.perimeter_px - reference.perimeter_px,
        "centroid_dx_px": centroid_dx_px,
        "centroid_dy_px": centroid_dy_px,
        "centroid_distance_px": float(np.hypot(centroid_dx_px, centroid_dy_px)),
        "orientation_difference_deg": (
            angular_difference_degrees(reference.orientation_deg, moving.orientation_deg)
            if reference.orientation_deg is not None and moving.orientation_deg is not None
            else None
        ),
        "aspect_ratio_delta": (
            moving.aspect_ratio - reference.aspect_ratio
            if reference.aspect_ratio is not None and moving.aspect_ratio is not None
            else None
        ),
    }
    if meters_per_pixel is not None:
        dx_m, dy_m = pixels_to_meters(centroid_dx_px, centroid_dy_px, meters_per_pixel)
        output["centroid_dx_m"] = dx_m
        output["centroid_dy_m"] = dy_m
        output["centroid_distance_m"] = float(np.hypot(dx_m, dy_m))
    return output
