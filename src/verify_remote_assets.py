import json
from pathlib import Path

import requests

from assets import load_assets


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "metadata" / "remote_asset_status.json"


def probe(asset):
    response = requests.get(
        asset["url"],
        headers={
            "User-Agent": "sipp-economic-stability-analysis/0.2",
            "Range": "bytes=0-0",
        },
        stream=True,
        timeout=45,
        allow_redirects=True,
    )
    response.raise_for_status()
    first = next(response.iter_content(chunk_size=1), b"")
    return {
        "asset_id": asset["asset_id"],
        "url": asset["url"],
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "content_length": response.headers.get("content-length"),
        "accept_ranges": response.headers.get("accept-ranges"),
        "first_byte_received": bool(first),
    }


def main():
    registry = load_assets()
    rows = [probe(asset) for asset in registry["assets"]]
    if not all(row["first_byte_received"] for row in rows):
        raise RuntimeError("One or more Census assets did not return data.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {"registry_version": registry["version"], "assets": rows},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
