"""Download public stage 4 inputs once, cache locally, and record scoped hashes."""

from pathlib import Path
from urllib.request import Request, urlopen
import hashlib, json, argparse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/science"
CACHE.mkdir(exist_ok=True)
URLS = {
    "dust-my36.nc": "https://www-mars.lmd.jussieu.fr/mars/dust_climatology/dataset_v2/griddedcdod_MY36_v2-5.nc",
    "hrsc-pds3.lbl": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2_pds3.lbl",
    "hrsc-isis.lbl": "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.lbl",
}


def main():
    registry = CACHE / "downloads.json"
    previous = json.loads(registry.read_text()) if registry.exists() else {}
    records = dict(previous)
    for name, url in URLS.items():
        destination = CACHE / name
        if not destination.exists():
            partial = destination.with_suffix(destination.suffix + ".partial")
            with (
                urlopen(
                    Request(
                        url,
                        headers={
                            "User-Agent": "Bridges-Mavors-scientific-preparation/1.0"
                        },
                    ),
                    timeout=60,
                ) as response,
                partial.open("wb") as file,
            ):
                while block := response.read(1024 * 1024):
                    file.write(block)
            partial.replace(destination)
        digest = hashlib.file_digest(destination.open("rb"), "sha256").hexdigest()
        if name in previous and digest != previous[name]["sha256"]:
            raise ValueError(f"Integrity mismatch: {name}")
        records[name] = {
            "url": url,
            "sha256": digest,
            "bytes": destination.stat().st_size,
            "access_date": "2026-11-15",
            "hash_scope": "entire downloaded file; initial hash is a reproducibility fingerprint, not provider-signed checksum",
        }
        registry.write_text(json.dumps(records, indent=2))
        print(name, records[name]["bytes"], flush=True)


if __name__ == "__main__":
    main()
