"""Spec: formal-semantics.md "STRUUID - Generate random UUID string"
Abstract: () → Literal
Python:   def execute(self) -> Literal
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from web_algebra.operation import Operation


class TestSTRUUIDPure:
    def test_returns_literal(self, settings):
        op = Operation.get("STRUUID")(settings=settings)
        result = op.execute()
        assert isinstance(result, Literal)

    def test_two_calls_differ(self, settings):
        op = Operation.get("STRUUID")(settings=settings)
        a = op.execute()
        b = op.execute()
        assert str(a) != str(b)

    @pytest.mark.skip(reason="UNCLEAR(spec): UUID format (UUID4? hyphenated? case?) not specified")
    def test_uuid_format(self, settings):
        pass


class TestSTRUUIDJson:
    def test_empty_args_via_json(self, settings):
        # () → Literal — JSON layer should accept an empty args dict
        op = Operation.get("STRUUID")(settings=settings)
        result = op.execute_json({})
        assert isinstance(result, Literal)
