from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import numpy as np

from app.core.config import get_settings
from app.schemas.aeolian import (
    AeolianAnalysisResult,
    AeolianAnalyzeRequest,
    AeolianCoordinateReferenceSystem,
    AeolianDataset,
    AeolianDatasetCapability,
    AeolianDatasetFile,
    AeolianPredictRequest,
    AeolianResolution,
    AnalysisObservationResult,
    AnalysisPair,
    AnalysisProvenance,
    AnalysisSummary,
    InputFileProvenance,
    ObservedMigration,
    PredictedMigration,
    RegistrationQuality,
)

from mars_ml.aeolian_dynamics.migration_analysis import (
    MigrationObservation,
    summarize_methods,
)
from mars_ml.computer_vision.image_io import (
    RasterImage,
    checksum_file,
    crs_linear_units,
    load_image,
    load_raster,
)
from mars_ml.computer_vision.image_registration import (
    RegistrationConfig,
)
from mars_ml.inference.mars_sequence import (
    MarsSequenceConfig,
    MarsSequenceError,
    SequenceObservation,
    run_mars_sequence,
)
from mars_ml.ingestion.catalog import (
    DatasetManifestError,
    DatasetRecord,
    load_mars_manifest,
)

_GEOSPATIAL_SUFFIXES = {".tif", ".tiff", ".jp2", ".img", ".vrt"}


class AeolianServiceError(Exception):
    status_code = 500
    code = "internal_error"


class AeolianConfigurationError(AeolianServiceError):
    pass


class AeolianDatasetNotFound(AeolianServiceError):
    status_code = 404
    code = "not_found"


class AeolianValidationError(AeolianServiceError):
    status_code = 422
    code = "validation_error"


class AeolianAnalysisNotFound(AeolianServiceError):
    status_code = 404
    code = "not_found"


class PredictionUnavailableError(AeolianServiceError):
    status_code = 501
    code = "not_implemented"

    def __init__(self, message: str, required_artifacts: list[str]) -> None:
        super().__init__(message)
        self.required_artifacts = required_artifacts


class PredictionProvider(Protocol):
    def predict(
        self,
        request: AeolianPredictRequest,
        analysis: AeolianAnalysisResult | None,
    ) -> list[PredictedMigration]: ...


class UnavailablePredictionProvider:
    """Prediction placeholder that never fabricates a model result."""

    def predict(
        self,
        request: AeolianPredictRequest,
        analysis: AeolianAnalysisResult | None,
    ) -> list[PredictedMigration]:
        raise PredictionUnavailableError(
            (
                "Prediction is not available: no scientifically validated model "
                "checkpoint, training report or Mars validation dataset is "
                "registered in MARS OPS."
            ),
            required_artifacts=[
                "A trained segmentation and/or regression checkpoint.",
                "A run report with held-out grouped metrics.",
                "Verified Mars observations with explicit dates and metric scale.",
                "An independent validation set that is not used for training.",
                "Explicit uncertainty calibration for the requested target.",
            ],
        )


def _canonical_crs(value: str) -> str:
    try:
        from rasterio.crs import CRS

        return CRS.from_user_input(value).to_string()
    except Exception:
        return value.strip().lower()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


class AeolianService:
    def __init__(
        self,
        *,
        data_root: str | Path | None = None,
        manifest_path: str | Path | None = None,
        prediction_provider: PredictionProvider | None = None,
    ) -> None:
        settings = get_settings()
        self.data_root = Path(
            data_root if data_root is not None else settings.aeolian_data_root
        )
        self.manifest_path = (
            None if manifest_path is None else Path(manifest_path)
        )
        self.prediction_provider = (
            prediction_provider or UnavailablePredictionProvider()
        )
        self._results: dict[str, AeolianAnalysisResult] = {}
        self._results_lock = threading.Lock()

    def _records(self) -> tuple[DatasetRecord, ...]:
        try:
            return load_mars_manifest(self.manifest_path)
        except DatasetManifestError as exc:
            raise AeolianConfigurationError(str(exc)) from exc

    def _record(self, dataset_id: str) -> DatasetRecord:
        for record in self._records():
            if record.dataset_id == dataset_id:
                return record
        raise AeolianDatasetNotFound(f"Dataset '{dataset_id}' not found.")

    def _dataset_dto(self, record: DatasetRecord) -> AeolianDataset:
        crs = record.coordinate_reference_system
        known = {"name", "units", "code", "spheroid"}
        blockers: list[str] = []
        if not record.has_temporal_series:
            blockers.append(
                "Dataset metadata does not declare a temporal image series."
            )
        if not record.has_pixels:
            blockers.append(
                "The repository manifest contains metadata only; observations "
                "must be supplied as local files."
            )
        if not record.acquisition_dates:
            blockers.append(
                "Acquisition dates are not stored in the manifest "
                f"(status: {record.acquisition_dates_status}). Dates must be "
                "resolved and supplied per observation."
            )
        return AeolianDataset(
            dataset_id=record.dataset_id,
            name=record.name,
            source=record.source,
            provider=record.provider,
            mission=record.mission,
            instrument=record.instrument,
            location=record.location,
            acquisition_dates=list(record.acquisition_dates),
            acquisition_dates_status=record.acquisition_dates_status,
            resolution=[
                AeolianResolution(
                    value=float(entry["value"]),
                    unit=str(entry["unit"]),
                    product=str(entry["product"]),
                )
                for entry in record.resolution
            ],
            coordinate_reference_system=AeolianCoordinateReferenceSystem(
                name=str(crs.get("name", "")),
                units=str(crs.get("units", "")),
                code=None if crs.get("code") is None else str(crs["code"]),
                spheroid=(
                    None if crs.get("spheroid") is None else str(crs["spheroid"])
                ),
                details={
                    str(key): value
                    for key, value in crs.items()
                    if key not in known
                },
            ),
            data_type=record.data_type,
            license=record.license,
            limitations=list(record.limitations),
            doi=record.doi,
            url=record.url,
            version=record.version,
            retrieved_at_utc=record.retrieved_at_utc,
            has_pixels=record.has_pixels,
            has_labels=record.has_labels,
            has_temporal_series=record.has_temporal_series,
            files=[
                AeolianDatasetFile(
                    name=entry.name,
                    size_bytes=entry.size_bytes,
                    url=entry.url,
                    sha256=entry.sha256,
                    role=entry.role,
                    selected=entry.selected,
                )
                for entry in record.files
            ],
            published_context=dict(record.published_context),
            notes=record.notes,
            analysis_capability=AeolianDatasetCapability(
                temporal_analysis=record.has_temporal_series,
                analysis_ready=bool(
                    record.has_temporal_series
                    and record.has_pixels
                    and record.acquisition_dates
                ),
                local_observations_required=True,
                blockers=blockers,
            ),
        )

    def list_datasets(self) -> list[AeolianDataset]:
        return [self._dataset_dto(record) for record in self._records()]

    def _resolve_path(self, value: str, field_name: str) -> tuple[Path, str]:
        if Path(value).is_absolute():
            raise AeolianValidationError(
                f"{field_name} must be relative to AEOLIAN_DATA_ROOT."
            )
        if not self.data_root.exists() or not self.data_root.is_dir():
            raise AeolianConfigurationError(
                f"AEOLIAN_DATA_ROOT is not an existing directory: {self.data_root}"
            )
        root = self.data_root.resolve()
        candidate = (root / value).resolve()
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise AeolianValidationError(
                f"{field_name} escapes AEOLIAN_DATA_ROOT."
            ) from exc
        if not candidate.is_file():
            raise AeolianValidationError(f"{field_name} not found: {relative.as_posix()}")
        return candidate, relative.as_posix()

    def _load_image(self, path: Path, field_name: str) -> RasterImage:
        try:
            if path.suffix.lower() in _GEOSPATIAL_SUFFIXES:
                return load_raster(path)
            return load_image(path)
        except Exception as exc:
            raise AeolianValidationError(
                f"{field_name} could not be loaded: {exc}"
            ) from exc

    def _load_mask(self, path: Path, field_name: str) -> np.ndarray:
        image = self._load_image(path, field_name)
        if image.data.ndim != 2:
            raise AeolianValidationError(
                f"{field_name} must be a single-band raster."
            )
        mask = np.asarray(image.data) > 0
        if not np.any(mask):
            raise AeolianValidationError(f"{field_name} is empty.")
        return mask

    def _validate_scale(
        self,
        metadata: object,
        scale: tuple[float, float],
        field_name: str,
    ) -> None:
        resolution = getattr(metadata, "resolution", None)
        crs = getattr(metadata, "crs", None)
        if resolution is None:
            return
        units = crs_linear_units(crs)
        if units not in {"metre", "meter", "m"}:
            raise AeolianValidationError(
                f"{field_name}: raster resolution is in {units!r}, not metres; "
                "a metric scale cannot be verified from this product."
            )
        if not np.allclose(
            (float(resolution[0]), float(resolution[1])),
            scale,
            rtol=1e-3,
            atol=1e-6,
        ):
            raise AeolianValidationError(
                f"{field_name}: declared scale {scale} does not match raster "
                f"resolution {tuple(float(value) for value in resolution)}."
            )

    def _build_observations(
        self,
        payload: AeolianAnalyzeRequest,
    ) -> tuple[
        tuple[SequenceObservation, ...],
        str,
        list[InputFileProvenance],
        list[str],
    ]:
        if payload.meters_per_pixel is None:
            scale = None
        else:
            scale = payload.meters_per_pixel.as_tuple()

        observations: list[SequenceObservation] = []
        provenance: list[InputFileProvenance] = []
        limitations: list[str] = []
        canonical_crs: str | None = None

        for index, entry in enumerate(payload.observations):
            image_path, image_relative = self._resolve_path(
                entry.image_path, f"observations[{index}].image_path"
            )
            mask_path, mask_relative = self._resolve_path(
                entry.mask_path, f"observations[{index}].mask_path"
            )
            image = self._load_image(image_path, f"observations[{index}].image_path")
            mask = self._load_mask(mask_path, f"observations[{index}].mask_path")
            if mask.shape != image.data.shape[:2]:
                raise AeolianValidationError(
                    f"observations[{index}]: mask shape must match the image."
                )

            file_crs = image.metadata.crs
            if entry.crs is not None and file_crs is not None:
                if _canonical_crs(entry.crs) != _canonical_crs(file_crs):
                    raise AeolianValidationError(
                        f"observations[{index}]: declared CRS {entry.crs!r} does "
                        f"not match raster CRS {file_crs!r}."
                    )
            crs = entry.crs or file_crs
            if crs is None:
                raise AeolianValidationError(
                    f"observations[{index}]: CRS is required in the request or "
                    "raster metadata."
                )
            canonical = _canonical_crs(crs)
            if canonical_crs is None:
                canonical_crs = canonical
            elif canonical != canonical_crs:
                raise AeolianValidationError(
                    "All observations must use the same coordinate reference system."
                )

            if scale is not None:
                self._validate_scale(
                    image.metadata, scale, f"observations[{index}]"
                )
                if image.metadata.resolution is None:
                    limitations.append(
                        "The supplied metric scale could not be cross-checked "
                        "against raster metadata."
                    )

            acquisition = entry.acquisition_datetime_utc.astimezone(
                timezone.utc
            ).isoformat()
            try:
                observation = SequenceObservation(
                    observation_id=entry.observation_id,
                    product_id=entry.product_id,
                    datetime_utc=acquisition,
                    image=image,
                    mask=mask,
                )
            except MarsSequenceError as exc:
                raise AeolianValidationError(
                    f"observations[{index}]: {exc}"
                ) from exc
            observations.append(observation)
            provenance.extend(
                [
                    InputFileProvenance(
                        observation_id=entry.observation_id,
                        role="image",
                        path=image_relative,
                        sha256=checksum_file(image_path),
                    ),
                    InputFileProvenance(
                        observation_id=entry.observation_id,
                        role="mask",
                        path=mask_relative,
                        sha256=checksum_file(mask_path),
                    ),
                ]
            )

        if canonical_crs is None:
            raise AeolianValidationError("No coordinate reference system was resolved.")
        return tuple(observations), canonical_crs, provenance, limitations

    def _pairs(
        self,
        pairs: tuple[object, ...],
    ) -> tuple[list[AnalysisPair], list[MigrationObservation]]:
        output: list[AnalysisPair] = []
        migrations: list[MigrationObservation] = []
        for raw_pair in pairs:
            pair = raw_pair
            payload = pair.as_dict()
            observed = None
            if pair.migration is not None:
                migrations.append(pair.migration)
                migration = pair.migration.as_dict()
                observed = ObservedMigration(
                    dataset_id=migration["dataset_id"],
                    dune_id=migration["dune_id"],
                    method=migration["method"],
                    reference_datetime_utc=migration["reference_datetime_utc"],
                    moving_datetime_utc=migration["moving_datetime_utc"],
                    interval_days=migration["interval_days"],
                    dx_m=migration["dx_m"],
                    dy_m=migration["dy_m"],
                    distance_m=migration["distance_m"],
                    direction_azimuth_deg=migration["azimuth_deg"],
                    rate_m_per_earth_year=migration["rate_m_per_year"],
                    rate_standard_error_m_per_earth_year=migration[
                        "rate_standard_error_m_per_year"
                    ],
                    distance_ci95_m=migration["distance_ci95_m"],
                    valid=bool(migration["valid"]),
                    reasons=list(migration["reasons"]),
                    assumptions=list(migration["assumptions"]),
                    provenance=dict(migration["provenance"]),
                )
            registration = None
            if pair.registration is not None:
                registration = RegistrationQuality(**pair.registration.as_dict())
            output.append(
                AnalysisPair(
                    reference_id=payload["reference_id"],
                    moving_id=payload["moving_id"],
                    reference_datetime_utc=payload["reference_datetime_utc"],
                    moving_datetime_utc=payload["moving_datetime_utc"],
                    status=payload["status"],
                    registration=registration,
                    displacement=payload.get("displacement"),
                    observed_migration=observed,
                    geometry=payload.get("geometry"),
                    environment=payload.get("environment"),
                    reasons=list(payload.get("reasons", [])),
                )
            )
        return output, migrations

    def analyze(self, payload: AeolianAnalyzeRequest) -> AeolianAnalysisResult:
        record = self._record(payload.dataset_id)
        if not record.has_temporal_series:
            raise AeolianValidationError(
                f"Dataset '{record.dataset_id}' does not declare a temporal "
                "series and cannot support migration analysis."
            )
        observations, crs, files, scale_limitations = self._build_observations(
            payload
        )
        registration = RegistrationConfig(**payload.registration.model_dump())
        config = MarsSequenceConfig(
            meters_per_pixel=(
                None
                if payload.meters_per_pixel is None
                else payload.meters_per_pixel.as_tuple()
            ),
            use_metric_from_metadata=False,
            min_interval_days=payload.min_interval_days,
            method=payload.method,
            registration=registration,
            include_geometry=payload.include_geometry,
        )
        try:
            result = run_mars_sequence(list(observations), config=config)
        except (MarsSequenceError, ValueError) as exc:
            raise AeolianValidationError(str(exc)) from exc

        pairs, migrations = self._pairs(result.pairs)
        valid_count = sum(
            1
            for migration in migrations
            if migration.valid
        )
        status = (
            "completed"
            if valid_count
            else "completed_without_valid_migration"
        )
        created_at = datetime.now(timezone.utc).isoformat()
        analysis_id = uuid.uuid4().hex

        dataset = self._dataset_dto(record)
        limitations = list(record.limitations)
        limitations.extend(
            [
                "Observed displacement is apparent 2D image motion, not "
                "sediment flux, vertical change or an operational forecast.",
                "Rates are linear annualizations over the observation interval "
                "and do not imply constant migration through time.",
                "The dataset manifest contains metadata only; input pixels and "
                "masks are caller-supplied local files and are not verified by "
                "this API against the provider archive.",
                "No prediction model is available; predictions are not generated.",
                "Uncertainty fields remain null unless component errors were "
                "explicitly supplied; they are not inferred.",
                "Analysis results are stored in memory for this backend process "
                "and are lost when it restarts.",
            ]
        )
        if payload.meters_per_pixel is None:
            limitations.append(
                "No explicit metres-per-pixel scale was supplied; metric "
                "displacement and migration rate were withheld."
            )
        if record.published_context:
            limitations.append(
                "Published ranges in the dataset metadata are aggregate context, "
                "not per-dune labels or API observations."
            )
        limitations.extend(scale_limitations)

        ordered_observations = sorted(
            observations, key=lambda observation: observation.datetime_utc
        )
        input_observations = [
            AnalysisObservationResult(
                observation_id=entry.observation_id,
                product_id=entry.product_id,
                acquisition_datetime_utc=entry.datetime_utc,
                shape=[int(entry.image.height), int(entry.image.width)],
                crs=crs,
                mask_foreground_pixels=int(np.count_nonzero(entry.mask)),
                image_path=next(
                    item.path
                    for item in files
                    if item.observation_id == entry.observation_id
                    and item.role == "image"
                ),
                mask_path=next(
                    item.path
                    for item in files
                    if item.observation_id == entry.observation_id
                    and item.role == "mask"
                ),
                image_sha256=next(
                    item.sha256
                    for item in files
                    if item.observation_id == entry.observation_id
                    and item.role == "image"
                ),
                mask_sha256=next(
                    item.sha256
                    for item in files
                    if item.observation_id == entry.observation_id
                    and item.role == "mask"
                ),
            )
            for entry in ordered_observations
        ]

        analysis = AeolianAnalysisResult(
            analysis_id=analysis_id,
            dataset_id=record.dataset_id,
            status=status,
            created_at_utc=created_at,
            dataset=dataset,
            observations=input_observations,
            pairs=pairs,
            summary=AnalysisSummary(
                observation_count=len(result.observations),
                pair_count=len(result.pairs),
                valid_migration_count=valid_count,
                method_summary=summarize_methods(migrations),
            ),
            provenance=AnalysisProvenance(
                dataset_id=record.dataset_id,
                dataset_name=record.name,
                dataset_source=record.source,
                dataset_provider=record.provider,
                dataset_doi=record.doi,
                dataset_url=record.url,
                dataset_retrieved_at_utc=record.retrieved_at_utc,
                local_observations_required=True,
                files=files,
                crs=crs,
                meters_per_pixel=(
                    None
                    if payload.meters_per_pixel is None
                    else list(payload.meters_per_pixel.as_tuple())
                ),
                scale_source=(
                    None
                    if payload.meters_per_pixel is None
                    else payload.meters_per_pixel.source
                ),
                software="mars_ml.inference.mars_sequence.run_mars_sequence",
                generated_at_utc=created_at,
                scientific_status="research_pipeline_unvalidated",
            ),
            units={
                "dx_m": "m (east-positive)",
                "dy_m": "m (north-positive)",
                "distance_m": "m",
                "direction_azimuth_deg": "degrees clockwise from north",
                "rate_m_per_earth_year": "m per Earth year (365.25 days)",
                "interval_days": "days",
                "meters_per_pixel": "m/pixel",
                "rms_error_px": "pixels",
            },
            limitations=_unique(limitations),
            notes=list(result.notes),
            predictions=[],
            prediction_status="not_available",
        )
        with self._results_lock:
            self._results[analysis_id] = analysis
        return analysis

    def get_result(self, analysis_id: str) -> AeolianAnalysisResult:
        with self._results_lock:
            analysis = self._results.get(analysis_id)
        if analysis is None:
            raise AeolianAnalysisNotFound(
                f"Analysis '{analysis_id}' not found."
            )
        return analysis.model_copy(deep=True)

    def predict(self, payload: AeolianPredictRequest) -> list[PredictedMigration]:
        analysis = None
        if payload.analysis_id is not None:
            analysis = self.get_result(payload.analysis_id)
        if payload.dataset_id is not None:
            record = self._record(payload.dataset_id)
            if analysis is not None and analysis.dataset_id != record.dataset_id:
                raise AeolianValidationError(
                    "analysis_id and dataset_id refer to different datasets."
                )
        return self.prediction_provider.predict(payload, analysis)


_service: AeolianService | None = None
_service_lock = threading.Lock()


def get_aeolian_service() -> AeolianService:
    global _service
    with _service_lock:
        if _service is None:
            _service = AeolianService()
        return _service
