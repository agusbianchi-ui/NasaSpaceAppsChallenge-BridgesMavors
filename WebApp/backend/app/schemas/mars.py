from typing import Literal

from pydantic import BaseModel, Field


class SpatialReference(BaseModel):
    """Coordinate reference system used by a data product."""

    code: str
    name: str
    units: str
    extent: list[float] | None = None
    notes: str | None = None


class DataProvenance(BaseModel):
    """Origin and verification state of a data product."""

    provider: str
    source_url: str
    citation: str | None = None
    attribution: str | None = None
    verified: bool = False
    verified_at: str | None = None
    retrieved_at: str | None = None
    verification_notes: str | None = None
    product_created_date: str | None = None


class WMSTileMatrix(BaseModel):
    """One zoom level advertised by a WMTS TileMatrixSet."""

    id: str
    scale_denominator: float
    resolution_degrees: float
    tile_width: int
    tile_height: int
    matrix_width: int
    matrix_height: int


class WMTSCapabilities(BaseModel):
    """Normalized metadata extracted from a WMTS GetCapabilities document."""

    service: str = "OGC WMTS"
    version: str = "1.0.0"
    endpoint: str
    capabilities_url: str
    resource_url_template: str
    layer_identifier: str
    style: str
    format: str
    tile_matrix_set: str
    supported_crs: str
    tile_matrices: list[WMSTileMatrix] = Field(default_factory=list)
    source: Literal["verified_snapshot", "live"] = "verified_snapshot"
    retrieved_at: str | None = None
    notes: str | None = None


class MarsDataSource(BaseModel):
    id: str
    name: str
    agency: str
    mission: str
    description: str
    url: str
    layer_ids: list[str] = Field(default_factory=list)


class MarsLayer(BaseModel):
    id: str
    name: str
    source: str
    mission: str
    instrument: str
    description: str
    data_type: str
    region: str
    resolution: float | None = None
    resolution_unit: str | None = None
    projection: str | None = None
    bounding_box: list[float] | None = None
    source_url: str
    acquisition_date: str | None = None
    processing_level: str | None = None
    limitations: str | None = None
    attribution: str
    status: Literal["available", "catalog_only", "planned"] = "catalog_only"
    visualizable: bool = False
    spatial_reference: SpatialReference | None = None
    provenance: DataProvenance | None = None
    wmts: WMTSCapabilities | None = None


class MarsLocation(BaseModel):
    id: str
    name: str
    region: str
    latitude: float
    longitude: float
    diameter_km: float | None = None
    description: str
    source_ids: list[str] = Field(default_factory=list)
    layer_ids: list[str] = Field(default_factory=list)
    bounding_box: list[float] | None = None
    spatial_reference: SpatialReference | None = None
    limitations: str | None = None
