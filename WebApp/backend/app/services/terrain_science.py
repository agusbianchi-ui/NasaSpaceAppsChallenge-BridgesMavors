"""Read-only scientific queries; regional caches verified once per process.

No outbound network in point queries. No data is replaced by demonstration values.
"""

from pathlib import Path
from functools import lru_cache
import os, json, hashlib, math
import numpy as np
from app.schemas.science import ScienceDatum
from app.services.tes_thermal import thermal_at, ROOT as TES_ROOT
from app.services.terrain_geospatial import (
    model_to_grid,
    grid_to_model,
    model_to_geographic,
    geographic_to_model,
)

ROOT = Path(__file__).resolve().parents[4]
CATALOG = json.loads(
    (Path(__file__).resolve().parents[1] / "data/science_catalog.json").read_text(
        encoding="utf8"
    )
)


def finite(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def verify(path, expected):
    with path.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"Integrity mismatch: {path.name}")


class TerrainScienceService:
    def __init__(self, data_dir=None):
        self.directory = Path(
            data_dir or os.getenv("MARS_SCIENCE_DATA_DIR", ROOT / "output-stage4")
        )
        self.metadata = None
        self.arrays = {}
        self.error = None
        self.dust = None
        self.dust_meta = None
        self.dust_error = None
        try:
            metadata = json.loads(
                (self.directory / "terrain_metadata.json").read_text(encoding="utf8")
            )
            if not metadata.get("georeference_verified"):
                raise ValueError("Source registration has not been validated.")
            shape = (metadata["rows"], metadata["columns"])
            for name in [
                "scientific_elevation",
                "visual_elevation",
                "slope",
                "aspect",
                "roughness",
                "local_relief",
                "valid_mask",
            ]:
                filename = f"{name}.bin"
                path = self.directory / filename
                record = metadata[filename]
                if path.stat().st_size != record["bytes"]:
                    raise ValueError(f"Incorrect size: {filename}")
                verify(path, record["sha256"])
                self.arrays[name] = np.memmap(
                    path,
                    dtype="u1" if name == "valid_mask" else "<f4",
                    mode="r",
                    shape=shape,
                )
            self.metadata = metadata
        except (OSError, KeyError, ValueError) as error:
            self.error = str(error)
            self.arrays = {}
        try:
            self.dust_meta = json.loads(
                (self.directory / "dust-metadata.json").read_text(encoding="utf8")
            )
            verify(
                self.directory / "dust-my36-region.npz", self.dust_meta["cache_sha256"]
            )
            with np.load(
                self.directory / "dust-my36-region.npz", allow_pickle=False
            ) as cache:
                self.dust = {name: cache[name].copy() for name in cache.files}
        except (OSError, KeyError, ValueError) as error:
            self.dust_error = str(error)
            self.dust = None

    def terrain_metadata(self):
        if self.metadata:
            return {"availability": "Available", "metadata": self.metadata}
        return {
            "availability": "Unavailable",
            "reason": self.error,
            "required_files": [
                "output-stage4/terrain_metadata.json",
                "output-stage4/*_elevation.bin",
                "output-stage4/valid_mask.bin",
                "output-stage4/{slope,aspect,roughness,local_relief}.bin",
            ],
            "local_geometry": "Stage3 viewer remains available independently.",
        }

    @lru_cache(maxsize=2048)
    def topography_at(self, row, column):
        return tuple(
            (name, finite(array[row, column]))
            for name, array in self.arrays.items()
            if name != "valid_mask"
        )

    def sources(self):
        result = []
        for source in CATALOG["sources"]:
            item = dict(source)
            if source["id"] == "tes-ti-2007":
                ready = all((TES_ROOT / "numeric" / f"tes_thermal_inertia_{period}{suffix}.tif").is_file()
                            for period in ("day", "night") for suffix in ("", "_quality"))
                item["availability"] = "Available" if ready else "Unavailable"
            if source["id"] == "hrsc-mola-v2":
                item.update(
                    availability="Available" if self.metadata else "Unavailable",
                    cache_error=self.error,
                )
                if self.metadata:
                    item["projection"] = self.metadata["crs_wkt"]
                    item["source_projection"] = self.metadata["source_info"]["wkt"]
                    item["source_nodata"] = self.metadata["source_info"]["nodata"]
                    item["lineage"] = self.metadata["lineage"]
            if source["id"] == "dust-my36":
                item.update(
                    availability="Available"
                    if self.dust is not None
                    else "Unavailable",
                    cache_error=self.dust_error,
                )
                if self.dust_meta:
                    item["source_sha256"] = self.dust_meta["source_sha256"]
                    item["projection"] = "Native latitude/longitude grid, positive east; no reprojection"
                    item["source_nodata"] = "NaN"
            result.append(item)
        return result

    def variables(self):
        available = {s["id"]: s["availability"] for s in self.sources()}
        return [
            {**v, "availability": available[v["source_id"]]}
            for v in CATALOG["variables"]
        ]

    def point(self, x, z, mars_year=None, sol=None):
        cell = model_to_grid(x, z, self.metadata) if self.metadata else None
        covered = cell is not None and self.arrays["valid_mask"][cell] == 1
        position = {
            "x": x,
            "z": z,
            "geographic": None,
            "grid": None,
            "visual_elevation": None,
            "scientific_elevation": None,
        }
        if covered:
            row, column = cell
            values = dict(self.topography_at(row, column))
            geo = model_to_geographic(x, values["visual_elevation"], z)
            position.update(
                grid={
                    "row": row,
                    "column": column,
                    "center_xz": grid_to_model(row, column, self.metadata),
                },
                visual_elevation=values["visual_elevation"],
                scientific_elevation=values["scientific_elevation"],
                geographic={
                    "latitude": geo["latitude"],
                    "longitude": geo["longitude"],
                    "latitude_type": "planetocentric",
                    "longitude_direction": "positive east",
                    "longitude_domain": [-180, 180],
                },
            )
        else:
            values = {}
        sources = {s["id"]: s for s in self.sources()}
        data = {}
        for variable in CATALOG["variables"]:
            source = sources[variable["source_id"]]
            datum = ScienceDatum(
                name=variable["name"],
                unit=variable["unit"],
                source=source["url"],
                product=source["product"],
                spatial_resolution=source["spatial_resolution"],
                temporal_resolution=source["temporal_reference"],
                method=variable.get("method") or source["method"],
                reason=source["limitations"],
            )
            if not covered:
                datum.reason = (
                    "No validated terrain coverage at this position."
                    if self.metadata
                    else "Georeferenced terrain cache unavailable; local viewer is independent."
                )
            elif source["id"] == "hrsc-mola-v2":
                value = values[variable["id"]]
                datum.value = value
                datum.availability = "Available" if value is not None else "Unavailable"
                datum.classification = "Derived" if value is not None else "Unavailable"
                datum.reason = (
                    None
                    if value is not None
                    else "Complete 3x3 neighborhood required; aspect is undefined on flat terrain."
                )
                datum.date_or_scenario = "Static source composite"
                datum.sample = {
                    "grid": position["grid"],
                    "source_resolution_nominal_m": 200,
                    "processed_grid_m": 250,
                }
            elif source["id"] == "dust-my36":
                self.sample_dust(
                    datum, geo["longitude"], geo["latitude"], mars_year, sol
                )
            elif source["id"] == "tes-ti-2007":
                period = variable["id"].rsplit("_", 1)[1]
                sampled = thermal_at(geo["latitude"], geo["longitude"], period)
                datum.value = sampled["value"]
                datum.availability = "Available" if sampled["value"] is not None else "Unavailable"
                datum.classification = "Derived" if sampled["value"] is not None else "Unavailable"
                datum.reason = sampled.get("reason") or source["limitations"]
                datum.date_or_scenario = source["temporal_reference"]
                datum.sample = sampled
            data[variable["id"]] = datum.model_dump()
        return {
            "coverage": "Available" if covered else "Unavailable",
            "position": position,
            "variables": data,
            "notice": "Scientific elevations retain the source product reference; visual heights are exaggerated. No route safety assessment.",
        }

    def sample_dust(self, datum, longitude, latitude, mars_year, sol):
        if self.dust is None:
            datum.reason = "Regional dust cache unavailable."
            return
        if mars_year != 36 or sol is None:
            datum.reason = "Select Mars year36 and sol-of-year1â€“669 explicitly; no current-date default."
            return
        west, south, east, north = self.dust_meta["bounds"]
        if not west <= longitude < east or not south <= latitude < north:
            datum.reason = "Outside native dust cache coverage."
            return
        indices = np.flatnonzero(self.dust["SOY"] == sol)
        if not len(indices):
            datum.reason = "No exact sol in cached dataset."
            return
        t = int(indices[0])
        r = int(np.argmin(abs(self.dust["latitude"] - latitude)))
        c = int(np.argmin(abs(self.dust["longitude"] - longitude)))
        value = finite(self.dust["cdod610"][t, r, c])
        uncertainty = finite(self.dust["cdod610unc"][t, r, c])
        datum.value = value
        datum.availability = "Available" if value is not None else "Unavailable"
        datum.classification = "Derived" if value is not None else "Unavailable"
        datum.reason = (
            None
            if value is not None
            else "Original dataset has no observation-derived value for this sol/cell."
        )
        datum.uncertainty = (
            {
                "value": uncertainty,
                "unit": "Pa/Pa",
                "method": "Original combined uncertainty cdod610unc",
            }
            if uncertainty is not None and value is not None
            else None
        )
        datum.date_or_scenario = {
            "mars_year": 36,
            "sol_of_year": sol,
            "solar_longitude_ls": finite(self.dust["Ls"][t]),
            "local_time": "diurnal mean",
            "reference_time_MJD": finite(self.dust["aveMJD"][t]),
            "cell_time_anomaly_days": finite(self.dust["gridMJDanom"][t, r, c]),
        }
        datum.sample = {
            "native_cell_center": [
                float(self.dust["longitude"][c]),
                float(self.dust["latitude"][r]),
            ],
            "native_cell_bounds": [
                float(self.dust["longitude"][c] - 3),
                float(self.dust["latitude"][r] - 2.5),
                float(self.dust["longitude"][c] + 3),
                float(self.dust["latitude"][r] + 2.5),
            ],
            "observation_window_sols": finite(self.dust["cdodtw"][t, r, c]),
            "mean_observation_count": finite(self.dust["cdodnum"][t, r, c]),
            "reliability": finite(self.dust["cdodrel"][t, r, c]),
        }

    def geographic_point(self, latitude, longitude, mars_year=None, sol=None):
        if not self.metadata:
            result = self.point(0, 0, mars_year, sol)
            result["position"]["x"] = None
            result["position"]["z"] = None
            result["requested_geographic"] = {"latitude": latitude, "longitude": longitude}
            return result
        position = geographic_to_model(latitude, longitude, 0)
        return self.point(position["x"], position["z"], mars_year, sol)


@lru_cache(maxsize=1)
def get_terrain_science_service():
    return TerrainScienceService()
