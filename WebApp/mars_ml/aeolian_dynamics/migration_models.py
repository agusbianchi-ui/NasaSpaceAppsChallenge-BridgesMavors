"""Interpretable migration models with grouped validation.

Models are research tools, not operational predictions. They require a minimum
number of observations, finite non-negative rates and groups that keep dune
fields separate during cross-validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

import numpy as np

from mars_ml.training.migration_metrics import (
    MigrationMetrics,
    MigrationMetricsError,
    migration_metrics,
)


class MigrationModelError(RuntimeError):
    """Raised when a migration model cannot be fitted or used safely."""


class InsufficientObservationsError(MigrationModelError):
    """Raised when there are too few independent observations."""


class ModelNotConfiguredError(MigrationModelError):
    """Raised when an optional model dependency is absent."""


class MigrationModel(Protocol):
    feature_names: tuple[str, ...]

    def fit(self, features: np.ndarray, rates: np.ndarray, groups: Sequence[str] | None = None) -> "MigrationModel": ...

    def predict(self, features: np.ndarray) -> np.ndarray: ...

    def as_dict(self) -> dict[str, Any]: ...


def _validate_features(features: np.ndarray, *, expected_features: int | None = None) -> np.ndarray:
    array = np.asarray(features, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    if array.ndim != 2:
        raise MigrationModelError("Features must be a 2D array.")
    if array.shape[0] == 0 or array.shape[1] == 0:
        raise MigrationModelError("Features cannot be empty.")
    if not np.all(np.isfinite(array)):
        raise MigrationModelError("Features must be finite; impute only with an explicit method.")
    if expected_features is not None and array.shape[1] != expected_features:
        raise MigrationModelError(
            f"Expected {expected_features} features, received {array.shape[1]}."
        )
    return array


def _validate_rates(rates: np.ndarray, expected_length: int) -> np.ndarray:
    array = np.asarray(rates, dtype=np.float64).reshape(-1)
    if array.size != expected_length:
        raise MigrationModelError("Rate and feature counts differ.")
    if not np.all(np.isfinite(array)):
        raise MigrationModelError("Rates must be finite.")
    if np.any(array < 0):
        raise MigrationModelError("Migration magnitudes cannot be negative.")
    return array


def _validate_groups(groups: Sequence[str] | None, length: int) -> tuple[str, ...]:
    if groups is None:
        return tuple(f"sample_{index}" for index in range(length))
    values = tuple(str(group) for group in groups)
    if len(values) != length:
        raise MigrationModelError("Group and feature counts differ.")
    if any(not value.strip() for value in values):
        raise MigrationModelError("Groups cannot be empty.")
    return values


@dataclass(frozen=True)
class CrossValidationReport:
    metrics: MigrationMetrics
    folds: tuple[dict[str, Any], ...]
    group_count: int
    feature_names: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics.as_dict(),
            "folds": [dict(fold) for fold in self.folds],
            "group_count": self.group_count,
            "feature_names": list(self.feature_names),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ModelReport:
    model_name: str
    feature_names: tuple[str, ...]
    sample_count: int
    group_count: int
    metrics: MigrationMetrics | None
    calibration_status: str
    feature_importance: dict[str, float] = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "feature_names": list(self.feature_names),
            "sample_count": self.sample_count,
            "group_count": self.group_count,
            "metrics": self.metrics.as_dict() if self.metrics else None,
            "calibration_status": self.calibration_status,
            "feature_importance": dict(self.feature_importance),
            "notes": list(self.notes),
        }


class RidgeMigrationModel:
    def __init__(self, *, alpha: float = 1.0, feature_names: Sequence[str] | None = None) -> None:
        if alpha < 0:
            raise MigrationModelError("alpha cannot be negative.")
        try:
            from sklearn.linear_model import Ridge
        except ImportError as exc:
            raise ModelNotConfiguredError("scikit-learn is required for RidgeMigrationModel.") from exc
        self.alpha = float(alpha)
        self._model = Ridge(alpha=self.alpha)
        self.feature_names = tuple(feature_names or ())
        self.is_fitted = False
        self.sample_count = 0
        self.group_count = 0

    def fit(
        self,
        features: np.ndarray,
        rates: np.ndarray,
        groups: Sequence[str] | None = None,
    ) -> "RidgeMigrationModel":
        matrix = _validate_features(features)
        target = _validate_rates(rates, matrix.shape[0])
        validated_groups = _validate_groups(groups, matrix.shape[0])
        if matrix.shape[0] < 6:
            raise InsufficientObservationsError("At least six observations are required.")
        if len(set(validated_groups)) < 3:
            raise InsufficientObservationsError("At least three distinct groups are required.")
        if not self.feature_names:
            self.feature_names = tuple(f"feature_{index}" for index in range(matrix.shape[1]))
        self._model.fit(matrix, target)
        self.is_fitted = True
        self.sample_count = int(matrix.shape[0])
        self.group_count = len(set(validated_groups))
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise MigrationModelError("Model is not fitted.")
        matrix = _validate_features(features, expected_features=len(self.feature_names))
        predictions = np.asarray(self._model.predict(matrix), dtype=np.float64)
        return np.maximum(predictions, 0.0)

    def report(self, metrics: MigrationMetrics | None = None) -> ModelReport:
        importance = {
            name: float(value)
            for name, value in zip(self.feature_names, np.ravel(self._model.coef_))
        }
        return ModelReport(
            model_name="ridge",
            feature_names=self.feature_names,
            sample_count=self.sample_count,
            group_count=self.group_count,
            metrics=metrics,
            calibration_status="research_model_requires_external_validation",
            feature_importance=importance,
            notes=(
                "Ridge regression is an interpretable baseline.",
                "Coefficients are associations, not causal transport laws.",
                "Negative predictions are clipped to zero; this is an extrapolation guard, not a physical model.",
                "Do not apply Earth-calibrated coefficients to Mars.",
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": "ridge",
            "alpha": self.alpha,
            "feature_names": list(self.feature_names),
            "is_fitted": self.is_fitted,
            "sample_count": self.sample_count,
            "group_count": self.group_count,
        }


class RandomForestMigrationModel:
    def __init__(
        self,
        *,
        n_estimators: int = 200,
        max_depth: int | None = 6,
        min_samples_leaf: int = 2,
        random_state: int = 0,
        feature_names: Sequence[str] | None = None,
    ) -> None:
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError as exc:
            raise ModelNotConfiguredError(
                "scikit-learn is required for RandomForestMigrationModel."
            ) from exc
        if n_estimators < 10:
            raise MigrationModelError("n_estimators must be at least 10.")
        if min_samples_leaf < 1:
            raise MigrationModelError("min_samples_leaf must be positive.")
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=1,
        )
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.feature_names = tuple(feature_names or ())
        self.is_fitted = False
        self.sample_count = 0
        self.group_count = 0

    def fit(
        self,
        features: np.ndarray,
        rates: np.ndarray,
        groups: Sequence[str] | None = None,
    ) -> "RandomForestMigrationModel":
        matrix = _validate_features(features)
        target = _validate_rates(rates, matrix.shape[0])
        validated_groups = _validate_groups(groups, matrix.shape[0])
        if matrix.shape[0] < 12:
            raise InsufficientObservationsError("At least twelve observations are required.")
        if len(set(validated_groups)) < 3:
            raise InsufficientObservationsError("At least three distinct groups are required.")
        if not self.feature_names:
            self.feature_names = tuple(f"feature_{index}" for index in range(matrix.shape[1]))
        self._model.fit(matrix, target)
        self.is_fitted = True
        self.sample_count = int(matrix.shape[0])
        self.group_count = len(set(validated_groups))
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise MigrationModelError("Model is not fitted.")
        matrix = _validate_features(features, expected_features=len(self.feature_names))
        predictions = np.asarray(self._model.predict(matrix), dtype=np.float64)
        return np.maximum(predictions, 0.0)

    def report(self, metrics: MigrationMetrics | None = None) -> ModelReport:
        importance = {
            name: float(value)
            for name, value in zip(self.feature_names, self._model.feature_importances_)
        }
        return ModelReport(
            model_name="random_forest",
            feature_names=self.feature_names,
            sample_count=self.sample_count,
            group_count=self.group_count,
            metrics=metrics,
            calibration_status="research_model_requires_external_validation",
            feature_importance=importance,
            notes=(
                "Random forest is a non-linear baseline for tabular covariates.",
                "Feature importance is not causal evidence.",
                "Negative predictions are clipped to zero; this is an extrapolation guard, not a physical model.",
                "Grouped validation is required; random patch splits leak information.",
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": "random_forest",
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_leaf": self.min_samples_leaf,
            "random_state": self.random_state,
            "feature_names": list(self.feature_names),
            "is_fitted": self.is_fitted,
            "sample_count": self.sample_count,
            "group_count": self.group_count,
        }


def cross_validate_migration_model(
    model_factory: Any,
    features: np.ndarray,
    rates: np.ndarray,
    groups: Sequence[str],
    *,
    n_splits: int = 5,
) -> CrossValidationReport:
    try:
        from sklearn.model_selection import GroupKFold
    except ImportError as exc:
        raise ModelNotConfiguredError("scikit-learn is required for grouped cross-validation.") from exc
    matrix = _validate_features(features)
    target = _validate_rates(rates, matrix.shape[0])
    validated_groups = _validate_groups(groups, matrix.shape[0])
    unique_groups = sorted(set(validated_groups))
    if len(unique_groups) < 2:
        raise InsufficientObservationsError("At least two groups are required for validation.")
    splits = min(n_splits, len(unique_groups))
    if splits < 2:
        raise InsufficientObservationsError("At least two validation folds are required.")
    group_array = np.asarray(validated_groups, dtype=object)
    predictions = np.full(matrix.shape[0], np.nan, dtype=np.float64)
    fold_reports: list[dict[str, Any]] = []
    for fold_index, (train_index, test_index) in enumerate(
        GroupKFold(n_splits=splits).split(matrix, target, group_array)
    ):
        model = model_factory()
        try:
            model.fit(matrix[train_index], target[train_index], group_array[train_index])
        except InsufficientObservationsError as exc:
            fold_reports.append(
                {
                    "fold": fold_index,
                    "status": "skipped",
                    "reason": str(exc),
                    "train_count": int(train_index.size),
                    "test_count": int(test_index.size),
                }
            )
            continue
        fold_predictions = model.predict(matrix[test_index])
        predictions[test_index] = fold_predictions
        fold_reports.append(
            {
                "fold": fold_index,
                "status": "evaluated",
                "train_count": int(train_index.size),
                "test_count": int(test_index.size),
                "test_groups": sorted(set(group_array[test_index].astype(str))),
                "metrics": migration_metrics(
                    fold_predictions,
                    target[test_index],
                ).as_dict(),
            }
        )
    finite = np.isfinite(predictions)
    if not np.any(finite):
        raise InsufficientObservationsError("No fold produced predictions.")
    metrics = migration_metrics(predictions[finite], target[finite])
    return CrossValidationReport(
        metrics=metrics,
        folds=tuple(fold_reports),
        group_count=len(unique_groups),
        feature_names=tuple(getattr(model_factory(), "feature_names", ())),
        notes=(
            "Predictions come from held-out groups.",
            "Metrics are not evidence of operational skill.",
            "Inspect skipped folds and group sizes before interpreting the summary.",
        ),
    )


def save_model_report(path: str | Path, report: ModelReport) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return output
