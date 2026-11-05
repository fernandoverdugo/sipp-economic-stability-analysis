import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import requests

from assets import load_assets


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
METADATA = ROOT / "data" / "metadata"
CHECKSUMS = METADATA / "checksums.json"


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(asset, overwrite=False):
    destination = RAW / asset["local_name"]
    if destination.exists() and not overwrite:
        return manifest_row(asset, destination, "existing")

    RAW.mkdir(parents=True, exist_ok=True)
    request = requests.get(
        asset["url"],
        stream=True,
        timeout=120,
        headers={"User-Agent": "sipp-economic-stability-analysis/0.2"},
    )
    request.raise_for_status()

    digest = hashlib.sha256()
    size = 0
    with destination.open("wb") as handle:
        for chunk in request.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)

    if destination.suffix == ".zip":
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"Corrupt ZIP asset: {asset['asset_id']}")

    row = manifest_row(asset, destination, "downloaded")
    row["sha256"] = digest.hexdigest()
    row["bytes"] = size
    return row


def manifest_row(asset, destination, status):
    return {
        "asset_id": asset["asset_id"],
        "survey_year": asset["survey_year"],
        "asset_type": asset["asset_type"],
        "url": asset["url"],
        "local_name": asset["local_name"],
        "status": status,
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["metadata", "all"],
        default="metadata",
        help="metadata skips assets marked large; all downloads every registered asset.",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    registry = load_assets()
    selected = [
        asset
        for asset in registry["assets"]
        if args.mode == "all" or not asset["large"]
    ]

    rows = [download(asset, overwrite=args.overwrite) for asset in selected]
    METADATA.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text(
        json.dumps(
            {
                "registry_version": registry["version"],
                "mode": args.mode,
                "assets": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(CHECKSUMS.relative_to(ROOT))


if __name__ == "__main__":
    main()
