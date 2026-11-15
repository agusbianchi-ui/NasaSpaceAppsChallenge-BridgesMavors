"""Pixel-level dune classifier trained from explicit annotation masks.

This is a classical baseline, not the U-Net and not a validated Mars product.
Training requires grouped samples so pixels from the same dune field cannot leak
between train and test. No checkpoint is implied until one is written.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import RasterImage, validate_image_array


class ClassifierTrainingError(ValueError):
    """Raised when a classifier cannot be trained safely."""


@dataclass(frozen=True)
class ClassifierConfig:
    n_estimators: int = 300
    max_depth: int | None = None
    min_samples_leaf: int = 5
    random_state: int = 0
    probability_threshold: float = 0.5
    scales: tuple[int, ...] = (1, 3, 7)

    def validate(self) -> None:
        if self.n_estimators < 10:
            raise ClassifierTrainingError("n_estimators must be at least 10.")
        if self.max_depth is not None and self.max_depth < 1:
            raise ClassifierTrainingError("max_depth must be positive when supplied.")
        if self.min_samples_leaf < 1:
            raise ClassifierTrainingError("min_samples_leaf must be positive.")
        if not 0.0 < self.probability_threshold < 1.0:
            raise ClassifierTrainingError("probability_threshold must be in (0, 1).")
        if not self.scales or any(scale < 1 or scale % 2 == 0 for scale in self.scales):
            raise ClassifierTrainingError("scales must be positive odd integers.")


@dataclass(frozen=True)
class PixelSamples:
    features: np.ndarray
    labels: np.ndarray
    groups: tuple[str, ...]
    feature_names: tuple[str, ...]
    coordinates: np.ndarray
    source_indices: np.ndarray

    def __post_init__(self) -> None:
        matrix = np.asarray(self.features, dtype=np.float64)
        labels = np.asarray(self.labels).astype(np.uint8).reshape(-1)
        if matrix.ndim != 2 or matrix.shape[0] == 0:
            raise ClassifierTrainingError("Features must be a non-empty 2D array.")
        if labels.size != matrix.shape[0]:
            raise ClassifierTrainingError("Label and feature counts differ.")
        if len(self.groups) != matrix.shape[0]:
            raise ClassifierTrainingError("Group and feature counts differ.")
        if len(self.feature_names) != matrix.shape[1]:
            raise ClassifierTrainingError("Feature-name and column counts differ.")
        if not np.all(np.isfinite(matrix)):
            raise ClassifierTrainingError("Features must be finite.")
        if not np.all(np.isin(labels, (0, 1))):
            raise ClassifierTrainingError("Labels must be binary 0/1.")
        if self.coordinates.shape != (matrix.shape[0], 2):
            raise ClassifierTrainingError("Coordinates must be an (N, 2) array.")
        if self.source_indices.shape != (matrix.shape[0],):
            raise ClassifierTrainingError("source_indices must be an (N,) array.")

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
            "positive_fraction": float(np.mean(self.labels)),
        }


def _gray(image: np.ndarray) -> np.ndarray:
    validate_image_array(image)
    value = np.asarray(image, dtype=np.float32)
    if value.ndim == 3:
        if value.shape[2] >= 3:
            value = 0.299 * value[..., 0] + 0.587 * value[..., 1] + 0.114 * value[..., 2]
        else:
            value = value[..., 0]
    if np.nanmax(value) > 1.5:
        finite = np.isfinite(value)
        if np.any(finite):
            low, high = np.percentile(value[finite], (2.0, 98.0))
            if high > low:
                value = np.clip((value - low) / (high - low), 0.0, 1.0)
    return np.asarray(value, dtype=np.float32)


def extract_pixel_features(
    image: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    scales: Sequence[int] = (1, 3, 7),
) -> tuple[np.ndarray, tuple[str, ...], np.ndarray]:
    gray = _gray(image)
    height, width = gray.shape
    if valid_mask is None:
        valid = np.ones(gray.shape, dtype=bool)
    else:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != gray.shape:
            raise ClassifierTrainingError("valid_mask must match the image shape.")
        valid = valid & np.isfinite(gray)
    ys, xs = np.nonzero(valid)
    if ys.size == 0:
        raise ClassifierTrainingError("No valid pixels were supplied.")
    features: list[np.ndarray] = [gray[ys, xs][:, None]]
    names: list[str] = ["gray"]
    if np.asarray(image).ndim == 3:
        raw = np.asarray(image, dtype=np.float32)
        for channel in range(min(3, raw.shape[2])):
            features.append(raw[ys, xs, channel][:, None])
            names.append(f"channel_{channel}")
    for scale in scales:
        if scale < 1 or scale % 2 == 0:
            raise ClassifierTrainingError("scales must be positive odd integers.")
        mean = cv2.boxFilter(gray, ddepth=-1, ksize=(scale, scale), normalize=True)
        mean_square = cv2.boxFilter(gray * gray, ddepth=-1, ksize=(scale, scale), normalize=True)
        variance = np.maximum(mean_square - mean * mean, 0.0)
        features.append(mean[ys, xs][:, None])
        names.append(f"mean_{scale}")
        features.append(np.sqrt(variance)[ys, xs][:, None])
        names.append(f"std_{scale}")
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.hypot(sobel_x, sobel_y)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    features.append(gradient[ys, xs][:, None])
    names.append("gradient_magnitude")
    features.append(laplacian[ys, xs][:, None])
    names.append("laplacian")
    coordinates = np.column_stack([xs, ys]).astype(np.int32)
    return np.concatenate(features, axis=1), tuple(names), coordinates


def build_pixel_samples(
    images: Sequence[np.ndarray | RasterImage],
    masks: Sequence[np.ndarray],
    groups: Sequence[str],
    *,
    valid_masks: Sequence[np.ndarray | None] | None = None,
    scales: Sequence[int] = (1, 3, 7),
    max_samples_per_group: int | None = 4000,
    random_state: int = 0,
) -> PixelSamples:
    if not (len(images) == len(masks) == len(groups)):
        raise ClassifierTrainingError("Images, masks and groups must have equal lengths.")
    if valid_masks is not None and len(valid_masks) != len(images):
        raise ClassifierTrainingError("valid_masks must match the image count.")
    all_features: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []
    all_groups: list[str] = []
    all_coordinates: list[np.ndarray] = []
    all_source_indices: list[np.ndarray] = []
    feature_names: tuple[str, ...] | None = None
    for index, (image, mask, group) in enumerate(zip(images, masks, groups)):
        array = image.data if isinstance(image, RasterImage) else np.asarray(image)
        mask_array = np.asarray(mask).astype(bool)
        if mask_array.ndim != 2 or mask_array.shape != array.shape[:2]:
            raise ClassifierTrainingError(
                f"Image {index}: mask shape must match image height and width."
            )
        valid = None if valid_masks is None else valid_masks[index]
        features, names, coordinates = extract_pixel_features(
            array, valid_mask=valid, scales=scales
        )
        labels = mask_array[coordinates[:, 1], coordinates[:, 0]].astype(np.uint8)
        if feature_names is None:
            feature_names = names
        elif names != feature_names:
            raise ClassifierTrainingError("Feature layout differs between images.")
        all_features.append(features)
        all_labels.append(labels)
        all_groups.extend([str(group)] * labels.size)
        all_coordinates.append(coordinates)
        all_source_indices.append(np.full(labels.size, index, dtype=np.int32))
    matrix = np.concatenate(all_features, axis=0)
    labels = np.concatenate(all_labels, axis=0)
    groups_array = np.asarray(all_groups, dtype=object)
    coordinates = np.concatenate(all_coordinates, axis=0)
    source_indices = np.concatenate(all_source_indices, axis=0)
    if max_samples_per_group is not None:
        rng = np.random.default_rng(random_state)
        keep = np.zeros(matrix.shape[0], dtype=bool)
        for group in sorted(set(all_groups)):
            indices = np.flatnonzero(groups_array == group)
            if indices.size > max_samples_per_group:
                indices = rng.choice(indices, size=max_samples_per_group, replace=False)
            keep[indices] = True
        matrix = matrix[keep]
        labels = labels[keep]
        groups_array = groups_array[keep]
        coordinates = coordinates[keep]
        source_indices = source_indices[keep]
    return PixelSamples(
        features=matrix,
        labels=labels,
        groups=tuple(str(group) for group in groups_array),
        feature_names=feature_names or (),
        coordinates=coordinates,
        source_indices=source_indices,
    )


def _binary_metrics(labels: np.ndarray, predictions: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels).astype(bool)
    predictions = np.asarray(predictions).astype(bool)
    true_positive = int(np.count_nonzero(labels & predictions))
    false_positive = int(np.count_nonzero(~labels & predictions))
    false_negative = int(np.count_nonzero(labels & ~predictions))
    true_negative = int(np.count_nonzero(~labels & ~predictions))
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else None
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    union = true_positive + false_positive + false_negative
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": true_positive / union if union else None,
        "accuracy": (true_positive + true_negative) / max(labels.size, 1),
    }


@dataclass(frozen=True)
class ClassifierReport:
    sample_count: int
    group_count: int
    feature_names: tuple[str, ...]
    train_metrics: dict[str, Any]
    cross_validation: dict[str, Any] | None
    calibration_status: str = "research_baseline_not_validated"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "group_count": self.group_count,
            "feature_names": list(self.feature_names),
            "train_metrics": dict(self.train_metrics),
            "cross_validation": self.cross_validation,
            "calibration_status": self.calibration_status,
            "notes": list(self.notes),
        }


class PixelDuneClassifier:
    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig()
        self.config.validate()
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError as exc:
            raise ClassifierTrainingError("scikit-learn is required for the pixel classifier.") from exc
        self._model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_leaf=self.config.min_samples_leaf,
            random_state=self.config.random_state,
            n_jobs=1,
            class_weight="balanced_subsample",
        )
        self.feature_names: tuple[str, ...] = ()
        self.is_fitted = False
        self.sample_count = 0
        self.group_count = 0

    def fit(self, samples: PixelSamples) -> "PixelDuneClassifier":
        if not isinstance(samples, PixelSamples):
            raise ClassifierTrainingError("samples must be PixelSamples.")
        if samples.sample_count < 50:
            raise ClassifierTrainingError("At least 50 pixel samples are required.")
        if samples.group_count < 2:
            raise ClassifierTrainingError("At least two independent groups are required.")
        if len(set(samples.labels.tolist())) < 2:
            raise ClassifierTrainingError("Both foreground and background samples are required.")
        self._model.fit(samples.features, samples.labels)
        self.feature_names = samples.feature_names
        self.is_fitted = True
        self.sample_count = samples.sample_count
        self.group_count = samples.group_count
        return self

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ClassifierTrainingError("Classifier is not fitted.")
        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.ndim != 2 or matrix.shape[1] != len(self.feature_names):
            raise ClassifierTrainingError("Feature matrix has the wrong number of columns.")
        if not np.all(np.isfinite(matrix)):
            raise ClassifierTrainingError("Features must be finite.")
        probabilities = self._model.predict_proba(matrix)
        classes = list(self._model.classes_)
        if 1 not in classes:
            return np.zeros(matrix.shape[0], dtype=np.float64)
        return np.asarray(probabilities[:, classes.index(1)], dtype=np.float64)

    def predict_mask(
        self,
        image: np.ndarray | RasterImage,
        *,
        valid_mask: np.ndarray | None = None,
        threshold: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        array = image.data if isinstance(image, RasterImage) else np.asarray(image)
        features, names, coordinates = extract_pixel_features(
            array, valid_mask=valid_mask, scales=self.config.scales
        )
        if names != self.feature_names:
            raise ClassifierTrainingError("Image features do not match the trained feature layout.")
        probability = self.predict_proba(features)
        cutoff = self.config.probability_threshold if threshold is None else float(threshold)
        if not 0.0 < cutoff < 1.0:
            raise ClassifierTrainingError("threshold must be in (0, 1).")
        probability_image = np.zeros(array.shape[:2], dtype=np.float32)
        probability_image[coordinates[:, 1], coordinates[:, 0]] = probability
        mask = np.zeros(array.shape[:2], dtype=bool)
        mask[coordinates[:, 1], coordinates[:, 0]] = probability >= cutoff
        return mask, probability_image

    def report(
        self,
        samples: PixelSamples,
        *,
        cross_validation: dict[str, Any] | None = None,
    ) -> ClassifierReport:
        if not self.is_fitted:
            raise ClassifierTrainingError("Classifier is not fitted.")
        predictions = self._model.predict(samples.features)
        metrics = _binary_metrics(samples.labels, predictions)
        return ClassifierReport(
            sample_count=self.sample_count,
            group_count=self.group_count,
            feature_names=self.feature_names,
            train_metrics=metrics,
            cross_validation=cross_validation,
            notes=(
                "Train metrics are optimistic and are not validation.",
                "Grouped cross-validation is required for any skill claim.",
                "This baseline is not the U-Net and is not a validated Mars segmentation model.",
            ),
        )

    def feature_importance(self) -> dict[str, float]:
        if not self.is_fitted:
            raise ClassifierTrainingError("Classifier is not fitted.")
        return {
            name: float(value)
            for name, value in zip(self.feature_names, self._model.feature_importances_)
        }

    def save(self, path: str | Path) -> Path:
        if not self.is_fitted:
            raise ClassifierTrainingError("Cannot save an unfitted classifier.")
        try:
            import joblib
        except ImportError as exc:
            raise ClassifierTrainingError("joblib is required to save the classifier.") from exc
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self._model,
                "config": self.config,
                "feature_names": self.feature_names,
                "sample_count": self.sample_count,
                "group_count": self.group_count,
            },
            output,
        )
        return output

    @classmethod
    def load(cls, path: str | Path) -> "PixelDuneClassifier":
        try:
            import joblib
        except ImportError as exc:
            raise ClassifierTrainingError("joblib is required to load the classifier.") from exc
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        payload = joblib.load(source)
        instance = cls(payload["config"])
        instance._model = payload["model"]
        instance.feature_names = tuple(payload["feature_names"])
        instance.sample_count = int(payload["sample_count"])
        instance.group_count = int(payload["group_count"])
        instance.is_fitted = True
        return instance


def cross_validate_pixel_classifier(
    samples: PixelSamples,
    *,
    config: ClassifierConfig | None = None,
    n_splits: int = 5,
) -> dict[str, Any]:
    try:
        from sklearn.model_selection import GroupKFold
    except ImportError as exc:
        raise ClassifierTrainingError("scikit-learn is required for grouped validation.") from exc
    unique_groups = sorted(set(samples.groups))
    if len(unique_groups) < 2:
        raise ClassifierTrainingError("At least two groups are required.")
    splits = min(n_splits, len(unique_groups))
    group_array = np.asarray(samples.groups, dtype=object)
    folds: list[dict[str, Any]] = []
    predictions = np.full(samples.labels.size, -1, dtype=np.int8)
    for fold_index, (train_index, test_index) in enumerate(
        GroupKFold(n_splits=splits).split(
            samples.features, samples.labels, group_array
        )
    ):
        fold_samples = PixelSamples(
            features=samples.features[train_index],
            labels=samples.labels[train_index],
            groups=tuple(group_array[train_index]),
            feature_names=samples.feature_names,
            coordinates=samples.coordinates[train_index],
            source_indices=samples.source_indices[train_index],
        )
        try:
            classifier = PixelDuneClassifier(config or ClassifierConfig()).fit(fold_samples)
        except ClassifierTrainingError as exc:
            folds.append(
                {
                    "fold": fold_index,
                    "status": "skipped",
                    "reason": str(exc),
                    "test_groups": sorted(set(group_array[test_index].astype(str))),
                }
            )
            continue
        fold_predictions = (
            classifier.predict_proba(samples.features[test_index])
            >= classifier.config.probability_threshold
        ).astype(np.int8)
        predictions[test_index] = fold_predictions
        folds.append(
            {
                "fold": fold_index,
                "status": "evaluated",
                "test_groups": sorted(set(group_array[test_index].astype(str))),
                "test_count": int(test_index.size),
                "metrics": _binary_metrics(samples.labels[test_index], fold_predictions),
            }
        )
    evaluated = predictions >= 0
    if not np.any(evaluated):
        raise ClassifierTrainingError("No fold produced predictions.")
    return {
        "overall": _binary_metrics(samples.labels[evaluated], predictions[evaluated]),
        "folds": folds,
        "group_count": len(unique_groups),
        "notes": (
            "Whole groups are held out per fold.",
            "Skipped folds must be inspected before interpreting the summary.",
        ),
    }


def save_classifier_report(path: str | Path, report: ClassifierReport) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return output
