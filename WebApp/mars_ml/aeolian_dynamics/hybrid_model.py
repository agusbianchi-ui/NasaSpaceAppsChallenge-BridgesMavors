"""Assemble hybrid migration datasets from dated observations and covariates.

The hybrid dataset is explicit: every row is a valid migration observation with
a named dune group and a finite, named covariate vector. Missing covariates are
never imputed silently, and an Earth-calibrated rate is never inserted as a
target or a prior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from mars_ml.aeolian_dynamics.environmental_sources import (
    EnvironmentalSource,
    EnvironmentalSourceError,
    source_by_id,
)
from mars_ml.aeolian_dynamics.migration_analysis import MigrationObservation
from mars_ml.aeolian_dynamics.migration_models import (
    CrossValidationReport,
    InsufficientObservationsError,
    MigrationModel,
    MigrationModelError,
    ModelReport,
    cross_validate_migration_model,
)


class HybridModelError(ValueError):
    """Raised when a hybrid dataset cannot be assembled safely."""


def observation_key(observation: MigrationObservation) -> str:
    return f"{observation.dataset_id}:{observation.dune_id}"


@dataclass(frozen=True)
class HybridDataset:
    features: np.ndarray
    rates_m_per_year: np.ndarray
    groups: tuple[str, ...]
    feature_names: tuple[str, ...]
    observation_keys: tuple[str, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        matrix = np.asarray(self.features, dtype=np.float64)
        target = np.asarray(self.rates_m_per_year, dtype=np.float64).reshape(-1)
        if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
            raise HybridModelError("Features must be a non-empty 2D array.")
        if target.size != matrix.shape[0]:
            raise HybridModelError("Rate and feature counts differ.")
        if len(self.groups) != matrix.shape[0]:
            raise HybridModelError("Group and feature counts differ.")
        if len(self.feature_names) != matrix.shape[1]:
            raise HybridModelError("Feature-name and column counts differ.")
        if len(self.observation_keys) != matrix.shape[0]:
            raise HybridModelError("Observation-key and feature counts differ.")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise HybridModelError("Feature names must be unique.")
        if not np.all(np.isfinite(matrix)):
            raise HybridModelError("Features must be finite.")
        if not np.all(np.isfinite(target)):
            raise HybridModelError("Rates must be finite.")
        if np.any(target < 0):
            raise HybridModelError("Migration magnitudes cannot be negative.")

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
            "groups": list(self.groups),
            "observation_keys": list(self.observation_keys),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class HybridModelResult:
    dataset: HybridDataset
    cross_validation: CrossValidationReport
    fitted_report: ModelReport
    status: str = "fitted_research_model"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dataset": self.dataset.as_dict(),
            "cross_validation": self.cross_validation.as_dict(),
            "fitted_report": self.fitted_report.as_dict(),
            "notes": list(self.notes),
        }


def build_hybrid_dataset(
    observations: Iterable[MigrationObservation],
    covariates_by_observation: Mapping[str, Mapping[str, float]],
    *,
    feature_names: Sequence[str],
    group_field: str = "dataset_id",
    sources: Mapping[str, EnvironmentalSource] | None = None,
    require_verified_sources: bool = False,
) -> HybridDataset:
    """Join valid migration observations to explicitly keyed covariates.

    Covariate keys are ``"<dataset_id>:<dune_id>"``. Every requested feature
    must be present, numeric and finite for every included observation.
    """

    names = tuple(str(name) for name in feature_names)
    if not names:
        raise HybridModelError("At least one feature name is required.")
    if len(set(names)) != len(names):
        raise HybridModelError("Feature names must be unique.")
    if group_field not in {"dataset_id", "dune_id"}:
        raise HybridModelError("group_field must be 'dataset_id' or 'dune_id'.")
    rows: list[list[float]] = []
    rates: list[float] = []
    groups: list[str] = []
    keys: list[str] = []
    observation_provenance: list[dict[str, Any]] = []
    for observation in observations:
        if not observation.valid:
            continue
        key = observation_key(observation)
        if key in keys:
            raise HybridModelError(f"Duplicate observation key: {key}")
        if observation.rate_m_per_year is None:
            raise HybridModelError(f"{key}: valid observation has no rate.")
        values = covariates_by_observation.get(key)
        if values is None:
            raise HybridModelError(
                f"{key}: no covariate row; imputation is not allowed."
            )
        row: list[float] = []
        for name in names:
            if name not in values:
                raise HybridModelError(f"{key}: missing covariate {name!r}.")
            raw = values[name]
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise HybridModelError(
                    f"{key}: covariate {name!r} is not numeric."
                ) from exc
            if not np.isfinite(value):
                raise HybridModelError(f"{key}: covariate {name!r} is not finite.")
            row.append(value)
        rows.append(row)
        rates.append(float(observation.rate_m_per_year))
        groups.append(
            observation.dataset_id if group_field == "dataset_id" else observation.dune_id
        )
        keys.append(key)
        observation_provenance.append(dict(observation.provenance))
    if not rows:
        raise InsufficientObservationsError("No valid migration observations were supplied.")
    provenance: dict[str, Any] = {
        "group_field": group_field,
        "observation_provenance": observation_provenance,
        "source_ids": [],
        "sources_verified": False,
        "notes": [
            "Targets are apparent migration magnitudes from dated observations.",
            "Covariates are not causal evidence and missing values were not imputed.",
            "No Earth migration rate was inserted as a target, prior or offset.",
        ],
    }
    if sources:
        source_ids = sorted(set(sources))
        provenance["source_ids"] = source_ids
        verified = True
        for source_id in source_ids:
            try:
                source = source_by_id(sources.values(), source_id)
            except EnvironmentalSourceError as exc:
                raise HybridModelError(str(exc)) from exc
            if not source.metadata_verified:
                verified = False
                if require_verified_sources:
                    raise HybridModelError(
                        f"{source_id}: source metadata has not been verified."
                    )
        provenance["sources_verified"] = verified
    return HybridDataset(
        features=np.asarray(rows, dtype=np.float64),
        rates_m_per_year=np.asarray(rates, dtype=np.float64),
        groups=tuple(str(group) for group in groups),
        feature_names=names,
        observation_keys=tuple(keys),
        provenance=provenance,
    )


def fit_hybrid_model(
    dataset: HybridDataset,
    model_factory: Any,
    *,
    n_splits: int = 5,
) -> HybridModelResult:
    if not isinstance(dataset, HybridDataset):
        raise HybridModelError("dataset must be a HybridDataset.")
    if dataset.sample_count < 6:
        raise InsufficientObservationsError("At least six hybrid observations are required.")
    if dataset.group_count < 3:
        raise InsufficientObservationsError("At least three independent groups are required.")
    cross_validation = cross_validate_migration_model(
        model_factory,
        dataset.features,
        dataset.rates_m_per_year,
        dataset.groups,
        n_splits=n_splits,
    )
    model: MigrationModel = model_factory()
    model.fit(dataset.features, dataset.rates_m_per_year, dataset.groups)
    report = model.report(cross_validation.metrics)
    return HybridModelResult(
        dataset=dataset,
        cross_validation=cross_validation,
        fitted_report=report,
        notes=(
            "Grouped cross-validation holds out whole dune fields.",
            "Metrics describe this sample only and are not operational skill.",
            "Environmental covariates remain unverified unless provenance says otherwise.",
            "Do not apply the fitted model to Jezero or another site without local validation.",
        ),
    )


def predict_rates(dataset: HybridDataset, model: MigrationModel) -> np.ndarray:
    if not isinstance(dataset, HybridDataset):
        raise HybridModelError("dataset must be a HybridDataset.")
    try:
        return np.asarray(model.predict(dataset.features), dtype=np.float64)
    except MigrationModelError:
        raise
    except Exception as exc:
        raise HybridModelError(f"Prediction failed: {exc}") from exc
