"""Image registration and alignment-quality gating.

Registration is treated as a prerequisite, not a detail. A transform is
returned together with match statistics and a ``reliable`` flag. Downstream
displacement code must refuse to report movement when this flag is false.

Methods:
- ORB feature matching + RANSAC homography (primary).
- Phase correlation (translation-only fallback) when the response is strong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import normalize_image, validate_image_array


class RegistrationError(RuntimeError):
    """Raised when registration cannot be attempted at all."""


@dataclass(frozen=True)
class RegistrationConfig:
    max_features: int = 5000
    match_ratio: float = 0.75
    ransac_reproj_threshold_px: float = 3.0
    min_matches: int = 20
    min_inliers: int = 12
    min_inlier_ratio: float = 0.3
    max_rms_error_px: float = 3.0
    min_phase_response: float = 0.12
    allow_phase_correlation: bool = True

    def validate(self) -> None:
        if self.max_features < 100:
            raise ValueError("max_features must be at least 100.")
        if not 0 < self.match_ratio < 1:
            raise ValueError("match_ratio must be in (0, 1).")
        if self.ransac_reproj_threshold_px <= 0:
            raise ValueError("ransac_reproj_threshold_px must be positive.")
        if self.min_matches < 4 or self.min_inliers < 4:
            raise ValueError("At least four matches and inliers are required.")
        if not 0 < self.min_inlier_ratio <= 1:
            raise ValueError("min_inlier_ratio must be in (0, 1].")
        if self.max_rms_error_px <= 0:
            raise ValueError("max_rms_error_px must be positive.")


@dataclass(frozen=True)
class RegistrationResult:
    transform: np.ndarray | None
    method: str
    reliable: bool
    matches: int = 0
    inliers: int = 0
    inlier_ratio: float = 0.0
    rms_error_px: float | None = None
    median_error_px: float | None = None
    phase_response: float | None = None
    message: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "reliable": self.reliable,
            "matches": self.matches,
            "inliers": self.inliers,
            "inlier_ratio": self.inlier_ratio,
            "rms_error_px": self.rms_error_px,
            "median_error_px": self.median_error_px,
            "phase_response": self.phase_response,
            "transform": self.transform.tolist() if self.transform is not None else None,
            "message": self.message,
            "diagnostics": dict(self.diagnostics),
        }


def _gray_float(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    validate_image_array(image)
    normalized, valid = normalize_image(image)
    if normalized.ndim == 3:
        gray = (
            0.299 * normalized[..., 0]
            + 0.587 * normalized[..., 1]
            + 0.114 * normalized[..., 2]
        )
    else:
        gray = normalized
    return np.asarray(gray, dtype=np.float32), valid


def _gray_u8(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray, valid = _gray_float(image)
    gray_u8 = np.round(np.clip(gray, 0, 1) * 255).astype(np.uint8)
    return gray_u8, valid


def _homography_is_plausible(transform: np.ndarray, shape: tuple[int, int]) -> bool:
    if transform is None or transform.shape != (3, 3) or not np.all(np.isfinite(transform)):
        return False
    determinant = float(np.linalg.det(transform))
    if not 0.02 <= abs(determinant) <= 50.0:
        return False
    height, width = shape
    corners = np.array(
        [[0, 0, 1], [width - 1, 0, 1], [width - 1, height - 1, 1], [0, height - 1, 1]],
        dtype=np.float64,
    ).T
    projected = transform @ corners
    if np.any(np.isclose(projected[2], 0)):
        return False
    projected_xy = projected[:2] / projected[2]
    margin = max(height, width)
    return bool(
        np.all(projected_xy[0] > -margin)
        and np.all(projected_xy[0] < width + margin)
        and np.all(projected_xy[1] > -margin)
        and np.all(projected_xy[1] < height + margin)
    )


def _orb_registration(
    reference: np.ndarray,
    moving: np.ndarray,
    config: RegistrationConfig,
) -> RegistrationResult:
    reference_gray, reference_valid = _gray_u8(reference)
    moving_gray, moving_valid = _gray_u8(moving)
    orb = cv2.ORB_create(nfeatures=config.max_features)
    reference_keypoints, reference_descriptors = orb.detectAndCompute(reference_gray, reference_valid.astype(np.uint8) * 255)
    moving_keypoints, moving_descriptors = orb.detectAndCompute(moving_gray, moving_valid.astype(np.uint8) * 255)

    if reference_descriptors is None or moving_descriptors is None:
        return RegistrationResult(
            transform=None,
            method="orb_homography",
            reliable=False,
            message="ORB found insufficient descriptors.",
        )

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    pairs = matcher.knnMatch(moving_descriptors, reference_descriptors, k=2)
    good: list[list[cv2.DMatch]] = []
    for pair in pairs:
        if len(pair) == 2 and pair[0].distance < config.match_ratio * pair[1].distance:
            good.append(pair)
    if len(good) < config.min_matches:
        return RegistrationResult(
            transform=None,
            method="orb_homography",
            reliable=False,
            matches=len(good),
            message=f"Only {len(good)} ratio-test matches; minimum is {config.min_matches}.",
        )

    moving_points = np.float32([moving_keypoints[m.queryIdx].pt for m, _ in good])
    reference_points = np.float32([reference_keypoints[m.trainIdx].pt for m, _ in good])
    transform, inlier_mask = cv2.findHomography(
        moving_points,
        reference_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=config.ransac_reproj_threshold_px,
        maxIters=5000,
        confidence=0.999,
    )
    if transform is None or inlier_mask is None:
        return RegistrationResult(
            transform=None,
            method="orb_homography",
            reliable=False,
            matches=len(good),
            message="RANSAC could not estimate a homography.",
        )

    inliers = int(np.count_nonzero(inlier_mask))
    inlier_ratio = inliers / max(1, len(good))
    errors = None
    if inliers >= 4:
        projected = cv2.perspectiveTransform(
            moving_points[inlier_mask.ravel().astype(bool)][None, ...], transform
        )[0]
        residuals = np.linalg.norm(projected - reference_points[inlier_mask.ravel().astype(bool)], axis=1)
        errors = residuals.astype(np.float64)
    rms = float(np.sqrt(np.mean(errors**2))) if errors is not None and errors.size else None
    median = float(np.median(errors)) if errors is not None and errors.size else None
    plausible = _homography_is_plausible(transform, reference.shape[:2])
    reliable = bool(
        plausible
        and inliers >= config.min_inliers
        and inlier_ratio >= config.min_inlier_ratio
        and rms is not None
        and rms <= config.max_rms_error_px
    )
    if not plausible:
        message = "Estimated homography failed the geometric sanity check."
    elif inliers < config.min_inliers:
        message = f"Only {inliers} RANSAC inliers; minimum is {config.min_inliers}."
    elif inlier_ratio < config.min_inlier_ratio:
        message = f"Inlier ratio {inlier_ratio:.2f} is below {config.min_inlier_ratio:.2f}."
    elif rms is None or rms > config.max_rms_error_px:
        message = f"Reprojection RMS {rms} px exceeds {config.max_rms_error_px} px."
    else:
        message = "Registration passed configured quality thresholds."
    return RegistrationResult(
        transform=transform.astype(np.float64),
        method="orb_homography",
        reliable=reliable,
        matches=len(good),
        inliers=inliers,
        inlier_ratio=float(inlier_ratio),
        rms_error_px=rms,
        median_error_px=median,
        message=message,
        diagnostics={"plausible_homography": plausible},
    )


def _translation_quality(reference: np.ndarray, moving: np.ndarray, transform: np.ndarray) -> float:
    aligned, valid = warp_to_reference(moving, transform, reference.shape[:2])
    if not np.any(valid):
        return float("inf")
    reference_float, _ = _gray_float(reference)
    aligned_float, _ = _gray_float(aligned)
    difference = (reference_float[valid] - aligned_float[valid]) ** 2
    return float(np.mean(difference))


def _phase_correlation_registration(
    reference: np.ndarray,
    moving: np.ndarray,
    config: RegistrationConfig,
) -> RegistrationResult:
    reference_gray, _ = _gray_float(reference)
    moving_gray, _ = _gray_float(moving)
    if reference_gray.shape != moving_gray.shape:
        return RegistrationResult(
            transform=None,
            method="phase_correlation",
            reliable=False,
            message="Phase correlation requires equal image dimensions.",
        )
    window = cv2.createHanningWindow((reference_gray.shape[1], reference_gray.shape[0]), cv2.CV_32F)
    shift, response = cv2.phaseCorrelate(reference_gray, moving_gray, window)
    dx, dy = float(shift[0]), float(shift[1])
    candidates = [
        np.array([[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]]),
        np.array([[1.0, 0.0, -dx], [0.0, 1.0, -dy], [0.0, 0.0, 1.0]]),
    ]
    costs = [_translation_quality(reference, moving, candidate) for candidate in candidates]
    best_index = int(np.argmin(costs))
    transform = candidates[best_index]
    reliable = bool(response >= config.min_phase_response and np.isfinite(costs[best_index]))
    return RegistrationResult(
        transform=transform,
        method="phase_correlation",
        reliable=reliable,
        phase_response=float(response),
        message=(
            "Translation-only fallback accepted."
            if reliable
            else f"Phase-correlation response {response:.3f} is below {config.min_phase_response:.3f}."
        ),
        diagnostics={
            "shift_x_px": float(transform[0, 2]),
            "shift_y_px": float(transform[1, 2]),
            "aligned_mse": float(costs[best_index]),
        },
    )


def register_images(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    config: RegistrationConfig | None = None,
) -> RegistrationResult:
    """Estimate the transform that maps ``moving`` onto ``reference``.

    Returns a :class:`RegistrationResult`. Never raise simply because alignment
    is poor; consumers must inspect ``reliable``.
    """

    cfg = config or RegistrationConfig()
    cfg.validate()
    validate_image_array(reference)
    validate_image_array(moving)

    primary = _orb_registration(reference, moving, cfg)
    if primary.reliable:
        return primary
    if not cfg.allow_phase_correlation:
        return primary
    fallback = _phase_correlation_registration(reference, moving, cfg)
    if fallback.reliable:
        fallback.diagnostics["orb_failure_message"] = primary.message
        return fallback
    if primary.matches or primary.inliers:
        return primary
    return fallback


def warp_to_reference(
    moving: np.ndarray,
    transform: np.ndarray,
    reference_shape: tuple[int, int],
    *,
    border_value: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Warp ``moving`` into the reference grid and return ``(image, valid_mask)``."""

    validate_image_array(moving)
    if transform is None or np.asarray(transform).shape != (3, 3):
        raise RegistrationError("A 3x3 transform is required for warping.")
    height, width = reference_shape
    if height < 1 or width < 1:
        raise RegistrationError("Reference shape must be positive.")
    is_color = moving.ndim == 3
    source = moving.astype(np.float32)
    aligned = cv2.warpPerspective(
        source,
        np.asarray(transform, dtype=np.float64),
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )
    source_valid = np.ones(moving.shape[:2], dtype=np.uint8)
    valid = cv2.warpPerspective(
        source_valid,
        np.asarray(transform, dtype=np.float64),
        (width, height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    ) > 0
    if not is_color:
        aligned = np.asarray(aligned, dtype=np.float32)
    return aligned, valid


def registration_quality_report(result: RegistrationResult) -> dict[str, Any]:
    """Return a compact report suitable for JSON output."""

    return {
        "method": result.method,
        "reliable": result.reliable,
        "matches": result.matches,
        "inliers": result.inliers,
        "inlier_ratio": result.inlier_ratio,
        "rms_error_px": result.rms_error_px,
        "median_error_px": result.median_error_px,
        "phase_response": result.phase_response,
        "message": result.message,
    }
