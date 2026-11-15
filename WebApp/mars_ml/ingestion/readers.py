"""Readers for Martian vector, tabular and raster products.

Shapefiles are read with pyshp and converted to GeoJSON-like geometry. Tables
are read with pandas and openpyxl. GeoTIFF metadata is read with Rasterio. All
readers preserve the source path and never infer missing dates or scales.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from mars_ml.computer_vision.image_io import ImageValidationError, SpatialMetadata


class IngestionError(ValueError):
    """Raised when a vector, table or raster cannot be read safely."""


@dataclass(frozen=True)
class VectorRecord:
    record_id: str
    attributes: dict[str, Any]
    geometry: dict[str, Any]
    bbox: tuple[float, float, float, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "attributes": dict(self.attributes),
            "geometry": dict(self.geometry),
            "bbox": list(self.bbox),
        }


@dataclass(frozen=True)
class VectorLayer:
    path: str
    crs: str | None
    geometry_type: str
    fields: tuple[str, ...]
    records: tuple[VectorRecord, ...]
    source_format: str

    def __post_init__(self) -> None:
        if not self.records:
            raise IngestionError(f"Vector layer has no records: {self.path}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "crs": self.crs,
            "geometry_type": self.geometry_type,
            "fields": list(self.fields),
            "record_count": len(self.records),
            "source_format": self.source_format,
        }


@dataclass(frozen=True)
class TableData:
    path: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    sheet_name: str | None = None

    def __post_init__(self) -> None:
        if not self.columns:
            raise IngestionError(f"Table has no columns: {self.path}")
        if not self.rows:
            raise IngestionError(f"Table has no rows: {self.path}")

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "columns": list(self.columns),
            "row_count": self.row_count,
            "sheet_name": self.sheet_name,
        }


def _native(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if not np.isfinite(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _iter_positions(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2 and all(
        isinstance(item, (int, float)) for item in value[:2]
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_positions(item)


def _geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    coordinates = geometry.get("coordinates")
    positions = list(_iter_positions(coordinates))
    if not positions:
        raise IngestionError("Geometry has no coordinate pairs.")
    xs = [position[0] for position in positions]
    ys = [position[1] for position in positions]
    return min(xs), min(ys), max(xs), max(ys)


def _normalise_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type is None or coordinates is None:
        raise IngestionError("Geometry requires type and coordinates.")
    if geometry_type == "GeometryCollection":
        raise IngestionError("GeometryCollection is not supported for annotations.")
    return {"type": str(geometry_type), "coordinates": coordinates}


def _record_id(attributes: dict[str, Any], index: int) -> str:
    for key in ("id", "ID", "Id", "fid", "FID", "OBJECTID", "objectid"):
        if key in attributes and attributes[key] is not None:
            return str(attributes[key])
    return str(index)


def _crs_to_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def read_shapefile(path: str | Path) -> VectorLayer:
    shape_path = Path(path)
    if not shape_path.exists():
        raise IngestionError(f"Shapefile not found: {shape_path}")
    try:
        import shapefile
    except ImportError as exc:
        raise IngestionError("pyshp is required to read shapefiles.") from exc
    reader = shapefile.Reader(str(shape_path))
    fields = tuple(field[0] for field in reader.fields[1:])
    crs = _crs_to_string(getattr(reader, "crs_wkt", None) or getattr(reader, "crs", None))
    records: list[VectorRecord] = []
    geometry_types: set[str] = set()
    for index, shape_record in enumerate(reader.iterShapeRecords()):
        geometry = _normalise_geometry(dict(shape_record.shape.__geo_interface__))
        raw_attributes = shape_record.record
        if hasattr(raw_attributes, "as_dict"):
            attributes = {key: _native(value) for key, value in raw_attributes.as_dict().items()}
        else:
            attributes = {
                key: _native(value) for key, value in zip(fields, list(raw_attributes))
            }
        geometry_types.add(str(geometry["type"]))
        records.append(
            VectorRecord(
                record_id=_record_id(attributes, index),
                attributes=attributes,
                geometry=geometry,
                bbox=_geometry_bbox(geometry),
            )
        )
    if len(geometry_types) != 1:
        raise IngestionError(f"Mixed geometry types are not supported: {sorted(geometry_types)}")
    return VectorLayer(
        path=str(shape_path.resolve()),
        crs=crs,
        geometry_type=geometry_types.pop(),
        fields=fields,
        records=tuple(records),
        source_format="shapefile",
    )


def _geojson_crs(payload: dict[str, Any]) -> str | None:
    crs = payload.get("crs")
    if isinstance(crs, dict):
        properties = crs.get("properties")
        if isinstance(properties, dict) and properties.get("name"):
            return str(properties["name"])
        return json.dumps(crs)
    return None


def read_geojson(path: str | Path) -> VectorLayer:
    geojson_path = Path(path)
    if not geojson_path.exists():
        raise IngestionError(f"GeoJSON not found: {geojson_path}")
    payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise IngestionError("GeoJSON FeatureCollection has no features.")
    elif payload.get("type") == "Feature":
        features = [payload]
    elif payload.get("type") in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }:
        features = [{"type": "Feature", "properties": {}, "geometry": payload}]
    else:
        raise IngestionError("Unsupported GeoJSON root type.")
    records: list[VectorRecord] = []
    geometry_types: set[str] = set()
    fields: set[str] = set()
    for index, feature in enumerate(features):
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise IngestionError(f"Feature {index} has no geometry object.")
        normalised = _normalise_geometry(geometry)
        attributes = {
            str(key): _native(value)
            for key, value in dict(feature.get("properties") or {}).items()
        }
        fields.update(attributes)
        geometry_types.add(str(normalised["type"]))
        records.append(
            VectorRecord(
                record_id=_record_id(attributes, index),
                attributes=attributes,
                geometry=normalised,
                bbox=_geometry_bbox(normalised),
            )
        )
    if len(geometry_types) != 1:
        raise IngestionError(f"Mixed geometry types are not supported: {sorted(geometry_types)}")
    return VectorLayer(
        path=str(geojson_path.resolve()),
        crs=_geojson_crs(payload),
        geometry_type=geometry_types.pop(),
        fields=tuple(sorted(fields)),
        records=tuple(records),
        source_format="geojson",
    )


def read_vector(path: str | Path) -> VectorLayer:
    vector_path = Path(path)
    suffix = vector_path.suffix.lower()
    if suffix == ".shp":
        return read_shapefile(vector_path)
    if suffix in {".geojson", ".json"}:
        return read_geojson(vector_path)
    raise IngestionError(
        f"Unsupported vector format {suffix!r}; use .shp, .geojson or .json."
    )


def read_table(path: str | Path, *, sheet_name: str | int | None = None) -> TableData:
    table_path = Path(path)
    if not table_path.exists():
        raise IngestionError(f"Table not found: {table_path}")
    try:
        import pandas as pd
    except ImportError as exc:
        raise IngestionError("pandas is required to read tables.") from exc
    suffix = table_path.suffix.lower()
    try:
        if suffix == ".csv":
            frame = pd.read_csv(table_path)
            resolved_sheet = None
        elif suffix in {".xlsx", ".xlsm"}:
            frame = pd.read_excel(table_path, sheet_name=sheet_name)
            resolved_sheet = None if sheet_name is None else str(sheet_name)
        else:
            raise IngestionError(f"Unsupported table format {suffix!r}; use .csv or .xlsx.")
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"Could not read table {table_path}: {exc}") from exc
    if isinstance(frame, dict):
        if not frame:
            raise IngestionError("Workbook has no sheets.")
        first_sheet, frame = next(iter(frame.items()))
        resolved_sheet = str(first_sheet)
    frame = frame.dropna(how="all")
    if frame.empty:
        raise IngestionError(f"Table has no data rows: {table_path}")
    columns = tuple(str(column) for column in frame.columns)
    rows = tuple(
        {str(key): _native(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    )
    return TableData(
        path=str(table_path.resolve()),
        columns=columns,
        rows=rows,
        sheet_name=resolved_sheet,
    )


def read_raster_metadata(path: str | Path) -> SpatialMetadata:
    raster_path = Path(path)
    if not raster_path.exists():
        raise IngestionError(f"Raster not found: {raster_path}")
    try:
        import rasterio
    except ImportError as exc:
        raise IngestionError("Rasterio is required to read raster metadata.") from exc
    with rasterio.open(raster_path) as dataset:
        transform = dataset.transform
        resolution = (abs(float(transform.a)), abs(float(transform.e)))
        if not all(np.isfinite(value) and value > 0 for value in resolution):
            raise ImageValidationError(f"Invalid raster resolution: {resolution}")
        return SpatialMetadata(
            crs=dataset.crs.to_string() if dataset.crs else None,
            transform=(
                float(transform.a),
                float(transform.b),
                float(transform.c),
                float(transform.d),
                float(transform.e),
                float(transform.f),
            ),
            resolution=resolution,
            nodata=float(dataset.nodata) if dataset.nodata is not None else None,
            source=str(raster_path),
            band_names=tuple(
                description or f"band_{index + 1}"
                for index, description in enumerate(dataset.descriptions or ())
            ),
            extra={
                "driver": dataset.driver,
                "height": dataset.height,
                "width": dataset.width,
                "count": dataset.count,
                "dtypes": list(dataset.dtypes),
            },
        )
