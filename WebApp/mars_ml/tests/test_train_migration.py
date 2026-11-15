from __future__ import annotations

import csv

import pytest

from mars_ml.training.train_migration import (
    MigrationTrainingError,
    observations_from_rows,
    train_migration_from_table,
)


def _rows():
    rows = []
    for group_index in range(6):
        for pair_index in range(2):
            dx_m = 10.0 + group_index + pair_index * 0.5
            rows.append(
                {
                    "dataset_id": f"field_{group_index}",
                    "dune_id": f"dune_{group_index}_{pair_index}",
                    "method": "centroid",
                    "reference_datetime_utc": "2020-01-01T00:00:00Z",
                    "moving_datetime_utc": "2022-01-01T00:00:00Z",
                    "dx_m": dx_m,
                    "dy_m": 0.0,
                    "distance_standard_error_m": 0.5,
                    "feature_wind": float(group_index + 1),
                    "feature_thermal": float(pair_index + 2),
                }
            )
    return rows


def test_observations_from_rows_requires_explicit_features_and_groups():
    dataset = observations_from_rows(_rows())
    assert dataset.sample_count == 12
    assert dataset.group_count == 6
    assert dataset.feature_names == ("feature_thermal", "feature_wind")
    assert all(observation.valid for observation in dataset.observations)
    assert dataset.rates_m_per_year.min() > 0

    with pytest.raises(MigrationTrainingError):
        observations_from_rows(
            [{"dataset_id": "a", "dune_id": "b", "method": "centroid"}],
            feature_columns=("feature_x",),
        )
    with pytest.raises(MigrationTrainingError):
        observations_from_rows(_rows(), feature_columns=())


def test_train_migration_from_csv_reports_without_checkpoint(tmp_path):
    path = tmp_path / "observations.csv"
    rows = _rows()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = train_migration_from_table(path, n_splits=3)
    assert report["status"] == "trained_research_model"
    assert report["checkpoint_saved"] is False
    assert report["dataset"]["group_count"] == 6
    assert report["cross_validation"]["metrics"]["count"] > 0
    assert report["model_report"]["metrics"] is not None
    assert "not operational skill" in " ".join(report["notes"])


def test_train_migration_rejects_bad_uncertainty_and_unknown_model(tmp_path):
    rows = _rows()
    rows[0]["distance_standard_error_m"] = "not-a-number"
    with pytest.raises(MigrationTrainingError):
        observations_from_rows(rows)
    path = tmp_path / "observations.csv"
    good = _rows()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(good[0]))
        writer.writeheader()
        writer.writerows(good)
    with pytest.raises(MigrationTrainingError):
        train_migration_from_table(path, model_name="earth_rate_transfer")
