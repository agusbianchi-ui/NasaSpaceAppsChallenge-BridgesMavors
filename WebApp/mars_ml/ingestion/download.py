"""Controlled, manifest-driven downloads.

Downloads require an explicit manifest entry, an allowlisted host, a declared
size and an optional SHA-256. A dry-run is the default. No credentials are read
or stored.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from mars_ml.ingestion.catalog import DatasetFile, DatasetRecord

DEFAULT_ALLOWED_HOSTS = frozenset(
    {
        "data.mendeley.com",
        "figshare.com",
        "ndownloader.figshare.com",
        "hirise-pds.lpl.arizona.edu",
        "pds-imaging.jpl.nasa.gov",
    }
)
DEFAULT_MAX_TOTAL_BYTES = 300 * 1024 * 1024


class DownloadError(RuntimeError):
    """Raised when a download plan violates the safety rules."""


@dataclass(frozen=True)
class DownloadItem:
    dataset_id: str
    name: str
    url: str
    size_bytes: int
    sha256: str | None
    relative_path: str
    role: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "relative_path": self.relative_path,
            "role": self.role,
        }


@dataclass(frozen=True)
class DownloadPlan:
    items: tuple[DownloadItem, ...]
    total_bytes: int
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_count": len(self.items),
            "total_bytes": self.total_bytes,
            "dry_run": self.dry_run,
            "items": [item.as_dict() for item in self.items],
        }


@dataclass(frozen=True)
class DownloadResult:
    item: DownloadItem
    status: str
    path: str | None = None
    bytes_written: int = 0
    sha256: str | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.item.dataset_id,
            "name": self.item.name,
            "status": self.status,
            "path": self.path,
            "bytes_written": self.bytes_written,
            "sha256": self.sha256,
            "message": self.message,
        }


def _host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DownloadError(f"Invalid download URL: {url}")
    return parsed.hostname.lower()


def plan_downloads(
    records: Iterable[DatasetRecord],
    *,
    dataset_ids: Iterable[str] | None = None,
    allowed_hosts: Iterable[str] | None = None,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    selected_only: bool = True,
) -> DownloadPlan:
    selected_ids = set(dataset_ids) if dataset_ids is not None else None
    hosts = {host.lower() for host in (allowed_hosts or DEFAULT_ALLOWED_HOSTS)}
    items: list[DownloadItem] = []
    for record in records:
        if selected_ids is not None and record.dataset_id not in selected_ids:
            continue
        files: Iterable[DatasetFile] = record.selected_files if selected_only else record.files
        for entry in files:
            if entry.url is None:
                raise DownloadError(
                    f"{record.dataset_id}/{entry.name}: no download URL in the manifest."
                )
            host = _host(entry.url)
            if host not in hosts:
                raise DownloadError(
                    f"{record.dataset_id}/{entry.name}: host {host!r} is not allowlisted."
                )
            items.append(
                DownloadItem(
                    dataset_id=record.dataset_id,
                    name=entry.name,
                    url=entry.url,
                    size_bytes=entry.size_bytes,
                    sha256=entry.sha256,
                    relative_path=f"{record.dataset_id}/{entry.name}",
                    role=entry.role,
                )
            )
    if not items:
        raise DownloadError("No downloadable items were selected.")
    total = sum(item.size_bytes for item in items)
    if total > max_total_bytes:
        raise DownloadError(
            f"Plan requires {total} bytes, above the configured limit of {max_total_bytes} bytes."
        )
    return DownloadPlan(items=tuple(items), total_bytes=total, dry_run=True)


def _hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _default_opener(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)


def download_plan(
    plan: DownloadPlan,
    destination: str | Path,
    *,
    dry_run: bool = True,
    timeout: float = 60.0,
    opener: Callable[[urllib.request.Request, float], Any] | None = None,
    max_bytes: int | None = None,
) -> tuple[DownloadResult, ...]:
    if max_bytes is not None and plan.total_bytes > max_bytes:
        raise DownloadError(
            f"Plan requires {plan.total_bytes} bytes, above the configured limit of {max_bytes} bytes."
        )
    output_root = Path(destination)
    results: list[DownloadResult] = []
    if dry_run:
        for item in plan.items:
            results.append(
                DownloadResult(
                    item=item,
                    status="planned",
                    path=str((output_root / item.relative_path).resolve()),
                    bytes_written=0,
                )
            )
        return tuple(results)
    output_root.mkdir(parents=True, exist_ok=True)
    open_url = opener or _default_opener
    for item in plan.items:
        if item.url is None:
            raise DownloadError(f"{item.name}: no URL.")
        target = output_root / item.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(
            item.url,
            headers={"User-Agent": "mars-ml/0.1 manifest-download"},
        )
        try:
            with open_url(request, timeout) as response, partial.open("wb") as handle:
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > item.size_bytes:
                    raise DownloadError(
                        f"{item.name}: server size {content_length} exceeds manifest size "
                        f"{item.size_bytes}."
                    )
                written = 0
                while chunk := response.read(1024 * 1024):
                    written += len(chunk)
                    if written > item.size_bytes:
                        raise DownloadError(
                            f"{item.name}: response exceeds declared size {item.size_bytes}."
                        )
                    handle.write(chunk)
        except DownloadError:
            partial.unlink(missing_ok=True)
            raise
        except Exception as exc:
            partial.unlink(missing_ok=True)
            raise DownloadError(f"{item.name}: download failed: {exc}") from exc
        if written != item.size_bytes:
            partial.unlink(missing_ok=True)
            raise DownloadError(
                f"{item.name}: wrote {written} bytes, expected {item.size_bytes}."
            )
        digest = _hash_file(partial)
        if item.sha256 is not None and digest != item.sha256.lower():
            partial.unlink(missing_ok=True)
            raise DownloadError(
                f"{item.name}: SHA-256 mismatch; expected {item.sha256}, got {digest}."
            )
        shutil.move(str(partial), str(target))
        results.append(
            DownloadResult(
                item=item,
                status="downloaded",
                path=str(target.resolve()),
                bytes_written=written,
                sha256=digest,
            )
        )
    return tuple(results)
