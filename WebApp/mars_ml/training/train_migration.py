"""Train a migration model from an explicit observation table.

The table must contain dated metric displacements and named covariate columns.
Rates are computed from the table; published ranges and Earth rates are never
used as targets. A JSON report is the default artifact; a model checkpoint is
written only when explicitly requested.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from mars_ml.aeolian_dynamics.migration_analysis import (
    MigrationAnalysisError,
    MigrationObservation,
    observation_from_metric,
)
from mars_ml.aeolian_dynamics.migration_models import (
    InsufficientObservationsError,
    MigrationModel,
    RandomForestMigrationModel,
    RidgeMigrationModel,
    cross_validate_migration_model,
)
from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    azimuth_degrees,
)


class MigrationTrainingError(ValueError):
    """Raised when a migration training table is invalid."""


REQUIRED_COLUMNS = (
    "dataset_id",
    "dune_id",
    "method",
    "reference_datetime_utc",
    "moving_datetime_utc",
    "dx_m",
    "dy_m",
)


@dataclass(frozen=True)
class MigrationTrainingData:
    observations: tuple[MigrationObservation, ...]
    features: np.ndarray
    rates_m_per_year: np.ndarray
    groups: tuple[str, ...]
    feature_names: tuple[str, ...]
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        matrix = np.asarray(self.features, dtype=np.float64)
        target = np.asarray(self.rates_m_per_year, dtype=np.float64).reshape(-1)
        if matrix.ndim != 2 or matrix.shape[0] == 0:
            raise MigrationTrainingError("Training features must be a non-empty 2D array.")
        if matrix.shape[0] != target.size:
            raise MigrationTrainingError("Feature and target counts differ.")
        if matrix.shape[0] != len(self.groups):
            raise MigrationTrainingError("Feature and group counts differ.")
        if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(target)):
            raise MigrationTrainingError("Training values must be finite.")
        if np.any(target < 0):
            raise MigrationTrainingError("Migration rates cannot be negative.")

    @property
    def sample_count(self) -> int:
        return int(self.features.shape[0])

    @property
    def group_count(self) -> int:
        return len(set(self.groups))

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "group_count": self.group_count,
            "feature_names": list(self.feature_names),
            "observation_count": len(self.observations),
            "provenance": dict(self.provenance),
        }


def _read_table(path: str | Path) -> tuple[dict[str, Any], ...]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise MigrationTrainingError("pandas is required to read the training table.") from exc
    table_path = Path(path)
    if not table_path.exists():
        raise FileNotFoundError(table_path)
    if table_path.suffix.lower() == ".csv":
        frame = pd.read_csv(table_path)
    elif table_path.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(table_path)
    else:
        raise MigrationTrainingError("Training table must be CSV or XLSX.")
    frame = frame.dropna(how="all")
    return tuple(
        {str(key): value for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    )


def _value(row: dict[str, Any], column: str) -> Any:
    value = row.get(column)
    if value is None:
        raise MigrationTrainingError(f"Missing value in column {column!r}.")
    if isinstance(value, float) and not np.isfinite(value):
        raise MigrationTrainingError(f"Non-finite value in column {column!r}.")
    return value


def observations_from_rows(
    rows: Sequence[dict[str, Any]],
    *,
    feature_columns: Sequence[str] | None = None,
    min_interval_days: float = 1.0,
) -> MigrationTrainingData:
    if not rows:
        raise MigrationTrainingError("Training table has no rows.")
    missing = sorted(set(REQUIRED_COLUMNS) - set(rows[0]))
    if missing:
        raise MigrationTrainingError(
            f"Training table is missing columns: {', '.join(missing)}."
        )
    if feature_columns is None:
        feature_columns = tuple(
            sorted(
                column
                for column in rows[0]
                if str(column).startswith("feature_")
            )
        )
    feature_names = tuple(str(column) for column in feature_columns)
    if not feature_names:
        raise MigrationTrainingError(
            "At least one feature column is required; use an explicit feature_ prefix."
        )
    observations: list[MigrationObservation] = []
    features: list[list[float]] = []
    rates: list[float] = []
    groups: list[str] = []
    for row_index, row in enumerate(rows):
        if "valid" in row and str(row["valid"]).strip().lower() in {"false", "0", "no"}:
            continue
        dataset_id = str(_value(row, "dataset_id")).strip()
        dune_id = str(_value(row, "dune_id")).strip()
        method = str(_value(row, "method")).strip()
        try:
            dx_m = float(_value(row, "dx_m"))
            dy_m = float(_value(row, "dy_m"))
        except (TypeError, ValueError) as exc:
            raise MigrationTrainingError(f"Row {row_index}: dx_m/dy_m must be numeric.") from exc
        displacement = MetricDisplacement(
            dx_m=dx_m,
            dy_m=dy_m,
            magnitude_m=float(np.hypot(dx_m, dy_m)),
            azimuth_deg=azimuth_degrees(dx_m, dy_m),
            meters_per_pixel=(1.0, 1.0),
            method=f"precomputed_metric:{method}",
        )
        rate_error = row.get("distance_standard_error_m")
        if rate_error is None or (
            isinstance(rate_error, float) and not np.isfinite(rate_error)
        ):
            rate_error = None
        else:
            try:
                rate_error = float(rate_error)
            except (TypeError, ValueError) as exc:
                raise MigrationTrainingError(
                    f"Row {row_index}: distance_standard_error_m must be numeric."
                ) from exc
            if not np.isfinite(rate_error):
                raise MigrationTrainingError(
                    f"Row {row_index}: distance_standard_error_m must be finite."
                )
        observation = observation_from_metric(
            dataset_id,
            dune_id,
            method,
            str(_value(row, "reference_datetime_utc")),
            str(_value(row, "moving_datetime_utc")),
            displacement,
            distance_standard_error_m=rate_error,
            min_interval_days=min_interval_days,
            provenance={
                "source": "migration_training_table",
                "row_index": row_index,
                "units": "metres",
            },
        )
        if not observation.valid:
            continue
        values: list[float] = []
        for name in feature_names:
            try:
                value = float(_value(row, name))
            except (TypeError, ValueError) as exc:
                raise MigrationTrainingError(
                    f"Row {row_index}: feature {name!r} must be numeric."
                ) from exc
            if not np.isfinite(value):
                raise MigrationTrainingError(
                    f"Row {row_index}: feature {name!r} must be finite."
                )
            values.append(value)
        observations.append(observation)
        features.append(values)
        rates.append(float(observation.rate_m_per_year))
        groups.append(dataset_id)
    if not observations:
        raise MigrationTrainingError("No valid dated observations remained after validation.")
    return MigrationTrainingData(
        observations=tuple(observations),
        features=np.asarray(features, dtype=np.float64),
        rates_m_per_year=np.asarray(rates, dtype=np.float64),
        groups=tuple(groups),
        feature_names=feature_names,
        provenance={
            "source": "explicit_observation_table",
            "row_count": len(rows),
            "included_count": len(observations),
            "feature_names": list(feature_names),
            "notes": [
                "Rates were computed from dated metric displacements.",
                "Published ranges and Earth rates were not used as targets.",
                "Grouped validation holds out whole dataset_id groups.",
            ],
        },
    )


def train_migration_from_table(
    table_path: str | Path,
    *,
    model_name: str = "ridge",
    feature_columns: Sequence[str] | None = None,
    n_splits: int = 5,
    min_interval_days: float = 1.0,
) -> dict[str, Any]:
    rows = _read_table(table_path)
    dataset = observations_from_rows(
        rows,
        feature_columns=feature_columns,
        min_interval_days=min_interval_days,
    )
    if dataset.sample_count < 6 or dataset.group_count < 3:
        raise InsufficientObservationsError(
            "At least six observations in three groups are required."
        )
    factory = _model_factory(model_name, dataset.feature_names)
    cross_validation = cross_validate_migration_model(
        factory,
        dataset.features,
        dataset.rates_m_per_year,
        dataset.groups,
        n_splits=n_splits,
    )
    model = factory()
    model.fit(dataset.features, dataset.rates_m_per_year, dataset.groups)
    report = model.report(cross_validation.metrics)
    return {
        "status": "trained_research_model",
        "dataset": dataset.as_dict(),
        "cross_validation": cross_validation.as_dict(),
        "model_report": report.as_dict(),
        "checkpoint_saved": False,
        "notes": [
            "No model artifact was saved by this function.",
            "Metrics are not operational skill and require external validation.",
            "Do not apply the model to Mars sites not represented in the training groups.",
        ],
    }


def _model_factory(model_name: str, feature_names: Sequence[str]) -> Callable[[], MigrationModel]:
    normalized = model_name.strip().lower()
    if normalized == "ridge":
        return lambda: RidgeMigrationModel(feature_names=feature_names)
    if normalized in {"random_forest", "forest"}:
        return lambda: RandomForestMigrationModel(feature_names=feature_names)
    raise MigrationTrainingError(
        f"Unknown model {model_name!r}; choose 'ridge' or 'random_forest'."
    )


def save_training_report(path: str | Path, report: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train a grouped migration model from an explicit metric table."
    )
    parser.add_argument("--table", required=True, help="CSV or XLSX observation table.")
    parser.add_argument(
        "--model",
        default="ridge",
        choices=("ridge", "random_forest"),
        help="Model family.",
    )
    parser.add_argument("--feature", action="append", dest="features", default=None)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-interval-days", type=float, default=1.0)
    parser.add_argument("--output", required=True, help="JSON report path.")
    arguments = parser.parse_args(argv)
    report = train_migration_from_table(
        arguments.table,
        model_name=arguments.model,
        feature_columns=arguments.features,
        n_splits=arguments.folds,
        min_interval_days=arguments.min_interval_days,
    )
    output = save_training_report(arguments.output, report)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
