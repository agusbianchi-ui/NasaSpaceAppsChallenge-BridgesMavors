"""Rasterize vector annotations onto a validated reference raster grid.

The output separates a binary dune mask from integer labels. Rasterization is a
geometry operation and does not imply that the annotation is a temporal label or
a migration measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from mars_ml.computer_vision.image_io import RasterImage
from mars_ml.ingestion.readers import IngestionError, VectorLayer, read_vector


class AnnotationError(ValueError):
    """Raised when an annotation cannot be rasterized safely."""


@dataclass(frozen=True)
class AnnotationRasterization:
    mask: np.ndarray
    labels: np.ndarray
    class_values: tuple[int, ...]
    record_ids: tuple[str, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mask.ndim != 2 or self.labels.ndim != 2:
            raise AnnotationError("Rasterized annotations must be 2D.")
        if self.mask.shape != self.labels.shape:
            raise AnnotationError("Mask and labels must share a shape.")
        if not np.any(self.mask):
            raise AnnotationError("Rasterized annotation mask is empty.")

    @property
    def foreground_fraction(self) -> float:
        return float(np.mean(self.mask))

    def as_dict(self) -> dict[str, Any]:
        return {
            "height": int(self.mask.shape[0]),
            "width": int(self.mask.shape[1]),
            "foreground_pixels": int(np.count_nonzero(self.mask)),
            "foreground_fraction": self.foreground_fraction,
            "class_values": list(self.class_values),
            "record_count": len(self.record_ids),
            "provenance": dict(self.provenance),
        }


def _reference_transform(reference: RasterImage) -> Any:
    if reference.metadata.transform is None:
        raise AnnotationError("Reference raster has no affine transform.")
    from affine import Affine

    return Affine(*reference.metadata.transform)


def _normalise_crs(value: str | None) -> str | None:
    if not value:
        return None
    try:
        from rasterio.crs import CRS

        try:
            return CRS.from_wkt(value).to_string()
        except Exception:
            return CRS.from_string(value).to_string()
    except Exception:
        return None


def _check_crs(layer: VectorLayer, reference: RasterImage) -> None:
    vector_crs = _normalise_crs(layer.crs)
    raster_crs = _normalise_crs(reference.metadata.crs)
    if vector_crs is not None and raster_crs is not None and vector_crs != raster_crs:
        raise AnnotationError(
            f"Vector CRS {vector_crs} does not match raster CRS {raster_crs}; reproject first."
        )


def _labels_from_records(
    layer: VectorLayer, class_field: str | None
) -> tuple[list[tuple[dict[str, Any], int]], tuple[int, ...], tuple[str, ...]]:
    if class_field is None:
        shapes = [(record.geometry, 1) for record in layer.records]
        return shapes, (1,), tuple(record.record_id for record in layer.records)
    if class_field not in layer.fields:
        raise AnnotationError(f"Class field {class_field!r} is not present in the vector layer.")
    shapes: list[tuple[dict[str, Any], int]] = []
    class_values: set[int] = set()
    for record in layer.records:
        raw_value = record.attributes.get(class_field)
        try:
            class_value = int(float(raw_value))
        except (TypeError, ValueError) as exc:
            raise AnnotationError(
                f"Record {record.record_id}: class field {class_field!r} is not numeric."
            ) from exc
        if class_value <= 0:
            raise AnnotationError(
                f"Record {record.record_id}: class values must be positive integers."
            )
        class_values.add(class_value)
        shapes.append((record.geometry, class_value))
    return shapes, tuple(sorted(class_values)), tuple(record.record_id for record in layer.records)


def rasterize_vector(
    layer: VectorLayer,
    reference: RasterImage,
    *,
    class_field: str | None = None,
    all_touched: bool = False,
) -> AnnotationRasterization:
    """Rasterize a vector layer onto the reference raster grid."""

    if not isinstance(layer, VectorLayer):
        raise AnnotationError("layer must be a VectorLayer.")
    if not isinstance(reference, RasterImage):
        raise AnnotationError("reference must be a RasterImage.")
    _check_crs(layer, reference)
    transform = _reference_transform(reference)
    shapes, class_values, record_ids = _labels_from_records(layer, class_field)
    try:
        from rasterio.features import rasterize
    except ImportError as exc:
        raise AnnotationError("Rasterio is required to rasterize annotations.") from exc
    try:
        labels = rasterize(
            shapes,
            out_shape=reference.data.shape[:2],
            transform=transform,
            fill=0,
            all_touched=all_touched,
            dtype="int32",
        )
    except Exception as exc:
        raise AnnotationError(f"Rasterization failed: {exc}") from exc
    labels = np.asarray(labels, dtype=np.int32)
    mask = labels > 0
    if not np.any(mask):
        raise AnnotationError(
            "Rasterized annotation is empty; check CRS, transform and geometry overlap."
        )
    return AnnotationRasterization(
        mask=mask,
        labels=labels,
        class_values=class_values,
        record_ids=record_ids,
        provenance={
            "vector_path": layer.path,
            "vector_format": layer.source_format,
            "vector_crs": layer.crs,
            "raster_crs": reference.metadata.crs,
            "class_field": class_field,
            "all_touched": all_touched,
            "record_count": len(layer.records),
        },
    )


def rasterize_annotations(
    vector_path: str | Path,
    reference: RasterImage,
    *,
    class_field: str | None = None,
    all_touched: bool = False,
) -> AnnotationRasterization:
    return rasterize_vector(
        read_vector(vector_path),
        reference,
        class_field=class_field,
        all_touched=all_touched,
    )


def write_annotation_rasters(output_dir: str | Path, result: AnnotationRasterization) -> dict[str, str]:
    from mars_ml.computer_vision.image_io import save_image

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mask_path = save_image(output / "annotation_mask.png", result.mask.astype(np.uint8) * 255, normalize=False)
    labels_path = save_image(
        output / "annotation_labels.png",
        np.clip(result.labels, 0, 255).astype(np.uint8),
        normalize=False,
    )
    return {"mask": str(mask_path), "labels": str(labels_path)}
