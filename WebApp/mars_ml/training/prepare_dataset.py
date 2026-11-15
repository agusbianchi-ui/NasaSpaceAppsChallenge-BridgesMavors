"""Build a validated image/mask manifest with leak-resistant grouped splits.

Expected layout::

    <root>/<region>/<sequence>/<observation>/image.<ext>
    <root>/<region>/<sequence>/<observation>/mask.<ext>

The group is the first two directories below ``root`` (region/sequence). All
observations from one group are assigned to exactly one split.

This script validates dimensions, channels, mask binarity and missing files.
It does not download imagery and does not invent labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from mars_ml.computer_vision.image_io import (
    ImageValidationError,
    RasterImage,
    load_image,
    load_raster,
    validate_image_array,
)


class DatasetPreparationError(RuntimeError):
    """Raised when the dataset cannot be prepared safely."""


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
_RASTER_SUFFIXES = {".tif", ".tiff"}


@dataclass(frozen=True)
class DiscoveredPair:
    image_path: Path
    mask_path: Path | None
    group_id: str


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _load_for_validation(path: Path) -> RasterImage:
    if path.suffix.lower() in _RASTER_SUFFIXES:
        try:
            return load_raster(path)
        except (RuntimeError, ImageValidationError):
            return load_image(path)
    return load_image(path)


def discover_pairs(root: str | Path, *, group_depth: int = 2) -> list[DiscoveredPair]:
    """Discover image/mask pairs and infer their leakage group."""

    root_path = Path(root)
    if not root_path.exists():
        raise DatasetPreparationError(f"Dataset root does not exist: {root_path}")
    if group_depth < 1:
        raise DatasetPreparationError("group_depth must be at least 1.")

    pairs: list[DiscoveredPair] = []
    for image_path in sorted(root_path.rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        if "_mask" in image_path.stem.lower():
            continue
        if image_path.stem.lower() == "mask":
            continue
        mask_path = _find_mask(image_path)
        relative_parts = image_path.relative_to(root_path).parts[:-1]
        if len(relative_parts) >= group_depth:
            group_id = "/".join(relative_parts[:group_depth])
        elif relative_parts:
            group_id = "/".join(relative_parts)
        else:
            group_id = "root"
        pairs.append(DiscoveredPair(image_path, mask_path, group_id))
    if not pairs:
        raise DatasetPreparationError(f"No candidate images found below {root_path}.")
    return pairs


def _find_mask(image_path: Path) -> Path | None:
    stem = image_path.stem
    suffix = image_path.suffix
    candidates: list[Path] = []
    if stem.lower().endswith("_image"):
        candidates.append(image_path.with_name(stem[:-6] + "_mask" + suffix))
        candidates.append(image_path.with_name("mask" + suffix))
    candidates.extend(
        [
            image_path.with_name(stem + "_mask" + suffix),
            image_path.with_name(stem + "_label" + suffix),
            image_path.with_name("mask" + suffix),
            image_path.with_name("mask.png"),
            image_path.with_name("mask.tif"),
        ]
    )
    for candidate in candidates:
        if candidate.exists() and candidate != image_path:
            return candidate
    return None


def _mask_as_binary(mask_image: RasterImage) -> tuple[np.ndarray, list[float]]:
    data = mask_image.data
    if data.ndim == 3:
        if data.shape[2] == 1:
            data = data[..., 0]
        else:
            data = data[..., 0]
    valid = np.isfinite(data)
    if not np.any(valid):
        raise DatasetPreparationError("Mask has no finite values.")
    unique = np.unique(data[valid]).astype(float).tolist()
    binary = data > 0
    if len(unique) > 2:
        raise DatasetPreparationError(
            "Mask is not binary after loading. Expected background 0 and foreground > 0."
        )
    if not np.any(binary):
        raise DatasetPreparationError("Mask contains no foreground pixels.")
    return binary, unique


def _inspect_sample(pair: DiscoveredPair) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    image = _load_for_validation(pair.image_path)
    validate_image_array(image.data)
    entry: dict[str, Any] = {
        "sample_id": pair.group_id + "/" + pair.image_path.stem,
        "group_id": pair.group_id,
        "image_path": str(pair.image_path),
        "image_sha256": _sha256(pair.image_path),
        "height": image.height,
        "width": image.width,
        "channels": image.channels,
        "image_dtype": str(image.data.dtype),
        "image_valid_fraction": float(np.mean(image.valid_mask)),
        "crs": image.metadata.crs,
        "transform": list(image.metadata.transform) if image.metadata.transform else None,
        "resolution": list(image.metadata.resolution) if image.metadata.resolution else None,
        "acquisition_datetime_utc": image.metadata.acquisition_datetime,
        "source": image.metadata.source,
    }
    if not np.isfinite(entry["image_valid_fraction"]) or entry["image_valid_fraction"] <= 0:
        raise DatasetPreparationError(f"Image has no valid pixels: {pair.image_path}")

    if pair.mask_path is None:
        entry["mask_path"] = None
        entry["has_mask"] = False
        warnings.append(f"Missing mask for {pair.image_path}")
        return entry, warnings

    mask = _load_for_validation(pair.mask_path)
    binary, unique = _mask_as_binary(mask)
    if mask.width != image.width or mask.height != image.height:
        raise DatasetPreparationError(
            f"Mask/image dimension mismatch for {pair.image_path}: "
            f"{image.width}x{image.height} vs {mask.width}x{mask.height}."
        )
    entry.update(
        {
            "mask_path": str(pair.mask_path),
            "mask_sha256": _sha256(pair.mask_path),
            "has_mask": True,
            "mask_values": unique,
            "mask_foreground_fraction": float(np.mean(binary)),
            "mask_height": mask.height,
            "mask_width": mask.width,
        }
    )
    return entry, warnings


def grouped_split(
    group_ids: Iterable[str],
    *,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, str]:
    """Assign whole groups to splits. All groups appear once."""

    groups = sorted(set(group_ids))
    ratios = {"train": train_ratio, "val": val_ratio, "test": test_ratio}
    if any(value < 0 for value in ratios.values()):
        raise DatasetPreparationError("Split ratios must be non-negative.")
    total = sum(ratios.values())
    if not np.isclose(total, 1.0, atol=1e-9):
        raise DatasetPreparationError("Split ratios must sum to 1.0.")
    if len(groups) < 3:
        raise DatasetPreparationError(
            "At least three distinct groups are required for train/validation/test splits."
        )
    shuffled = list(groups)
    random.Random(seed).shuffle(shuffled)
    n_train = max(1, int(round(len(groups) * train_ratio)))
    n_val = max(1, int(round(len(groups) * val_ratio)))
    n_test = max(1, len(groups) - n_train - n_val)
    if n_train + n_val + n_test > len(groups):
        n_train = len(groups) - 2
        n_val = 1
        n_test = 1
    if n_train < 1 or n_val < 1 or n_test < 1:
        raise DatasetPreparationError("Not enough groups to populate all three splits.")
    assignments: dict[str, str] = {}
    for index, group in enumerate(shuffled):
        if index < n_train:
            assignments[group] = "train"
        elif index < n_train + n_val:
            assignments[group] = "val"
        else:
            assignments[group] = "test"
    return assignments


def prepare_dataset(
    root: str | Path,
    output_manifest: str | Path,
    *,
    group_depth: int = 2,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
    require_masks: bool = True,
) -> dict[str, Any]:
    """Validate pairs, assign grouped splits and write a JSON manifest."""

    pairs = discover_pairs(root, group_depth=group_depth)
    assignments = grouped_split(
        (pair.group_id for pair in pairs),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
    )
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    for pair in pairs:
        entry, sample_warnings = _inspect_sample(pair)
        warnings.extend(sample_warnings)
        if require_masks and not entry["has_mask"]:
            continue
        entry["split"] = assignments[pair.group_id]
        entries.append(entry)
    if not entries:
        raise DatasetPreparationError("No samples with masks were found.")
    if any(entry["split"] == "train" for entry in entries) is False:
        raise DatasetPreparationError("Train split is empty.")
    if any(entry["split"] == "val" for entry in entries) is False:
        raise DatasetPreparationError("Validation split is empty.")
    if any(entry["split"] == "test" for entry in entries) is False:
        raise DatasetPreparationError("Test split is empty.")

    group_splits: dict[str, set[str]] = {}
    for entry in entries:
        group_splits.setdefault(entry["group_id"], set()).add(entry["split"])
    leaking = sorted(group for group, splits in group_splits.items() if len(splits) > 1)
    if leaking:
        raise DatasetPreparationError(f"Group leakage detected: {leaking}")

    manifest = {
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(Path(root).resolve()),
        "seed": seed,
        "group_depth": group_depth,
        "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
        "sample_count": len(entries),
        "split_counts": {
            split: sum(1 for entry in entries if entry["split"] == split)
            for split in ("train", "val", "test")
        },
        "group_count": len(assignments),
        "warnings": warnings,
        "entries": entries,
    }
    output_path = Path(output_manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise DatasetPreparationError(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise DatasetPreparationError("Manifest has no entries.")
    for entry in entries:
        if entry.get("split") not in {"train", "val", "test"}:
            raise DatasetPreparationError(
                f"Invalid split for sample {entry.get('sample_id')}: {entry.get('split')!r}"
            )
        if not entry.get("has_mask"):
            raise DatasetPreparationError(
                f"Sample {entry.get('sample_id')} has no mask and cannot be used for training."
            )
    return manifest


def manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_count": manifest.get("sample_count"),
        "split_counts": manifest.get("split_counts"),
        "group_count": manifest.get("group_count"),
        "warnings": len(manifest.get("warnings", [])),
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Dataset root with region/sequence/observation folders.")
    parser.add_argument("--output", required=True, help="Output JSON manifest.")
    parser.add_argument("--group-depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--allow-missing-masks", action="store_true")
    args = parser.parse_args(argv)
    manifest = prepare_dataset(
        args.root,
        args.output,
        group_depth=args.group_depth,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        require_masks=not args.allow_missing_masks,
    )
    print(json.dumps(manifest_summary(manifest), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
