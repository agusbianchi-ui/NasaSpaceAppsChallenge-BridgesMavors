from __future__ import annotations

import cv2
import numpy as np
import pytest

from mars_ml.computer_vision.image_io import (
    ImageValidationError,
    RasterImage,
    SpatialMetadata,
    crop_image,
    extract_valid_mask,
    load_image,
    load_raster,
    normalize_image,
    save_raster,
)


def test_load_image_preserves_channels_and_shape(tmp_path):
    array = np.zeros((20, 30, 3), dtype=np.uint8)
    array[..., 0] = 255
    path = tmp_path / "rgb.png"
    cv2.imwrite(str(path), cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
    image = load_image(path)
    assert image.shape == (20, 30, 3)
    assert image.channels == 3
    assert image.data[0, 0, 0] == 255
    assert image.data[0, 0, 1] == 0


def test_normalization_ignores_nodata():
    array = np.array([[1.0, 2.0], [3.0, 0.0]], dtype=np.float32)
    valid = extract_valid_mask(array, nodata=0.0)
    normalized, valid_out = normalize_image(array, valid)
    assert valid_out.tolist() == [[True, True], [True, False]]
    assert normalized[1, 1] == 0.0
    assert np.all((normalized[valid] >= 0) & (normalized[valid] <= 1))


def test_normalization_constant_image_returns_zeros():
    array = np.full((10, 10), 42, dtype=np.uint16)
    normalized, valid = normalize_image(array)
    assert np.all(valid)
    assert np.allclose(normalized, 0.0)


def test_crop_updates_affine_transform():
    data = np.arange(100, dtype=np.uint16).reshape(10, 10)
    metadata = SpatialMetadata(
        crs="EPSG:32630",
        transform=(10.0, 0.0, 100.0, 0.0, -10.0, 200.0),
        resolution=(10.0, 10.0),
    )
    image = RasterImage(data, metadata)
    cropped = crop_image(image, 2, 7, 3, 9)
    assert cropped.shape == (5, 6)
    assert cropped.metadata.transform == (10.0, 0.0, 130.0, 0.0, -10.0, 180.0)
    assert cropped.metadata.extra["crop_pixels"]["row_start"] == 2


def test_raster_roundtrip_keeps_georeferencing(tmp_path):
    data = np.arange(48, dtype=np.uint16).reshape(6, 8)
    metadata = SpatialMetadata(
        crs="EPSG:32630",
        transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 3400000.0),
        resolution=(10.0, 10.0),
        nodata=0.0,
        source="synthetic test fixture",
    )
    path = tmp_path / "synthetic.tif"
    save_raster(path, RasterImage(data, metadata))
    loaded = load_raster(path)
    assert loaded.metadata.crs == "EPSG:32630"
    assert loaded.metadata.transform == metadata.transform
    assert loaded.metadata.resolution == (10.0, 10.0)
    assert loaded.metadata.nodata == 0.0
    assert np.array_equal(loaded.data, data)


def test_invalid_mask_shape_is_rejected():
    array = np.zeros((8, 8), dtype=np.float32)
    with pytest.raises(ImageValidationError):
        normalize_image(array, np.ones((4, 4), dtype=bool))


def test_invalid_resolution_is_rejected():
    with pytest.raises(ImageValidationError):
        SpatialMetadata(resolution=(0.0, 10.0)).validate()
