"""W3C-style PositiveExecutionTest runner.

Each `tests/fixtures/positive/*.json` file follows the shape:

    {"name": "...", "operation": {"@op": ..., "args": {...}}, "expected": ...}

The fixture's "expected" payload is compared (via the JSON-comparable form
returned by `result_to_json`) against the result of `Operation.process_json`.

Fixtures whose filename starts with `ldh-` or contains `linkeddatahub` need
LinkedDataHub credentials and are skipped without `CERT_PEM_PATH` and
`CERT_PASSWORD`. External-service network failures are converted to xfail.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from web_algebra.main import LinkedDataHubSettings
from web_algebra.operation import Operation

from tests.conftest import result_to_json


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "positive"
EXTERNAL_SERVICE_KEYWORDS = ("dbpedia", "wikidata", "external")
NETWORK_ERROR_FRAGMENTS = ("timeout", "connection", "network", "http", "403", "404")


def _needs_ldh(name: str) -> bool:
    lower = name.lower()
    return "ldh-" in lower or "linkeddatahub" in lower


def _settings_for(name: str) -> LinkedDataHubSettings:
    if _needs_ldh(name):
        return LinkedDataHubSettings(
            cert_pem_path=os.getenv("CERT_PEM_PATH"),
            cert_password=os.getenv("CERT_PASSWORD"),
        )
    return LinkedDataHubSettings()


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURES.glob("*.json")),
    ids=lambda p: p.name,
)
def test_positive_fixture(fixture_path: Path) -> None:
    if _needs_ldh(fixture_path.name) and not (
        os.getenv("CERT_PEM_PATH") and os.getenv("CERT_PASSWORD")
    ):
        pytest.skip(
            f"{fixture_path.name} needs CERT_PEM_PATH and CERT_PASSWORD"
        )

    with fixture_path.open() as fh:
        payload = json.load(fh)

    name = payload.get("name", fixture_path.name)
    settings = _settings_for(fixture_path.name)

    try:
        result = Operation.process_json(settings, payload["operation"])
    except Exception as exc:
        lower_name = fixture_path.name.lower()
        lower_err = str(exc).lower()
        if any(svc in lower_name for svc in EXTERNAL_SERVICE_KEYWORDS) and any(
            frag in lower_err for frag in NETWORK_ERROR_FRAGMENTS
        ):
            pytest.xfail(f"External-service test {name} failed: {exc}")
        raise

    if "expected" in payload:
        actual_json = result_to_json(result)
        expected_json = payload["expected"]
        assert actual_json == expected_json, (
            f"Test {name} output mismatch:\n"
            f"Expected: {json.dumps(expected_json, indent=2)}\n"
            f"Actual:   {json.dumps(actual_json, indent=2)}"
        )
