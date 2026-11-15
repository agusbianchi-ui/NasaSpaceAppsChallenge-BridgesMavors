# Models

No trained model or checkpoint is included in this repository.

The classical OpenCV baseline runs without weights. The U-Net adapter expects a
checkpoint produced by `mars_ml/training/train_segmentation.py` from a validated,
labelled manifest:

```bash
uv pip install --python mars_ml/.venv/bin/python \
  -r mars_ml/requirements.txt -r mars_ml/requirements-training.txt
mars_ml/.venv/bin/python -m mars_ml.training.prepare_dataset \
  --root mars_ml/datasets/earth/sahara/labelled \
  --output mars_ml/datasets/earth/sahara/manifest.json
mars_ml/.venv/bin/python -m mars_ml.training.train_segmentation \
  --manifest mars_ml/datasets/earth/sahara/manifest.json \
  --output-dir mars_ml/models/runs/sahara_unet
```

The checkpoint is written to `models/runs/` and ignored by git. Never claim a
model is trained unless a checkpoint and its run report exist. Never copy
validation metrics into documentation as if they were test metrics.
