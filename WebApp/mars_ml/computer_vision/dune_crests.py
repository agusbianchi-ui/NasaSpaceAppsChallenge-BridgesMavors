"""Crest and ridge extraction from dune imagery.

Crests are image ridges, not dune-body segmentation and not migration labels.
The extractor is deterministic and uses only NumPy and OpenCV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import normalize_image, validate_image_array


class CrestExtractionError(ValueError):
    """Raised when crest extraction cannot be performed."""


@dataclass(frozen=True)
class CrestConfig:
    gaussian_sigma: float = 1.4
    threshold_percentile: float = 88.0
    min_response: float = 0.02
    min_component_px: int = 12
    min_length_px: int = 20
    polarity: str = "bright"
    max_thinning_iterations: int = 80

    def validate(self) -> None:
        if self.gaussian_sigma <= 0:
            raise CrestExtractionError("gaussian_sigma must be positive.")
        if not 50.0 <= self.threshold_percentile < 100.0:
            raise CrestExtractionError("threshold_percentile must be in [50, 100).")
        if not 0.0 <= self.min_response <= 1.0:
            raise CrestExtractionError("min_response must be in [0, 1].")
        if self.min_component_px < 1 or self.min_length_px < 1:
            raise CrestExtractionError("Minimum sizes must be positive.")
        if self.polarity not in {"bright", "dark"}:
            raise CrestExtractionError("polarity must be 'bright' or 'dark'.")
        if self.max_thinning_iterations < 1:
            raise CrestExtractionError("max_thinning_iterations must be positive.")


@dataclass(frozen=True)
class CrestResult:
    skeleton: np.ndarray
    ridge_response: np.ndarray
    threshold: float
    length_px: int
    orientation_deg: float | None
    orientation_strength: float | None
    component_count: int
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.skeleton.ndim != 2 or self.ridge_response.ndim != 2:
            raise CrestExtractionError("Crest outputs must be 2D.")
        if self.skeleton.shape != self.ridge_response.shape:
            raise CrestExtractionError("Crest outputs must share a shape.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "length_px": self.length_px,
            "orientation_deg": self.orientation_deg,
            "orientation_strength": self.orientation_strength,
            "component_count": self.component_count,
            "threshold": self.threshold,
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


def _ridge_response(gray: np.ndarray, sigma: float, polarity: str) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)
    hxx = cv2.Sobel(blurred, cv2.CV_32F, 2, 0, ksize=3)
    hyy = cv2.Sobel(blurred, cv2.CV_32F, 0, 2, ksize=3)
    hxy = cv2.Sobel(blurred, cv2.CV_32F, 1, 1, ksize=3)
    trace = hxx + hyy
    discriminant = np.sqrt(((hxx - hyy) * 0.5) ** 2 + hxy**2)
    lambda_max = trace * 0.5 + discriminant
    lambda_min = trace * 0.5 - discriminant
    if polarity == "bright":
        response = np.maximum(0.0, -np.minimum(lambda_max, lambda_min))
    else:
        response = np.maximum(0.0, np.maximum(lambda_max, lambda_min))
    maximum = float(np.max(response)) if response.size else 0.0
    if maximum > 0:
        response = response / maximum
    return np.asarray(response, dtype=np.float32)


def _zhang_suen(mask: np.ndarray, max_iterations: int) -> np.ndarray:
    image = np.asarray(mask, dtype=np.uint8).copy()
    for _ in range(max_iterations):
        changed = False
        for step in (0, 1):
            padded = np.pad(image, 1, mode="constant")
            p2 = padded[:-2, 1:-1]
            p3 = padded[:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, :-2]
            p8 = padded[1:-1, :-2]
            p9 = padded[:-2, :-2]
            neighbours = (p2, p3, p4, p5, p6, p7, p8, p9)
            neighbor_count = sum(neighbour.astype(np.int16) for neighbour in neighbours)
            transitions = sum(
                ((neighbours[index] == 0) & (neighbours[(index + 1) % 8] == 1)).astype(np.int16)
                for index in range(8)
            )
            base = (
                (image == 1)
                & (neighbor_count >= 2)
                & (neighbor_count <= 6)
                & (transitions == 1)
            )
            if step == 0:
                remove = base & ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                remove = base & ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)
            if np.any(remove):
                image[remove] = 0
                changed = True
        if not changed:
            break
    return image.astype(bool)


def _remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    output = np.zeros_like(mask, dtype=bool)
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= min_area:
            output |= labels == label
    return output


def _orientation(skeleton: np.ndarray) -> tuple[float | None, float | None]:
    ys, xs = np.nonzero(skeleton)
    if xs.size < 3:
        return None, None
    coordinates = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    centered = coordinates - coordinates.mean(axis=0)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 0.0)
    major = eigenvectors[:, order[0]]
    east = float(major[0])
    north = float(-major[1])
    if abs(east) < 1e-12 and abs(north) < 1e-12:
        orientation = None
    else:
        orientation = float(np.degrees(np.arctan2(east, north)) % 180.0)
    strength = (
        float((eigenvalues[0] - eigenvalues[1]) / eigenvalues[0])
        if eigenvalues[0] > 0
        else None
    )
    return orientation, strength


def extract_crests(
    image: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    config: CrestConfig | None = None,
) -> CrestResult:
    cfg = config or CrestConfig()
    cfg.validate()
    gray = _gray_float(image)
    if valid_mask is not None:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != gray.shape:
            raise CrestExtractionError("valid_mask must match image dimensions.")
    else:
        valid = np.ones(gray.shape, dtype=bool)
    if not np.any(valid):
        raise CrestExtractionError("Image has no valid pixels.")
    response = _ridge_response(gray, cfg.gaussian_sigma, cfg.polarity)
    response[~valid] = 0.0
    valid_response = response[valid]
    threshold = float(np.percentile(valid_response, cfg.threshold_percentile))
    threshold = max(threshold, cfg.min_response)
    candidate = (response >= threshold) & valid
    candidate = _remove_small_components(candidate, cfg.min_component_px)
    skeleton = _zhang_suen(candidate, cfg.max_thinning_iterations)
    skeleton = _remove_small_components(skeleton, cfg.min_component_px)
    length = int(np.count_nonzero(skeleton))
    component_count = int(
        cv2.connectedComponents(skeleton.astype(np.uint8), connectivity=8)[0] - 1
    )
    orientation, strength = _orientation(skeleton)
    if length < cfg.min_length_px:
        skeleton = np.zeros_like(skeleton, dtype=bool)
        length = 0
        component_count = 0
        orientation = None
        strength = None
    return CrestResult(
        skeleton=skeleton,
        ridge_response=response,
        threshold=threshold,
        length_px=length,
        orientation_deg=orientation,
        orientation_strength=strength,
        component_count=component_count,
        diagnostics={
            "polarity": cfg.polarity,
            "threshold_percentile": cfg.threshold_percentile,
            "valid_fraction": float(np.mean(valid)),
            "candidate_pixels": int(np.count_nonzero(candidate)),
        },
    )
