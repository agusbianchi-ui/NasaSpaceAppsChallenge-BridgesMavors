"""End-to-end dune analysis for two dated observations.

The orchestrator enforces the scientific safety rules of this stage:

- registration is evaluated before displacement;
- displacement is withheld when registration is unreliable;
- metric values require an explicit metres-per-pixel scale;
- migration requires two dated observations, a metric scale and a reliable
  displacement;
- segmentation is classical unless an external U-Net checkpoint is supplied.

Outputs are inspection artifacts and a JSON report. They are not operational
Mars predictions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from mars_ml.aeolian_dynamics.dune_migration import (
    MigrationError,
    MigrationResult,
    migration_from_metric,
)
from mars_ml.aeolian_dynamics.dune_morphology import (
    MorphologyError,
    MorphologyFeatures,
    extract_morphology,
    morphological_change,
)
from mars_ml.computer_vision.displacement_detection import (
    DisplacementReport,
    ScaleUnavailableError,
    estimate_displacement,
)
from mars_ml.computer_vision.dune_segmentation import (
    ClassicalDuneSegmenter,
    DuneSegmenter,
    SegmentationConfig,
    SegmentationError,
    SegmentationResult,
    UNetSegmenter,
)
from mars_ml.computer_vision.image_io import (
    ImageValidationError,
    RasterImage,
    load_image,
    load_raster,
)
from mars_ml.computer_vision.image_registration import (
    RegistrationConfig,
    RegistrationResult,
    register_images,
    warp_to_reference,
)
from mars_ml.visualization.plots import (
    plot_alignment,
    plot_difference,
    plot_displacement,
    plot_image,
    plot_mask_overlay,
    plot_morphology,
)


class DuneAnalysisError(RuntimeError):
    """Raised when the analysis cannot be run safely."""


@dataclass(frozen=True)
class DuneAnalysisConfig:
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    registration: RegistrationConfig = field(default_factory=RegistrationConfig)
    checkpoint: str | None = None
    meters_per_pixel: float | tuple[float, float] | None = None
    use_flow: bool = True
    save_visualizations: bool = True
    min_interval_days: float = 1.0

    def validate(self) -> None:
        self.segmentation.validate()
        self.registration.validate()
        if self.meters_per_pixel is not None:
            values = (
                (self.meters_per_pixel, self.meters_per_pixel)
                if np.isscalar(self.meters_per_pixel)
                else tuple(self.meters_per_pixel)
            )
            if len(values) != 2 or not all(np.isfinite(v) and v > 0 for v in values):
                raise DuneAnalysisError("meters_per_pixel must be positive and finite.")


def _load_observation(path: Path) -> RasterImage:
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            return load_raster(path)
        except Exception:
            return load_image(path)
    return load_image(path)


def _load_mask(path: Path) -> np.ndarray:
    mask_image = _load_observation(path)
    data = mask_image.data
    if data.ndim == 3:
        data = data[..., 0]
    if data.shape[0] < 2 or data.shape[1] < 2:
        raise DuneAnalysisError(f"Mask is too small: {path}")
    mask = np.asarray(data) > 0
    if not np.any(mask):
        raise DuneAnalysisError(f"Mask has no foreground pixels: {path}")
    return mask.astype(bool)


def _warp_mask(mask: np.ndarray, transform: np.ndarray, reference_shape: tuple[int, int]) -> np.ndarray:
    warped, valid = warp_to_reference(mask.astype(np.uint8), transform, reference_shape, border_value=0)
    return (warped > 0.5) & valid


def _morphology_or_none(
    mask: np.ndarray | None,
    meters_per_pixel: float | tuple[float, float] | None,
) -> MorphologyFeatures | None:
    if mask is None or not np.any(mask):
        return None
    try:
        return extract_morphology(mask, meters_per_pixel=meters_per_pixel)
    except (MorphologyError, ImageValidationError):
        return None


def _segmentation_summary(result: SegmentationResult | None) -> dict[str, Any] | None:
    return result.as_dict() if result is not None else None


def run_analysis(
    reference_path: str | Path,
    moving_path: str | Path,
    output_dir: str | Path,
    *,
    reference_mask_path: str | Path | None = None,
    moving_mask_path: str | Path | None = None,
    reference_datetime: str | datetime | None = None,
    moving_datetime: str | datetime | None = None,
    config: DuneAnalysisConfig | None = None,
) -> dict[str, Any]:
    """Run registration, segmentation, morphology, displacement and migration."""

    cfg = config or DuneAnalysisConfig()
    cfg.validate()
    reference_file = Path(reference_path)
    moving_file = Path(moving_path)
    if not reference_file.exists() or not moving_file.exists():
        raise DuneAnalysisError("Both observation files must exist.")

    reference = _load_observation(reference_file)
    moving = _load_observation(moving_file)
    warnings: list[str] = []
    if (
        reference.metadata.crs
        and moving.metadata.crs
        and reference.metadata.crs != moving.metadata.crs
    ):
        raise DuneAnalysisError(
            "Observations use different CRS values. Reproject to a common grid before analysis."
        )
    if bool(reference.metadata.crs) != bool(moving.metadata.crs):
        warnings.append("Only one observation declares a CRS; georeferencing is incomplete.")

    reference_mask = _load_mask(Path(reference_mask_path)) if reference_mask_path else None
    moving_mask = _load_mask(Path(moving_mask_path)) if moving_mask_path else None
    if reference_mask is not None and reference_mask.shape != reference.data.shape[:2]:
        raise DuneAnalysisError("Reference mask dimensions do not match the reference image.")
    if moving_mask is not None and moving_mask.shape != moving.data.shape[:2]:
        raise DuneAnalysisError("Moving mask dimensions do not match the moving image.")

    if cfg.checkpoint:
        segmenter: DuneSegmenter = UNetSegmenter(cfg.checkpoint)
    else:
        segmenter = ClassicalDuneSegmenter(cfg.segmentation)

    reference_segmentation = None
    moving_segmentation = None
    if reference_mask is None:
        try:
            reference_segmentation = segmenter.segment(reference.data, reference.valid_mask)
            reference_mask = reference_segmentation.mask
        except SegmentationError as exc:
            warnings.append(f"Reference segmentation failed: {exc}")
            reference_mask = np.zeros(reference.data.shape[:2], dtype=bool)
    if moving_mask is None:
        try:
            moving_segmentation = segmenter.segment(moving.data, moving.valid_mask)
            moving_mask = moving_segmentation.mask
        except SegmentationError as exc:
            warnings.append(f"Moving segmentation failed: {exc}")
            moving_mask = np.zeros(moving.data.shape[:2], dtype=bool)

    registration = register_images(
        reference.data,
        moving.data,
        config=cfg.registration,
    )
    aligned_moving = None
    aligned_moving_mask = None
    overlap = None
    if registration.reliable and registration.transform is not None:
        aligned_moving, overlap = warp_to_reference(
            moving.data, registration.transform, reference.data.shape[:2]
        )
        aligned_moving_mask = _warp_mask(
            moving_mask, registration.transform, reference.data.shape[:2]
        )
    else:
        warnings.append(
            "Registration was not reliable; displacement and cross-date morphology are withheld."
        )

    displacement: DisplacementReport | None = None
    if aligned_moving is not None and aligned_moving_mask is not None:
        displacement = estimate_displacement(
            reference.data,
            aligned_moving,
            reference_mask,
            aligned_moving_mask,
            alignment=registration,
            meters_per_pixel=cfg.meters_per_pixel,
            use_flow=cfg.use_flow,
        )

    reference_features = _morphology_or_none(reference_mask, cfg.meters_per_pixel)
    moving_features = _morphology_or_none(
        aligned_moving_mask if aligned_moving_mask is not None else moving_mask,
        cfg.meters_per_pixel,
    )
    morphology_change = None
    if registration.reliable and reference_features is not None and moving_features is not None:
        morphology_change = morphological_change(
            reference_features,
            moving_features,
            meters_per_pixel=cfg.meters_per_pixel,
        )

    migration: MigrationResult | None = None
    migration_error: str | None = None
    if not registration.reliable:
        migration_error = "Registration was not reliable."
    elif reference_datetime is None or moving_datetime is None:
        migration_error = "Observation datetimes were not supplied."
    elif cfg.meters_per_pixel is None:
        migration_error = "A verified metres-per-pixel scale was not supplied."
    elif displacement is None or not displacement.reliable or displacement.metric_centroid is None:
        migration_error = "Reliable metric displacement is unavailable."
    else:
        try:
            migration = migration_from_metric(
                reference_datetime,
                moving_datetime,
                displacement.metric_centroid,
                area_change=morphology_change,
                min_interval_days=cfg.min_interval_days,
            )
        except (MigrationError, ScaleUnavailableError) as exc:
            migration_error = str(exc)

    if not registration.reliable:
        status = "registration_unreliable"
    elif displacement is None or not displacement.reliable:
        status = "displacement_unreliable"
    elif migration is None:
        status = "analysis_complete_without_migration"
    else:
        status = "analysis_complete"

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    if cfg.save_visualizations:
        artifacts["reference_image"] = str(
            plot_image(reference.data, output / "01_reference_image.png", title="Reference observation")
        )
        artifacts["reference_mask"] = str(
            plot_mask_overlay(
                reference.data,
                reference_mask,
                output / "02_reference_mask.png",
                title="Reference candidate dune mask",
            )
        )
        artifacts["moving_image"] = str(
            plot_image(moving.data, output / "03_moving_image.png", title="Moving observation")
        )
        artifacts["moving_mask"] = str(
            plot_mask_overlay(
                moving.data,
                moving_mask,
                output / "04_moving_mask.png",
                title="Moving candidate dune mask",
            )
        )
        if aligned_moving is not None:
            artifacts["alignment"] = str(
                plot_alignment(
                    reference.data,
                    aligned_moving,
                    output / "05_aligned_observation.png",
                )
            )
            if overlap is not None:
                artifacts["difference"] = str(
                    plot_difference(
                        reference.data,
                        aligned_moving,
                        output / "06_difference.png",
                        valid_mask=overlap,
                    )
                )
        if displacement is not None:
            artifacts["displacement"] = str(
                plot_displacement(
                    reference_mask,
                    displacement,
                    output / "07_displacement_vectors.png",
                )
            )
        if reference_features is not None:
            artifacts["reference_morphology"] = str(
                plot_morphology(
                    reference_mask,
                    reference_features,
                    output / "08_reference_morphology.png",
                )
            )
        if aligned_moving_mask is not None and moving_features is not None:
            artifacts["moving_morphology"] = str(
                plot_morphology(
                    aligned_moving_mask,
                    moving_features,
                    output / "09_moving_morphology.png",
                )
            )

    result = {
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_status": "research_pipeline_unvalidated",
        "inputs": {
            "reference_path": str(reference_file.resolve()),
            "moving_path": str(moving_file.resolve()),
            "reference_mask_path": str(Path(reference_mask_path).resolve()) if reference_mask_path else None,
            "moving_mask_path": str(Path(moving_mask_path).resolve()) if moving_mask_path else None,
            "reference_datetime_utc": str(reference_datetime) if reference_datetime else None,
            "moving_datetime_utc": str(moving_datetime) if moving_datetime else None,
        },
        "spatial_metadata": {
            "reference": reference.metadata.as_dict(),
            "moving": moving.metadata.as_dict(),
            "meters_per_pixel_supplied": cfg.meters_per_pixel,
        },
        "registration": registration.as_dict(),
        "segmentation": {
            "reference": _segmentation_summary(reference_segmentation),
            "moving": _segmentation_summary(moving_segmentation),
            "reference_mask_source": "provided" if reference_mask_path else "classical_or_model_segmenter",
            "moving_mask_source": "provided" if moving_mask_path else "classical_or_model_segmenter",
        },
        "reference_morphology": reference_features.as_dict() if reference_features else None,
        "moving_morphology": moving_features.as_dict() if moving_features else None,
        "morphology_change": morphology_change,
        "displacement": displacement.as_dict() if displacement else None,
        "migration": migration.as_dict() if migration else None,
        "migration_unavailable_reason": migration_error,
        "warnings": warnings,
        "artifacts": artifacts,
        "notes": (
            "Apparent 2D analysis only. Segmentation is an unvalidated baseline unless "
            "an external checkpoint is supplied. No operational Mars prediction is made."
        ),
    }
    report_path = output / "analysis_report.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["artifacts"]["analysis_report"] = str(report_path)
    return result


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Reference (earlier) observation.")
    parser.add_argument("--moving", required=True, help="Moving (later) observation.")
    parser.add_argument("--reference-mask", help="Optional reference mask.")
    parser.add_argument("--moving-mask", help="Optional moving mask.")
    parser.add_argument("--reference-date", help="ISO 8601 datetime with timezone.")
    parser.add_argument("--moving-date", help="ISO 8601 datetime with timezone.")
    parser.add_argument("--output", default="outputs/dune_analysis")
    parser.add_argument("--meters-per-pixel", type=float, help="Verified ground sample distance in metres.")
    parser.add_argument("--checkpoint", help="Optional U-Net checkpoint (requires PyTorch).")
    parser.add_argument("--no-flow", action="store_true", help="Disable optical-flow estimates.")
    parser.add_argument("--no-visuals", action="store_true")
    args = parser.parse_args(argv)
    config = DuneAnalysisConfig(
        checkpoint=args.checkpoint,
        meters_per_pixel=args.meters_per_pixel,
        use_flow=not args.no_flow,
        save_visualizations=not args.no_visuals,
    )
    result = run_analysis(
        args.reference,
        args.moving,
        args.output,
        reference_mask_path=args.reference_mask,
        moving_mask_path=args.moving_mask,
        reference_datetime=args.reference_date,
        moving_datetime=args.moving_date,
        config=config,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "registration_reliable": result["registration"]["reliable"],
                "displacement_reliable": result["displacement"]["reliable"] if result["displacement"] else None,
                "migration": result["migration"],
                "analysis_report": result["artifacts"].get("analysis_report"),
            },
            indent=2,
        )
    )
    return 0 if result["status"] != "registration_unreliable" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
