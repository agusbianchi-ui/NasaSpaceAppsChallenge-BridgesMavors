from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from mars_ml.training.prepare_dataset import (
    DatasetPreparationError,
    grouped_split,
    load_manifest,
    prepare_dataset,
)


def _write_sample(root, region: str, sequence: str, observation: str, *, mask: bool = True):
    sample_dir = root / region / sequence / observation
    sample_dir.mkdir(parents=True, exist_ok=True)
    image = np.zeros((32, 32), dtype=np.uint8)
    image[8:24, 8:24] = 120
    cv2.imwrite(str(sample_dir / "image.png"), image)
    if mask:
        mask_array = np.zeros((32, 32), dtype=np.uint8)
        mask_array[10:22, 10:22] = 255
        cv2.imwrite(str(sample_dir / "mask.png"), mask_array)
    return sample_dir


def test_prepare_dataset_groups_splits_and_writes_manifest(tmp_path):
    root = tmp_path / "dataset"
    for index in range(6):
        _write_sample(root, f"region{index}", "sequence", "obs")
    manifest_path = tmp_path / "manifest.json"
    manifest = prepare_dataset(root, manifest_path, seed=3)
    assert manifest["sample_count"] == 6
    assert sum(manifest["split_counts"].values()) == 6
    assert all(count >= 1 for count in manifest["split_counts"].values())
    assert manifest_path.exists()

    loaded = load_manifest(manifest_path)
    groups: dict[str, set[str]] = {}
    for entry in loaded["entries"]:
        groups.setdefault(entry["group_id"], set()).add(entry["split"])
        assert entry["image_sha256"]
        assert entry["mask_sha256"]
        assert entry["height"] == 32
        assert entry["channels"] == 1
    assert all(len(splits) == 1 for splits in groups.values())


def test_prepare_dataset_rejects_missing_masks_when_required(tmp_path):
    root = tmp_path / "dataset"
    for index in range(3):
        _write_sample(root, f"region{index}", "sequence", "obs", mask=False)
    with pytest.raises(DatasetPreparationError):
        prepare_dataset(root, tmp_path / "manifest.json", require_masks=True)


def test_prepare_dataset_records_missing_masks_when_allowed(tmp_path):
    root = tmp_path / "dataset"
    for index in range(6):
        _write_sample(root, f"region{index}", "sequence", "obs", mask=index > 0)
    manifest = prepare_dataset(
        root,
        tmp_path / "manifest.json",
        require_masks=False,
    )
    assert manifest["sample_count"] == 6
    assert any("Missing mask" in warning for warning in manifest["warnings"])
    with pytest.raises(DatasetPreparationError):
        load_manifest(tmp_path / "manifest.json")


def test_grouped_split_is_deterministic_and_disjoint():
    groups = [f"group{index}" for index in range(10)]
    first = grouped_split(groups, seed=5)
    second = grouped_split(groups, seed=5)
    assert first == second
    assert set(first) == set(groups)
    assert set(first.values()) == {"train", "val", "test"}


def test_grouped_split_requires_enough_groups():
    with pytest.raises(DatasetPreparationError):
        grouped_split(["a", "b"])
