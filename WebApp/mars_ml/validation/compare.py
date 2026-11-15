"""Compare local aggregate results with published ranges, without relabelling.

Published ranges are context. A median inside a published range does not prove
correctness; a median outside it is a prompt to inspect registration, dates,
segmentation and scale, not evidence that the published range is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from mars_ml.aeolian_dynamics.migration_analysis import MigrationObservation
from mars_ml.validation.published_measurements import (
    PublishedMeasurement,
    measurements_for_dataset,
    migration_range,
)


class ComparisonError(ValueError):
    """Raised when a comparison would misuse published values."""


@dataclass(frozen=True)
class AggregateComparison:
    dataset_id: str
    measurement_ids: tuple[str, ...]
    method: str
    observation_count: int
    observed_median: float | None
    observed_iqr: tuple[float, float] | None
    published_min: float | None
    published_max: float | None
    unit: str | None
    status: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "measurement_ids": list(self.measurement_ids),
            "method": self.method,
            "observation_count": self.observation_count,
            "observed_median": self.observed_median,
            "observed_iqr": list(self.observed_iqr) if self.observed_iqr else None,
            "published_min": self.published_min,
            "published_max": self.published_max,
            "unit": self.unit,
            "status": self.status,
            "notes": list(self.notes),
        }


def _migration_measurements(
    measurements: Iterable[PublishedMeasurement], dataset_id: str
) -> tuple[PublishedMeasurement, ...]:
    return tuple(
        measurement
        for measurement in measurements_for_dataset(measurements, dataset_id)
        if measurement.quantity
        in {"dune_migration_rate", "dune_brink_migration_rate"}
    )


def compare_values_to_range(
    values: Sequence[float] | np.ndarray,
    published: PublishedMeasurement,
    *,
    dataset_id: str | None = None,
    method: str = "aggregate",
) -> AggregateComparison:
    array = np.asarray(list(values), dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        raise ComparisonError("No finite values were supplied.")
    median = float(np.median(array))
    iqr = (
        float(np.percentile(array, 25)),
        float(np.percentile(array, 75)),
    )
    inside_median = published.value_min <= median <= published.value_max
    overlaps = iqr[1] >= published.value_min and iqr[0] <= published.value_max
    if inside_median:
        status = "inside_published_range"
    elif overlaps:
        status = "partial_overlap"
    else:
        status = "outside_published_range"
    return AggregateComparison(
        dataset_id=dataset_id or published.dataset_id,
        measurement_ids=(published.measurement_id,),
        method=method,
        observation_count=int(array.size),
        observed_median=median,
        observed_iqr=iqr,
        published_min=published.value_min,
        published_max=published.value_max,
        unit=published.unit,
        status=status,
        notes=(
            "Comparison uses an aggregate median and IQR, not individual labels.",
            "Agreement does not establish measurement accuracy.",
            "A mismatch requires checking dates, registration, segmentation and scale.",
            f"Published scope: {published.spatial_scope}; {published.temporal_scope}.",
        ),
    )


def compare_observations_to_published(
    observations: Iterable[MigrationObservation],
    measurements: Iterable[PublishedMeasurement],
    *,
    dataset_id: str | None = None,
    method: str | None = None,
) -> tuple[AggregateComparison, ...]:
    observation_list = list(observations)
    if dataset_id is None:
        dataset_ids = sorted(
            {observation.dataset_id for observation in observation_list if observation.valid}
        )
    else:
        dataset_ids = [dataset_id]
    outputs: list[AggregateComparison] = []
    for current_dataset in dataset_ids:
        selected = [
            observation
            for observation in observation_list
            if observation.valid
            and observation.dataset_id == current_dataset
            and (method is None or observation.method == method)
        ]
        if not selected:
            outputs.append(
                AggregateComparison(
                    dataset_id=current_dataset,
                    measurement_ids=(),
                    method=method or "all",
                    observation_count=0,
                    observed_median=None,
                    observed_iqr=None,
                    published_min=None,
                    published_max=None,
                    unit=None,
                    status="not_comparable_no_valid_observations",
                    notes=("No valid migration observations were available.",),
                )
            )
            continue
        published_entries = _migration_measurements(measurements, current_dataset)
        if not published_entries:
            outputs.append(
                AggregateComparison(
                    dataset_id=current_dataset,
                    measurement_ids=(),
                    method=method or "all",
                    observation_count=len(selected),
                    observed_median=float(
                        np.median([entry.rate_m_per_year for entry in selected if entry.rate_m_per_year is not None])
                    ),
                    observed_iqr=None,
                    published_min=None,
                    published_max=None,
                    unit=None,
                    status="not_comparable_no_published_range",
                    notes=("No published migration range for this dataset.",),
                )
            )
            continue
        rates = [
            entry.rate_m_per_year
            for entry in selected
            if entry.rate_m_per_year is not None and np.isfinite(entry.rate_m_per_year)
        ]
        for published in published_entries:
            outputs.append(
                compare_values_to_range(
                    rates,
                    published,
                    dataset_id=current_dataset,
                    method=method or "all",
                )
            )
    return tuple(outputs)


def published_range_summary(
    measurements: Iterable[PublishedMeasurement], dataset_id: str
) -> dict[str, Any]:
    entries = _migration_measurements(measurements, dataset_id)
    combined = migration_range(measurements, dataset_id)
    return {
        "dataset_id": dataset_id,
        "measurement_ids": [entry.measurement_id for entry in entries],
        "range": list(combined) if combined else None,
        "units": sorted({entry.unit for entry in entries}),
        "context_only": True,
    }


def published_as_labels(measurement: PublishedMeasurement) -> None:
    raise ComparisonError(
        f"{measurement.measurement_id}: published values are aggregate context and "
        "must not be converted into per-dune labels."
    )
