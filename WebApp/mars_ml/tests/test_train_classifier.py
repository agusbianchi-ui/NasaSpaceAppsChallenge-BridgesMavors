from __future__ import annotations

import numpy as np
import pytest

from mars_ml.training.train_classifier import (
    ClassifierConfig,
    ClassifierTrainingError,
    PixelDuneClassifier,
    build_pixel_samples,
    cross_validate_pixel_classifier,
    extract_pixel_features,
)
from mars_ml.tests.synthetic import dune_scene


def _samples(groups: int = 4, size: int = 64):
    images = []
    masks = []
    labels = []
    for index in range(groups):
        image, mask = dune_scene(
            size,
            size,
            center=(size // 2, size // 2),
            axes=(size // 5, size // 8),
            seed=20 + index,
        )
        images.append(image)
        masks.append(mask)
        labels.append(f"field_{index}")
    return build_pixel_samples(
        images,
        masks,
        labels,
        scales=(1, 3),
        max_samples_per_group=300,
    )


def test_pixel_features_and_training():
    samples = _samples()
    assert samples.sample_count > 50
    assert samples.group_count == 4
    assert samples.features.shape[1] == len(samples.feature_names)
    classifier = PixelDuneClassifier(
        ClassifierConfig(n_estimators=20, min_samples_leaf=2, scales=(1, 3))
    ).fit(samples)
    mask, probability = classifier.predict_mask(
        dune_scene(64, 64, center=(32, 32), axes=(12, 7), seed=30)[0]
    )
    assert mask.shape == (64, 64)
    assert probability.shape == (64, 64)
    assert probability.max() > 0
    report = classifier.report(samples)
    assert report.sample_count == samples.sample_count
    assert report.train_metrics["f1"] is not None
    assert classifier.feature_importance()


def test_grouped_pixel_cross_validation():
    samples = _samples()
    report = cross_validate_pixel_classifier(
        samples,
        config=ClassifierConfig(n_estimators=20, min_samples_leaf=2, scales=(1, 3)),
        n_splits=2,
    )
    assert report["group_count"] == 4
    assert report["overall"]["f1"] is not None
    assert any(fold["status"] == "evaluated" for fold in report["folds"])


def test_classifier_roundtrip_and_guards(tmp_path):
    samples = _samples()
    classifier = PixelDuneClassifier(
        ClassifierConfig(n_estimators=20, min_samples_leaf=2, scales=(1, 3))
    ).fit(samples)
    path = classifier.save(tmp_path / "model.joblib")
    loaded = PixelDuneClassifier.load(path)
    image = dune_scene(64, 64, center=(32, 32), axes=(12, 7), seed=31)[0]
    first_mask, _ = classifier.predict_mask(image)
    second_mask, _ = loaded.predict_mask(image)
    assert np.array_equal(first_mask, second_mask)
    with pytest.raises(ClassifierTrainingError):
        PixelDuneClassifier().save(tmp_path / "unfitted.joblib")


def test_classifier_rejects_one_group_and_single_class():
    samples = _samples()
    with pytest.raises(ClassifierTrainingError):
        PixelDuneClassifier(
            ClassifierConfig(n_estimators=20, scales=(1, 3))
        ).fit(
            type(samples)(
                features=samples.features,
                labels=np.zeros_like(samples.labels),
                groups=samples.groups,
                feature_names=samples.feature_names,
                coordinates=samples.coordinates,
                source_indices=samples.source_indices,
            )
        )
    features, names, coordinates = extract_pixel_features(
        np.zeros((16, 16), dtype=np.float32), scales=(1, 3)
    )
    assert features.shape == (16 * 16, len(names))
    assert coordinates.shape == (16 * 16, 2)
