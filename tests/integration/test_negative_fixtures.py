"""W3C-style NegativeExecutionTest runner.

Each `tests/fixtures/negative/*.json` file follows the shape:

    {"name": "...", "operation": {"@op": ..., "args": {...}},
     "expected_error": "TypeError"}

`Operation.process_json` is expected to raise a matching exception with a
non-empty message.
"""

from __future__ import annotations

import builtins
import json
import os
from pathlib import Path

import pytest

from web_algebra.main import LinkedDataHubSettings
from web_algebra.operation import Operation


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "negative"


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


def _resolve_exception(name: str) -> type[BaseException]:
    if not name:
        return Exception
    candidate = getattr(builtins, name, None)
    if isinstance(candidate, type) and issubclass(candidate, BaseException):
        return candidate
    return Exception


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURES.glob("*.json")),
    ids=lambda p: p.name,
)
def test_negative_fixture(fixture_path: Path) -> None:
    if _needs_ldh(fixture_path.name) and not (
        os.getenv("CERT_PEM_PATH") and os.getenv("CERT_PASSWORD")
    ):
        pytest.skip(
            f"{fixture_path.name} needs CERT_PEM_PATH and CERT_PASSWORD"
        )

    with fixture_path.open() as fh:
        payload = json.load(fh)

    name = payload.get("name", fixture_path.name)
    expected_exc = _resolve_exception(payload.get("expected_error", "Exception"))
    settings = _settings_for(fixture_path.name)

    with pytest.raises(expected_exc) as exc_info:
        Operation.process_json(settings, payload["operation"])

    assert str(exc_info.value), f"Test {name} should have non-empty error message"
