"""Fail the Render build when required local deployment datasets are absent."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
science = root / "output-stage4"
numeric = root / "data/additional-science/BridgesMavors_science_pack/numeric"
required = [science / f"{name}.bin" for name in (
    "scientific_elevation", "visual_elevation", "slope", "aspect", "roughness", "local_relief", "valid_mask"
)] + [science / "terrain_metadata.json", science / "dust-metadata.json", science / "dust-my36-region.npz"]
required += [numeric / f"tes_thermal_inertia_{name}.tif" for name in ("day", "night", "day_quality", "night_quality")]
missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Missing deployment datasets: " + ", ".join(missing))
print("Scientific deployment datasets found")
