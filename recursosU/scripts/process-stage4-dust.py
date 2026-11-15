"""Cache native-resolution dust cells intersecting terrain; no spatial interpolation."""

from pathlib import Path
import json, hashlib
import numpy as np, netCDF4

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output-stage4"
downloads = json.loads((ROOT / "data/science/downloads.json").read_text())
with (ROOT / "data/science/dust-my36.nc").open("rb") as source_file:
    digest = hashlib.file_digest(source_file, "sha256").hexdigest()
if digest != downloads["dust-my36.nc"]["sha256"]:
    raise ValueError("Dust source integrity mismatch; no processing performed.")
meta = json.loads((OUT / "terrain_metadata.json").read_text())
west, south, east, north = meta["coverage_lon_lat"]
with netCDF4.Dataset(ROOT / "data/science/dust-my36.nc") as ds:
    lon = np.array(ds["longitude"][:])
    lat = np.array(ds["latitude"][:])
    cols = np.where((lon + 3 > west) & (lon - 3 <= east))[0]
    rows = np.where((lat + 2.5 > south) & (lat - 2.5 <= north))[0]
    arrays = {name: np.array(ds[name][:]) for name in ["Time", "SOY", "Ls", "aveMJD"]}
    arrays.update(longitude=lon[cols], latitude=lat[rows])
    for name in [
        "cdod610",
        "cdod610unc",
        "cdodnum",
        "cdodtw",
        "cdodrel",
        "gridMJDanom",
    ]:
        arrays[name] = np.ma.filled(ds[name][:, rows, cols], np.nan).astype("<f4")
    # Preserve native NaNs rather than replace absence with zero.
    np.savez_compressed(OUT / "dust-my36-region.npz", **arrays)
    info = {
        "product": "Gridded CDOD MY36 v2.5",
        "source_file": "data/science/dust-my36.nc",
        "source_sha256": hashlib.sha256(
            (ROOT / "data/science/dust-my36.nc").read_bytes()
        ).hexdigest(),
        "native_resolution_degrees": [6, 5],
        "temporal_resolution": "1 sol; diurnal average, source observation windows recorded per cell",
        "year": 36,
        "sol_range": [int(arrays["SOY"][0]), int(arrays["SOY"][-1])],
        "longitude_centers": lon[cols].tolist(),
        "latitude_centers": lat[rows].tolist(),
        "source_rows": rows.tolist(),
        "source_columns": cols.tolist(),
        "bounds": [
            float(lon[cols].min() - 3),
            float(lat[rows].min() - 2.5),
            float(lon[cols].max() + 3),
            float(lat[rows].max() + 2.5),
        ],
        "classification": "Derived",
        "value": "9.3 micron absorption column dust optical depth normalized to 610 Pa",
        "units": "Pa/Pa",
        "not_equivalent_to": "visible extinction, surface dust, local instantaneous opacity, storm forecast",
        "method": "Native cell lookup; daily value by exact SOY, no interpolation or pressure conversion",
        "nodata": "NaN",
        "valid_daily_cells": int(np.isfinite(arrays["cdod610"]).sum()),
        "license": ds.getncattr("copyright"),
        "original_global_metadata": {key: ds.getncattr(key) for key in ds.ncattrs()},
        "variables": {
            name: {key: ds[name].getncattr(key) for key in ds[name].ncattrs()}
            for name in arrays
            if name in ds.variables
        },
    }
    info["cache_sha256"] = hashlib.sha256(
        (OUT / "dust-my36-region.npz").read_bytes()
    ).hexdigest()
    (OUT / "dust-metadata.json").write_text(json.dumps(info, indent=2), encoding="utf8")
    print(
        json.dumps(
            {key: info[key] for key in ["bounds", "valid_daily_cells", "sol_range"]}
        )
    )
