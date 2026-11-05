import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

from registry import load_registry


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "metadata" / "discovered_assets.json"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href is not None:
            self.links.append(
                {
                    "href": self.current_href,
                    "text": " ".join("".join(self.current_text).split()),
                }
            )
            self.current_href = None
            self.current_text = []


def classify_asset(text, href):
    label = f"{text} {href}".lower()

    if "longitudinal replicate" in label and "2-year" in label:
        return "two_year_longitudinal_replicate_weights"
    if "longitudinal weight" in label and "2-year" in label:
        return "two_year_longitudinal_weights"
    if "data dictionary" in label:
        return "data_dictionary"
    if (
        "pipe-delimited" in label
        and "replicate" not in label
        and "longitudinal" not in label
        and href.lower().endswith(".zip")
    ):
        return "primary_data"
    return None


def discover_source(source):
    response = requests.get(
        source["url"],
        timeout=30,
        headers={"User-Agent": "sipp-economic-stability-analysis/0.1"},
    )
    response.raise_for_status()

    parser = LinkParser()
    parser.feed(response.text)

    assets = []
    seen = set()

    for link in parser.links:
        asset_type = classify_asset(link["text"], link["href"])
        if not asset_type:
            continue

        url = urljoin(source["url"], link["href"])
        key = (asset_type, url)
        if key in seen:
            continue
        seen.add(key)

        assets.append(
            {
                "asset_type": asset_type,
                "label": link["text"],
                "url": url,
            }
        )

    return {
        "source_id": source["source_id"],
        "survey_year": source["survey_year"],
        "release_page": source["url"],
        "assets": assets,
    }


def main():
    registry = load_registry()
    discovered = {
        "registry_version": registry["version"],
        "sources": [discover_source(source) for source in registry["sources"]],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(discovered, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
