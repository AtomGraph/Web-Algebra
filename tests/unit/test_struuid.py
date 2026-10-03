"""Spec: formal-semantics.md "STRUUID - Generate random UUID string"
Abstract: () → Literal
Python:   def execute(self) -> Literal
"""

from __future__ import annotations

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

    def test_uuid_format(self, settings):
        # §4.2: simple literal per `simple literal STRUUID()`, holding an
        # RFC 4122 version-4 UUID in lowercase hyphenated form
        import re

        op = Operation.get("STRUUID")(settings=settings)
        result = op.execute()
        assert result.datatype is None and result.language is None
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            str(result),
        )


class TestSTRUUIDJson:
    def test_empty_args_via_json(self, settings):
        # () → Literal — JSON layer should accept an empty args dict
        op = Operation.get("STRUUID")(settings=settings)
        result = op.execute_json({})
        assert isinstance(result, Literal)
