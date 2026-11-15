"""Orchestrate a dated Mars image sequence without inventing missing inputs.

Each consecutive pair is registered independently. Displacement and migration
are withheld when registration is unreliable, masks are missing, dates are
absent or no verified metric scale is available. Environmental values remain
optional and are never imputed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from mars_ml.aeolian_dynamics.environmental_observations import (
    EnvironmentalObservation,
)
from mars_ml.aeolian_dynamics.migration_analysis import (
    MigrationObservation,
    observation_from_pixels,
)
from mars_ml.computer_vision.displacement_detection import (
    DisplacementReport,
    PixelDisplacement,
    centroid_displacement,
    estimate_displacement,
    mask_change,
)
from mars_ml.computer_vision.dune_crests import extract_crests
from mars_ml.computer_vision.geometry_comparison import compare_masks
from mars_ml.computer_vision.image_io import RasterImage, load_image, load_raster
from mars_ml.computer_vision.image_registration import (
    RegistrationConfig,
    RegistrationResult,
    register_images,
    warp_to_reference,
)


class MarsSequenceError(ValueError):
    """Raised when a Mars sequence cannot be assembled."""


def _normalize_utc(value: str) -> str:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MarsSequenceError(f"Invalid ISO 8601 datetime {value!r}.") from exc
    if parsed.tzinfo is None:
        raise MarsSequenceError("Observation datetimes must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class SequenceObservation:
    observation_id: str
    product_id: str
    datetime_utc: str
    image: RasterImage
    mask: np.ndarray
    environment: EnvironmentalObservation | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.product_id.strip():
            raise MarsSequenceError("observation_id and product_id are required.")
        if not self.datetime_utc.strip():
            raise MarsSequenceError("datetime_utc is required.")
        object.__setattr__(self, "datetime_utc", _normalize_utc(self.datetime_utc))
        mask = np.asarray(self.mask)
        if mask.ndim != 2 or mask.shape != self.image.data.shape[:2]:
            raise MarsSequenceError("Mask shape must match the image height and width.")
        if not np.any(mask):
            raise MarsSequenceError("Mask is empty.")
        if self.environment is not None and self.environment.scene_id not in {
            None,
            self.product_id,
        }:
            raise MarsSequenceError(
                "Environmental observation scene_id does not match product_id."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "product_id": self.product_id,
            "datetime_utc": self.datetime_utc,
            "shape": [int(value) for value in self.image.data.shape[:2]],
            "crs": self.image.metadata.crs,
            "mask_foreground_pixels": int(np.count_nonzero(self.mask)),
            "environment": self.environment.as_dict() if self.environment else None,
        }


@dataclass(frozen=True)
class MarsSequenceConfig:
    meters_per_pixel: float | tuple[float, float] | None = None
    use_metric_from_metadata: bool = False
    min_interval_days: float = 1.0
    method: str = "centroid"
    registration: RegistrationConfig = field(default_factory=RegistrationConfig)
    include_geometry: bool = True

    def validate(self) -> None:
        if self.method not in {"centroid", "crest"}:
            raise MarsSequenceError(
                "method must be centroid or crest; advancing_front is not implemented."
            )
        if self.min_interval_days < 0:
            raise MarsSequenceError("min_interval_days must be non-negative.")
        self.registration.validate()


@dataclass(frozen=True)
class SequencePairResult:
    reference_id: str
    moving_id: str
    reference_datetime_utc: str
    moving_datetime_utc: str
    status: str
    registration: RegistrationResult | None
    displacement: DisplacementReport | None
    migration: MigrationObservation | None
    geometry: dict[str, Any] | None
    environment: dict[str, Any] | None
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "moving_id": self.moving_id,
            "reference_datetime_utc": self.reference_datetime_utc,
            "moving_datetime_utc": self.moving_datetime_utc,
            "status": self.status,
            "registration": self.registration.as_dict() if self.registration else None,
            "displacement": self.displacement.as_dict() if self.displacement else None,
            "migration": self.migration.as_dict() if self.migration else None,
            "geometry": self.geometry,
            "environment": self.environment,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class MarsSequenceResult:
    observations: tuple[dict[str, Any], ...]
    pairs: tuple[SequencePairResult, ...]
    config: dict[str, Any]
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def valid_migration_count(self) -> int:
        return sum(
            1
            for pair in self.pairs
            if pair.migration is not None and pair.migration.valid
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_count": len(self.observations),
            "pair_count": len(self.pairs),
            "valid_migration_count": self.valid_migration_count,
            "observations": [dict(entry) for entry in self.observations],
            "pairs": [pair.as_dict() for pair in self.pairs],
            "config": dict(self.config),
            "notes": list(self.notes),
        }


def _resolve_scale(
    reference: SequenceObservation,
    moving: SequenceObservation,
    config: MarsSequenceConfig,
) -> tuple[float | tuple[float, float] | None, str | None]:
    if config.meters_per_pixel is not None:
        return config.meters_per_pixel, None
    if not config.use_metric_from_metadata:
        return None, "A verified metres-per-pixel scale was not supplied."
    try:
        reference_resolution = reference.image.metadata.ensure_metric_resolution()
        moving_resolution = moving.image.metadata.ensure_metric_resolution()
    except Exception as exc:
        return None, str(exc)
    if not np.allclose(reference_resolution, moving_resolution, rtol=1e-6, atol=1e-9):
        return None, "Observation resolutions differ; resample before displacement."
    return tuple(float(value) for value in reference_resolution), None


def _registration_gate(
    reference: SequenceObservation,
    moving: SequenceObservation,
    config: MarsSequenceConfig,
) -> tuple[RegistrationResult, str | None]:
    if reference.image.data.shape != moving.image.data.shape:
        return (
            RegistrationResult(
                transform=None,
                method="not_attempted",
                reliable=False,
                message="Images do not share dimensions.",
            ),
            "Images do not share dimensions; resample to a common grid.",
        )
    reference_crs = reference.image.metadata.crs
    moving_crs = moving.image.metadata.crs
    if reference_crs and moving_crs and reference_crs != moving_crs:
        return (
            RegistrationResult(
                transform=None,
                method="not_attempted",
                reliable=False,
                message="CRS values differ.",
            ),
            "Observations use different CRS values; reproject first.",
        )
    return register_images(
        reference.image.data, moving.image.data, config=config.registration
    ), None


def _pair_analysis(
    reference: SequenceObservation,
    moving: SequenceObservation,
    config: MarsSequenceConfig,
) -> SequencePairResult:
    registration, gate_reason = _registration_gate(reference, moving, config)
    if gate_reason is not None:
        return SequencePairResult(
            reference_id=reference.observation_id,
            moving_id=moving.observation_id,
            reference_datetime_utc=reference.datetime_utc,
            moving_datetime_utc=moving.datetime_utc,
            status="registration_not_attempted",
            registration=registration,
            displacement=None,
            migration=None,
            geometry=None,
            environment=_environment_payload(moving),
            reasons=(gate_reason,),
        )
    if not registration.reliable or registration.transform is None:
        return SequencePairResult(
            reference_id=reference.observation_id,
            moving_id=moving.observation_id,
            reference_datetime_utc=reference.datetime_utc,
            moving_datetime_utc=moving.datetime_utc,
            status="registration_unreliable",
            registration=registration,
            displacement=None,
            migration=None,
            geometry=None,
            environment=_environment_payload(moving),
            reasons=(
                "Registration was not reliable; displacement and migration are withheld.",
                registration.message,
            ),
        )
    aligned, overlap = warp_to_reference(
        moving.image.data,
        registration.transform,
        reference.image.data.shape[:2],
    )
    aligned_mask = warp_to_reference(
        moving.mask.astype(np.uint8),
        registration.transform,
        reference.image.data.shape[:2],
    )[0].astype(bool)
    aligned_mask &= overlap
    if not np.any(aligned_mask):
        return SequencePairResult(
            reference_id=reference.observation_id,
            moving_id=moving.observation_id,
            reference_datetime_utc=reference.datetime_utc,
            moving_datetime_utc=moving.datetime_utc,
            status="mask_not_overlapping",
            registration=registration,
            displacement=None,
            migration=None,
            geometry=None,
            environment=_environment_payload(moving),
            reasons=("Warped moving mask has no overlap with the reference grid.",),
        )
    scale, scale_reason = _resolve_scale(reference, moving, config)
    displacement = estimate_displacement(
        reference.image.data,
        aligned,
        reference.mask,
        aligned_mask,
        alignment=registration,
        meters_per_pixel=scale,
        use_flow=True,
    )
    migration = None
    reasons: list[str] = []
    if scale_reason is not None:
        reasons.append(scale_reason)
    migration_displacement: PixelDisplacement | None = displacement.centroid
    if config.method == "crest":
        reference_crests = extract_crests(
            reference.image.data, valid_mask=reference.image.valid_mask
        )
        moving_crests = extract_crests(
            aligned, valid_mask=overlap
        )
        if reference_crests.length_px == 0 or moving_crests.length_px == 0:
            reasons.append("Crest extraction produced an empty skeleton.")
            migration_displacement = None
        else:
            migration_displacement = centroid_displacement(
                reference_crests.skeleton, moving_crests.skeleton
            )
    if migration_displacement is None or not migration_displacement.reliable:
        reasons.append("Reliable displacement is unavailable.")
    else:
        migration = observation_from_pixels(
            dataset_id="mars_sequence",
            dune_id=f"{reference.observation_id}->{moving.observation_id}",
            method=config.method,
            reference_datetime=reference.datetime_utc,
            moving_datetime=moving.datetime_utc,
            displacement=migration_displacement,
            meters_per_pixel=scale,
            min_interval_days=config.min_interval_days,
            provenance={
                "reference_product_id": reference.product_id,
                "moving_product_id": moving.product_id,
                "registration_method": registration.method,
                "registration_reliable": registration.reliable,
                "scale_source": "config" if config.meters_per_pixel else "metadata",
            },
        )
        if not migration.valid:
            reasons.extend(migration.reasons)
    geometry = None
    if config.include_geometry:
        comparison = compare_masks(
            reference.mask,
            aligned_mask,
            meters_per_pixel=scale,
        )
        geometry = comparison.as_dict()
        geometry["mask_change"] = mask_change(
            reference.mask,
            aligned_mask,
            meters_per_pixel=scale,
        )
    return SequencePairResult(
        reference_id=reference.observation_id,
        moving_id=moving.observation_id,
        reference_datetime_utc=reference.datetime_utc,
        moving_datetime_utc=moving.datetime_utc,
        status="analyzed" if migration is not None and migration.valid else "displacement_only",
        registration=registration,
        displacement=displacement,
        migration=migration,
        geometry=geometry,
        environment=_environment_payload(moving),
        reasons=tuple(reasons),
    )


def _environment_payload(observation: SequenceObservation) -> dict[str, Any] | None:
    if observation.environment is None:
        return None
    payload = observation.environment.as_dict()
    payload["simultaneous_with_image"] = (
        observation.environment.simultaneous_with_image()
    )
    return payload


def run_mars_sequence(
    observations: Sequence[SequenceObservation],
    *,
    config: MarsSequenceConfig | None = None,
) -> MarsSequenceResult:
    cfg = config or MarsSequenceConfig()
    cfg.validate()
    if len(observations) < 2:
        raise MarsSequenceError("At least two dated observations are required.")
    identifiers = [observation.observation_id for observation in observations]
    if len(set(identifiers)) != len(identifiers):
        raise MarsSequenceError("Observation IDs must be unique.")
    ordered = sorted(observations, key=lambda observation: observation.datetime_utc)
    pairs = tuple(
        _pair_analysis(ordered[index], ordered[index + 1], cfg)
        for index in range(len(ordered) - 1)
    )
    return MarsSequenceResult(
        observations=tuple(observation.as_dict() for observation in ordered),
        pairs=pairs,
        config={
            "meters_per_pixel": cfg.meters_per_pixel,
            "use_metric_from_metadata": cfg.use_metric_from_metadata,
            "min_interval_days": cfg.min_interval_days,
            "method": cfg.method,
            "include_geometry": cfg.include_geometry,
        },
        notes=(
            "Pairs are consecutive in the supplied datetime order.",
            "Registration is evaluated independently for each pair.",
            "No displacement is reported when registration or scale fails.",
            "Environmental observations are never imputed or treated as simultaneous by default.",
            "This is an apparent 2D sequence analysis, not a sediment-flux retrieval.",
        ),
    )


_GEOSPATIAL_SUFFIXES = {".tif", ".tiff", ".jp2", ".img", ".vrt", ".cub"}


def _load_image(path: Path) -> RasterImage:
    if path.suffix.lower() in _GEOSPATIAL_SUFFIXES:
        return load_raster(path)
    return load_image(path)


def _load_mask(path: Path) -> np.ndarray:
    image = _load_image(path)
    if image.data.ndim != 2:
        raise MarsSequenceError(f"Mask must be a single-band raster: {path}")
    return np.asarray(image.data) > 0


def _plan_text(entry: dict[str, Any], key: str, index: int) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MarsSequenceError(f"Observation {index} requires {key}.")
    return value


def _resolve_plan_path(base: Path, value: Any, field_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise MarsSequenceError(f"Sequence plan requires {field_name}.")
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _config_from_payload(payload: dict[str, Any] | None) -> MarsSequenceConfig:
    values = dict(payload or {})
    if "meters_per_pixel" in values and isinstance(values["meters_per_pixel"], list):
        values["meters_per_pixel"] = tuple(values["meters_per_pixel"])
    registration_payload = values.pop("registration", None)
    if registration_payload is not None:
        if not isinstance(registration_payload, dict):
            raise MarsSequenceError("registration must be an object.")
        try:
            values["registration"] = RegistrationConfig(**registration_payload)
        except TypeError as exc:
            raise MarsSequenceError(f"Invalid registration config: {exc}") from exc
    try:
        config = MarsSequenceConfig(**values)
    except TypeError as exc:
        raise MarsSequenceError(f"Invalid sequence config: {exc}") from exc
    config.validate()
    return config


def load_sequence_plan(
    path: str | Path,
) -> tuple[tuple[SequenceObservation, ...], MarsSequenceConfig]:
    """Load a JSON sequence plan with local image and mask paths."""

    plan_path = Path(path)
    if not plan_path.exists():
        raise MarsSequenceError(f"Sequence plan not found: {plan_path}")
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MarsSequenceError(f"Invalid JSON in sequence plan: {exc}") from exc
    if not isinstance(payload, dict):
        raise MarsSequenceError("Sequence plan must be a JSON object.")
    entries = payload.get("observations")
    if not isinstance(entries, list) or len(entries) < 2:
        raise MarsSequenceError("Sequence plan requires at least two observations.")
    base = plan_path.parent
    config = _config_from_payload(payload.get("config"))
    observations: list[SequenceObservation] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MarsSequenceError(f"Observation {index} must be an object.")
        image_path = _resolve_plan_path(base, entry.get("image"), f"observations[{index}].image")
        mask_path = _resolve_plan_path(base, entry.get("mask"), f"observations[{index}].mask")
        environment_payload = entry.get("environment")
        environment = None
        if environment_payload is not None:
            if not isinstance(environment_payload, dict):
                raise MarsSequenceError(f"Observation {index} environment must be an object.")
            try:
                environment = EnvironmentalObservation(**environment_payload)
            except (TypeError, ValueError) as exc:
                raise MarsSequenceError(
                    f"Observation {index} environment is invalid: {exc}"
                ) from exc
        try:
            image = _load_image(image_path)
        except Exception as exc:
            raise MarsSequenceError(
                f"Observation {index} image could not be loaded: {exc}"
            ) from exc
        try:
            mask = _load_mask(mask_path)
        except Exception as exc:
            raise MarsSequenceError(
                f"Observation {index} mask could not be loaded: {exc}"
            ) from exc
        observations.append(
            SequenceObservation(
                observation_id=_plan_text(entry, "observation_id", index),
                product_id=_plan_text(entry, "product_id", index),
                datetime_utc=_plan_text(entry, "datetime_utc", index),
                image=image,
                mask=mask,
                environment=environment,
            )
        )
    return tuple(observations), config


def run_sequence_plan(
    plan_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    observations, config = load_sequence_plan(plan_path)
    result = run_mars_sequence(observations, config=config)
    payload = result.as_dict()
    payload["plan_path"] = str(Path(plan_path).resolve())
    payload["scientific_status"] = "research_pipeline_unvalidated"
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["report_path"] = str(output.resolve())
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a dated Mars sequence from an explicit JSON plan."
    )
    parser.add_argument("--plan", required=True, help="JSON plan with local image and mask paths.")
    parser.add_argument("--output", required=True, help="Output sequence report JSON.")
    arguments = parser.parse_args(argv)
    report = run_sequence_plan(arguments.plan, arguments.output)
    print(
        json.dumps(
            {
                "observation_count": report["observation_count"],
                "pair_count": report["pair_count"],
                "valid_migration_count": report["valid_migration_count"],
                "report_path": report["report_path"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
