"""Helpers that turn rasterized vector annotations into training masks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from mars_ml.computer_vision.image_io import RasterImage
from mars_ml.ingestion.annotations import (
    AnnotationRasterization,
    rasterize_annotations,
    rasterize_vector,
)
from mars_ml.ingestion.readers import VectorLayer, read_vector


def annotation_mask_from_vector(
    vector: str | Path | VectorLayer,
    reference: RasterImage,
    *,
    class_field: str | None = None,
    all_touched: bool = False,
) -> AnnotationRasterization:
    layer = read_vector(vector) if isinstance(vector, (str, Path)) else vector
    return rasterize_vector(
        layer,
        reference,
        class_field=class_field,
        all_touched=all_touched,
    )


def annotation_mask_from_file(
    vector_path: str | Path,
    reference: RasterImage,
    *,
    class_field: str | None = None,
    all_touched: bool = False,
) -> AnnotationRasterization:
    return rasterize_annotations(
        vector_path,
        reference,
        class_field=class_field,
        all_touched=all_touched,
    )


def class_masks(result: AnnotationRasterization) -> dict[int, np.ndarray]:
    if not isinstance(result, AnnotationRasterization):
        raise TypeError("result must be an AnnotationRasterization.")
    return {
        int(value): result.labels == int(value)
        for value in result.class_values
        if np.any(result.labels == int(value))
    }


def annotation_summary(result: AnnotationRasterization) -> dict[str, Any]:
    summary = result.as_dict()
    summary["class_pixel_counts"] = {
        int(value): int(np.count_nonzero(result.labels == int(value)))
        for value in result.class_values
    }
    return summary
