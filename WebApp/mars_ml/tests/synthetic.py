"""Synthetic fixtures for unit tests.

These arrays are generated for tests only. They are not satellite imagery and
must never be described as observations.
"""

from __future__ import annotations

import cv2
import numpy as np


def textured_scene(height: int = 192, width: int = 192, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 90, size=(height, width), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (5, 5), 0)
    image = base.astype(np.uint8)
    rng_shapes = np.random.default_rng(seed + 1)
    for _ in range(40):
        x = int(rng_shapes.integers(5, width - 5))
        y = int(rng_shapes.integers(5, height - 5))
        radius = int(rng_shapes.integers(3, 14))
        value = int(rng_shapes.integers(100, 255))
        cv2.circle(image, (x, y), radius, value, thickness=-1)
    for _ in range(20):
        x1 = int(rng_shapes.integers(0, width - 1))
        y1 = int(rng_shapes.integers(0, height - 1))
        x2 = int(rng_shapes.integers(0, width - 1))
        y2 = int(rng_shapes.integers(0, height - 1))
        value = int(rng_shapes.integers(120, 255))
        cv2.line(image, (x1, y1), (x2, y2), value, thickness=2)
    return image


def translate(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    matrix = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    return cv2.warpAffine(
        image,
        matrix,
        (image.shape[1], image.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )


def ellipse_mask(
    height: int = 192,
    width: int = 192,
    *,
    center: tuple[int, int] = (96, 96),
    axes: tuple[int, int] = (45, 25),
    angle: float = 20.0,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(mask, center, axes, angle, 0, 360, 255, thickness=-1)
    return mask > 0


def dune_scene(
    height: int = 192,
    width: int = 192,
    *,
    center: tuple[int, int] = (96, 96),
    axes: tuple[int, int] = (55, 32),
    angle: float = 18.0,
    seed: int = 11,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth background plus a ripple-textured elliptical candidate dune."""

    rng = np.random.default_rng(seed)
    background = rng.normal(0.28, 0.015, size=(height, width)).clip(0, 1).astype(np.float32)
    image = background.copy()
    mask = ellipse_mask(height, width, center=center, axes=axes, angle=angle)
    ys, xs = np.indices((height, width)).astype(np.float32)
    radians = np.radians(angle)
    rotated = (xs - center[0]) * np.cos(radians) + (ys - center[1]) * np.sin(radians)
    ripples = 0.11 * np.sin(rotated / 2.2) + 0.03 * np.sin(rotated / 0.9)
    image[mask] = (0.63 + ripples[mask] + rng.normal(0, 0.02, size=int(mask.sum()))).astype(np.float32)
    image = np.clip(image, 0, 1)
    return image, mask


def dune_pair(
    *,
    height: int = 192,
    width: int = 192,
    dx: float = 10.0,
    dy: float = -4.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    first, mask = dune_scene(height, width)
    second = translate(first, dx, dy)
    moved_mask = translate(mask.astype(np.uint8) * 255, dx, dy) > 127
    return first, second, mask, moved_mask
