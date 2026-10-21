"""What a release publishes agrees with itself: the MCP Registry entry
(server.json) names the package's version and the server name the README
carries for the registry's ownership check, and CHANGELOG.md has the notes
the GitHub Release is made from."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from release_notes import notes  # noqa: E402

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = None

SERVER = json.loads((ROOT / "server.json").read_text())


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    if tomllib:
        return tomllib.loads(text)["project"]["version"]
    return re.search(r'^version = "([^"]+)"', text, re.M).group(1)


def test_server_json_has_the_package_version():
    assert SERVER["version"] == project_version()
    assert [p["version"] for p in SERVER["packages"]] == [project_version()]


def test_server_json_names_the_pypi_package():
    assert [p["identifier"] for p in SERVER["packages"] if p["registryType"] == "pypi"] == ["web-algebra"]


def test_readme_carries_the_server_name():
    assert f"mcp-name: {SERVER['name']} " in (ROOT / "README.md").read_text().replace("-->", " -->")


def test_changelog_has_the_versions_notes():
    assert notes(project_version(), (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")).strip()
