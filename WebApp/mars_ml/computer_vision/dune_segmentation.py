"""Dune candidate segmentation.

The default segmenter is a classical OpenCV pipeline. It combines local texture
and edge energy, thresholds the resulting score and cleans the mask with
morphology. It is intentionally presented as an unvalidated baseline, not as a
trained dune detector.

A U-Net adapter is included for the next stage. It requires an explicitly
supplied checkpoint and PyTorch. No checkpoint ships with this repository and
no metric in this module implies that such a model has been trained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import (
    ImageValidationError,
    normalize_image,
    validate_image_array,
)


class SegmentationError(RuntimeError):
    """Raised when segmentation cannot produce a scientifically usable mask."""


@dataclass(frozen=True)
class SegmentationConfig:
    """Parameters for the classical texture/edge baseline."""

    texture_window: int = 9
    gradient_window: int = 5
    texture_weight: float = 0.6
    gradient_weight: float = 0.4
    threshold_scale: float = 1.0
    min_component_fraction: float = 0.002
    closing_kernel: int = 5
    opening_kernel: int = 3
    fill_holes: bool = True
    use_clahe: bool = True

    def validate(self) -> None:
        for name in ("texture_window", "gradient_window", "closing_kernel", "opening_kernel"):
            value = getattr(self, name)
            if value < 1 or value % 2 == 0:
                raise ValueError(f"{name} must be a positive odd integer.")
        if self.texture_weight < 0 or self.gradient_weight < 0:
            raise ValueError("Texture and gradient weights must be non-negative.")
        if self.texture_weight + self.gradient_weight == 0:
            raise ValueError("At least one feature weight must be positive.")
        if not 0 <= self.min_component_fraction < 1:
            raise ValueError("min_component_fraction must be in [0, 1).")
        if self.threshold_scale <= 0:
            raise ValueError("threshold_scale must be positive.")


@dataclass(frozen=True)
class SegmentationResult:
    """Binary mask plus diagnostics. ``mask`` is True on candidate dunes."""

    mask: np.ndarray
    method: str
    confidence: float | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        mask = np.asarray(self.mask)
        if mask.ndim != 2:
            raise SegmentationError("Segmentation mask must be 2D.")
        if mask.dtype != bool:
            object.__setattr__(self, "mask", mask.astype(bool))

    @property
    def area_px(self) -> int:
        return int(np.count_nonzero(self.mask))

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "area_px": self.area_px,
            "confidence": self.confidence,
            "diagnostics": dict(self.diagnostics),
            "notes": self.notes,
        }


@runtime_checkable
class DuneSegmenter(Protocol):
    """Interface shared by classical and future semantic segmenters."""

    def segment(
        self,
        image: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> SegmentationResult: ...


def _to_gray(image: np.ndarray, valid_mask: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    validate_image_array(image)
    normalized, valid = normalize_image(image, valid_mask)
    if normalized.ndim == 3:
        rgb = normalized
        gray = (
            0.299 * rgb[..., 0]
            + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]
        ).astype(np.float32)
    else:
        gray = normalized.astype(np.float32)
    gray[~valid] = 0.0
    return gray, valid


def _normalize_feature(feature: np.ndarray, valid: np.ndarray) -> np.ndarray:
    values = feature[valid]
    if values.size == 0:
        return np.zeros_like(feature, dtype=np.float32)
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return np.zeros_like(feature, dtype=np.float32)
    return np.clip((feature - low) / (high - low), 0.0, 1.0).astype(np.float32)


def _fill_mask_holes(mask: np.ndarray) -> np.ndarray:
    uint8 = (mask.astype(np.uint8) * 255)
    contours, _ = cv2.findContours(uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(uint8)
    if contours:
        cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled > 0


def _remove_small_components(mask: np.ndarray, min_area_px: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    cleaned = np.zeros_like(mask, dtype=bool)
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_area_px:
            cleaned |= labels == label
    return cleaned


class ClassicalDuneSegmenter:
    """Classical baseline using local texture and gradient energy.

    Limitations:
    - It responds to generic rough/textured terrain, not specifically to dunes.
    - Illumination and resolution changes alter the score.
    - Thresholds are heuristic and have not been validated against labelled data.
    """

    method = "classical_texture_gradient_v1"

    def __init__(self, config: SegmentationConfig | None = None) -> None:
        self.config = config or SegmentationConfig()
        self.config.validate()

    def segment(
        self,
        image: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> SegmentationResult:
        cfg = self.config
        gray, valid = _to_gray(image, valid_mask)
        if not np.any(valid):
            raise SegmentationError("Image has no valid pixels to segment.")

        if cfg.use_clahe:
            gray_u8 = np.round(gray * 255).astype(np.uint8)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray_u8).astype(np.float32) / 255.0
            gray = np.where(valid, enhanced, 0.0).astype(np.float32)

        mean = cv2.GaussianBlur(gray, (cfg.texture_window, cfg.texture_window), 0)
        mean_sq = cv2.GaussianBlur(gray * gray, (cfg.texture_window, cfg.texture_window), 0)
        local_variance = np.maximum(mean_sq - mean * mean, 0.0)
        texture = np.sqrt(local_variance).astype(np.float32)
        texture = cv2.GaussianBlur(texture, (cfg.texture_window, cfg.texture_window), 0)

        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        gradient = cv2.magnitude(grad_x, grad_y)
        gradient = cv2.GaussianBlur(gradient, (cfg.gradient_window, cfg.gradient_window), 0)

        texture_n = _normalize_feature(texture, valid)
        gradient_n = _normalize_feature(gradient, valid)
        weight_sum = cfg.texture_weight + cfg.gradient_weight
        score = (
            cfg.texture_weight * texture_n + cfg.gradient_weight * gradient_n
        ) / weight_sum
        score = np.where(valid, score, 0.0).astype(np.float32)

        score_u8 = np.round(score * 255).astype(np.uint8)
        otsu_threshold, _ = cv2.threshold(score_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        threshold_value = float(np.clip(otsu_threshold / 255.0 * cfg.threshold_scale, 0.0, 1.0))
        if threshold_value <= 0:
            raise SegmentationError("Segmentation threshold degenerated to zero.")

        mask = (score >= threshold_value) & valid
        if cfg.closing_kernel > 1:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (cfg.closing_kernel, cfg.closing_kernel)
            )
            mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel) > 0
        if cfg.opening_kernel > 1:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (cfg.opening_kernel, cfg.opening_kernel)
            )
            mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel) > 0
        if cfg.fill_holes:
            mask = _fill_mask_holes(mask)

        min_area = max(1, int(round(cfg.min_component_fraction * mask.size)))
        mask = _remove_small_components(mask, min_area)
        mask &= valid

        if not np.any(mask):
            confidence = 0.0
            notes = "No candidate region survived thresholding and cleanup."
        else:
            confidence = float(np.mean(score[mask]))
            notes = "Classical baseline; not validated against a labelled dune dataset."
        return SegmentationResult(
            mask=mask.astype(bool),
            method=self.method,
            confidence=confidence,
            diagnostics={
                "threshold": threshold_value,
                "otsu_threshold": float(otsu_threshold / 255.0),
                "texture_weight": cfg.texture_weight,
                "gradient_weight": cfg.gradient_weight,
                "min_component_area_px": min_area,
                "valid_fraction": float(np.mean(valid)),
            },
            notes=notes,
        )


def segment_dunes(
    image: np.ndarray,
    valid_mask: np.ndarray | None = None,
    *,
    config: SegmentationConfig | None = None,
) -> SegmentationResult:
    """Convenience wrapper around the classical baseline."""

    return ClassicalDuneSegmenter(config).segment(image, valid_mask)


class TrainedModelUnavailable(SegmentationError):
    """Raised when a supervised segmenter is requested without usable weights."""


class UNetSegmenter:
    """Adapter for a supervised U-Net checkpoint.

    The checkpoint is external. The class deliberately fails if it is missing
    rather than silently falling back to untrained weights.
    """

    def __init__(
        self,
        checkpoint: str | Path,
        *,
        device: str = "cpu",
        threshold: float = 0.5,
        input_channels: int = 1,
        base_channels: int = 32,
    ) -> None:
        checkpoint_path = Path(checkpoint)
        if not checkpoint_path.exists():
            raise TrainedModelUnavailable(
                f"U-Net checkpoint not found: {checkpoint_path}. "
                "No trained model is included in this repository."
            )
        if not 0 < threshold < 1:
            raise ValueError("threshold must be in (0, 1).")
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise TrainedModelUnavailable(
                "PyTorch is required for the U-Net adapter. Install the training extra."
            ) from exc

        from mars_ml.models.unet import build_unet

        self._torch = torch
        self.device = torch.device(device)
        self.threshold = threshold
        self.input_channels = input_channels
        self.model = build_unet(input_channels=input_channels, base_channels=base_channels)
        state = torch.load(checkpoint_path, map_location=self.device)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()
        self.checkpoint = str(checkpoint_path)

    def segment(
        self,
        image: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> SegmentationResult:
        torch = self._torch
        normalized, valid = normalize_image(image, valid_mask)
        if normalized.ndim == 3:
            gray = (
                0.299 * normalized[..., 0]
                + 0.587 * normalized[..., 1]
                + 0.114 * normalized[..., 2]
            )
        else:
            gray = normalized
        if self.input_channels == 3:
            model_input = normalized if normalized.ndim == 3 else np.repeat(normalized[..., None], 3, axis=2)
        else:
            model_input = gray[..., None] if gray.ndim == 2 else gray
        array = np.moveaxis(np.asarray(model_input, dtype=np.float32), -1, 0)[None, ...]
        tensor = torch.from_numpy(array).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = torch.sigmoid(logits)[0, 0].cpu().numpy()
        mask = (probabilities >= self.threshold) & valid
        confidence = float(probabilities[mask].mean()) if np.any(mask) else 0.0
        return SegmentationResult(
            mask=mask,
            method="unet_supervised_checkpoint",
            confidence=confidence,
            diagnostics={
                "checkpoint": self.checkpoint,
                "threshold": self.threshold,
                "device": str(self.device),
            },
            notes=(
                "Supervised weights were supplied externally. "
                "Their training data and metrics are not embedded in this package."
            ),
        )


def resolve_segmenter(
    *,
    checkpoint: str | Path | None = None,
    config: SegmentationConfig | None = None,
) -> DuneSegmenter:
    """Return a U-Net segmenter when a checkpoint is supplied, else classical."""

    if checkpoint:
        return UNetSegmenter(checkpoint)
    return ClassicalDuneSegmenter(config)
