"""Shared fixtures and helpers for the Web Algebra test suite.

Test bodies under tests/unit/ derive from formal-semantics.md only and must not
read implementation modules. This file is harness, not test cases — wiring up
the registry, fixtures, and helpers may use code knowledge.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import rdflib

import web_algebra.operations
from web_algebra.json_result import JSONResult
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses
from web_algebra.operation import Operation


@pytest.fixture(scope="session", autouse=True)
def _register_operations() -> None:
    """Discover and register every Operation subclass once per session."""
    for cls in list_operation_subclasses(web_algebra.operations, Operation):
        Operation.register(cls)


@pytest.fixture
def settings() -> LinkedDataHubSettings:
    """Bare settings, no auth — covers offline unit and most integration cases."""
    return LinkedDataHubSettings()


@pytest.fixture
def settings_with_auth() -> LinkedDataHubSettings:
    """Settings with cert auth from env. Skip if creds aren't provided."""
    cert_pem_path = os.getenv("CERT_PEM_PATH")
    cert_password = os.getenv("CERT_PASSWORD")
    if not (cert_pem_path and cert_password):
        pytest.skip("CERT_PEM_PATH and CERT_PASSWORD env vars required")
    return LinkedDataHubSettings(
        cert_pem_path=cert_pem_path,
        cert_password=cert_password,
    )


@pytest.fixture
def fixture_dir() -> Path:
    """Absolute path to tests/fixtures/, independent of pytest's cwd."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def run_op(settings: LinkedDataHubSettings):
    """Convenience wrapper around Operation.process_json for integration tests."""

    def _run(json_data: Any, *, with_settings: LinkedDataHubSettings | None = None) -> Any:
        return Operation.process_json(with_settings or settings, json_data)

    return _run


def result_to_json(result: Any) -> Any:
    """Convert a Web Algebra result to JSON-comparable Python data.

    Mirrors the helper from the original tests/test_web_algebra.py so existing
    fixture `expected` payloads keep working.
    """
    if isinstance(result, JSONResult):
        return result.to_json()
    if isinstance(result, (rdflib.URIRef, rdflib.Literal, rdflib.BNode)):
        return str(result)
    if isinstance(result, rdflib.Graph):
        try:
            jsonld_str = result.serialize(format="json-ld")
            if isinstance(jsonld_str, bytes):
                jsonld_str = jsonld_str.decode("utf-8")
            return json.loads(jsonld_str)
        except Exception:
            return {
                "error": "Could not serialize to JSON-LD",
                "turtle": result.serialize(format="turtle"),
            }
    if isinstance(result, list):
        return [result_to_json(item) for item in result]
    if isinstance(result, dict):
        return {k: result_to_json(v) for k, v in result.items()}
    return str(result)


@pytest.fixture
def to_json():
    """Expose result_to_json as a fixture for tests that prefer DI."""
    return result_to_json


def pytest_collection_modifyitems(config, items) -> None:
    """Auto-tag tests under tests/unit/ as `unit`, tests/integration/ as `integration`."""
    root = Path(__file__).parent
    unit_dir = (root / "unit").resolve()
    integration_dir = (root / "integration").resolve()
    for item in items:
        item_path = Path(str(item.fspath)).resolve()
        try:
            item_path.relative_to(unit_dir)
            item.add_marker(pytest.mark.unit)
            continue
        except ValueError:
            pass
        try:
            item_path.relative_to(integration_dir)
            item.add_marker(pytest.mark.integration)
        except ValueError:
            pass
