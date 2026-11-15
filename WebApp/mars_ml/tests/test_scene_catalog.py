from __future__ import annotations

import json
from dataclasses import replace

import pytest

from mars_ml.datasets.scene_catalog import (
    CatalogError,
    catalog_summary,
    load_scene_catalog,
    multitemporal_sequences,
    scenes_for_sequence,
)


def test_verified_sahara_catalog_loads():
    scenes = load_scene_catalog()
    assert len(scenes) == 5
    assert all(scene.data_status == "metadata_verified_not_downloaded" for scene in scenes)
    assert all(scene.acquisition_datetime.tzinfo is not None for scene in scenes)
    assert all(scene.resolution_m[0] > 0 for scene in scenes)
    summary = catalog_summary(scenes)
    assert summary["scene_count"] == 5
    assert "sentinel2_t30rvv_april" in summary["sequences"]
    assert summary["sequences"]["sentinel2_t30rvv_april"]["scene_count"] == 4


def test_sentinel_sequence_is_ordered_and_multitemporal():
    scenes = load_scene_catalog()
    sequence = scenes_for_sequence(scenes, "sentinel2_t30rvv_april")
    assert len(sequence) == 4
    assert sequence == tuple(sorted(sequence, key=lambda scene: scene.acquisition_datetime))
    assert len(multitemporal_sequences(scenes)) >= 1


def test_bbox_order_is_validated():
    scene = load_scene_catalog()[0]
    with pytest.raises(CatalogError):
        replace(scene, bbox_wgs84=(10.0, 20.0, 5.0, 25.0))


def test_missing_metadata_is_rejected(tmp_path):
    payload = {
        "scenes": [
            {
                "scene_id": "incomplete",
                "provider": "test",
                "collection": "test",
            }
        ]
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CatalogError):
        load_scene_catalog(path)
