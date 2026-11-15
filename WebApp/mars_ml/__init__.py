"""MARS OPS aeolian dynamics toolkit.

This package is an independent scientific workspace. The FastAPI backend
imports it as an installed Python package; it never imports the React frontend.

Scientific scope:
- Detect and segment candidate dune regions with classical computer vision.
- Register multitemporal imagery and reject unreliable alignment.
- Estimate apparent 2D displacement only when the registration and spatial
  scale are known.
- Extract morphology features for future supervised learning.

Nothing in this package claims that a segmentation model has been trained.
"""

__version__ = "0.1.0"

SCIENTIFIC_STATUS = "research_pipeline_unvalidated"
