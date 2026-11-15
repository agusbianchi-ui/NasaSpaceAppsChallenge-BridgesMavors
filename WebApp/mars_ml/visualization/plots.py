"""Deterministic PNG visualizations for dune analysis outputs.

All plots are inspection aids. They do not add scientific evidence beyond the
mask, registration and displacement objects supplied by the caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from mars_ml.aeolian_dynamics.dune_morphology import MorphologyFeatures
from mars_ml.computer_vision.displacement_detection import DisplacementReport
from mars_ml.computer_vision.image_io import normalize_image


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _display_image(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if np.issubdtype(array.dtype, np.floating):
        normalized, _ = normalize_image(array)
        return normalized
    if array.dtype == np.uint8:
        return array.astype(np.float32) / 255.0
    normalized, _ = normalize_image(array)
    return normalized


def _save(figure: Any, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(output, dpi=140, bbox_inches="tight")
    return output


def plot_image(image: np.ndarray, path: str | Path, *, title: str = "Image") -> Path:
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=(8, 6))
    display = _display_image(image)
    if display.ndim == 2:
        axis.imshow(display, cmap="gray")
    else:
        axis.imshow(display)
    axis.set_title(title)
    axis.set_xlabel("x [px]")
    axis.set_ylabel("y [px]")
    output = _save(figure, path)
    plt.close(figure)
    return output


def plot_mask_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    path: str | Path,
    *,
    title: str = "Candidate dune mask",
) -> Path:
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=(8, 6))
    display = _display_image(image)
    if display.ndim == 2:
        axis.imshow(display, cmap="gray")
    else:
        axis.imshow(display)
    overlay = np.zeros((*mask.shape, 4), dtype=np.float32)
    overlay[mask.astype(bool)] = (0.0, 0.8, 0.9, 0.35)
    axis.imshow(overlay)
    axis.set_title(title)
    axis.set_xlabel("x [px]")
    axis.set_ylabel("y [px]")
    output = _save(figure, path)
    plt.close(figure)
    return output


def plot_alignment(
    reference: np.ndarray,
    aligned_moving: np.ndarray,
    path: str | Path,
    *,
    title: str = "Reference and aligned observation",
) -> Path:
    plt = _pyplot()
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    first = _display_image(reference)
    second = _display_image(aligned_moving)
    axes[0].imshow(first, cmap="gray" if first.ndim == 2 else None)
    axes[0].set_title("Reference")
    axes[1].imshow(second, cmap="gray" if second.ndim == 2 else None)
    axes[1].set_title("Aligned observation")
    figure.suptitle(title)
    output = _save(figure, path)
    plt.close(figure)
    return output


def plot_difference(
    reference: np.ndarray,
    aligned_moving: np.ndarray,
    path: str | Path,
    *,
    valid_mask: np.ndarray | None = None,
    title: str = "Normalized difference",
) -> Path:
    plt = _pyplot()
    first = _display_image(reference)
    second = _display_image(aligned_moving)
    if first.ndim == 3:
        first = first.mean(axis=2)
    if second.ndim == 3:
        second = second.mean(axis=2)
    difference = second - first
    if valid_mask is not None:
        difference = np.where(valid_mask, difference, np.nan)
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    image = axes[0].imshow(difference, cmap="coolwarm", vmin=-1, vmax=1)
    axes[0].set_title("Signed difference (moving - reference)")
    figure.colorbar(image, ax=axes[0], fraction=0.046, pad=0.04)
    axes[1].imshow(np.abs(difference), cmap="magma")
    axes[1].set_title("Absolute difference")
    figure.suptitle(title)
    output = _save(figure, path)
    plt.close(figure)
    return output


def plot_displacement(
    reference_mask: np.ndarray,
    report: DisplacementReport,
    path: str | Path,
    *,
    title: str = "Displacement estimates",
) -> Path:
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.imshow(reference_mask.astype(float), cmap="gray")
    mask = reference_mask.astype(bool)
    if np.any(mask):
        ys, xs = np.nonzero(mask)
        origin = (float(xs.mean()), float(ys.mean()))
    else:
        origin = (reference_mask.shape[1] / 2.0, reference_mask.shape[0] / 2.0)
    colors = {"centroid": "cyan", "farneback": "yellow", "lucas": "magenta"}
    for name, displacement in (
        ("centroid", report.centroid),
        ("farneback", report.farneback),
        ("lucas", report.lucas_kanade),
    ):
        if displacement is None:
            continue
        axis.annotate(
            "",
            xy=(origin[0] + displacement.dx_px, origin[1] - displacement.dy_px),
            xytext=origin,
            arrowprops={
                "arrowstyle": "->",
                "color": colors[name],
                "linewidth": 2,
                "alpha": 0.85,
            },
        )
        axis.text(
            origin[0] + displacement.dx_px,
            origin[1] - displacement.dy_px,
            f" {name}: {displacement.magnitude_px:.2f} px",
            color=colors[name],
            fontsize=8,
        )
    axis.set_title(f"{title} (status: {report.status})")
    axis.set_xlabel("x [px]")
    axis.set_ylabel("y [px]")
    output = _save(figure, path)
    plt.close(figure)
    return output


def plot_morphology(
    mask: np.ndarray,
    features: MorphologyFeatures,
    path: str | Path,
    *,
    title: str = "Morphology",
) -> Path:
    plt = _pyplot()
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.imshow(mask.astype(float), cmap="gray")
    axis.plot(features.centroid_x_px, features.centroid_y_px, "c+", markersize=12)
    angle = features.orientation_deg
    if angle is not None and features.major_axis_px is not None:
        length = features.major_axis_px / 2.0
        radians = np.radians(angle)
        east = np.sin(radians) * length
        north = np.cos(radians) * length
        axis.plot(
            [features.centroid_x_px - east, features.centroid_x_px + east],
            [features.centroid_y_px + north, features.centroid_y_px - north],
            color="cyan",
            linewidth=2,
        )
    axis.set_title(title)
    text = (
        f"area={features.area_px} px2\n"
        f"perimeter={features.perimeter_px:.1f} px\n"
        f"aspect={features.aspect_ratio:.2f}"
        if features.aspect_ratio is not None
        else f"area={features.area_px} px2\nperimeter={features.perimeter_px:.1f} px"
    )
    axis.text(
        0.01,
        0.99,
        text,
        transform=axis.transAxes,
        va="top",
        color="white",
        fontsize=8,
        bbox={"facecolor": "black", "alpha": 0.6, "edgecolor": "none"},
    )
    output = _save(figure, path)
    plt.close(figure)
    return output
