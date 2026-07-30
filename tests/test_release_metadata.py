from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

from hayate_fetch import __version__

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_HOME = "https://hayatepy.dev/"
PUBLIC_PACKAGE_HOME = "https://hayatepy.dev/ecosystem/#hayate-fetch"
PUBLIC_COMPATIBILITY = "https://hayatepy.dev/evidence/compatibility/"
SUPERSEDED_DOCS_PREFIX = "https://github.com/hayatepy/.github/blob/main/docs/"


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_public_version_matches_distribution_metadata() -> None:
    project_version = _project()["version"]

    assert __version__ == project_version == version("hayate-fetch")


def test_public_discovery_uses_the_canonical_site() -> None:
    project = _project()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert project["urls"]["Homepage"] == PUBLIC_PACKAGE_HOME
    assert f"[Start here]({PUBLIC_HOME})" in readme
    assert f"[Tested compatibility]({PUBLIC_COMPATIBILITY})" in readme
    assert SUPERSEDED_DOCS_PREFIX not in readme
