import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validate_project import markdown_paths


def test_markdown_paths_filters_external_links():
    text = """
[Local](docs/file.md)
![Figure](docs/figure.svg)
[Web](https://example.com)
[Anchor](#section)
"""
    assert markdown_paths(text) == [
        "docs/file.md",
        "docs/figure.svg",
    ]
