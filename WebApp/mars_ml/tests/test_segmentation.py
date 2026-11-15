from __future__ import annotations

import numpy as np
import pytest

from mars_ml.computer_vision.dune_segmentation import (
    ClassicalDuneSegmenter,
    SegmentationConfig,
    SegmentationError,
    TrainedModelUnavailable,
    UNetSegmenter,
    segment_dunes,
)
from mars_ml.tests.synthetic import dune_scene


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    union = np.count_nonzero(first | second)
    return float(np.count_nonzero(first & second) / union) if union else 1.0


def test_classical_segmenter_finds_a_synthetic_dune_like_region():
    image, truth = dune_scene()
    result = segment_dunes(image)
    assert result.mask.shape == truth.shape
    assert result.area_px > 0
    assert _iou(result.mask, truth) > 0.25
    assert result.confidence is not None
    assert result.method == "classical_texture_gradient_v1"


def test_segmenter_returns_mask_on_uint8_input():
    image, truth = dune_scene()
    uint8 = np.round(image * 255).astype(np.uint8)
    result = ClassicalDuneSegmenter().segment(uint8)
    assert result.mask.dtype == bool
    assert _iou(result.mask, truth) > 0.2


def test_segmenter_rejects_a_flat_image():
    with pytest.raises(SegmentationError):
        segment_dunes(np.zeros((64, 64), dtype=np.uint8))


def test_invalid_segmentation_config_is_rejected():
    with pytest.raises(ValueError):
        SegmentationConfig(texture_window=8).validate()
    with pytest.raises(ValueError):
        SegmentationConfig(texture_weight=0.0, gradient_weight=0.0).validate()


def test_unet_without_checkpoint_does_not_pretend_to_be_trained(tmp_path):
    with pytest.raises(TrainedModelUnavailable):
        UNetSegmenter(tmp_path / "missing.pt")
