"""Validation for scene catalogs.

Catalogs contain verified metadata only. They do not imply that pixels were
downloaded, that labels exist or that a scene is cloud-free outside the reported
scene-level cloud percentage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parent / "earth" / "sahara" / "scene_catalog.json"
)


class CatalogError(ValueError):
    """Raised when a scene catalog is missing or inconsistent."""


@dataclass(frozen=True)
class SceneRecord:
    scene_id: str
    provider: str
    collection: str
    platform: str
    instrument: str
    area_id: str
    sequence_id: str
    acquisition_datetime_utc: str
    bbox_wgs84: tuple[float, float, float, float]
    crs: str
    resolution_m: tuple[float, float]
    bands: tuple[str, ...]
    cloud_cover_pct: float | None
    stac_item_url: str
    retrieved_at_utc: str
    data_status: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.scene_id.strip():
            raise CatalogError("scene_id cannot be empty.")
        if not self.provider.strip() or not self.collection.strip():
            raise CatalogError(f"{self.scene_id}: provider and collection are required.")
        if not self.area_id.strip() or not self.sequence_id.strip():
            raise CatalogError(f"{self.scene_id}: area_id and sequence_id are required.")
        if len(self.bbox_wgs84) != 4:
            raise CatalogError(f"{self.scene_id}: bbox must be (west, south, east, north).")
        west, south, east, north = (float(v) for v in self.bbox_wgs84)
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise CatalogError(f"{self.scene_id}: invalid WGS84 bounding box.")
        if len(self.resolution_m) != 2 or not all(
            value > 0 and value == value for value in self.resolution_m
        ):
            raise CatalogError(f"{self.scene_id}: resolution_m must be two positive values.")
        if self.cloud_cover_pct is not None and not 0 <= self.cloud_cover_pct <= 100:
            raise CatalogError(f"{self.scene_id}: cloud cover must be in [0, 100].")
        if not self.crs.strip():
            raise CatalogError(f"{self.scene_id}: CRS is required.")
        self.acquisition_datetime
        self.retrieved_at

    @property
    def acquisition_datetime(self) -> datetime:
        return _parse_aware_datetime(self.acquisition_datetime_utc, self.scene_id)

    @property
    def retrieved_at(self) -> datetime:
        return _parse_aware_datetime(self.retrieved_at_utc, self.scene_id)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return tuple(float(v) for v in self.bbox_wgs84)  # type: ignore[return-value]

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "provider": self.provider,
            "collection": self.collection,
            "platform": self.platform,
            "instrument": self.instrument,
            "area_id": self.area_id,
            "sequence_id": self.sequence_id,
            "acquisition_datetime_utc": self.acquisition_datetime_utc,
            "bbox_wgs84": list(self.bbox_wgs84),
            "crs": self.crs,
            "resolution_m": list(self.resolution_m),
            "bands": list(self.bands),
            "cloud_cover_pct": self.cloud_cover_pct,
            "stac_item_url": self.stac_item_url,
            "retrieved_at_utc": self.retrieved_at_utc,
            "data_status": self.data_status,
            "notes": self.notes,
        }


def _parse_aware_datetime(value: str, scene_id: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CatalogError(f"{scene_id}: invalid ISO 8601 datetime {value!r}.") from exc
    if parsed.tzinfo is None:
        raise CatalogError(f"{scene_id}: datetime must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _record_from_dict(payload: dict[str, Any]) -> SceneRecord:
    required = {
        "scene_id",
        "provider",
        "collection",
        "platform",
        "instrument",
        "area_id",
        "sequence_id",
        "acquisition_datetime_utc",
        "bbox_wgs84",
        "crs",
        "resolution_m",
        "bands",
        "cloud_cover_pct",
        "stac_item_url",
        "retrieved_at_utc",
        "data_status",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise CatalogError(f"Scene record is missing fields: {', '.join(missing)}.")
    try:
        return SceneRecord(
            scene_id=str(payload["scene_id"]),
            provider=str(payload["provider"]),
            collection=str(payload["collection"]),
            platform=str(payload["platform"]),
            instrument=str(payload["instrument"]),
            area_id=str(payload["area_id"]),
            sequence_id=str(payload["sequence_id"]),
            acquisition_datetime_utc=str(payload["acquisition_datetime_utc"]),
            bbox_wgs84=tuple(float(v) for v in payload["bbox_wgs84"]),  # type: ignore[arg-type]
            crs=str(payload["crs"]),
            resolution_m=tuple(float(v) for v in payload["resolution_m"]),  # type: ignore[arg-type]
            bands=tuple(str(v) for v in payload["bands"]),
            cloud_cover_pct=(
                None if payload["cloud_cover_pct"] is None else float(payload["cloud_cover_pct"])
            ),
            stac_item_url=str(payload["stac_item_url"]),
            retrieved_at_utc=str(payload["retrieved_at_utc"]),
            data_status=str(payload["data_status"]),
            notes=str(payload.get("notes", "")),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, CatalogError):
            raise
        raise CatalogError(f"Invalid scene record {payload.get('scene_id', '<unknown>')}: {exc}") from exc


def load_scene_catalog(path: str | Path | None = None) -> tuple[SceneRecord, ...]:
    catalog_path = Path(path) if path is not None else DEFAULT_CATALOG_PATH
    if not catalog_path.exists():
        raise CatalogError(f"Scene catalog not found: {catalog_path}")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise CatalogError("Scene catalog must contain a non-empty 'scenes' list.")
    scenes = tuple(_record_from_dict(item) for item in raw_scenes)
    seen: set[str] = set()
    for scene in scenes:
        if scene.scene_id in seen:
            raise CatalogError(f"Duplicate scene_id: {scene.scene_id}")
        seen.add(scene.scene_id)
    return scenes


def scenes_for_sequence(scenes: Iterable[SceneRecord], sequence_id: str) -> tuple[SceneRecord, ...]:
    selected = tuple(scene for scene in scenes if scene.sequence_id == sequence_id)
    return tuple(sorted(selected, key=lambda scene: scene.acquisition_datetime))


def multitemporal_sequences(scenes: Iterable[SceneRecord]) -> dict[str, tuple[SceneRecord, ...]]:
    groups: dict[str, list[SceneRecord]] = {}
    for scene in scenes:
        groups.setdefault(scene.sequence_id, []).append(scene)
    return {
        key: tuple(sorted(value, key=lambda scene: scene.acquisition_datetime))
        for key, value in groups.items()
        if len(value) >= 2
    }


def catalog_summary(scenes: Iterable[SceneRecord]) -> dict[str, Any]:
    scene_list = tuple(scenes)
    sequences = multitemporal_sequences(scene_list)
    return {
        "scene_count": len(scene_list),
        "providers": sorted({scene.provider for scene in scene_list}),
        "areas": sorted({scene.area_id for scene in scene_list}),
        "sequences": {
            key: {
                "scene_count": len(value),
                "first_acquisition_utc": value[0].acquisition_datetime_utc,
                "last_acquisition_utc": value[-1].acquisition_datetime_utc,
            }
            for key, value in sequences.items()
        },
        "data_status": sorted({scene.data_status for scene in scene_list}),
    }
