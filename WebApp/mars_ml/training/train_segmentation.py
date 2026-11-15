"""U-Net training entry point.

This module is prepared but intentionally has no trained model or embedded
metrics. It refuses to train unless a validated manifest contains labelled
train/validation splits and the training extra (PyTorch) is installed.

Run ``--dry-run`` to validate a manifest without PyTorch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

from mars_ml.computer_vision.image_io import load_image, load_raster, normalize_image
from mars_ml.training.evaluate import segmentation_metrics
from mars_ml.training.prepare_dataset import load_manifest


class TrainingNotConfigured(RuntimeError):
    """Raised when the dataset or environment is insufficient for training."""


class TrainingDependencyError(RuntimeError):
    """Raised when optional training dependencies are unavailable."""


@dataclass(frozen=True)
class TrainingConfig:
    patch_size: int = 256
    epochs: int = 20
    batch_size: int = 4
    learning_rate: float = 1e-3
    base_channels: int = 32
    input_channels: int = 1
    seed: int = 42
    num_workers: int = 0
    device: str = "cpu"
    min_train_samples: int = 8
    min_val_samples: int = 2

    def validate(self) -> None:
        if self.patch_size < 32:
            raise ValueError("patch_size must be at least 32.")
        if self.epochs < 1 or self.batch_size < 1:
            raise ValueError("epochs and batch_size must be positive.")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")
        if self.input_channels not in (1, 3):
            raise ValueError("input_channels must be 1 or 3.")
        if self.min_train_samples < 1 or self.min_val_samples < 1:
            raise ValueError("Minimum sample counts must be positive.")


@dataclass(frozen=True)
class TrainingReadiness:
    ready: bool
    manifest_path: str
    train_samples: int
    val_samples: int
    test_samples: int
    group_count: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    trained_model_present: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_training_inputs(
    manifest_path: str | Path,
    config: TrainingConfig | None = None,
) -> TrainingReadiness:
    """Check whether a manifest can support supervised training."""

    cfg = config or TrainingConfig()
    cfg.validate()
    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    entries = manifest["entries"]
    split_counts = {
        split: sum(1 for entry in entries if entry.get("split") == split)
        for split in ("train", "val", "test")
    }
    reasons: list[str] = []
    warnings = list(manifest.get("warnings", []))
    if split_counts["train"] < cfg.min_train_samples:
        reasons.append(
            f"Train split has {split_counts['train']} samples; minimum is {cfg.min_train_samples}."
        )
    if split_counts["val"] < cfg.min_val_samples:
        reasons.append(
            f"Validation split has {split_counts['val']} samples; minimum is {cfg.min_val_samples}."
        )
    if split_counts["test"] < 1:
        reasons.append("Test split is empty.")
    group_splits: dict[str, set[str]] = {}
    for entry in entries:
        group_splits.setdefault(entry["group_id"], set()).add(entry["split"])
    leaking = sorted(group for group, splits in group_splits.items() if len(splits) > 1)
    if leaking:
        reasons.append(f"Group leakage detected: {leaking}")
    for entry in entries:
        for key in ("image_path", "mask_path"):
            path = Path(entry[key])
            if not path.is_absolute():
                path = manifest_file.parent / path
            if not path.exists():
                reasons.append(f"Missing {key} for {entry.get('sample_id')}: {path}")
        if not entry.get("has_mask"):
            reasons.append(f"Sample without mask: {entry.get('sample_id')}")
    return TrainingReadiness(
        ready=not reasons,
        manifest_path=str(manifest_file.resolve()),
        train_samples=split_counts["train"],
        val_samples=split_counts["val"],
        test_samples=split_counts["test"],
        group_count=int(manifest.get("group_count", len(group_splits))),
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def _resolve(path_text: str, manifest_file: Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else manifest_file.parent / path


def _read_gray(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            image = load_raster(path, band=1)
        except Exception:
            image = load_image(path)
    else:
        image = load_image(path)
    normalized, _ = normalize_image(image.data)
    if normalized.ndim == 3:
        gray = (
            0.299 * normalized[..., 0]
            + 0.587 * normalized[..., 1]
            + 0.114 * normalized[..., 2]
        )
    else:
        gray = normalized
    return np.asarray(gray, dtype=np.float32)


def _read_mask(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            mask_image = load_raster(path, band=1)
        except Exception:
            mask_image = load_image(path)
    else:
        mask_image = load_image(path)
    mask = mask_image.data
    if mask.ndim == 3:
        mask = mask[..., 0]
    return (np.asarray(mask) > 0).astype(np.float32)


def _resize_pair(image: np.ndarray, mask: np.ndarray, size: int) -> tuple[np.ndarray, np.ndarray]:
    image_resized = cv2.resize(image, (size, size), interpolation=cv2.INTER_LINEAR)
    mask_resized = cv2.resize(mask, (size, size), interpolation=cv2.INTER_NEAREST)
    return image_resized.astype(np.float32), mask_resized.astype(np.float32)


def _require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise TrainingDependencyError(
            "PyTorch is required for training. Install mars_ml/requirements-training.txt."
        ) from exc
    return torch


def _build_loader(entries: list[dict[str, Any]], manifest_file: Path, cfg: TrainingConfig, training: bool) -> Any:
    torch = _require_torch()
    from torch.utils.data import DataLoader, Dataset

    class DuneDataset(Dataset):  # type: ignore[misc]
        def __init__(self) -> None:
            self.entries = entries

        def __len__(self) -> int:
            return len(self.entries)

        def __getitem__(self, index: int) -> tuple[Any, Any]:
            entry = self.entries[index]
            image = _read_gray(_resolve(entry["image_path"], manifest_file))
            mask = _read_mask(_resolve(entry["mask_path"], manifest_file))
            image, mask = _resize_pair(image, mask, cfg.patch_size)
            if training:
                if random.random() < 0.5:
                    image = np.ascontiguousarray(image[:, ::-1])
                    mask = np.ascontiguousarray(mask[:, ::-1])
                if random.random() < 0.5:
                    image = np.ascontiguousarray(image[::-1, :])
                    mask = np.ascontiguousarray(mask[::-1, :])
            if cfg.input_channels == 3:
                image_tensor = np.repeat(image[None, ...], 3, axis=0)
            else:
                image_tensor = image[None, ...]
            mask_tensor = mask[None, ...]
            return (
                torch.from_numpy(image_tensor),
                torch.from_numpy(mask_tensor),
            )

    generator = torch.Generator()
    generator.manual_seed(cfg.seed)
    return DataLoader(
        DuneDataset(),
        batch_size=cfg.batch_size,
        shuffle=training,
        num_workers=cfg.num_workers,
        generator=generator,
    )


def _dice_loss_from_logits(logits: Any, targets: Any, epsilon: float = 1e-6) -> Any:
    torch = _require_torch()
    probabilities = torch.sigmoid(logits)
    intersection = torch.sum(probabilities * targets, dim=(1, 2, 3))
    denominator = torch.sum(probabilities, dim=(1, 2, 3)) + torch.sum(targets, dim=(1, 2, 3))
    dice = (2.0 * intersection + epsilon) / (denominator + epsilon)
    return 1.0 - dice.mean()


def _evaluate_loader(model: Any, loader: Any, device: Any) -> dict[str, Any]:
    torch = _require_torch()
    model.eval()
    predictions: list[np.ndarray] = []
    references: list[np.ndarray] = []
    with torch.no_grad():
        for images, masks in loader:
            images = images.to(device)
            logits = model(images)
            probabilities = torch.sigmoid(logits)[:, 0].cpu().numpy()
            truth = masks[:, 0].cpu().numpy() > 0.5
            predictions.append(probabilities >= 0.5)
            references.append(truth)
    metric = segmentation_metrics(
        np.concatenate([p.ravel() for p in predictions]),
        np.concatenate([r.ravel() for r in references]),
    )
    return metric


def train_segmentation(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    config: TrainingConfig | None = None,
) -> dict[str, Any]:
    """Train a U-Net and write a checkpoint plus an actual training report."""

    cfg = config or TrainingConfig()
    readiness = validate_training_inputs(manifest_path, cfg)
    if not readiness.ready:
        raise TrainingNotConfigured(
            "Dataset is not ready for training: " + "; ".join(readiness.reasons)
        )
    torch = _require_torch()
    from mars_ml.models.unet import build_unet

    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    entries = manifest["entries"]
    train_entries = [entry for entry in entries if entry["split"] == "train"]
    val_entries = [entry for entry in entries if entry["split"] == "val"]

    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    device = torch.device(cfg.device)

    model = build_unet(
        input_channels=cfg.input_channels,
        output_channels=1,
        base_channels=cfg.base_channels,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)
    bce = torch.nn.BCEWithLogitsLoss()
    train_loader = _build_loader(train_entries, manifest_file, cfg, training=True)
    val_loader = _build_loader(val_entries, manifest_file, cfg, training=False)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, Any]] = []
    best_val_dice = -1.0
    best_state: dict[str, Any] | None = None
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        running_loss = 0.0
        batches = 0
        for images, masks in train_loader:
            images = images.to(device)
            masks = masks.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = bce(logits, masks) + 0.5 * _dice_loss_from_logits(logits, masks)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.detach().cpu())
            batches += 1
        val_metrics = _evaluate_loader(model, val_loader, device)
        epoch_record = {
            "epoch": epoch,
            "train_loss": running_loss / max(1, batches),
            "validation": val_metrics,
        }
        history.append(epoch_record)
        val_dice = val_metrics.get("dice")
        if val_dice is not None and val_dice > best_val_dice:
            best_val_dice = float(val_dice)
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state is None:
        raise TrainingNotConfigured("No epoch produced a valid validation Dice score.")
    checkpoint_path = output / "unet_best.pt"
    torch.save({"state_dict": best_state, "config": asdict(cfg)}, checkpoint_path)
    manifest_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    report = {
        "status": "trained_on_supplied_manifest",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(checkpoint_path),
        "manifest": str(manifest_file.resolve()),
        "manifest_sha256": manifest_hash,
        "config": asdict(cfg),
        "readiness": readiness.as_dict(),
        "history": history,
        "best_validation_dice": best_val_dice,
        "notes": (
            "Metrics in this report were produced by this run only. "
            "No test-set metric is reported here."
        ),
    }
    (output / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Validated dataset manifest JSON.")
    parser.add_argument("--output-dir", default="models/runs/dune_unet")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    cfg = TrainingConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        patch_size=args.patch_size,
        device=args.device,
    )
    if args.dry_run:
        readiness = validate_training_inputs(args.manifest, cfg)
        print(json.dumps(readiness.as_dict(), indent=2))
        return 0 if readiness.ready else 1
    report = train_segmentation(args.manifest, args.output_dir, config=cfg)
    print(json.dumps({"checkpoint": report["checkpoint"], "best_validation_dice": report["best_validation_dice"]}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
