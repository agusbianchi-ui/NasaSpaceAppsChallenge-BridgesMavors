"""Image loading, validation and normalization with geospatial metadata.

The loader keeps raster coordinates (CRS, affine transform, nodata and pixel
resolution) attached to the pixel array. Cropping updates the affine transform
so a cropped array never silently loses its georeferencing.

Rasterio is imported lazily so unit tests and classical CV experiments can run
with only NumPy and OpenCV for ordinary images.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

_AFFINE_FIELDS = ("a", "b", "c", "d", "e", "f")


class ImageValidationError(ValueError):
    """Raised when an image or its metadata is not usable for analysis."""


class CRSUnitError(ImageValidationError):
    """Raised when a metric operation is requested on a non-metric CRS."""


@dataclass(frozen=True)
class SpatialMetadata:
    """Georeferencing and provenance attached to an image.

    ``resolution`` is expressed in CRS units per pixel as ``(x, y)``. For a
    geographic CRS those units are degrees and MUST NOT be treated as metres.
    """

    crs: str | None = None
    transform: tuple[float, float, float, float, float, float] | None = None
    resolution: tuple[float, float] | None = None
    nodata: float | None = None
    acquisition_datetime: str | None = None
    source: str | None = None
    band_names: tuple[str, ...] = ()
    extra: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.transform is not None and len(self.transform) != 6:
            raise ImageValidationError("Affine transform must have six coefficients.")
        if self.resolution is not None:
            if len(self.resolution) != 2:
                raise ImageValidationError("Resolution must be a (x, y) pair.")
            if not all(np.isfinite(v) and v > 0 for v in self.resolution):
                raise ImageValidationError("Resolution values must be finite and positive.")
        if self.nodata is not None and not np.isfinite(self.nodata):
            raise ImageValidationError("Nodata values must be finite when declared.")

    @property
    def linear_units(self) -> str | None:
        return crs_linear_units(self.crs)

    def ensure_metric_resolution(self) -> tuple[float, float]:
        units = self.linear_units
        if units not in {"metre", "meter", "m"}:
            raise CRSUnitError(
                f"Metric operation requires metre CRS units; found {units!r}."
            )
        if self.resolution is None or not all(
            np.isfinite(value) and value > 0 for value in self.resolution
        ):
            raise CRSUnitError("Metric operation requires a valid (x, y) resolution.")
        return self.resolution

    def as_dict(self) -> dict[str, Any]:
        return {
            "crs": self.crs,
            "transform": list(self.transform) if self.transform else None,
            "resolution": list(self.resolution) if self.resolution else None,
            "linear_units": self.linear_units,
            "nodata": self.nodata,
            "acquisition_datetime": self.acquisition_datetime,
            "source": self.source,
            "band_names": list(self.band_names),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class RasterImage:
    """A validated pixel array plus spatial metadata."""

    data: np.ndarray
    metadata: SpatialMetadata = field(default_factory=SpatialMetadata)

    def __post_init__(self) -> None:
        validate_image_array(self.data)
        self.metadata.validate()

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def channels(self) -> int:
        return 1 if self.data.ndim == 2 else int(self.data.shape[2])

    @property
    def valid_mask(self) -> np.ndarray:
        return extract_valid_mask(self.data, self.metadata.nodata)

    def with_metadata(self, metadata: SpatialMetadata) -> "RasterImage":
        return RasterImage(self.data, metadata)


def validate_image_array(array: np.ndarray, *, min_size: int = 2) -> None:
    """Validate dimensions, channels and dtype without altering the data."""

    if not isinstance(array, np.ndarray):
        raise ImageValidationError("Image data must be a NumPy array.")
    if array.ndim not in (2, 3):
        raise ImageValidationError("Image must be 2D (grayscale) or 3D (channels).")
    if array.ndim == 3 and not 1 <= array.shape[2] <= 16:
        raise ImageValidationError("Unsupported channel count.")
    if array.shape[0] < min_size or array.shape[1] < min_size:
        raise ImageValidationError("Image is smaller than the minimum accepted size.")
    if array.size == 0:
        raise ImageValidationError("Image is empty.")
    if not np.issubdtype(array.dtype, np.number):
        raise ImageValidationError("Image dtype must be numeric.")
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ImageValidationError("Complex-valued images are not supported.")


def extract_valid_mask(
    array: np.ndarray,
    nodata: float | None = None,
    *,
    additional_invalid: Sequence[np.ndarray] | None = None,
) -> np.ndarray:
    """Return a boolean mask of finite pixels that are not declared nodata."""

    finite = np.isfinite(array)
    if array.ndim == 3:
        finite = np.all(finite, axis=2)
    valid = finite
    if nodata is not None:
        if array.ndim == 3:
            valid = valid & ~np.any(np.isclose(array, nodata), axis=2)
        else:
            valid = valid & ~np.isclose(array, nodata)
    for extra in additional_invalid or ():
        if extra.shape != valid.shape:
            raise ImageValidationError("Invalid-data masks must match the image shape.")
        valid = valid & ~extra.astype(bool)
    return valid.astype(bool)


def _to_float32(array: np.ndarray) -> np.ndarray:
    return np.asarray(array, dtype=np.float32)


def to_uint8(
    array: np.ndarray,
    valid_mask: np.ndarray | None = None,
    *,
    percentiles: tuple[float, float] = (2.0, 98.0),
) -> np.ndarray:
    """Normalize an array to uint8 using robust percentiles.

    Invalid pixels are assigned zero. A constant valid region becomes zeros.
    """

    normalized, valid = normalize_image(array, valid_mask, percentiles=percentiles)
    gray_or_channels = np.clip(normalized, 0.0, 1.0)
    out = np.round(gray_or_channels * 255.0).astype(np.uint8)
    if out.ndim == 2:
        out[~valid] = 0
    else:
        out[~valid] = 0
    return out


def normalize_image(
    array: np.ndarray,
    valid_mask: np.ndarray | None = None,
    *,
    percentiles: tuple[float, float] = (2.0, 98.0),
    nodata: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Robustly normalize an image to ``[0, 1]`` without losing invalid data.

    Returns ``(normalized_float32, valid_mask)``. Percentiles are computed only
    over valid pixels. If no valid pixels exist, the array is zero and the mask
    is all ``False``.
    """

    validate_image_array(array)
    data = _to_float32(array)
    if valid_mask is None:
        valid = extract_valid_mask(array, nodata)
    else:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != data.shape[:2]:
            raise ImageValidationError("Valid mask shape must match the image height and width.")
        valid = valid & extract_valid_mask(array, nodata)

    if not np.any(valid):
        return np.zeros_like(data, dtype=np.float32), valid

    low, high = percentiles
    if not (0.0 <= low < high <= 100.0):
        raise ImageValidationError("Percentiles must satisfy 0 <= low < high <= 100.")

    if data.ndim == 3:
        sample = data[valid]
        vmin = float(np.percentile(sample, low))
        vmax = float(np.percentile(sample, high))
    else:
        sample = data[valid]
        vmin = float(np.percentile(sample, low))
        vmax = float(np.percentile(sample, high))

    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        normalized = np.zeros_like(data, dtype=np.float32)
    else:
        normalized = (data - vmin) / (vmax - vmin)
        normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)
    normalized = np.asarray(normalized, dtype=np.float32)
    if normalized.ndim == 2:
        normalized[~valid] = 0.0
    else:
        normalized[~valid] = 0.0
    return normalized, valid


def _read_with_opencv(path: Path) -> RasterImage:
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ImageValidationError(f"OpenCV could not read image: {path}")
    if raw.ndim == 3 and raw.shape[2] == 3:
        raw = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
    elif raw.ndim == 3 and raw.shape[2] == 4:
        raw = cv2.cvtColor(raw, cv2.COLOR_BGRA2RGBA)
    metadata = SpatialMetadata(source=str(path))
    return RasterImage(raw, metadata)


def load_image(path: str | Path, *, metadata: SpatialMetadata | None = None) -> RasterImage:
    """Load a PNG/JPEG/TIFF image using OpenCV.

    Georeferenced GeoTIFFs should use :func:`load_raster` so CRS and affine
    transform are preserved.
    """

    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    image = _read_with_opencv(image_path)
    if metadata is not None:
        merged = replace(metadata, source=metadata.source or str(image_path))
        return image.with_metadata(merged)
    return image


def _rasterio_transform_to_tuple(transform: Any) -> tuple[float, float, float, float, float, float]:
    return (
        float(transform.a),
        float(transform.b),
        float(transform.c),
        float(transform.d),
        float(transform.e),
        float(transform.f),
    )


def _tuple_to_rasterio_transform(values: tuple[float, ...]) -> Any:
    from affine import Affine

    return Affine(*values)


def load_raster(
    path: str | Path,
    *,
    band: int | None = None,
    acquisition_datetime: str | None = None,
    source: str | None = None,
) -> RasterImage:
    """Load a georeferenced raster with Rasterio, preserving geospatial data.

    With ``band=None`` all bands are stacked as ``(H, W, C)``. With an explicit
    band index the result is 2D. Nodata remains in the array; use
    ``RasterImage.valid_mask`` to exclude it.
    """

    raster_path = Path(path)
    if not raster_path.exists():
        raise FileNotFoundError(raster_path)

    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("Rasterio is required to load georeferenced rasters.") from exc

    with rasterio.open(raster_path) as dataset:
        if band is not None:
            if not 1 <= band <= dataset.count:
                raise ImageValidationError(f"Band {band} is outside 1..{dataset.count}.")
            data = dataset.read(band)
            band_names = (dataset.descriptions[band - 1] or f"band_{band}",)
        else:
            data = dataset.read()
            if data.shape[0] == 1:
                data = data[0]
            else:
                data = np.moveaxis(data, 0, -1)
            band_names = tuple(
                description or f"band_{index + 1}"
                for index, description in enumerate(dataset.descriptions)
                if band is None
            )
        transform = dataset.transform
        resolution = (abs(float(transform.a)), abs(float(transform.e)))
        metadata = SpatialMetadata(
            crs=dataset.crs.to_string() if dataset.crs else None,
            transform=_rasterio_transform_to_tuple(transform),
            resolution=resolution,
            nodata=float(dataset.nodata) if dataset.nodata is not None else None,
            acquisition_datetime=acquisition_datetime,
            source=source or str(raster_path),
            band_names=band_names,
        )
    return RasterImage(data, metadata)


def crop_image(
    image: RasterImage,
    row_start: int,
    row_stop: int,
    col_start: int,
    col_stop: int,
) -> RasterImage:
    """Crop an image and update the affine transform for the new origin."""

    height, width = image.height, image.width
    if not (0 <= row_start < row_stop <= height):
        raise ImageValidationError("Invalid row crop bounds.")
    if not (0 <= col_start < col_stop <= width):
        raise ImageValidationError("Invalid column crop bounds.")
    cropped = image.data[row_start:row_stop, col_start:col_stop]
    metadata = image.metadata
    transform = metadata.transform
    if transform is not None:
        a, b, c, d, e, f = transform
        new_transform = (
            a,
            b,
            c + a * col_start + b * row_start,
            d,
            e,
            f + d * col_start + e * row_start,
        )
        extra = dict(metadata.extra)
        extra["crop_pixels"] = {
            "row_start": row_start,
            "row_stop": row_stop,
            "col_start": col_start,
            "col_stop": col_stop,
        }
        metadata = replace(metadata, transform=new_transform, extra=extra)
    return RasterImage(cropped, metadata)


def save_image(
    path: str | Path,
    image: RasterImage | np.ndarray,
    *,
    normalize: bool = True,
) -> Path:
    """Save an image for inspection. This does not preserve CRS metadata.

    Use :func:`save_raster` when georeferencing must be retained.
    """

    if isinstance(image, RasterImage):
        array = image.data
    else:
        array = image
    validate_image_array(array)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if np.issubdtype(array.dtype, np.floating):
        if normalize:
            array, _ = normalize_image(array)
            array = np.round(array * 255).astype(np.uint8)
        else:
            array = np.clip(array, 0, 255).astype(np.uint8)
    elif array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    if array.ndim == 3 and array.shape[2] == 3:
        array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
    success = cv2.imwrite(str(output), array)
    if not success:
        raise ImageValidationError(f"OpenCV could not write image: {output}")
    return output


def save_raster(path: str | Path, image: RasterImage) -> Path:
    """Write a GeoTIFF, retaining CRS, transform and nodata."""

    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("Rasterio is required to write georeferenced rasters.") from exc

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = image.data
    if data.ndim == 3:
        write_data = np.moveaxis(data, -1, 0)
        count = write_data.shape[0]
    else:
        write_data = data[np.newaxis, ...]
        count = 1
    transform = image.metadata.transform
    if transform is None:
        raise ImageValidationError("Cannot write a georeferenced raster without an affine transform.")
    profile = {
        "driver": "GTiff",
        "height": image.height,
        "width": image.width,
        "count": count,
        "dtype": write_data.dtype,
        "crs": image.metadata.crs,
        "transform": _tuple_to_rasterio_transform(transform),
        "nodata": image.metadata.nodata,
    }
    with rasterio.open(output, "w", **profile) as dataset:
        dataset.write(write_data)
        for index, name in enumerate(image.metadata.band_names, start=1):
            if index <= count:
                dataset.set_band_description(index, name)
    return output


def crs_linear_units(crs: str | None) -> str | None:
    """Return the linear unit name for a projected CRS, or ``degrees``."""

    if not crs:
        return None
    try:
        from rasterio.crs import CRS

        try:
            parsed = CRS.from_string(crs)
        except Exception:
            parsed = CRS.from_wkt(crs)
    except Exception:
        return None
    if parsed.is_geographic:
        return "degrees"
    try:
        return parsed.linear_units or "unknown"
    except Exception:
        return "unknown"


def checksum_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    import hashlib

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pds3_label(path: str | Path) -> dict[str, str]:
    """Parse simple ``KEY = VALUE`` fields from a PDS3 label.

    Repeated keys keep the first value. Nested objects are parsed as flat keys.
    This is a metadata reader, not a complete PDS3 validator.
    """

    import re

    label_path = Path(path)
    if not label_path.exists():
        raise FileNotFoundError(label_path)
    text = label_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        if not key or key.startswith("END_"):
            continue
        cleaned = value.strip().rstrip(",").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1]
        if cleaned and key not in values:
            values[key] = cleaned
    return values


def acquisition_datetime_from_label(label: Mapping[str, str]) -> str | None:
    for key in ("START_TIME", "OBSERVATION_START_TIME", "IMAGE_TIME", "STOP_TIME"):
        value = label.get(key)
        if value:
            return value
    return None


def load_pds_image(
    path: str | Path,
    *,
    label_path: str | Path | None = None,
    band: int | None = None,
) -> RasterImage:
    """Load a PDS image or JP2 through Rasterio and attach simple label fields."""

    image = load_raster(path, band=band)
    if label_path is None:
        return image
    label = parse_pds3_label(label_path)
    extra = dict(image.metadata.extra)
    extra["pds_label"] = label
    metadata = replace(
        image.metadata,
        acquisition_datetime=acquisition_datetime_from_label(label),
        extra=extra,
    )
    return image.with_metadata(metadata)
