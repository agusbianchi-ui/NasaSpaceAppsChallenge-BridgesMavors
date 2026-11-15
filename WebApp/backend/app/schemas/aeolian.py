from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field, model_validator


class SpatialResolutionInput(BaseModel):
    """Explicit metric scale supplied by the caller."""

    x_m_per_pixel: float = Field(gt=0)
    y_m_per_pixel: float | None = Field(default=None, gt=0)
    source: str = Field(min_length=1, max_length=500)

    def as_tuple(self) -> tuple[float, float]:
        y_value = self.x_m_per_pixel if self.y_m_per_pixel is None else self.y_m_per_pixel
        return (float(self.x_m_per_pixel), float(y_value))


class RegistrationOptions(BaseModel):
    max_features: int = Field(default=5000, ge=100)
    match_ratio: float = Field(default=0.75, gt=0, lt=1)
    ransac_reproj_threshold_px: float = Field(default=3.0, gt=0)
    min_matches: int = Field(default=20, ge=4)
    min_inliers: int = Field(default=12, ge=4)
    min_inlier_ratio: float = Field(default=0.3, gt=0, le=1)
    max_rms_error_px: float = Field(default=3.0, gt=0)
    min_phase_response: float = Field(default=0.12, ge=0)
    allow_phase_correlation: bool = True


class AnalysisObservationInput(BaseModel):
    observation_id: str = Field(min_length=1, max_length=120)
    product_id: str = Field(min_length=1, max_length=200)
    acquisition_datetime_utc: AwareDatetime
    image_path: str = Field(min_length=1, max_length=1000)
    mask_path: str = Field(min_length=1, max_length=1000)
    crs: str | None = Field(default=None, min_length=1, max_length=500)


class AeolianAnalyzeRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=120)
    observations: list[AnalysisObservationInput] = Field(min_length=2, max_length=50)
    method: Literal["centroid", "crest"] = "centroid"
    meters_per_pixel: SpatialResolutionInput | None = None
    min_interval_days: float = Field(default=1.0, ge=0)
    include_geometry: bool = True
    registration: RegistrationOptions = Field(default_factory=RegistrationOptions)

    @model_validator(mode="after")
    def validate_observation_ids(self) -> "AeolianAnalyzeRequest":
        identifiers = [item.observation_id for item in self.observations]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("observation_id values must be unique.")
        return self


class AeolianDatasetFile(BaseModel):
    name: str
    size_bytes: int
    url: str | None = None
    sha256: str | None = None
    role: str
    selected: bool


class AeolianResolution(BaseModel):
    value: float
    unit: str
    product: str


class AeolianCoordinateReferenceSystem(BaseModel):
    name: str
    units: str
    code: str | None = None
    spheroid: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AeolianDatasetCapability(BaseModel):
    temporal_analysis: bool
    analysis_ready: bool
    local_observations_required: bool = True
    blockers: list[str] = Field(default_factory=list)


class AeolianDataset(BaseModel):
    dataset_id: str
    name: str
    source: str
    provider: str
    mission: str
    instrument: str
    location: str
    acquisition_dates: list[str]
    acquisition_dates_status: str
    resolution: list[AeolianResolution]
    coordinate_reference_system: AeolianCoordinateReferenceSystem
    data_type: str
    license: str
    limitations: list[str]
    doi: str | None = None
    url: str | None = None
    version: str | None = None
    retrieved_at_utc: str | None = None
    has_pixels: bool
    has_labels: bool
    has_temporal_series: bool
    files: list[AeolianDatasetFile]
    published_context: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    analysis_capability: AeolianDatasetCapability


class AnalysisObservationResult(BaseModel):
    observation_id: str
    product_id: str
    acquisition_datetime_utc: str
    shape: list[int]
    crs: str
    mask_foreground_pixels: int
    image_path: str
    mask_path: str
    image_sha256: str
    mask_sha256: str


class RegistrationQuality(BaseModel):
    method: str
    reliable: bool
    matches: int = 0
    inliers: int = 0
    inlier_ratio: float = 0.0
    rms_error_px: float | None = None
    median_error_px: float | None = None
    phase_response: float | None = None
    message: str = ""
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ObservedMigration(BaseModel):
    source: Literal["observed"] = "observed"
    dataset_id: str
    dune_id: str
    method: str
    reference_datetime_utc: str | None
    moving_datetime_utc: str | None
    interval_days: float | None
    dx_m: float | None
    dy_m: float | None
    distance_m: float | None
    direction_azimuth_deg: float | None
    rate_m_per_earth_year: float | None
    rate_standard_error_m_per_earth_year: float | None
    distance_ci95_m: list[float] | None
    valid: bool
    reasons: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class AnalysisPair(BaseModel):
    reference_id: str
    moving_id: str
    reference_datetime_utc: str
    moving_datetime_utc: str
    status: str
    registration: RegistrationQuality | None = None
    displacement: dict[str, Any] | None = None
    observed_migration: ObservedMigration | None = None
    geometry: dict[str, Any] | None = None
    environment: dict[str, Any] | None = None
    reasons: list[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    observation_count: int
    pair_count: int
    valid_migration_count: int
    method_summary: dict[str, Any] = Field(default_factory=dict)


class InputFileProvenance(BaseModel):
    observation_id: str
    role: Literal["image", "mask"]
    path: str
    sha256: str


class AnalysisProvenance(BaseModel):
    dataset_id: str
    dataset_name: str
    dataset_source: str
    dataset_provider: str
    dataset_doi: str | None = None
    dataset_url: str | None = None
    dataset_retrieved_at_utc: str | None = None
    local_observations_required: bool = True
    files: list[InputFileProvenance]
    crs: str
    meters_per_pixel: list[float] | None = None
    scale_source: str | None = None
    software: str
    generated_at_utc: str
    scientific_status: str


class PredictedMigration(BaseModel):
    source: Literal["model"] = "model"
    model_id: str
    target: Literal["migration_rate", "migration_direction", "both"]
    rate_m_per_earth_year: float | None = None
    direction_azimuth_deg: float | None = None
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class AeolianAnalysisResult(BaseModel):
    analysis_id: str
    dataset_id: str
    status: Literal["completed", "completed_without_valid_migration"]
    created_at_utc: str
    dataset: AeolianDataset
    observations: list[AnalysisObservationResult]
    pairs: list[AnalysisPair]
    summary: AnalysisSummary
    provenance: AnalysisProvenance
    units: dict[str, str]
    limitations: list[str]
    notes: list[str]
    predictions: list[PredictedMigration] = Field(default_factory=list)
    prediction_status: Literal["not_available", "available"] = "not_available"


class PredictionFeatures(BaseModel):
    wind_speed_m_s: float | None = Field(default=None, ge=0)
    wind_direction_deg: float | None = Field(default=None, ge=0, lt=360)
    atmospheric_density_kg_m3: float | None = Field(default=None, gt=0)
    pressure_pa: float | None = Field(default=None, gt=0)
    temperature_k: float | None = Field(default=None, gt=0)
    dune_height_m: float | None = Field(default=None, gt=0)
    dune_width_m: float | None = Field(default=None, gt=0)
    grain_diameter_m: float | None = Field(default=None, gt=0)
    grain_density_kg_m3: float | None = Field(default=None, gt=0)
    gravity_m_s2: float | None = Field(default=None, gt=0)


class AeolianPredictRequest(BaseModel):
    analysis_id: str | None = Field(default=None, min_length=1, max_length=120)
    dataset_id: str | None = Field(default=None, min_length=1, max_length=120)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    target: Literal["migration_rate", "migration_direction", "both"] = "both"
    horizon_earth_years: float | None = Field(default=None, gt=0)
    features: PredictionFeatures = Field(default_factory=PredictionFeatures)

    @model_validator(mode="after")
    def validate_reference(self) -> "AeolianPredictRequest":
        if self.analysis_id is None and self.dataset_id is None:
            raise ValueError("analysis_id or dataset_id is required.")
        return self


class PredictionAvailability(BaseModel):
    available: bool
    reason: str
    required_artifacts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
