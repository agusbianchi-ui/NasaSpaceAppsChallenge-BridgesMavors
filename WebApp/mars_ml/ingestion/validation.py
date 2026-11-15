"""Validation gates for Martian metadata, vectors, rasters and tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from mars_ml.computer_vision.image_io import SpatialMetadata, checksum_file
from mars_ml.ingestion.catalog import (
    DatasetFile,
    DatasetManifestError,
    DatasetRecord,
    load_mars_manifest,
    manifest_summary,
)
from mars_ml.ingestion.readers import (
    IngestionError,
    TableData,
    VectorLayer,
    read_raster_metadata,
)


class ValidationError(ValueError):
    """Raised when an ingested product fails a scientific safety gate."""


@dataclass(frozen=True)
class FileVerification:
    dataset_id: str
    name: str
    relative_path: str
    expected_size_bytes: int
    actual_size_bytes: int | None
    expected_sha256: str | None
    actual_sha256: str | None
    status: str
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "relative_path": self.relative_path,
            "expected_size_bytes": self.expected_size_bytes,
            "actual_size_bytes": self.actual_size_bytes,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class RasterInspection:
    metadata: SpatialMetadata
    height: int
    width: int
    band_count: int
    dtypes: tuple[str, ...]
    crs_units: str | None
    metric_resolution: tuple[float, float] | None
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.as_dict(),
            "height": self.height,
            "width": self.width,
            "band_count": self.band_count,
            "dtypes": list(self.dtypes),
            "crs_units": self.crs_units,
            "metric_resolution": (
                list(self.metric_resolution) if self.metric_resolution is not None else None
            ),
            "warnings": list(self.warnings),
        }


def _crs_units(crs: str | None) -> str | None:
    if not crs:
        return None
    try:
        from rasterio.crs import CRS

        parsed = CRS.from_string(crs)
    except Exception:
        return None
    if parsed.is_geographic:
        return "degrees"
    try:
        return parsed.linear_units or "unknown"
    except Exception:
        return "unknown"


def inspect_raster(path: str | Path) -> RasterInspection:
    metadata = read_raster_metadata(path)
    extra = dict(metadata.extra)
    units = _crs_units(metadata.crs)
    warnings: list[str] = []
    metric_resolution: tuple[float, float] | None = None
    if units is None:
        warnings.append("CRS is missing or could not be parsed.")
    elif units == "degrees":
        warnings.append("Resolution is in degrees, not metres; metric conversion is withheld.")
    elif units in {"metre", "meter", "m"}:
        if metadata.resolution is None:
            raise ValidationError("Metric raster has no resolution.")
        metric_resolution = metadata.resolution
    else:
        warnings.append(f"CRS linear unit {units!r} is not a recognized metre unit.")
    return RasterInspection(
        metadata=metadata,
        height=int(extra.get("height", 0)),
        width=int(extra.get("width", 0)),
        band_count=int(extra.get("count", 0)),
        dtypes=tuple(str(value) for value in extra.get("dtypes", ())),
        crs_units=units,
        metric_resolution=metric_resolution,
        warnings=tuple(warnings),
    )


def require_metric_resolution(metadata: SpatialMetadata) -> tuple[float, float]:
    units = _crs_units(metadata.crs)
    if units != "metre" and units != "meter" and units != "m":
        raise ValidationError(
            f"Metric conversion requires a metre CRS; found units {units!r}."
        )
    if metadata.resolution is None or not all(
        np.isfinite(value) and value > 0 for value in metadata.resolution
    ):
        raise ValidationError("Metric conversion requires a valid (x, y) resolution.")
    return metadata.resolution


def _verify_file(
    record: DatasetRecord,
    entry: DatasetFile,
    root: Path,
) -> FileVerification:
    root_resolved = root.resolve()
    target = (root / record.dataset_id / entry.name).resolve()
    try:
        relative = target.relative_to(root_resolved)
    except ValueError:
        return FileVerification(
            dataset_id=record.dataset_id,
            name=entry.name,
            relative_path=str(target),
            expected_size_bytes=entry.size_bytes,
            actual_size_bytes=None,
            expected_sha256=entry.sha256,
            actual_sha256=None,
            status="invalid_path",
            message="Manifest path escapes the destination root.",
        )
    if not target.exists():
        return FileVerification(
            dataset_id=record.dataset_id,
            name=entry.name,
            relative_path=str(target.relative_to(root_resolved)),
            expected_size_bytes=entry.size_bytes,
            actual_size_bytes=None,
            expected_sha256=entry.sha256,
            actual_sha256=None,
            status="missing",
            message="File does not exist.",
        )
    actual_size = target.stat().st_size
    actual_sha = checksum_file(target) if entry.sha256 is not None else None
    if actual_size != entry.size_bytes:
        return FileVerification(
            dataset_id=record.dataset_id,
            name=entry.name,
            relative_path=str(target.relative_to(root_resolved)),
            expected_size_bytes=entry.size_bytes,
            actual_size_bytes=actual_size,
            expected_sha256=entry.sha256,
            actual_sha256=actual_sha,
            status="size_mismatch",
            message=f"Expected {entry.size_bytes} bytes; found {actual_size}.",
        )
    if entry.sha256 is None:
        return FileVerification(
            dataset_id=record.dataset_id,
            name=entry.name,
            relative_path=str(target.relative_to(root_resolved)),
            expected_size_bytes=entry.size_bytes,
            actual_size_bytes=actual_size,
            expected_sha256=None,
            actual_sha256=None,
            status="size_verified",
            message="Size matches; no SHA-256 was declared, so the checksum is unverified.",
        )
    if actual_sha != entry.sha256.lower():
        return FileVerification(
            dataset_id=record.dataset_id,
            name=entry.name,
            relative_path=str(target.relative_to(root_resolved)),
            expected_size_bytes=entry.size_bytes,
            actual_size_bytes=actual_size,
            expected_sha256=entry.sha256,
            actual_sha256=actual_sha,
            status="checksum_mismatch",
            message="SHA-256 does not match the manifest.",
        )
    return FileVerification(
        dataset_id=record.dataset_id,
        name=entry.name,
        relative_path=str(target.relative_to(root_resolved)),
        expected_size_bytes=entry.size_bytes,
        actual_size_bytes=actual_size,
        expected_sha256=entry.sha256,
        actual_sha256=actual_sha,
        status="verified",
        message="Size and SHA-256 match the manifest.",
    )


def verify_manifest_files(
    records: Iterable[DatasetRecord],
    root: str | Path,
    *,
    dataset_ids: Iterable[str] | None = None,
    selected_only: bool = True,
) -> dict[str, Any]:
    """Verify locally downloaded files against manifest sizes and checksums."""

    root_path = Path(root)
    selected_ids = set(dataset_ids) if dataset_ids is not None else None
    checks: list[FileVerification] = []
    for record in records:
        if selected_ids is not None and record.dataset_id not in selected_ids:
            continue
        for entry in record.files:
            if selected_only and not entry.selected:
                continue
            checks.append(_verify_file(record, entry, root_path))
    verified = sum(1 for item in checks if item.status == "verified")
    return {
        "root": str(root_path.resolve()),
        "checked_count": len(checks),
        "verified_count": verified,
        "all_verified": bool(checks) and verified == len(checks),
        "files": [item.as_dict() for item in checks],
    }


def validate_vector_layer(layer: VectorLayer) -> dict[str, Any]:
    if not layer.records:
        raise ValidationError("Vector layer has no records.")
    ids: set[str] = set()
    for record in layer.records:
        if record.record_id in ids:
            raise ValidationError(f"Duplicate vector record ID: {record.record_id}")
        ids.add(record.record_id)
        if not all(np.isfinite(value) for value in record.bbox):
            raise ValidationError(f"Record {record.record_id}: non-finite bounding box.")
        west, south, east, north = record.bbox
        if west > east or south > north:
            raise ValidationError(f"Record {record.record_id}: invalid bounding box order.")
        if south < -90.0 or north > 90.0:
            raise ValidationError(
                f"Record {record.record_id}: latitude outside [-90, 90]; check CRS units."
            )
    return {
        "record_count": len(layer.records),
        "geometry_type": layer.geometry_type,
        "fields": list(layer.fields),
        "crs": layer.crs,
        "duplicate_ids": 0,
    }


def validate_table(table: TableData) -> dict[str, Any]:
    if not table.rows:
        raise ValidationError("Table has no rows.")
    if len(set(table.columns)) != len(table.columns):
        raise ValidationError("Table has duplicate column names.")
    missing_by_column: dict[str, int] = {}
    for column in table.columns:
        missing = sum(1 for row in table.rows if row.get(column) is None)
        if missing:
            missing_by_column[column] = missing
    return {
        "row_count": table.row_count,
        "column_count": len(table.columns),
        "columns": list(table.columns),
        "missing_values": missing_by_column,
    }


def validate_manifest(records: Iterable[DatasetRecord]) -> dict[str, Any]:
    dataset_list = tuple(records)
    if not dataset_list:
        raise DatasetManifestError("Manifest has no datasets.")
    for record in dataset_list:
        if record.has_temporal_series and not (
            record.acquisition_dates
            or record.acquisition_dates_status
            in {"requires_pds_resolution", "not_reported"}
        ):
            raise DatasetManifestError(
                f"{record.dataset_id}: temporal series requires dates or an explicit unresolved status."
            )
        if record.has_labels and not record.files and record.data_type != "assessment_record":
            raise DatasetManifestError(
                f"{record.dataset_id}: labelled dataset must declare at least one file."
            )
        for entry in record.files:
            if entry.selected and entry.url is None:
                raise DatasetManifestError(
                    f"{record.dataset_id}/{entry.name}: selected files require a URL."
                )
    return manifest_summary(dataset_list)


def validate_manifest_file(path: str | Path | None = None) -> dict[str, Any]:
    try:
        records = load_mars_manifest(path)
        summary = validate_manifest(records)
    except (DatasetManifestError, IngestionError, ValueError) as exc:
        return {"valid": False, "error": str(exc), "summary": None}
    return {"valid": True, "error": None, "summary": summary}
