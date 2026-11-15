"""Validated Martian dataset manifests.

A manifest records verified metadata only. It does not imply that pixels exist
locally, that acquisition dates are known for every product, or that a dataset
supports temporal displacement analysis.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MARS_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "mars" / "manifest.json"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_DATE_STATUS = {
    "reported",
    "not_reported",
    "requires_pds_resolution",
    "not_applicable",
    "mixed",
}
_ALLOWED_RESOLUTION_UNITS = {"m/pixel", "m", "km/pixel", "degrees/pixel"}


class DatasetManifestError(ValueError):
    """Raised when a Martian dataset manifest is missing or inconsistent."""


@dataclass(frozen=True)
class DatasetFile:
    name: str
    size_bytes: int
    url: str | None = None
    sha256: str | None = None
    role: str = "data"
    selected: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DatasetManifestError("Dataset file name cannot be empty.")
        if self.size_bytes < 0:
            raise DatasetManifestError(f"{self.name}: size_bytes must be non-negative.")
        if self.sha256 is not None and not _SHA256_PATTERN.match(self.sha256.lower()):
            raise DatasetManifestError(f"{self.name}: sha256 must be 64 hexadecimal characters.")
        if self.url is not None and not self.url.startswith(("https://", "http://")):
            raise DatasetManifestError(f"{self.name}: file URL must use HTTP(S).")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "url": self.url,
            "sha256": self.sha256,
            "role": self.role,
            "selected": self.selected,
        }


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    name: str
    source: str
    mission: str
    instrument: str
    location: str
    acquisition_dates: tuple[str, ...]
    resolution: tuple[dict[str, Any], ...]
    coordinate_reference_system: dict[str, Any]
    data_type: str
    license: str
    limitations: tuple[str, ...]
    provider: str
    acquisition_dates_status: str = "reported"
    doi: str | None = None
    url: str | None = None
    version: str | None = None
    retrieved_at_utc: str | None = None
    has_pixels: bool = False
    has_labels: bool = False
    has_temporal_series: bool = False
    files: tuple[DatasetFile, ...] = field(default_factory=tuple)
    published_context: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "dataset_id",
            "name",
            "source",
            "mission",
            "instrument",
            "location",
            "data_type",
            "license",
            "provider",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DatasetManifestError(f"{self.dataset_id or '<unknown>'}: {field_name} is required.")
        if not self.dataset_id.replace("_", "").replace("-", "").isalnum():
            raise DatasetManifestError(f"{self.dataset_id}: dataset_id must be alphanumeric with _ or -.")
        if self.acquisition_dates_status not in _ALLOWED_DATE_STATUS:
            raise DatasetManifestError(
                f"{self.dataset_id}: invalid acquisition_dates_status {self.acquisition_dates_status!r}."
            )
        for value in self.acquisition_dates:
            _parse_acquisition_date(value, self.dataset_id)
        if not self.acquisition_dates and self.acquisition_dates_status == "reported":
            raise DatasetManifestError(
                f"{self.dataset_id}: reported dates cannot be empty; use an explicit status."
            )
        if not self.resolution:
            raise DatasetManifestError(f"{self.dataset_id}: at least one resolution entry is required.")
        for entry in self.resolution:
            _validate_resolution_entry(entry, self.dataset_id)
        if not isinstance(self.coordinate_reference_system, dict):
            raise DatasetManifestError(f"{self.dataset_id}: CRS must be an object.")
        if not str(self.coordinate_reference_system.get("name", "")).strip():
            raise DatasetManifestError(f"{self.dataset_id}: CRS name is required.")
        if not str(self.coordinate_reference_system.get("units", "")).strip():
            raise DatasetManifestError(f"{self.dataset_id}: CRS units are required.")
        if not self.limitations:
            raise DatasetManifestError(f"{self.dataset_id}: limitations cannot be empty.")
        if any(not str(value).strip() for value in self.limitations):
            raise DatasetManifestError(f"{self.dataset_id}: limitations cannot contain empty entries.")
        names: set[str] = set()
        for entry in self.files:
            if entry.name in names:
                raise DatasetManifestError(f"{self.dataset_id}: duplicate file {entry.name}.")
            names.add(entry.name)
        if self.retrieved_at_utc is not None:
            _parse_aware_datetime(self.retrieved_at_utc, self.dataset_id)
        if self.url is not None and not self.url.startswith(("https://", "http://")):
            raise DatasetManifestError(f"{self.dataset_id}: URL must use HTTP(S).")

    @property
    def resolutions_in_metres(self) -> tuple[float, ...]:
        values: list[float] = []
        for entry in self.resolution:
            unit = str(entry["unit"])
            value = float(entry["value"])
            if unit == "m/pixel":
                values.append(value)
            elif unit == "km/pixel":
                values.append(value * 1000.0)
        return tuple(values)

    @property
    def selected_files(self) -> tuple[DatasetFile, ...]:
        return tuple(entry for entry in self.files if entry.selected)

    @property
    def selected_size_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.selected_files)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "source": self.source,
            "provider": self.provider,
            "mission": self.mission,
            "instrument": self.instrument,
            "location": self.location,
            "acquisition_dates": list(self.acquisition_dates),
            "acquisition_dates_status": self.acquisition_dates_status,
            "resolution": [dict(entry) for entry in self.resolution],
            "coordinate_reference_system": dict(self.coordinate_reference_system),
            "data_type": self.data_type,
            "license": self.license,
            "limitations": list(self.limitations),
            "doi": self.doi,
            "url": self.url,
            "version": self.version,
            "retrieved_at_utc": self.retrieved_at_utc,
            "has_pixels": self.has_pixels,
            "has_labels": self.has_labels,
            "has_temporal_series": self.has_temporal_series,
            "files": [entry.as_dict() for entry in self.files],
            "published_context": dict(self.published_context),
            "notes": self.notes,
        }


def _parse_aware_datetime(value: str, dataset_id: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DatasetManifestError(
            f"{dataset_id}: invalid ISO 8601 datetime {value!r}."
        ) from exc
    if parsed.tzinfo is None:
        raise DatasetManifestError(f"{dataset_id}: datetime must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _parse_acquisition_date(value: str, dataset_id: str) -> date | datetime:
    text = str(value).strip()
    if not text:
        raise DatasetManifestError(f"{dataset_id}: acquisition date cannot be empty.")
    try:
        if "T" in text or " " in text:
            return _parse_aware_datetime(text, dataset_id)
        return date.fromisoformat(text)
    except ValueError as exc:
        raise DatasetManifestError(
            f"{dataset_id}: invalid ISO 8601 acquisition date {value!r}."
        ) from exc


def _validate_resolution_entry(entry: dict[str, Any], dataset_id: str) -> None:
    if not isinstance(entry, dict):
        raise DatasetManifestError(f"{dataset_id}: resolution entries must be objects.")
    try:
        value = float(entry["value"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetManifestError(f"{dataset_id}: resolution value must be numeric.") from exc
    if not value > 0:
        raise DatasetManifestError(f"{dataset_id}: resolution value must be positive.")
    unit = str(entry.get("unit", ""))
    if unit not in _ALLOWED_RESOLUTION_UNITS:
        raise DatasetManifestError(f"{dataset_id}: unsupported resolution unit {unit!r}.")
    if not str(entry.get("product", "")).strip():
        raise DatasetManifestError(f"{dataset_id}: resolution product is required.")


def _file_from_dict(payload: dict[str, Any]) -> DatasetFile:
    if "name" not in payload or "size_bytes" not in payload:
        raise DatasetManifestError("Dataset file entries require name and size_bytes.")
    return DatasetFile(
        name=str(payload["name"]),
        size_bytes=int(payload["size_bytes"]),
        url=None if payload.get("url") is None else str(payload["url"]),
        sha256=None if payload.get("sha256") is None else str(payload["sha256"]),
        role=str(payload.get("role", "data")),
        selected=bool(payload.get("selected", True)),
    )


def _record_from_dict(payload: dict[str, Any]) -> DatasetRecord:
    required = {
        "dataset_id",
        "name",
        "source",
        "mission",
        "instrument",
        "location",
        "acquisition_dates",
        "resolution",
        "coordinate_reference_system",
        "data_type",
        "license",
        "limitations",
        "provider",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise DatasetManifestError(f"Dataset record is missing fields: {', '.join(missing)}.")
    try:
        return DatasetRecord(
            dataset_id=str(payload["dataset_id"]),
            name=str(payload["name"]),
            source=str(payload["source"]),
            provider=str(payload["provider"]),
            mission=str(payload["mission"]),
            instrument=str(payload["instrument"]),
            location=str(payload["location"]),
            acquisition_dates=tuple(str(value) for value in payload["acquisition_dates"]),
            acquisition_dates_status=str(payload.get("acquisition_dates_status", "reported")),
            resolution=tuple(dict(entry) for entry in payload["resolution"]),
            coordinate_reference_system=dict(payload["coordinate_reference_system"]),
            data_type=str(payload["data_type"]),
            license=str(payload["license"]),
            limitations=tuple(str(value) for value in payload["limitations"]),
            doi=None if payload.get("doi") is None else str(payload["doi"]),
            url=None if payload.get("url") is None else str(payload["url"]),
            version=None if payload.get("version") is None else str(payload["version"]),
            retrieved_at_utc=(
                None if payload.get("retrieved_at_utc") is None else str(payload["retrieved_at_utc"])
            ),
            has_pixels=bool(payload.get("has_pixels", False)),
            has_labels=bool(payload.get("has_labels", False)),
            has_temporal_series=bool(payload.get("has_temporal_series", False)),
            files=tuple(_file_from_dict(item) for item in payload.get("files", [])),
            published_context=dict(payload.get("published_context", {})),
            notes=str(payload.get("notes", "")),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, DatasetManifestError):
            raise
        raise DatasetManifestError(
            f"Invalid dataset record {payload.get('dataset_id', '<unknown>')}: {exc}"
        ) from exc


def load_mars_manifest(path: str | Path | None = None) -> tuple[DatasetRecord, ...]:
    manifest_path = Path(path) if path is not None else DEFAULT_MARS_MANIFEST_PATH
    if not manifest_path.exists():
        raise DatasetManifestError(f"Mars manifest not found: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetManifestError(f"Invalid JSON in Mars manifest: {exc}") from exc
    entries = payload.get("datasets")
    if not isinstance(entries, list) or not entries:
        raise DatasetManifestError("Mars manifest must contain a non-empty 'datasets' list.")
    records: list[DatasetRecord] = []
    for entry in entries:
        if isinstance(entry, str):
            dataset_path = (manifest_path.parent / entry).resolve()
            if not dataset_path.exists():
                raise DatasetManifestError(f"Dataset file not found: {dataset_path}")
            try:
                dataset_payload = json.loads(dataset_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise DatasetManifestError(f"Invalid JSON in {dataset_path}: {exc}") from exc
        elif isinstance(entry, dict):
            dataset_payload = entry
        else:
            raise DatasetManifestError("Dataset entries must be paths or objects.")
        records.append(_record_from_dict(dataset_payload))
    seen: set[str] = set()
    for record in records:
        if record.dataset_id in seen:
            raise DatasetManifestError(f"Duplicate dataset_id: {record.dataset_id}")
        seen.add(record.dataset_id)
    return tuple(records)


def dataset_by_id(records: Iterable[DatasetRecord], dataset_id: str) -> DatasetRecord:
    for record in records:
        if record.dataset_id == dataset_id:
            return record
    raise DatasetManifestError(f"Unknown dataset_id: {dataset_id}")


def manifest_summary(records: Iterable[DatasetRecord]) -> dict[str, Any]:
    dataset_list = tuple(records)
    return {
        "dataset_count": len(dataset_list),
        "dataset_ids": [record.dataset_id for record in dataset_list],
        "with_pixels": [record.dataset_id for record in dataset_list if record.has_pixels],
        "with_labels": [record.dataset_id for record in dataset_list if record.has_labels],
        "with_temporal_series": [
            record.dataset_id for record in dataset_list if record.has_temporal_series
        ],
        "dates_unresolved": [
            record.dataset_id
            for record in dataset_list
            if record.acquisition_dates_status in {"requires_pds_resolution", "not_reported"}
        ],
        "selected_size_bytes": sum(record.selected_size_bytes for record in dataset_list),
    }


def validate_manifest_file(path: str | Path | None = None) -> dict[str, Any]:
    try:
        records = load_mars_manifest(path)
    except (DatasetManifestError, json.JSONDecodeError) as exc:
        return {"valid": False, "error": str(exc), "datasets": []}
    return {"valid": True, "error": None, "summary": manifest_summary(records)}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
