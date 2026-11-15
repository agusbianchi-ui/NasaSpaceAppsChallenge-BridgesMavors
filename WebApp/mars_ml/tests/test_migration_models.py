from __future__ import annotations

import numpy as np
import pytest

from mars_ml.aeolian_dynamics.environmental_sources import (
    EnvironmentalSourceError,
    load_environmental_sources,
    require_simultaneous,
    source_by_id,
    source_summary,
)
from mars_ml.aeolian_dynamics.hybrid_model import (
    HybridModelError,
    build_hybrid_dataset,
    fit_hybrid_model,
)
from mars_ml.aeolian_dynamics.migration_analysis import observation_from_metric
from mars_ml.aeolian_dynamics.migration_models import (
    InsufficientObservationsError,
    MigrationModelError,
    RandomForestMigrationModel,
    RidgeMigrationModel,
    cross_validate_migration_model,
)
from mars_ml.computer_vision.displacement_detection import (
    MetricDisplacement,
    azimuth_degrees,
)
from mars_ml.training.migration_metrics import (
    MigrationMetricsError,
    migration_metrics,
)
from mars_ml.validation.compare import (
    compare_observations_to_published,
    compare_values_to_range,
    published_as_labels,
    published_range_summary,
)
from mars_ml.validation.published_measurements import (
    load_published_measurements,
    measurement_by_id,
    migration_range,
)


def _metric(dx: float, dy: float) -> MetricDisplacement:
    return MetricDisplacement(
        dx_m=dx,
        dy_m=dy,
        magnitude_m=(dx**2 + dy**2) ** 0.5,
        azimuth_deg=azimuth_degrees(dx, dy),
        meters_per_pixel=(10.0, 10.0),
        method="test",
    )


def _observation(dataset_id: str, dune_id: str, rate: float):
    return observation_from_metric(
        dataset_id,
        dune_id,
        "centroid",
        "2020-01-01T00:00:00Z",
        "2021-01-01T00:00:00Z",
        _metric(rate, 0.0),
    )


def _training_arrays():
    rng = np.random.default_rng(2)
    features = rng.normal(size=(30, 3))
    rates = np.abs(np.abs(features[:, 0]) * 0.4 + rng.normal(scale=0.03, size=30))
    groups = [f"group_{index % 6}" for index in range(30)]
    return features, rates, groups


def test_migration_metrics_handle_angles_and_intervals():
    metrics = migration_metrics(
        [1.0, 2.0, 3.0],
        [1.0, 2.0, 4.0],
        estimate_azimuths_deg=[10.0, 20.0, 30.0],
        reference_azimuths_deg=[5.0, 25.0, 40.0],
        lower_m_per_year=[0.5, 1.5, 2.5],
        upper_m_per_year=[1.5, 2.5, 3.5],
    )
    assert metrics.count == 3
    assert metrics.mae_m_per_year == pytest.approx(1.0 / 3.0)
    assert metrics.mean_absolute_angular_error_deg == pytest.approx(20.0 / 3.0)
    assert metrics.interval_coverage == pytest.approx(2.0 / 3.0)
    filtered = migration_metrics(
        [1.0, np.nan, 3.0],
        [1.0, 2.0, 4.0],
        estimate_azimuths_deg=[10.0, 20.0, 30.0],
        reference_azimuths_deg=[5.0, 25.0, 40.0],
        lower_m_per_year=[0.5, 1.5, 2.5],
        upper_m_per_year=[1.5, 2.5, 3.5],
    )
    assert filtered.count == 2
    with pytest.raises(MigrationMetricsError):
        migration_metrics([1.0], [1.0, 2.0])


def test_ridge_and_random_forest_require_groups_and_valid_targets():
    features, rates, groups = _training_arrays()
    ridge = RidgeMigrationModel(feature_names=("a", "b", "c")).fit(
        features, rates, groups
    )
    assert np.all(ridge.predict(features) >= 0)
    assert ridge.report().sample_count == 30
    forest = RandomForestMigrationModel(feature_names=("a", "b", "c")).fit(
        features, rates, groups
    )
    assert forest.predict(features[:4]).shape == (4,)
    with pytest.raises(InsufficientObservationsError):
        RidgeMigrationModel().fit(features[:5], rates[:5], groups[:5])
    with pytest.raises(MigrationModelError):
        RidgeMigrationModel().fit(features, -rates, groups)


def test_grouped_cross_validation_holds_out_groups():
    features, rates, groups = _training_arrays()
    report = cross_validate_migration_model(
        lambda: RidgeMigrationModel(feature_names=("a", "b", "c")),
        features,
        rates,
        groups,
        n_splits=6,
    )
    assert report.group_count == 6
    assert report.metrics.count > 0
    assert any(fold["status"] == "evaluated" for fold in report.folds)


def test_hybrid_dataset_requires_explicit_covariates():
    observations = [
        _observation("field_a", "dune_1", 1.0),
        _observation("field_a", "dune_2", 1.2),
        _observation("field_b", "dune_3", 0.8),
        _observation("field_b", "dune_4", 0.9),
        _observation("field_c", "dune_5", 1.4),
        _observation("field_c", "dune_6", 1.1),
    ]
    covariates = {
        f"{entry.dataset_id}:{entry.dune_id}": {
            "feature_wind": 3.0 + index,
            "feature_height": 5.0 + index,
        }
        for index, entry in enumerate(observations)
    }
    dataset = build_hybrid_dataset(
        observations,
        covariates,
        feature_names=("feature_wind", "feature_height"),
    )
    assert dataset.sample_count == 6
    assert dataset.group_count == 3
    with pytest.raises(HybridModelError):
        build_hybrid_dataset(
            observations,
            {
                key: value
                for key, value in list(covariates.items())[1:]
            },
            feature_names=("feature_wind", "feature_height"),
        )
    broken = dict(covariates)
    broken["field_a:dune_1"] = {"feature_wind": float("nan"), "feature_height": 5.0}
    with pytest.raises(HybridModelError):
        build_hybrid_dataset(
            observations,
            broken,
            feature_names=("feature_wind", "feature_height"),
        )
    sources = {source.source_id: source for source in load_environmental_sources()}
    with pytest.raises(HybridModelError):
        build_hybrid_dataset(
            observations,
            covariates,
            feature_names=("feature_wind", "feature_height"),
            sources=sources,
            require_verified_sources=True,
        )


def test_hybrid_model_fits_with_grouped_validation():
    observations = []
    covariates = {}
    counter = 0
    for field_index in range(4):
        for dune_index in range(4):
            rate = 0.5 + 0.1 * field_index + 0.02 * dune_index
            observation = _observation(
                f"field_{field_index}", f"dune_{dune_index}", rate
            )
            observations.append(observation)
            covariates[f"field_{field_index}:dune_{dune_index}"] = {
                "feature_wind": rate + 1.0,
                "feature_height": rate + 2.0,
            }
            counter += 1
    dataset = build_hybrid_dataset(
        observations,
        covariates,
        feature_names=("feature_wind", "feature_height"),
    )
    result = fit_hybrid_model(
        dataset,
        lambda: RidgeMigrationModel(feature_names=("feature_wind", "feature_height")),
        n_splits=4,
    )
    assert result.status == "fitted_research_model"
    assert result.cross_validation.metrics.count > 0
    assert result.fitted_report.sample_count == counter


def test_environmental_sources_remain_unverified_context():
    sources = load_environmental_sources()
    assert len(sources) == 5
    summary = source_summary(sources)
    assert summary["unverified"]
    source = source_by_id(sources, "mcd_mars_climate_database")
    assert source.source_type == "model"
    with pytest.raises(EnvironmentalSourceError):
        require_simultaneous(source)
    with pytest.raises(EnvironmentalSourceError):
        source_by_id(sources, "missing")


def test_published_measurements_are_aggregate_context_only():
    measurements = load_published_measurements()
    assert len(measurements) == 4
    coprates = measurement_by_id(measurements, "coprates_brink_migration")
    assert migration_range(measurements, "coprates_chasma_dunes") == (0.1, 0.3)
    inside = compare_values_to_range([0.2, 0.25, 0.3], coprates)
    assert inside.status == "inside_published_range"
    outside = compare_values_to_range([2.0, 3.0, 4.0], coprates)
    assert outside.status == "outside_published_range"
    with pytest.raises(Exception):
        published_as_labels(coprates)
    observations = [
        _observation("coprates_chasma_dunes", "dune_1", 0.2),
        _observation("coprates_chasma_dunes", "dune_2", 0.25),
    ]
    comparisons = compare_observations_to_published(observations, measurements)
    assert comparisons[0].observation_count == 2
    assert comparisons[0].status == "inside_published_range"
    summary = published_range_summary(measurements, "coprates_chasma_dunes")
    assert summary["context_only"] is True
    assert summary["range"] == [0.1, 0.3]
